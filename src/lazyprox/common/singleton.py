"""
Thread-safe singleton decorator for Python classes.
"""

import threading
from functools import wraps
from typing import Type, TypeVar

T = TypeVar('T')


def singleton(cls: Type[T]) -> Type[T]:
    """
    A thread-safe singleton decorator for Python classes.

    Usage:
        @singleton
        class MySingleton:
            def __init__(self):
                self.value = 0

    This ensures only one instance of MySingleton exists throughout the application.
    """
    instances = {}
    lock = threading.Lock()

    @wraps(cls)
    def get_instance(*args, **kwargs):
        if cls not in instances:
            with lock:
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance
