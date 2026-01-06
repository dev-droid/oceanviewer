
import unittest
import time
from src.core.event_bus import EventBus
from src.agents.alert_agent import AlertAgent
from src.core.types import RiskLevel

class TestAlertFormat(unittest.TestCase):
    def test_alert_json_structure(self):
        bus = EventBus()
        agent = AlertAgent(bus)
        
        captured_events = []
        def on_alert(payload):
            captured_events.append(payload)
            
        bus.subscribe("alert_event", on_alert)
        
        # Inject Risk Event
        risk_payload = {
            "risk_level": "HIGH",
            "reason": "Large marine life detected ahead."
        }
        
        agent.process_risk(risk_payload)
        
        # Verify
        self.assertEqual(len(captured_events), 1)
        event = captured_events[0]
        
        print(f"Captured Event: {event}")
        
        self.assertEqual(event["alert_type"], "NAVIGATION_WARNING")
        self.assertEqual(event["level"], "HIGH")
        self.assertIn("Large marine life detected ahead.", event["message"])
        self.assertIn("Recommend immediate evasion.", event["message"])
        self.assertTrue(isinstance(event["timestamp"], float))

if __name__ == "__main__":
    unittest.main()
