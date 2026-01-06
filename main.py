import time
import logging
import sys
import threading
from src.core.event_bus import EventBus
from src.core.types import NetworkStatus
from src.database.storage import StorageManager
from src.agents.net_status_agent import NetStatusAgent
from src.agents.vision_agent import VisionAgent
from src.agents.bioconfirm_agent import BioConfirmAgent
from src.agents.risk_agent import RiskAgent
from src.agents.sync_agent import SyncAgent
from src.agents.strategy_agent import StrategyAgent
from src.agents.alert_agent import AlertAgent
from src.database.storage import StorageManager
import config

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("oceanviewer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Main")

def main():
    logger.info("Starting OceanViewer 0.1.0-MVP - System ID: OV_NODE_001")
    
    # Core
    event_bus = EventBus()
    storage = StorageManager() # Init Storage
    
    # Agents (Init)
    # Order implies dependency graph roughly:
    # NetStatus -> Strategy
    # Vision -> BioConfirm -> Risk -> Alert -> Strategy -> Vision (Feedback)
    
    net_agent = NetStatusAgent(event_bus)
    vision_agent = VisionAgent(event_bus)
    bio_agent = BioConfirmAgent(event_bus)
    risk_agent = RiskAgent(event_bus)
    alert_agent = AlertAgent(event_bus) # New Alert System
    sync_agent = SyncAgent(event_bus, storage) # Pass Storage
    strategy_agent = StrategyAgent(event_bus) # Strategy Controller init last to catch up

    # Start
    try:
        net_agent.start()
        vision_agent.start()
        bio_agent.start() # Runs internal loop
        sync_agent.start()
        alert_agent.start()
        
        # Resource agent logic is mostly event-driven but has a check loop
        # We can add a periodic resource check to the main loop or dedicated thread
        # For MVP, let's just trigger it once
        strategy_agent.check_resources()
        
        while True:
            time.sleep(1)
            strategy_agent.check_resources() # Periodic System Check
            
    except KeyboardInterrupt:
        logger.info("Shutdown signal received.")
        logger.info("Stopping agents...")
        vision_agent.stop()
        net_agent.stop()
        logger.info("System halted.")

if __name__ == "__main__":
    main()
