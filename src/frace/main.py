import asyncio
import logging
import time
from typing import Any, Dict, List, Tuple, Optional

from frace.models import FraceException, FunctionModel

logger = logging.getLogger("frace")

class FunctionRaceCaller:
    """
    Manages and calls functions with resilience, switching to alternate functions upon failures.

    :param max_failures: Number of consecutive failures after which to switch functions.
    :param function_timeouts: Mapping of function IDs to their timeouts.
    """

    def __init__(self, max_failures: int = 2, function_timeouts: Dict[str, float] = {}):
        self.function_timeouts = function_timeouts
        self.max_failures = max_failures

        # Map function id to FunctionModel to maintain state across calls
        self.function_models: Dict[str, FunctionModel] = {}
        # Store buckets of function ids
        self.buckets: List[List[str]] = []

    def register_function(self, func_model: FunctionModel):
        """
        Registers a FunctionModel with the caller.

        :param func_model: Instance of FunctionModel to register.
        :type func_model: :class:`frace.models.FunctionModel`
        :return: None
        :rtype: None
        """
        self.function_models[func_model.id] = func_model
        logger.info(f"Registered function {func_model.id}")

    async def call_functions(self, buckets: List[List[str]], function_args: Dict[str, Tuple[Any, ...]] = None, function_kwargs: Dict[str, Dict[str, Any]] = None, function_timeouts: Optional[Dict[str, float]] = None):
        """
        Calls one function from each bucket concurrently and returns the result of the first successful call.
        When functions fail, the caller switches to the next function in the bucket, while marking the failed function.

        :param buckets: List of lists of function IDs to execute concurrently.
        :param function_args: Optional mapping of function IDs to their positional arguments.
        :param function_kwargs: Optional mapping of function IDs to their keyword arguments.
        :param function_timeouts: Optional mapping of function IDs to their timeouts.
        :type buckets: List[List[str]]
        :type function_args: Dict[str, Tuple[Any, ...]]
        :type function_kwargs: Dict[str, Dict[str, Any]]
        :type function_timeouts: Optional[Dict[str, float]]
        :return: The result of the first successfully completed function.
        :raises FraceException: If all functions fail.
        """
        logger.debug("Updating configuration for function calls.")
        if function_timeouts:
            self.function_timeouts.update(function_timeouts)

        # Handle timeouts and failed functions
        await self._resolve_failures()

        function_args = function_args or {}
        function_kwargs = function_kwargs or {}
        for func_id, args in function_args.items():
            if func_id in self.function_models:
                self.function_models[func_id].args = args
        for func_id, kwargs in function_kwargs.items():
            if func_id in self.function_models:
                self.function_models[func_id].kwargs = kwargs

        self.buckets = buckets

        selected_functions = []
        for bucket in self.buckets:
            func_model = self._select_function(bucket)
            if func_model is not None:
                selected_functions.append((func_model, bucket))

        tasks = []
        for func_model, bucket in selected_functions:
            timeout = self.function_timeouts.get(func_model.id, None)
            coro = self._run_function(func_model, bucket)
            if timeout:
                coro = asyncio.wait_for(coro, timeout=timeout)
            tasks.append(asyncio.create_task(coro))

        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        # Resolve pending tasks and dynamically update failed functions
        for task in pending:
            task.cancel()

        for task in done:
            try:
                result = task.result()
                logger.info(f"Function succeeded with result: {result}")
                return result
            except Exception as e:
                logger.error(f"Function failed: {e}")

        raise FraceException("No function succeeded")

    async def get_ids_on_timeout(self):
        """
        Gets all the ids of the functions that have timed out/currently failing and bypassed.

        :return: List of ids of the functions that have timed out/currently failing and bypassed
        :rtype: List[str]
        """
        # Resolve if any function has timed out
        await self._resolve_failures()

        ids = []
        for func_id, func_model in self.function_models.items():
            if func_model.failures >= self.max_failures:
                ids.append(func_id)
        return ids

    async def _run_function(self, func_model: FunctionModel, bucket: List[str]):
        """
        Executes a function and handles failures by retrying the next available function in the bucket.
        """
        try:
            result = await func_model.call()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Function {func_model.id} failed with error: {e}")
            await self._handle_failure(func_model)
                
            # Select the next function and retry if available
            next_func_model = self._select_function(bucket)
            if next_func_model:
                timeout = self.function_timeouts.get(next_func_model.id, None)
                coro = self._run_function(next_func_model, bucket)
                if timeout:
                    coro = asyncio.wait_for(coro, timeout=timeout)
                return await coro
            else:
                logger.error(f"All functions in the bucket have failed.")
                raise FraceException("No function succeeded in the bucket.")
        else:
            # Reset failure state on success
            func_model.failures = 0
            func_model.backoff = 1.0
            return result

    async def _handle_failure(self, func_model: FunctionModel):
        func_model.failures += 1
        func_model.last_failure_time = time.time()
        func_model.backoff *= 2

    async def _resolve_failures(self):
        """
        Updates the state of all failed or timed-out functions to dynamically adjust call behavior.
        """
        current_time = time.time()
        for func_id, func_model in self.function_models.items():
            if func_model.failures >= self.max_failures:
                # Check if the backoff period has elapsed
                if current_time - func_model.last_failure_time > func_model.backoff:
                    logger.info(f"Reactivating function {func_id} after {func_model.failures} failures.")
                    func_model.failures = 0
                    func_model.backoff = 1.0
                else:
                    print("Time remaining for function to be reactivated: ", func_model.backoff - (current_time - func_model.last_failure_time))

    def _select_function(self, bucket: List[str]):
        """
        Selects the first function in the bucket that has not exceeded the max_failures threshold.
        Returns None if all functions in the bucket have failed.
        """
        for func_id in bucket:
            func_model = self.function_models[func_id]
            if func_model.failures < self.max_failures:
                return func_model
        return None  # All functions have failed