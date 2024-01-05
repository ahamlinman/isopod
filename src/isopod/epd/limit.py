import time
from dataclasses import dataclass, field


@dataclass
class BucketEmpty(Exception):
    """
    Raised by :meth:`Bucket.take` when no tokens are available.
    :property:`seconds_remaining` indicates how long to wait for the next token.
    """

    seconds_remaining: float


@dataclass
class Bucket:
    """
    A specialized token bucket for use with the E-Ink display that Isopod
    supports, which is not designed to refresh more than once every few minutes.

    This bucket adds tokens based on the time at which the last token was taken,
    rather than at a constant rate, as this better represents the intent to
    delay E-Ink refreshes. (TODO: more.)
    """

    capacity: int
    full_delay: float

    _take_time: float = field(default_factory=time.monotonic, init=False)
    _take_remaining: int = field(default=0, init=False)

    def __post_init__(self):
        if self.capacity < 1:
            raise ValueError("capacity must be at least 1")

        self._take_remaining = self.capacity

    @property
    def available(self):
        now = time.monotonic()
        seconds_since_take = now - self._take_time
        tokens_since_take = int(seconds_since_take / self.full_delay)
        return min(self._take_remaining + tokens_since_take, self.capacity)

    def take(self):
        available = self.available
        if available == 0:
            fill_time = self._take_time + self.full_delay
            seconds_remaining = max(0, fill_time - time.monotonic())
            raise BucketEmpty(seconds_remaining=seconds_remaining)

        self._take_time = time.monotonic()
        self._take_remaining = available - 1
