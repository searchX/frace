# Frace - Python Functions in a Race

Welcome to the Frace Project, a powerful Python library designed to execute multiple functions concurrently. Frace ensures rapid and reliable execution by prioritizing latency and aiming for quick success across functions intended to accomplish the same goal. Even **if some functions encounter failures, others continue to run, offering results as soon as possible**.

## Key Features

- **Resilient Execution**: Automatically transitions to alternate functions upon failures, ensuring the best chance of success.
- **Concurrency**: Executes one function from each bucket concurrently, enhancing overall performance.
- **Customizable Timeouts**: Allows specific timeouts for individual functions to manage long-running tasks.
- **Failure Management**: Monitors function performance, optimizing subsequent executions by marking functions that fail.
- **Exponential Backoff**: Employs exponential backoff for failed functions to prevent system overloads and disables functions that fail repeatedly.

## Why Choose Frace?

When dealing with operations that may experience intermittent failures and where getting a result quickly is more important than which function succeeds, Frace is ideal. Its concurrent execution and automatic failover to alternate functions ensure your application remains responsive and reliable.

### Frace at a Glance
<img src="https://raw.githubusercontent.com/searchX/frace/main/images/frace_executor.png" height="512">

Frace executes one function from each bucket concurrently, allowing multiple functions to run simultaneously, If a function fails, Frace automatically switches to the next available function in the bucket. This process continues until a successful function is found or all functions in the bucket fail.. while execution if any bucket gives a successful response, the execution stops and returns the result.

## Installation

Install the `frace` package using pip:

```bash
$ pip install frace
```

Or install the latest package directly from GitHub:

```bash
$ pip install git+https://github.com/searchX/frace
```

## Handling Failures

Frace automatically handles function failures by attempting to execute the next available function within the defined bucket. If all functions in a bucket fail, a `FraceException` is raised.

## Use Case: Large Language Model Completions

Suppose you need to get a response from large language models and multiple models are available. It doesn't matter which model provides the output as long as it returns quickly. You can use Frace to manage this redundancy efficiently by running calls to different models concurrently, taking the first successful response.

```python
import asyncio
import pytest
from frace import FunctionModel

def get_fast_llm_response():
    race_caller = FunctionRaceCaller(max_failures=2, function_timeouts={})

    async def llm_model_a():
        await asyncio.sleep(1)  # Simulate delay for Model A
        return "Model A Response"

    async def llm_model_b():
        await asyncio.sleep(0.5)  # Simulate faster delay for Model B
        return "Model B Response"

    # Register the functions as models
    model_a = FunctionModel(id="model_a", func=llm_model_a)
    model_b = FunctionModel(id="model_b", func=llm_model_b)

    race_caller.register_function(model_a)
    race_caller.register_function(model_b)

    # Use buckets to create a group of functions to race
    buckets = [["model_a", "model_b"]]

    # Start the event loop to run the asynchronous function
    result = asyncio.run(race_caller.call_functions(buckets))
    assert result == "Model B Response"  # Expect the fastest function result
```

## Contributing

Frace is an essential tool for achieving resilience in concurrent function execution. Contributions are welcome to extend its capabilities and improve its robustness. Feel free to submit issues or pull requests on GitHub.