
import unittest
import datetime
import os
import sqlite3
import logging
import traceback
from src.core.event_bus import EventBus
from src.agents.sync_agent import SyncAgent
from src.core.types import NetworkStatus, RiskLevel, OceanEvent, EventType, Evidence
from src.database.storage import StorageManager

# Configure logging to stdout
logging.basicConfig(level=logging.DEBUG)

class TestSyncLogic(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_sync.db"
        # Clean start
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except PermissionError:
                print("Permissions error removing DB in setUp")
            
        self.bus = EventBus()
        self.storage = StorageManager(self.test_db)
        self.agent = SyncAgent(self.bus, self.storage)

    def tearDown(self):
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except PermissionError:
                print("Permissions error removing DB in tearDown")

    def is_event_synced_in_db(self, event_id):
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT synced FROM events WHERE event_id=?", (event_id,))
        row = cursor.fetchone()
        conn.close()
        return row and row[0] == 1

    def create_mock_event(self, risk: RiskLevel, evt_id_suffix=""):
        return OceanEvent(
            event_id=f"test_evt_{evt_id_suffix}",
            timestamp=datetime.datetime.now(),
            event_type=EventType.UNKNOWN,
            risk_level=risk,
            confidence=0.9,
            evidence=Evidence()
        )

    def test_offline_blocks_all(self):
        try:
            self.agent.update_network_status(NetworkStatus.OFFLINE)
            event = self.create_mock_event(RiskLevel.HIGH, "off")
            self.agent.handle_final_event(event) 
            self.assertFalse(self.is_event_synced_in_db(event.event_id), "OFFLINE should block HIGH risk sync")
        except Exception:
            traceback.print_exc()
            raise

    def test_intermittent_allows_high_only(self):
        try:
            self.agent.update_network_status(NetworkStatus.INTERMITTENT)
            
            # Test Low Risk
            low_risk_event = self.create_mock_event(RiskLevel.LOW, "int_low")
            self.agent.handle_final_event(low_risk_event)
            self.assertFalse(self.is_event_synced_in_db(low_risk_event.event_id), "INTERMITTENT should block LOW risk")
            
            # Test High Risk
            high_risk_event = self.create_mock_event(RiskLevel.HIGH, "int_high")
            self.agent.handle_final_event(high_risk_event)
            self.assertTrue(self.is_event_synced_in_db(high_risk_event.event_id), "INTERMITTENT should allow HIGH risk")
        except Exception:
            traceback.print_exc()
            raise

    def test_online_allows_all(self):
        try:
            self.agent.update_network_status(NetworkStatus.ONLINE)
            event = self.create_mock_event(RiskLevel.LOW, "onl")
            self.agent.handle_final_event(event)
            self.assertTrue(self.is_event_synced_in_db(event.event_id), "ONLINE should allow any sync")
        except Exception:
            traceback.print_exc()
            raise

if __name__ == "__main__":
    unittest.main()
