import asyncio
import pytest
from frace import FunctionRaceCaller, FunctionModel

@pytest.mark.asyncio
async def test_single_bucket_one_function(simple_function_model, race_caller):
    race_caller.register_function(simple_function_model)

    buckets = [["func1"]]
    result = await race_caller.call_functions(buckets)
    assert result == "success"

@pytest.mark.asyncio
async def test_two_buckets_one_function_each(race_caller):
    async def fast_function():
        return "fast"

    async def slow_function():
        await asyncio.sleep(0.01)
        return "slow"

    fast_model = FunctionModel(id="func_fast", func=fast_function)
    slow_model = FunctionModel(id="func_slow", func=slow_function)

    race_caller.register_function(fast_model)
    race_caller.register_function(slow_model)

    buckets = [["func_fast"], ["func_slow"]]
    result = await race_caller.call_functions(buckets)
    assert result == "fast"

    buckets = [["func_slow"], ["func_fast"]]
    result = await race_caller.call_functions(buckets)
    assert result == "fast"

@pytest.mark.asyncio
async def test_one_bucket_malfunction(race_caller):
    async def good():
        await asyncio.sleep(1)
        return "good"

    async def bad():
        raise Exception("Function failed")

    fast_model = FunctionModel(id="good", func=good)
    slow_model = FunctionModel(id="bad", func=bad)

    race_caller.register_function(fast_model)
    race_caller.register_function(slow_model)

    buckets = [["good"], ["bad"]]
    result = await race_caller.call_functions(buckets)
    assert result == "good"
