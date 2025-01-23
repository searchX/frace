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
        await asyncio.sleep(2)
        return "slow"

    fast_model = FunctionModel(id="func_fast", func=fast_function)
    slow_model = FunctionModel(id="func_slow", func=slow_function)

    race_caller.register_function(fast_model)
    race_caller.register_function(slow_model)

    buckets = [["func_fast"], ["func_slow"]]
    result = await race_caller.call_functions(buckets)
    assert result == "fast"
