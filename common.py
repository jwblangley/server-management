import time


DEFAULT_INTERVAL = 5


class WaitForTimeoutException(Exception):
    def _init__(self, msg):
        super().__init__(msg)


def wait_for(predicate, interval=DEFAULT_INTERVAL, timeout=None):
    attempt = 0
    while timeout is None or attempt * interval < timeout:
        if predicate():
            return
        attempt += 1
        time.sleep(interval)
        print("Waiting...")

    raise WaitForTimeoutException("Wait for timed out")
