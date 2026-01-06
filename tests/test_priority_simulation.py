
import unittest
import threading
from src.core.event_bus import EventBus
from src.agents.strategy_agent import StrategyAgent
from src.core.types import RiskLevel, SystemStrategy

class TestStrategyPrioritization(unittest.TestCase):
    def test_battery_override_high_risk(self):
        bus = EventBus()
        agent = StrategyAgent(bus)
        
        # 1. Establish Baseline (Offline Conservative)
        # Default Battery 100, Network OFFLINE, Risk UNKNOWN
        self.assertEqual(agent.current_strategy.fps, 5, "Should start in OFFLINE_CONSERVATIVE (5 FPS)")
        
        # 2. Trigger High Risk
        agent.on_risk_assessment({"risk_level": "HIGH"})
        
        # Verify Escalation
        self.assertEqual(agent.current_strategy.fps, 30, "High Risk should escalate to 30 FPS")
        self.assertEqual(agent.current_strategy.model_type, "large")
        
        # 3. Trigger Critical Battery (Simulate Drain)
        agent.battery_level = 15
        agent.check_resources() # Forces update
        
        # Verify Degradation despite High Risk
        # Priority: Power (1) > Risk (2)
        print(f"Current Strategy FPS: {agent.current_strategy.fps}")
        print(f"Current Strategy Model: {agent.current_strategy.model_type}")
        
        self.assertEqual(agent.current_strategy.fps, 1, "Critical Battery should force 1 FPS")
        self.assertEqual(agent.current_strategy.model_type, "tiny")
        self.assertEqual(agent.current_strategy.storage_policy, "critical_only")

if __name__ == "__main__":
    unittest.main()
