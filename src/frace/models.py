import logging
from pydantic import BaseModel
from typing import Any, Callable, Dict, List, Tuple, Optional

logger = logging.getLogger("frace")

class FunctionModel(BaseModel):
    """
    Represents a function to be called with metadata for resilience.

    :param id: Unique identifier for the function.
    :param func: The callable function.
    :param args: Positional arguments for the function.
    :param kwargs: Keyword arguments for the function.
    :param failures: Count of consecutive failures.
    :param last_failure_time: Timestamp of the last failure.
    :param backoff: Time in seconds to wait before retrying after a failure.
    """
    id: str  # Unique identifier for the function
    func: Callable[..., Any]
    args: Tuple[Any, ...] = ()
    kwargs: Dict[str, Any] = {}
    failures: int = 0
    last_failure_time: Optional[float] = None
    backoff: float = 1.0  # seconds

    async def call(self):
        """
        Calls the associated function asynchronously.

        :return: The result of the function call.
        :raises Exception: Propagates any exception raised by the function.
        """
        logger.debug(f"Calling function {self.id} with args: {self.args}, kwargs: {self.kwargs}")
        return await self.func(*self.args, **self.kwargs)

class FraceException(Exception):
    """
    Custom exception class for Frace.
    """
    pass