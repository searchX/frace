import asyncio
import pytest
from frace import FunctionModel, FraceException

@pytest.mark.asyncio
async def test_function_reactivation(race_caller, failing_function_model, simple_function_model):
    """Tests if a function is reactivated after initial failures once its failure count resets."""
    
    # Simulate a failing function that recovers on the third attempt
    attempts = {"count": 0}

    async def recoverable_function():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise Exception("Function is failing")
        return "recovered success"

    recoverable_model = FunctionModel(id="func_recover", func=recoverable_function)
    race_caller.register_function(recoverable_model)
    race_caller.register_function(simple_function_model)

    buckets = [["func_recover", "func1"]]
    result = await race_caller.call_functions(buckets)
    assert result == "success"

    # Check and verify the id is on timeout
    ids_on_timeout = await race_caller.get_ids_on_timeout()
    assert "func_recover" in ids_on_timeout

    # Wait for the function to recover
    await asyncio.sleep(5)

    # Check and verify the id is not on timeout
    ids_on_timeout = await race_caller.get_ids_on_timeout()
    assert "func_recover" not in ids_on_timeout

    # Make two times function fail
    # result = await race_caller.call_functions(buckets)
    # assert result == "success"

    # # Calling again will not succeed as function is bypassed now :o
    # result = await race_caller.call_functions(buckets)
    # assert result == "success"

    # # After 3s the function will be reactivated
    # await asyncio.sleep(5)
    # result = await race_caller.call_functions(buckets)
    # assert result == "recovered success"

@pytest.mark.asyncio
async def test_all_functions_fail(race_caller, failing_function_model):
    """Tests if the caller raises an exception when all functions fail."""
    race_caller.register_function(failing_function_model)

    buckets = [["func_fail", "func_fail"]]
    with pytest.raises(FraceException, match="No function succeeded"):
        await race_caller.call_functions(buckets)
