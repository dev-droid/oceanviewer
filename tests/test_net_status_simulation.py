import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.event_bus import EventBus
from src.agents.net_status_agent import NetStatusAgent
from src.core.types import NetworkStatus
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_logic():
    bus = EventBus()
    agent = NetStatusAgent(bus)
    
    print(f"Initial State: {agent.current_status.name}")
    
    # 1. Start OFFLINE
    # Feed 7 successes (Should stay OFFLINE because threshold is 8)
    print("\n--- Phase 1: 7 Successes (Expect OFFLINE) ---")
    for i in range(7):
        agent._evaluate_state(True)
        print(f"Ping {i+1}: Status={agent.current_status.name} (ConsSucc={agent.consecutive_successes})")
    
    # 2. Feed 8th success (Should go ONLINE or INTERMITTENT depending on ratio)
    print("\n--- Phase 2: 8th Success (Expect Transition) ---")
    agent._evaluate_state(True)
    print(f"Ping 8: Status={agent.current_status.name}")

    if agent.current_status != NetworkStatus.ONLINE and agent.current_status != NetworkStatus.INTERMITTENT:
        print("FAIL: Did not transition after 8 successes")
    
    # 3. Force ONLINE (Assumed we got there)
    # Feed failures. Should tolerate < 5.
    print("\n--- Phase 3: Failures (Expect Tolerance) ---")
    agent.current_status = NetworkStatus.ONLINE
    agent.consecutive_failures = 0
    
    for i in range(4):
        agent._evaluate_state(False)
        print(f"Fail {i+1}: Status={agent.current_status.name} (ConsFail={agent.consecutive_failures})")
        
    if agent.current_status != NetworkStatus.ONLINE:
        print("FAIL: Flapped to OFFLINE too early")
        
    # 4. 5th Failure -> OFFLINE
    print("\n--- Phase 4: 5th Failure (Expect OFFLINE) ---")
    agent._evaluate_state(False)
    print(f"Fail 5: Status={agent.current_status.name}")
    
    if agent.current_status != NetworkStatus.OFFLINE:
        print("FAIL: Did not go OFFLINE after 5 failures")

if __name__ == "__main__":
    test_logic()
