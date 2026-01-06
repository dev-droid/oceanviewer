from src.core.event_bus import EventBus
from src.core.types import NetworkStatus
import time
import threading
import logging
import random
from collections import deque
import json

logger = logging.getLogger("NetStatusAgent")

class NetStatusAgent:
    def __init__(self, event_bus: EventBus):
        self.bus = event_bus
        self.current_status = NetworkStatus.OFFLINE
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._monitor_loop)
        
        # Stability Configuration
        self.history_window = 10
        self.ping_history = deque(maxlen=self.history_window)
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        
        # Thresholds
        self.OFFLINE_THRESHOLD_FAILURES = 5   # Short failure != Offline, need 5 in a row
        self.RECOVERY_THRESHOLD_SUCCESS = 8   # Strict recovery: need 8 good pings to leave OFFLINE
        self.INTERMITTENT_RATIO_MIN = 0.3     # At least 30% success to be Intermittent (vs Offline)
        self.ONLINE_RATIO_MIN = 0.9          # 90% success to be strict ONLINE

    def start(self):
        logger.info("Starting NetStatusAgent (Stable Mode)...")
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join()

    def _mock_ping(self) -> bool:
        # Simulate environment: 
        # For demo, let's fluctuate. 
        # Real impl would allow `ping 8.8.8.8` or checking satellite modem status.
        # This function should be replaced by actual hardware checks.
        
        # Simulating a mostly offline but occasionally connected scenario
        status_roll = random.random()
        return status_roll > 0.7 # 30% chance of success (Poor connection)

    def _evaluate_state(self, ping_result: bool):
        self.ping_history.append(ping_result)
        
        if ping_result:
            self.consecutive_successes += 1
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            self.consecutive_successes = 0

        # Calculate metrics
        success_ratio = sum(self.ping_history) / len(self.ping_history) if self.ping_history else 0
        
        new_status = self.current_status
        confidence = 0.0

        # Logic based on Current State (Hysteresis)
        
        if self.current_status == NetworkStatus.OFFLINE:
            # STRICT RECOVERY: Must have stable consecutive successes
            if self.consecutive_successes >= self.RECOVERY_THRESHOLD_SUCCESS:
                if success_ratio > self.ONLINE_RATIO_MIN:
                    new_status = NetworkStatus.ONLINE
                else:
                    new_status = NetworkStatus.INTERMITTENT
            # Else stay OFFLINE
            confidence = 1.0 if not ping_result else 0.5

        elif self.current_status == NetworkStatus.ONLINE:
             # Short failure != Offline
             if self.consecutive_failures >= self.OFFLINE_THRESHOLD_FAILURES:
                 new_status = NetworkStatus.OFFLINE
             elif success_ratio < self.ONLINE_RATIO_MIN:
                 new_status = NetworkStatus.INTERMITTENT
             confidence = success_ratio

        elif self.current_status == NetworkStatus.INTERMITTENT:
             if self.consecutive_failures >= self.OFFLINE_THRESHOLD_FAILURES:
                 new_status = NetworkStatus.OFFLINE
             elif success_ratio > self.ONLINE_RATIO_MIN:
                 new_status = NetworkStatus.ONLINE
             confidence = success_ratio

        # Log current state in strict JSON format as requested
        output = {
            "net_status": self.current_status.name,
            "confidence": round(confidence, 2)
        }
        logger.info(json.dumps(output))

        if new_status != self.current_status:
            # logger.info(f"State Transition: ...") # Suppressed for brevity
            self.current_status = new_status
            self.bus.publish("network_status_change", self.current_status)

    def _monitor_loop(self):
        while not self._stop_event.is_set():
            result = self._mock_ping()
            self._evaluate_state(result)
            # Faster ping rate for more reactive (but smoothed) state
            time.sleep(1) 
