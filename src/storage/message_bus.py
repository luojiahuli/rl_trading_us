"""进程内消息总线（复用 A 股版本）"""
import logging
from queue import Queue, Empty
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MessageBus:
    def __init__(self):
        self._queues: dict[str, Queue] = {}
        self._topics: set[str] = set()

    def publish(self, topic: str, message: Any):
        if topic not in self._queues:
            self._queues[topic] = Queue()
        self._queues[topic].put(message)
        self._topics.add(topic)

    def subscribe(self, topic: str) -> Queue:
        if topic not in self._queues:
            self._queues[topic] = Queue()
        self._topics.add(topic)
        return self._queues[topic]

    def consume(self, topic: str, timeout: Optional[float] = None) -> Any:
        queue = self.subscribe(topic)
        try:
            return queue.get(timeout=timeout)
        except Empty:
            return None

    @property
    def topics(self) -> list[str]:
        return sorted(self._topics)

    def consume_all(self, topic: str, timeout: Optional[float] = 0.1) -> list:
        results = []
        while True:
            msg = self.consume(topic, timeout=timeout)
            if msg is None:
                break
            results.append(msg)
        return results
