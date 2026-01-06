import logging
import json
import time
from src.core.event_bus import EventBus
from src.core.types import RiskLevel

logger = logging.getLogger("AlertAgent")

class AlertAgent:
    def __init__(self, event_bus: EventBus):
        self.bus = event_bus
        self.bus.subscribe("risk_assessment", self.process_risk)
        
        # Deduplication state
        self.last_alert_time = 0
        self.last_alert_key = None # (risk_level, reason)
        self.COOLDOWN_SECONDS = 10 

    def start(self):
        logger.info("Alert System Initialized - Listening for Risk Assessments...")

    def stop(self):
        pass

    def process_risk(self, payload):
        """
        Process risk assessment and generate actionable alerts.
        Principles: Based on confirmed risk, clear, restrained, non-repetitive.
        """
        try:
            risk_str = payload.get("risk_level")
            reason = payload.get("reason", "Unknown risk factor")
            
            if not risk_str:
                return

            risk_level = RiskLevel[risk_str]
            
            # Filter: Only alert on HIGH or MEDIUM
            if risk_level not in [RiskLevel.HIGH, RiskLevel.MEDIUM]:
                return

            # Deduplication
            current_key = (risk_level, reason)
            now = time.time()
            
            if current_key == self.last_alert_key:
                if (now - self.last_alert_time) < self.COOLDOWN_SECONDS:
                    return # Suppress duplicate
            
            # Actionable Mapping
            alert_type = "NAVIGATION_WARNING"
            level = risk_level.name # "HIGH" or "MEDIUM"
            recommendation = ""
            
            if risk_level == RiskLevel.HIGH:
                recommendation = "Recommend immediate evasion."
            elif risk_level == RiskLevel.MEDIUM:
                recommendation = "Recommend speed reduction."

            # Generate Alert Message
            # reason comes from RiskAgent, e.g., "Large organic target in close proximity."
            full_message = f"{reason} {recommendation}"
            
            # Log for UI/Crew (keep human readable log)
            logger.warning(f"[{level}] {full_message}")
            
            # Update state
            self.last_alert_time = now
            self.last_alert_key = current_key
            
            # Publish for UI consumption
            self.bus.publish("alert_event", {
                "alert_type": alert_type,
                "level": level,
                "message": full_message,
                "timestamp": now
            })

        except Exception as e:
            logger.error(f"Alert generation error: {e}")
