from __future__ import annotations

import email.utils
import time
import typing
from functools import wraps
from inspect import isgenerator
from random import random
from time import sleep

from loguru import logger

F = typing.TypeVar("F", bound=typing.Callable)
R = typing.TypeVar("R")

MAX_RETRIES = 10


RETRYABLE_HTTP_STATUS_CODES = frozenset(
    {
        408,  # Request Timeout
        409,  # Conflict
        425,  # Too Early
        429,  # Too Many Requests / rate limit
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
        529,  # Overloaded (Anthropic)
    }
)

# Error `type` values that map to retryable HTTP status codes, used to filter
# bare `openai.APIError`s raised mid-stream (e.g. by `openai/_streaming.py`)
# where no `status_code` is attached. Vocabulary taken from
# https://docs.anthropic.com/en/api/errors which is what surfaces here in
# practice via OpenAI-compatible providers.
OPENAI_RETRYABLE_ERROR_TYPES = frozenset(
    {
        "rate_limit_error",  # 429
        "api_error",  # 500
        "timeout_error",  # 504
        "overloaded_error",  # 529
    }
)


def openai_should_retry(e: Exception) -> bool:
    """
    https://platform.openai.com/docs/guides/error-codes

    Retry policy:
    - openai.APIConnectionError / APITimeoutError: always retry (transient network).
    - openai.APIStatusError: retry only if status_code is in
      `RETRYABLE_HTTP_STATUS_CODES`, after honoring the `x-should-retry` header.
    - bare openai.APIError (e.g. raised mid-stream by openai/_streaming.py when an
      OpenAI-compatible provider returns an error inside the SSE body, where the
      HTTP response was 200 OK and there's no status_code): retry only if the
      error body's `type` is in `OPENAI_RETRYABLE_ERROR_TYPES`. This also
      implicitly excludes `APIResponseValidationError` (no body type set).
    """
    import openai

    is_transient_network_error = isinstance(
        e, (openai.APIConnectionError, openai.APITimeoutError)
    )
    has_retryable_error_type = (
        isinstance(e, openai.APIError) and e.type in OPENAI_RETRYABLE_ERROR_TYPES
    )
    return (
        is_transient_network_error
        or _openai_status_error_should_retry(e)
        or has_retryable_error_type
    )


def _openai_status_error_should_retry(e: Exception) -> bool:
    import openai

    if not isinstance(e, openai.APIStatusError):
        return False
    # If the server explicitly says whether or not to retry, obey.
    if e.response is not None and e.response.headers:
        should_retry_header = e.response.headers.get("x-should-retry")
        if should_retry_header == "true":
            return True
        if should_retry_header == "false":
            return False
    return e.status_code in RETRYABLE_HTTP_STATUS_CODES


def vertex_ai_should_retry(e: Exception) -> bool:
    import google.api_core.exceptions

    return isinstance(
        e,
        (
            google.api_core.exceptions.ServiceUnavailable,
            google.api_core.exceptions.TooManyRequests,
            google.api_core.exceptions.InternalServerError,
            google.api_core.exceptions.GatewayTimeout,
        ),
    )


def http_should_retry(e: Exception) -> bool:
    import requests

    is_transient_network_error = isinstance(
        e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)
    )
    is_retryable_status_error = (
        isinstance(e, requests.HTTPError)
        and e.response is not None
        and e.response.status_code in RETRYABLE_HTTP_STATUS_CODES
    )
    return is_transient_network_error or is_retryable_status_error


def try_all(*fns: typing.Callable[[], R]) -> R:
    assert len(fns) > 0, "Must provide at least one fn"
    prev_exc = None
    for i, fn in enumerate(fns):
        if prev_exc:
            logger.warning(f"[{i + 1}/{len(fns)}] tyring next fn, {prev_exc=}")
        try:
            return fn()
        except Exception as e:
            set_root_cause(e, prev_exc)
            prev_exc = e
    raise prev_exc


def calculate_retry_delay(
    *,
    exc: Exception,
    idx: int,
    initial_retry_delay: float,
    max_retry_delay: float,
) -> float:
    """
    Stolen from https://github.com/openai/openai-python/blob/90aa5eb3ed6b92d9a1de89c0ee063f4768f92256/src/openai/_base_client.py#L586
    """

    api_errors = ()
    try:
        import openai

        api_errors += (openai.APIStatusError,)
    except ImportError:
        pass
    try:
        import requests

        api_errors += (requests.HTTPError,)
    except ImportError:
        pass
    try:
        import httpx

        api_errors += (httpx.HTTPStatusError,)
    except ImportError:
        pass

    try:
        # About the Retry-After header: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Retry-After
        #
        # <http-date>". See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Retry-After#syntax for
        # details.
        if isinstance(exc, api_errors) and exc.response.headers:
            retry_header = exc.response.headers.get("retry-after")
            try:
                retry_after = int(retry_header)
            except Exception:
                retry_date_tuple = email.utils.parsedate_tz(retry_header)
                if retry_date_tuple is None:
                    retry_after = -1
                else:
                    retry_date = email.utils.mktime_tz(retry_date_tuple)
                    retry_after = int(retry_date - time.time())
        else:
            retry_after = -1
    except Exception:
        retry_after = -1

    # If the API asks us to wait a certain amount of time (and it's a reasonable amount), just do what it says.
    if 0 < retry_after <= 60:
        return retry_after

    # Apply exponential backoff, but not more than the max.
    sleep_seconds = min(initial_retry_delay * pow(2.0, idx), max_retry_delay)

    # Apply some jitter, plus-or-minus half a second.
    jitter = 1 - 0.25 * random()
    timeout = sleep_seconds * jitter
    return timeout if timeout >= 0 else 0


def retry_if(
    shuld_retry_fn: typing.Callable[[Exception], bool],
    *,
    max_retries: int = MAX_RETRIES,
    initial_retry_delay: float = 0.5,
    max_retry_delay: float = 8.0,
    calculate_retry_delay: typing.Callable[..., float] = calculate_retry_delay,
) -> typing.Callable[[F], F]:
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            prev_exc = None
            assert max_retries, "max_retries must be > 0"
            for idx in range(max_retries + 1):
                try:
                    ret = fn(*args, **kwargs)
                    if isgenerator(ret):
                        return generator_wrapper(ret)
                    else:
                        return ret
                except Exception as exc:
                    set_root_cause(exc, prev_exc)
                    prev_exc = exc
                    if not shuld_retry_fn(exc):
                        break
                    retry_delay = calculate_retry_delay(
                        exc=exc,
                        idx=idx,
                        initial_retry_delay=initial_retry_delay,
                        max_retry_delay=max_retry_delay,
                    )
                    logger.warning(
                        f"[{idx + 1}/{max_retries}] captured error, {retry_delay=}s, {exc=}"
                    )
                    sleep(retry_delay)
            raise prev_exc

        return wrapper

    return decorator


G = typing.TypeVar("G", bound=typing.Generator)


def generator_wrapper(g: G) -> G:
    # get the first value from the generator to catch any exceptions
    first_val = next(g)

    def wrapper() -> G:
        yield first_val
        return (yield from g)

    return wrapper()


def set_root_cause(exc: Exception, cause: Exception) -> Exception | None:
    while True:
        if exc.__cause__ is None:
            exc.__cause__ = cause
            return exc
        exc = exc.__cause__
