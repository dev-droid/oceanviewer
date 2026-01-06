from typing import Callable, Dict, List, Any
import logging

# Configure logging for the bus
logger = logging.getLogger("EventBus")

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed to {event_type}: {handler.__name__}")

    def publish(self, event_type: str, data: Any = None):
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"Error handling event {event_type}: {e}")
