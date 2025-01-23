import asyncio
import logging
import time
from typing import Dict, List
from typing import Any, Callable, Dict, List, Tuple, Optional

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
        # For each bucket, keep track of current function index
        self.bucket_function_indices: List[int] = []

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
        When functions fail, the caller switches to the next function in the bucket, while marking the failed function!

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

        function_args = function_args or {}
        function_kwargs = function_kwargs or {}
        for func_id, args in function_args.items():
            if func_id in self.function_models:
                self.function_models[func_id].args = args
        for func_id, kwargs in function_kwargs.items():
            if func_id in self.function_models:
                self.function_models[func_id].kwargs = kwargs

        self.buckets = buckets
        if not self.bucket_function_indices or len(self.bucket_function_indices) != len(buckets):
            self.bucket_function_indices = [0] * len(self.buckets)

        selected_functions = []
        for bucket_idx, bucket in enumerate(self.buckets):
            func_model = self._select_function(bucket_idx)
            selected_functions.append((bucket_idx, func_model))

        tasks = []
        for (bucket_idx, func_model) in selected_functions:
            timeout = self.function_timeouts.get(func_model.id, None)
            coro = self._run_function(func_model, bucket_idx)
            if timeout:
                coro = asyncio.wait_for(coro, timeout=timeout)
            tasks.append(asyncio.create_task(coro))

        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

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

    async def _run_function(self, func_model: FunctionModel, bucket_idx: int):
        """
        Executes a function and handles failures by retrying the next available function in the bucket.
        """
        try:
            result = await func_model.call()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Function {func_model.id} failed with error: {e}")
            await self._handle_failure(func_model, bucket_idx)
            
            # Select the next function and retry if available
            next_func_model = self._select_function(bucket_idx)
            if next_func_model:
                timeout = self.function_timeouts.get(next_func_model.id, None)
                coro = self._run_function(next_func_model, bucket_idx)
                if timeout:
                    coro = asyncio.wait_for(coro, timeout=timeout)
                return await coro
            else:
                logger.error(f"All functions in bucket {bucket_idx} have failed.")
                raise FraceException("No function succeeded in the bucket.")
        else:
            # Reset failure state on success
            func_model.failures = 0
            func_model.backoff = 1.0
            return result

    async def _handle_failure(self, func_model: FunctionModel, bucket_idx: int):
        func_model.failures += 1
        func_model.last_failure_time = time.time()
        func_model.backoff *= 2
        if func_model.failures >= self.max_failures:
            logger.info(f"Switching to next function in bucket {bucket_idx} after {func_model.failures} failures.")
            self._switch_to_next_function(bucket_idx)

    def _switch_to_next_function(self, bucket_idx: int):
        bucket = self.buckets[bucket_idx]
        current_idx = self.bucket_function_indices[bucket_idx]
        next_idx = (current_idx + 1) % len(bucket)
        self.bucket_function_indices[bucket_idx] = next_idx

    def _select_function(self, bucket_idx: int):
        """
        Selects the next function in the bucket that has not exceeded the max_failures threshold.
        Returns None if all functions in the bucket have failed.
        """
        bucket = self.buckets[bucket_idx]
        for idx in range(len(bucket)):
            func_id = bucket[(self.bucket_function_indices[bucket_idx] + idx) % len(bucket)]
            func_model = self.function_models[func_id]
            if func_model.failures < self.max_failures:
                self.bucket_function_indices[bucket_idx] = (self.bucket_function_indices[bucket_idx] + idx) % len(bucket)
                return func_model
        return None  # All functions have failed
