import time
from functools import wraps
from datetime import timedelta


def timed(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        run_time = end_time - start_time
        print(f"...finished in {str(timedelta(seconds=run_time))}")
        return result
    return wrapper
