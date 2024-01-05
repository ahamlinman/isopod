import time
from dataclasses import dataclass, field


@dataclass
class TakeBlocked(Exception):
    """
    Raised by :meth:`Bucket.take` when it is not possible to take a token.
    :property:`seconds_remaining` indicates how long to wait before retrying.
    """

    seconds_remaining: float


@dataclass
class Bucket:
    """
    A specialized token bucket for use with the E-Ink display that Isopod
    supports, which is not designed to refresh more than once every few minutes.
    The bucket adds tokens based on the time at which the last token was taken,
    rather than at a constant rate. It also enforces a minimum delay after
    taking a token regardless of how many are left in the bucket.
    """

    capacity: int
    fill_delay: float
    burst_delay: float

    _take_time: float = field(default=0, init=False)
    _take_remaining: int = field(default=0, init=False)

    def __post_init__(self):
        if self.capacity < 1:
            raise ValueError("capacity must be at least 1")

        self._take_remaining = self.capacity

    def take(self):
        now = time.monotonic()
        seconds_since_take = now - self._take_time
        tokens_since_take = int(seconds_since_take / self.fill_delay)
        available = min(self._take_remaining + tokens_since_take, self.capacity)
        assert available >= 0
        if available == 0:
            fill_time = self._take_time + self.fill_delay
            seconds_remaining = max(0, fill_time - time.monotonic())
            raise TakeBlocked(seconds_remaining=seconds_remaining)

        if seconds_since_take < self.burst_delay:
            ready_time = self._take_time + self.burst_delay
            seconds_remaining = max(0, ready_time - time.monotonic())
            raise TakeBlocked(seconds_remaining=seconds_remaining)

        self._take_time = time.monotonic()
        self._take_remaining = available - 1
