import json
import logging
from src.core.event_bus import EventBus
from src.core.types import OceanEvent, RiskLevel

logger = logging.getLogger("RiskAgent")

class RiskAgent:
    def __init__(self, event_bus: EventBus):
        self.bus = event_bus
        self.bus.subscribe("confirmed_event", self.assess_risk)
        
        # Mock Telemetry for MVP
        self.current_speed_knots = 12.0
        self.current_heading = 0.0 # North

    def assess_risk(self, event: OceanEvent):
        """
        Evaluate risk based on strict user rules:
        - LOW/MEDIUM/HIGH only.
        - Must explain source of risk.
        - Insufficient info -> MEDIUM.
        """
        
        try:
            # Extract data
            detections = event.metadata.get("detections", [])
            # In confirmed event, we might have specific 'bbox' and 'motion' in metadata 
            # or we need to look at the 'latest_observation' which bio agent should have passed.
            # BioConfirm passes the *Event* object. 
            # Let's assume the event metadata contains the 'bbox' and 'motion' from the *latest* frame that triggered confirmation.
            
            risk_level = RiskLevel.MEDIUM
            reason = "Insufficient data to determine trajectory."
            uncertainty = True
            
            # Use the first detection if available (BioConfirm usually focuses on one track)
            # We explicitly check the 'motion' and 'bbox' keys if injected by BioConfirm, 
            # otherwise fall back to raw detection list.
            
            bbox = event.metadata.get("bbox") or event.metadata.get("box")
            motion = event.metadata.get("motion")
            
            # Fallback if BioConfirm didn't inject flat keys
            if not bbox and detections:
                bbox = detections[0].get("bbox") or detections[0].get("box")
                motion = detections[0].get("motion")

            if bbox and motion:
                width = bbox[2] - bbox[0]
                dy = motion[1] # Vertical motion
                
                # Heuristic Logic
                # 1. Close Proximity (Large BBox) + Moving Closer (dy > 0 or small dy)
                if width > 150: # Arbitrary "Close" threshold
                    if dy >= -1.0: # Not moving away significantly
                        risk_level = RiskLevel.HIGH
                        reason = "Large organic target in close proximity/collision path."
                        uncertainty = False
                    else:
                        risk_level = RiskLevel.MEDIUM
                        reason = "Large target moving away, but proximity warrants caution."
                        uncertainty = False
                
                # 2. Distant but closing fast
                elif dy > 5.0:
                    risk_level = RiskLevel.MEDIUM
                    reason = "Distant target closing rapidly."
                    uncertainty = False
                    
                # 3. Moving away / Neutral
                else:
                    risk_level = RiskLevel.LOW
                    reason = "Target moving away or keeping distance."
                    uncertainty = False
            else:
                 # Check if explicitly "Bio Confirmed" but missing motion data
                 if event.metadata.get("confirmed"):
                     risk_level = RiskLevel.MEDIUM
                     reason = "Confirmed living entity but motion data unavailable."
                     uncertainty = True

            # Enforce "No Exaggeration" - Double check HIGH
            if risk_level == RiskLevel.HIGH and event.confidence < 0.6:
                 risk_level = RiskLevel.MEDIUM
                 reason = "Potential high risk but confidence low. Downgraded."
                 uncertainty = True

            # Update Event
            event.risk_level = risk_level
            
            # Calculate uncertainty float
            uncertainty_score = round(1.0 - event.confidence, 2)
            if uncertainty: # If heuristic flagged uncertainty
                 uncertainty_score = max(uncertainty_score, 0.5)

            # Output JSON as requested
            result = {
                "risk_level": risk_level.name,
                "reason": reason,
                "uncertainty": uncertainty_score
            }
            
            logger.info(json.dumps(result))
            
            # Publish Dict for AlertAgent/StrategyAgent (Lightweight)
            self.bus.publish("risk_assessment", result)
            
            # Publish Full Event for SyncAgent (Heavyweight)
            # The event object has been updated in place (event.risk_level = ...)
            self.bus.publish("risk_assessed_event", event)
            
        except Exception as e:
            logger.error(f"Risk Assessment Failed: {e}")
            # Fail safe
            event.risk_level = RiskLevel.MEDIUM
            logger.info(json.dumps({
                "risk_level": "MEDIUM", 
                "reason": "Internal Error - Failsafe", 
                "uncertainty": 1.0
            }))
