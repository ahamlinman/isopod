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
    A token bucket that enforces a minimum delay between tokens regardless of
    how many are available.
    """

    capacity: int
    fill_delay: float
    burst_delay: float

    _take_time: float = field(default=0, init=False)
    _take_remaining: float = field(default=0, init=False)

    def __post_init__(self):
        if self.capacity < 1:
            raise ValueError("capacity must be at least 1")
        if self.fill_delay <= 0:
            raise ValueError("fill_delay must be greater than 0")

        self._take_remaining = self.capacity

    def take(self):
        """
        Take exactly 1 token from the bucket, or raise :exception:`TakeBlocked`
        if the bucket does not have 1 full token available.
        """

        now = time.monotonic()
        seconds_since_take = now - self._take_time
        tokens_since_take = seconds_since_take / self.fill_delay
        available = min(self._take_remaining + tokens_since_take, self.capacity)
        delays = []

        if available < 1:
            tokens_missing = 1 - available
            fill_time = now + (self.fill_delay * tokens_missing)
            delays.append(fill_time - now)

        if seconds_since_take < self.burst_delay:
            ready_time = self._take_time + self.burst_delay
            delays.append(ready_time - now)

        if delays:
            raise TakeBlocked(seconds_remaining=max(delays))

        self._take_time = now
        self._take_remaining = available - 1

    @property
    def seconds_until_full(self):
        """
        The duration in seconds after which the bucket will be filled to
        capacity if no :meth:`take` occurs.
        """

        now = time.monotonic()
        seconds_since_take = now - self._take_time
        tokens_since_take = seconds_since_take / self.fill_delay
        available = min(self._take_remaining + tokens_since_take, self.capacity)
        required = self.capacity - available
        return self.fill_delay * required
