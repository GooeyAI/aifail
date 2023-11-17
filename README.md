# AiFail
Python Library for retrying openai/gcp API calls    

### Installation
```bash
pip install aifail
```

### Usage

To get started, simply wrap your functions with `@retry_if`, specifying the condition to retry on.

https://github.com/GooeyAI/gooey-server/blob/master/examples/basic_openai.py

### Advanced Usage

This library is used by GooeyAI in production to handle thousands of API calls every day. 
To save costs and handle rate limits, you can intelligently specify quick fallbacks -

https://github.com/GooeyAI/gooey-server/blob/master/examples/azure_openai_fallback.py

### Inspectable Errors

AiFail comes with a built in logger, and outputs complete stack traces tracing the error back to the original call site.

```
/Users/dev/.virtualenvs/aifail-b178d07d/bin/python /Users/dev/Projects/dara/aifail/examples/azure_openai_fallback.py 
2023-11-18 04:36:01.364 | WARNING  | aifail.aifail:try_all:63 - [2/2] tyring next fn, prev_exc=NotFoundError("Error code: 404 - {'error': {'code': 'DeploymentNotFound', 'message': 'The API deployment for this resource does not exist. If you created the deployment within the last 5 minutes, please wait a moment and try again.'}}")
2023-11-18 04:36:01.778 | WARNING  | aifail.aifail:wrapper:98 - [1/1] captured error, retry_delay=0.4117675457681431s, exc=NotFoundError("Error code: 404 - {'error': {'message': 'The model `gpt-4-x` does not exist', 'type': 'invalid_request_error', 'param': None, 'code': 'model_not_found'}}")
2023-11-18 04:36:02.483 | WARNING  | aifail.aifail:try_all:63 - [2/2] tyring next fn, prev_exc=NotFoundError("Error code: 404 - {'error': {'code': 'DeploymentNotFound', 'message': 'The API deployment for this resource does not exist. If you created the deployment within the last 5 minutes, please wait a moment and try again.'}}")
2023-11-18 04:36:04.093 | WARNING  | aifail.aifail:wrapper:98 - [2/1] captured error, retry_delay=0.9974197744911488s, exc=NotFoundError("Error code: 404 - {'error': {'message': 'The model `gpt-4-x` does not exist', 'type': 'invalid_request_error', 'param': None, 'code': 'model_not_found'}}")
Traceback (most recent call last):
  File "/Users/dev/Projects/dara/aifail/aifail/aifail.py", line 65, in try_all
    return fn()
  File "/Users/dev/Projects/dara/aifail/examples/azure_openai_fallback.py", line 28, in <lambda>
    lambda: azure_client.chat.completions.create(
  ...
openai.NotFoundError: Error code: 404 - {'error': {'code': 'DeploymentNotFound', 'message': 'The API deployment for this resource does not exist. If you created the deployment within the last 5 minutes, please wait a moment and try again.'}}

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/dev/Projects/dara/aifail/aifail/aifail.py", line 86, in wrapper
    return fn(*args, **kwargs)
  File "/Users/dev/Projects/dara/aifail/examples/azure_openai_fallback.py", line 26, in chad_gpt4
    response = try_all(
  File "/Users/dev/Projects/dara/aifail/aifail/aifail.py", line 69, in try_all
    raise prev_exc
  File "/Users/dev/Projects/dara/aifail/aifail/aifail.py", line 65, in try_all
    return fn()
  File "/Users/dev/Projects/dara/aifail/examples/azure_openai_fallback.py", line 34, in <lambda>
    lambda: openai_client.chat.completions.create(
  ...
openai.NotFoundError: Error code: 404 - {'error': {'message': 'The model `gpt-4-x` does not exist', 'type': 'invalid_request_error', 'param': None, 'code': 'model_not_found'}}

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/dev/Projects/dara/aifail/aifail/aifail.py", line 65, in try_all
    return fn()
  File "/Users/dev/Projects/dara/aifail/examples/azure_openai_fallback.py", line 28, in <lambda>
    lambda: azure_client.chat.completions.create(
  ...
openai.NotFoundError: Error code: 404 - {'error': {'code': 'DeploymentNotFound', 'message': 'The API deployment for this resource does not exist. If you created the deployment within the last 5 minutes, please wait a moment and try again.'}}

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/dev/Projects/dara/aifail/examples/azure_openai_fallback.py", line 43, in <module>
    chad_gpt4(
  File "/Users/dev/Projects/dara/aifail/aifail/aifail.py", line 102, in wrapper
    raise prev_exc
  File "/Users/dev/Projects/dara/aifail/aifail/aifail.py", line 86, in wrapper
    return fn(*args, **kwargs)
  File "/Users/dev/Projects/dara/aifail/examples/azure_openai_fallback.py", line 26, in chad_gpt4
    response = try_all(
  File "/Users/dev/Projects/dara/aifail/aifail/aifail.py", line 69, in try_all
    raise prev_exc
  File "/Users/dev/Projects/dara/aifail/aifail/aifail.py", line 65, in try_all
    return fn()
  File "/Users/dev/Projects/dara/aifail/examples/azure_openai_fallback.py", line 34, in <lambda>
    lambda: openai_client.chat.completions.create(
  ...
openai.NotFoundError: Error code: 404 - {'error': {'message': 'The model `gpt-4-x` does not exist', 'type': 'invalid_request_error', 'param': None, 'code': 'model_not_found'}}

Process finished with exit code 1
```