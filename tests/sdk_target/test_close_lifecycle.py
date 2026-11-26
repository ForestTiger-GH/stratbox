"""A second SDK close can wait for a previously requested asynchronous drain."""
from stratbox.sdk import StrategyBox


def test_repeated_close_delegates_wait_and_cancel_to_the_existing_service():
    class Service:
        def __init__(self):
            self.requests = []

        def close(self, *, wait, cancel):
            self.requests.append((wait, cancel))

    box = StrategyBox()
    service = box._session = Service()
    box.close(wait=False)
    box.close(wait=True, cancel=True)
    assert service.requests == [(False, False), (True, True)]
    assert box._closed
