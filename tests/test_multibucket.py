import asyncio
import logging
import pytest

from frace import FunctionRaceCaller, FunctionModel

# Adjust the logger to output messages to the console
logger = logging.getLogger("frace")
logger.setLevel(logging.DEBUG)

# Add a console handler if not already present
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

@pytest.fixture
def race_caller():
    return FunctionRaceCaller(max_failures=2)

@pytest.mark.asyncio
async def test_multi_bucket_failover(race_caller):
    """
    Tests FunctionRaceCaller's behavior with multiple buckets and functions.
    It simulates failures in functions and verifies that backup functions are used appropriately.
    """
    
    # Tracking call counts to verify which functions are called
    call_counts = {"func1": 0, "func2": 0, "func3": 0, "func4": 0}

    # Define functions with controlled behaviors
    async def func1():
        call_counts["func1"] += 1
        logger.debug("func1 is called and will fail")
        raise Exception("func1 failed")

    async def func2():
        call_counts["func2"] += 1
        logger.debug("func2 is called and will fail after 0.5 seconds")
        await asyncio.sleep(0.5)
        raise Exception("func2 failed after some time")

    async def func3():
        call_counts["func3"] += 1
        logger.debug("func3 is called and will succeed after 1 second")
        await asyncio.sleep(1)
        return "func3 success"

    async def func4():
        call_counts["func4"] += 1
        logger.debug("func4 is called and will succeed")
        return "func4 success"

    # Register functions
    race_caller.register_function(FunctionModel(id="func1", func=func1))
    race_caller.register_function(FunctionModel(id="func2", func=func2))
    race_caller.register_function(FunctionModel(id="func3", func=func3))
    race_caller.register_function(FunctionModel(id="func4", func=func4))

    # Set up buckets
    buckets = [["func1", "func2"], ["func3", "func4"]]

    # First call: func1 fails immediately, func2 fails after 0.5s, func4 succeeds immediately
    result = await race_caller.call_functions(buckets)
    assert result == "func3 success"

    # Verify that func1 and func2 were called
    assert call_counts["func1"] == 1
    assert call_counts["func2"] == 1
