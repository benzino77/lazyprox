import threading

from lazyprox.common.singleton import singleton


def test_singleton_returns_same_instance():
    @singleton
    class Dummy:
        pass

    first = Dummy()
    second = Dummy()

    assert first is second


def test_singleton_different_classes_yield_distinct_instances():
    @singleton
    class First:
        pass

    @singleton
    class Second:
        pass

    assert First() is not Second()


def test_singleton_preserves_wraps_metadata():
    @singleton
    class Documented:
        """My singleton docstring."""

    assert Documented.__name__ == "Documented"
    assert Documented.__doc__ == "My singleton docstring."


def test_singleton_is_thread_safe():
    instantiation_count = 0
    count_lock = threading.Lock()
    barrier = threading.Barrier(8)

    @singleton
    class Concurrent:
        def __init__(self):
            nonlocal instantiation_count
            with count_lock:
                instantiation_count += 1

    results = []
    results_lock = threading.Lock()

    def worker():
        barrier.wait()
        instance = Concurrent()
        with results_lock:
            results.append(instance)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert instantiation_count == 1
    assert all(r is results[0] for r in results)
