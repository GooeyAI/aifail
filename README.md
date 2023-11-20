# AiFail
Python Library for retrying openai/gcp API calls    

### Installation

```bash
pip install aifail
```

### Usage

To get started, simply wrap your functions with `@retry_if`, specifying the condition to retry on.

https://github.com/GooeyAI/aifail/blob/a540c05a2a9436c0b6b1caab8ed823387999d5f9/examples/basic_openai.py#L5

https://github.com/GooeyAI/aifail/blob/a540c05a2a9436c0b6b1caab8ed823387999d5f9/examples/basic_openai.py#L13-L30


### Custom logic

You can use this with anything that needs retrying, e.g. google sheets -


```py
def sheets_api_should_retry(e: Exception) -> bool:
    return isinstance(e, HttpError) and (
        e.resp.status in (408, 429) or e.resp.status > 500
    )


@retry_if(sheets_api_should_retry)
def update_cell(spreadsheet_id: str, row: int, col: int, value: str):
    get_spreadsheet_service().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{col_i2a(col)}{row}:{col_i2a(col)}{row}",
        body={"values": [[value]]},
        valueInputOption="RAW",
    ).execute()
```

### Advanced Usage

This library is used by GooeyAI in production to handle thousands of API calls every day. 
To save costs and handle rate limits, you can intelligently specify quick fallbacks (eg azure openai) -

https://github.com/GooeyAI/aifail/blob/a540c05a2a9436c0b6b1caab8ed823387999d5f9/examples/azure_openai_fallback.py#L7-L16

https://github.com/GooeyAI/aifail/blob/a540c05a2a9436c0b6b1caab8ed823387999d5f9/examples/azure_openai_fallback.py#L19-L35

### Traceable Errors

AiFail comes with a built in logger, and outputs complete stack traces tracing the error back to the original call site.

```bash
# python examples/azure_openai_fallback.py 
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

Sentry too, will capture the entire retry loop

<img width="573" alt="image" src="https://github.com/GooeyAI/aifail/assets/19492893/958e4a74-4159-4784-a69c-e50e45b47494">

