from src.core.event_bus import EventBus
from src.core.types import OceanEvent, NetworkStatus, RiskLevel
from src.database.storage import StorageManager
import logging
import time

logger = logging.getLogger("SyncAgent")

class SyncAgent:
    def __init__(self, event_bus: EventBus, storage: StorageManager):
        self.bus = event_bus
        self.storage = storage
        self.network_status = NetworkStatus.OFFLINE
        
        self.bus.subscribe("network_status_change", self.update_network_status)
        self.bus.subscribe("risk_assessed_event", self.handle_final_event)

    def update_network_status(self, payload):
        if isinstance(payload, NetworkStatus):
            self.network_status = payload
        elif isinstance(payload, dict):
            status_str = payload.get("net_status")
            if status_str:
                self.network_status = NetworkStatus[status_str]
        
        logger.info(f"Network Status Updated: {self.network_status.name}")

    def handle_final_event(self, event: OceanEvent):
        # 1. System Storage (Performed by system/infra, invoked here as the entry point)
        self.storage.save_event(event)

        decision = "BLOCKED"
        reason = "Unknown"
        should_sync = False
        
        # 3. Traffic Control (Anti-Avalanche)
        # We check rate limits BEFORE assessing network rules to calculate "allowance"
        # But logically, if network is down, we don't care about rate.
        # Let's check Network first, then Rate.

        # 2. Decision Logic
        if self.network_status == NetworkStatus.OFFLINE:
            decision = "BLOCKED"
            reason = "Network OFFLINE"
            should_sync = False
            
        elif self.network_status == NetworkStatus.INTERMITTENT:
            if event.risk_level == RiskLevel.HIGH:
                 if self._check_rate_limit("HIGH"):
                     decision = "ALLOWED"
                     reason = "INTERMITTENT - HIGH PRIORITY (Rate OK)"
                     should_sync = True
                 else:
                     decision = "DEFERRED"
                     reason = "INTERMITTENT - RATE LIMIT EXCEEDED"
                     should_sync = False
            else:
                 decision = "SKIPPED"
                 reason = "INTERMITTENT - LOW PRIORITY"
                 should_sync = False

        elif self.network_status == NetworkStatus.ONLINE:
            # Even in ONLINE, avoid flooding
            if self._check_rate_limit("STANDARD"):
                decision = "ALLOWED"
                reason = "ONLINE - STANDARD SYNC"
                should_sync = True
            else:
                decision = "DEFERRED"
                reason = "ONLINE - RATE LIMIT EXCEEDED"
                should_sync = False

        logger.info(f"Sync Decision for {event.event_id}: {decision} ({reason})")
        
        if should_sync:
            self._execute_system_sync(event)
    
    def _execute_system_sync(self, event: OceanEvent):
        logger.info(f"Initiating System Uplink for Event {event.event_id}...")
        self.storage.mark_synced(event.event_id)

    def _check_rate_limit(self, priority: str) -> bool:
        # Simple Sliding Window or Minimum Interval
        # To avoid avalanche, we enforce a minimum gap between syncs.
        
        now = time.time()
        
        # Init state if needed (using dict for extensibility)
        if not hasattr(self, "_last_sync_times"):
            self._last_sync_times = {"HIGH": 0, "STANDARD": 0}
            
        last_time = self._last_sync_times.get(priority, 0)
        
        # Constraints
        # HIGH: Allow burst but limit sustained? For MVP, simple gap.
        # INTERMITTENT/HIGH: 2 seconds gap (allows urgent but stops machine gun)
        # ONLINE/STANDARD: 0.5 seconds gap (high throughput)
        
        min_gap = 2.0 if priority == "HIGH" else 0.5
        
        if (now - last_time) > min_gap:
            self._last_sync_times[priority] = now
            return True
        return False
