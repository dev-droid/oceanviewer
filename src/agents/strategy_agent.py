import json
from src.core.event_bus import EventBus
import logging
import shutil
from src.core.types import RiskLevel, NetworkStatus, SystemStrategy, SystemMode

logger = logging.getLogger("StrategyAgent")

class StrategyAgent:
    def __init__(self, event_bus: EventBus, storage_path: str = "./"):
        self.bus = event_bus
        self.storage_path = storage_path
        
        # State
        self.battery_level = 100
        self.current_risk = RiskLevel.UNKNOWN
        self.network_status = NetworkStatus.OFFLINE
        self.current_uncertainty = 0.0  # Track uncertainty from RiskAgent
        
        self.current_strategy: SystemStrategy = None

        # Subscribe
        self.bus.subscribe("network_status_change", self.on_network_status)
        self.bus.subscribe("risk_assessment", self.on_risk_assessment)
        
        # Initial Strategy Calc
        self.update_strategy()

    def on_network_status(self, payload):
        # Payload might be dict or direct Enum
        if isinstance(payload, NetworkStatus):
            self.network_status = payload
        elif isinstance(payload, dict):
            status_str = payload.get("net_status")
            if status_str:
                self.network_status = NetworkStatus[status_str]
        
        self.update_strategy()

    def on_risk_assessment(self, payload):
        # RiskAgent publishes {"risk_level": "LOW", "uncertainty": 0.2, ...}
        risk_str = payload.get("risk_level")
        if risk_str:
            self.current_risk = RiskLevel[risk_str]
        
        # Capture uncertainty for conservative strategy
        uncertainty = payload.get("uncertainty", 0.0)
        self.current_uncertainty = uncertainty
        
        self.update_strategy()

    def update_strategy(self, force_publish=False):
        # 1. Power Check (Priority 1: Hard Constraint)
        new_strategy = None
        mode = "UNKNOWN"
        decision_reason = "Unknown"

        if self.battery_level < 20:
            mode = "CRITICAL_POWER"
            decision_reason = "Battery critical (<20%)"
            new_strategy = SystemStrategy(
                fps=1,
                model_type="tiny", 
                confirm_frames=6,
                storage_policy="critical_only"
            )
        # 2. Uncertainty Check (Priority 2: Stability Protection)
        # If uncertainty > 0.7, DO NOT boost performance - stay conservative
        elif self.current_uncertainty > 0.7:
            mode = "HIGH_UNCERTAINTY"
            decision_reason = f"Uncertainty too high ({self.current_uncertainty:.2f}), prioritizing stability"
            new_strategy = SystemStrategy(
                fps=5,  # Low rate
                model_type="medium",  # Don't waste on unreliable data
                confirm_frames=6,  # More confirmation needed
                storage_policy="events_only"
            )
        # 3. Risk Check (Priority 3: Only if confident)
        elif self.current_risk == RiskLevel.HIGH:
            # Only boost if we're confident (uncertainty already checked above)
            mode = "HIGH_RISK"
            decision_reason = f"Confirmed high risk (uncertainty: {self.current_uncertainty:.2f})"
            new_strategy = SystemStrategy(
                fps=30,
                model_type="large",
                confirm_frames=2,
                storage_policy="all"
            )
        # 4. Network Check (Priority 4: Lowest)
        elif self.network_status == NetworkStatus.OFFLINE:
            mode = "OFFLINE_CONSERVATIVE"
            decision_reason = "Network offline, conserving resources"
            new_strategy = SystemStrategy(
                fps=5,
                model_type="medium",
                confirm_frames=5,
                storage_policy="events_only"
            )
        else:
            mode = "ONLINE_BALANCED"
            decision_reason = "Network online, balanced mode"
            new_strategy = SystemStrategy(
                fps=15,
                model_type="medium",
                confirm_frames=4,
                storage_policy="events_only"
            )

        if self.current_strategy != new_strategy or force_publish:
            # Calculate Decision Payload (only if there was a previous strategy)
            if self.current_strategy:
                old_fps = self.current_strategy.fps
                new_fps = new_strategy.fps
                action = "maintain_inference_rate"
                
                if new_fps > old_fps:
                    action = "increase_inference_rate"
                elif new_fps < old_fps:
                    action = "decrease_inference_rate"
                
                # Log decision payload
                if self.current_strategy != new_strategy:
                    decision_payload = {
                        "action": action,
                        "from_fps": old_fps,
                        "to_fps": new_fps,
                        "reason": decision_reason
                    }
                    logger.info(json.dumps(decision_payload))

            self.current_strategy = new_strategy
            logger.info(f"Strategy Update [{mode}]: {self.current_strategy.to_dict()}")
            self.bus.publish("system_strategy_update", self.current_strategy.to_dict())

    def check_resources(self):
        # Check Disk
        total, used, free = shutil.disk_usage(self.storage_path)
        percent_free = (free / total) * 100
        
        # Ensure strategy is up to date (and republish if changed/needed)
        self.update_strategy(force_publish=True)
        
        logger.info(f"Storage: {percent_free:.1f}% free | Battery: {self.battery_level}%")

        if percent_free < 10:
             self.bus.publish("resource_warning", {"type": "storage", "level": "critical"})
        
        return {
            "storage_free_percent": percent_free,
            "battery_level": self.battery_level
        }
