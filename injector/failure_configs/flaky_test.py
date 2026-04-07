import random
import threading
import time


def test_random_pass():
    # Fails ~30% of the time
    assert random.random() > 0.3


def test_timeout_flaky():
    # Fails if CI runner is slow
    result = {"done": False}

    def slow_operation():
        time.sleep(0.8)
        result["done"] = True

    t = threading.Thread(target=slow_operation)
    t.start()
    t.join(timeout=0.5)
    assert result["done"]
