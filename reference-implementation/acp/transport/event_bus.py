"""ACP Asynchronous Event Bus and Pub/Sub Broker abstraction."""
from typing import Callable, Dict, List, Any
from acp.models.envelope import Envelope


class EventBus:
    """Publish/Subscribe Event Bus & Broker supporting Topics, Subscriptions, and Dead Letter Queue."""

    def __init__(self) -> None:
        self.topics: Dict[str, List[Callable[[Envelope], None]]] = {}
        self.dlq: List[Envelope] = []

    def subscribe(self, topic: str, callback: Callable[[Envelope], None]) -> None:
        """Subscribe a callback to a topic."""
        if topic not in self.topics:
            self.topics[topic] = []
        self.topics[topic].append(callback)

    def publish(self, topic: str, envelope: Envelope) -> int:
        """Publish an envelope to all subscribers of a topic or wildcard matching."""
        delivered = 0
        for t, callbacks in self.topics.items():
            if t == topic or (t.endswith(".*") and topic.startswith(t[:-2])):
                for cb in callbacks:
                    try:
                        cb(envelope)
                        delivered += 1
                    except Exception:
                        self.dlq.append(envelope)
        if delivered == 0 and not topic.startswith("acp.internal."):
            self.dlq.append(envelope)
        return delivered
