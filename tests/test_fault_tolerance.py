import pytest
from frace import FunctionModel, FraceException

@pytest.mark.asyncio
async def test_fault_tolerance_one_bucket(race_caller, failing_function_model, simple_function_model):
    race_caller.register_function(failing_function_model)
    race_caller.register_function(simple_function_model)

    buckets = [["func_fail", "func1"]]
    result = await race_caller.call_functions(buckets)
    assert result == "success"

@pytest.mark.asyncio
async def test_fault_tolerance_two_buckets(race_caller):
    async def fast_failing_function():
        raise Exception("Fast function failed")

    async def fast_function():
        return "fast success"

    failing_model = FunctionModel(id="func_fail", func=fast_failing_function)
    fast_model = FunctionModel(id="func_fast", func=fast_function)

    race_caller.register_function(failing_model)
    race_caller.register_function(fast_model)

    buckets = [["func_fail", "func_fast"], ["func_fail", "func_fast"]]
    result = await race_caller.call_functions(buckets)
    assert result == "fast success"

@pytest.mark.asyncio
async def test_fault_cycle_back(race_caller, failing_function_model, simple_function_model):
    race_caller.register_function(failing_function_model)
    race_caller.register_function(simple_function_model)

    buckets = [["func_fail", "func_fail", "func_fail", "func_fail", "func1"]]
    result = await race_caller.call_functions(buckets)
    assert result == "success"