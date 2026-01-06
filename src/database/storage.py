import sqlite3
import json
from datetime import datetime
from src.core.types import OceanEvent, RiskLevel
import logging
import os

logger = logging.getLogger("Storage")

class StorageManager:
    def __init__(self, db_path: str = "ocean_data.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS events
                     (event_id TEXT PRIMARY KEY,
                      timestamp TEXT,
                      type TEXT,
                      risk TEXT,
                      confidence REAL,
                      evidence TEXT, 
                      synced INTEGER,
                      meta TEXT)''')
        conn.commit()
        conn.close()

    def save_event(self, event: OceanEvent):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Serialize complex objects
            evidence_json = json.dumps(event.evidence.__dict__)
            meta_json = json.dumps(event.metadata)
            
            c.execute('''INSERT OR REPLACE INTO events VALUES (?,?,?,?,?,?,?,?)''',
                      (event.event_id, 
                       event.timestamp.isoformat(),
                       event.event_type.value,
                       event.risk_level.name,
                       event.confidence,
                       evidence_json,
                       1 if event.synced else 0,
                       meta_json))
            conn.commit()
            conn.close()
            logger.info(f"Event {event.event_id} saved locally. Risk: {event.risk_level.name}")
        except Exception as e:
            logger.error(f"DB Error: {e}")

    def get_pending_sync(self):
        # Retrieve events that need syncing
        pass

    def mark_synced(self, event_id: str):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("UPDATE events SET synced=1 WHERE event_id=?", (event_id,))
            conn.commit()
            conn.close()
            logger.info(f"Event {event_id} marked as SYNCED in system storage.")
        except Exception as e:
            logger.error(f"DB Error marking synced: {e}")
