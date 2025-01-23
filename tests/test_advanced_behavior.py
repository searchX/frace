import asyncio
import pytest
from frace import FunctionModel

@pytest.mark.asyncio
async def test_arguments_update(race_caller):
    async def func_with_args(x, y):
        return x + y

    model = FunctionModel(id="func_args", func=func_with_args)
    race_caller.register_function(model)

    buckets = [["func_args"]]
    args = {"func_args": (3, 4)}
    result = await race_caller.call_functions(buckets, function_args=args)
    assert result == 7

@pytest.mark.asyncio
async def test_function_timeouts(race_caller):
    async def slow_function():
        await asyncio.sleep(2)
        return "slow success"

    async def fast_function():
        await asyncio.sleep(1)
        return "fast success"

    slow_model = FunctionModel(id="func_slow", func=slow_function)
    fast_model = FunctionModel(id="func_fast", func=fast_function)

    race_caller.register_function(slow_model)
    race_caller.register_function(fast_model)

    buckets = [["func_slow", "func_fast"]]
    timeouts = {"func_fast": 0.5}  # Set a short timeout for the slow function
    result = await race_caller.call_functions(buckets, function_timeouts=timeouts)
    assert result == "slow success"
