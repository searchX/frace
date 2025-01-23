import pytest
from frace import FunctionRaceCaller, FunctionModel

@pytest.fixture
def simple_function_model():
    """Creates a simple function model that returns a result."""
    async def simple_function():
        return "success"

    return FunctionModel(id="func1", func=simple_function)

@pytest.fixture
def failing_function_model():
    """Creates a function model that raises an exception."""
    async def failing_function():
        raise Exception("Function failed")

    return FunctionModel(id="func_fail", func=failing_function)

@pytest.fixture
def race_caller():
    """Provides a preconfigured FunctionRaceCaller instance."""
    return FunctionRaceCaller(max_failures=2, function_timeouts={})
