from os import path
from typing import Callable, List
from time import sleep


def retry(
    func: Callable,
    on_retry: Callable,
    max_retries: int = 5,
    delay: float = 0.2,
    *args,
    **kwargs
):
    was_error = True
    retries = 0
    while was_error and (retries < max_retries or retries <= 0):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            was_error = not on_retry(e)
            retries += 1
            sleep(delay)

    return None
