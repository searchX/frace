import asyncio
import pytest
from frace import FunctionModel, FraceException

# Get and set logger debug level
import logging
logger = logging.getLogger("frace")
logger.setLevel(logging.DEBUG)

@pytest.mark.asyncio
async def test_function_reactivation(race_caller):
    """Tests if a function is reactivated after initial failures once its failure count resets."""
    
    # Simulate a failing function that recovers on the third attempt
    attempts = {"count": 0}

    async def recoverable_function():
        attempts["count"] += 1
        logger.debug("CALLING RECOVERABLE FUNCTION")
        if attempts["count"] < 4:
            logger.debug("FAILED RECOVERABLE FUNCTION" + str(attempts["count"]))
            raise Exception("Function is failing")
        return "recovered success"
    
    async def simple_function():
        return "success"

    race_caller.register_function(FunctionModel(id="func_recover", func=recoverable_function))
    race_caller.register_function(FunctionModel(id="func1", func=simple_function))

    buckets = [["func_recover", "func1"]]
    result = await race_caller.call_functions(buckets)
    assert result == "success"

    # Check and verify the id is not on timeout (as only once function failed)
    ids_on_timeout = await race_caller.get_ids_on_timeout()
    assert "func_recover" not in ids_on_timeout

    # Call again and now this should put things into timeout
    result = await race_caller.call_functions(buckets)
    assert result == "success"

    # Check and verify the id is on timeout
    ids_on_timeout = await race_caller.get_ids_on_timeout()
    assert "func_recover" in ids_on_timeout

    # check how much time is left for the function to recover
    remaining = await race_caller.get_function_remaining_timeout_in_seconds("func_recover")
   
    # This timeout should be 4+ seconds
    assert remaining > 3.0

    # A call again shouldnt change the timeout
    result = await race_caller.call_functions(buckets)
    assert result == "success"

    remaining_after_call = await race_caller.get_function_remaining_timeout_in_seconds("func_recover")
    assert remaining - remaining_after_call < 0.1

    # Wait for the function to recover
    await asyncio.sleep(remaining_after_call + 0.5)

    # Check if the function is reactivated
    ids_on_timeout = await race_caller.get_ids_on_timeout()
    assert "func_recover" not in ids_on_timeout

    # Now make the function fail again (exponetial backoff applies)
    result = await race_caller.call_functions(buckets)
    assert result == "success"

    # The timeout should be very high now
    remaining_after_call = await race_caller.get_function_remaining_timeout_in_seconds("func_recover")
    assert remaining_after_call > 6.0

    # wait for last call to recover
    await asyncio.sleep(remaining_after_call + 0.5)

    # Retry the function and check if it succeeds
    result = await race_caller.call_functions(buckets)
    assert result == "recovered success"

@pytest.mark.asyncio
async def test_all_functions_fail(race_caller, failing_function_model):
    """Tests if the caller raises an exception when all functions fail."""
    race_caller.register_function(failing_function_model)

    buckets = [["func_fail", "func_fail"]]
    with pytest.raises(FraceException, match="No function succeeded"):
        await race_caller.call_functions(buckets)

# @pytest.mark.asyncio
# async def test_successively_increasing_timeouts