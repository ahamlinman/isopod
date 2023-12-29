import queue


class Trigger:
    def __init__(self):
        self._q = queue.Queue(maxsize=1)

    def wait(self):
        self._q.get()

    def set(self):
        try:
            self._q.put_nowait(True)
        except queue.Full:
            pass
