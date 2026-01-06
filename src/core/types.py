from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime

class NetworkStatus(Enum):
    ONLINE = auto()
    INTERMITTENT = auto()
    OFFLINE = auto()

class RiskLevel(Enum):
    LOW = auto()      # Routine, log locally
    MEDIUM = auto()   # Potential interest, sync summaries when possible
    HIGH = auto()     # Critical, immediate action/sync required
    UNKNOWN = auto()  # "Unknown Living Object" - treat with caution

class EventType(Enum):
    MARINE_LIFE = "marine_life" 
    # Keeping generic types for the Event Bus, but Vision Agent will be more specific in metadata or a new field.
    # Actually user requested strict output categories. It's better to align EventType or create a specific DetectionClass.
    VESSEL = "vessel"
    DEBRIS = "debris"
    SYSTEM_STATUS = "system_status"
    UNKNOWN = "unknown"

class VisionLabel(Enum):
    LARGE_MARINE_LIFE = "large_marine_life"
    SMALL_MARINE_LIFE = "small_marine_life"
    HUMAN_OR_LIFE_RAFT = "human_or_life_raft"
    UNKNOWN_LIVING_OBJECT = "unknown_living_object"
    NON_LIVING_OBJECT = "non_living_object"

@dataclass
class Evidence:
    image_paths: list[str] = field(default_factory=list)
    clip_path: Optional[str] = None
    feature_vectors: Optional[list[float]] = None # For multi-frame confirmation

@dataclass
class OceanEvent:
    event_id: str
    timestamp: datetime
    event_type: EventType
    risk_level: RiskLevel
    confidence: float
    evidence: Evidence
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Status flags
    synced: bool = False
    processed_locally: bool = False

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.event_type.value,
            "risk": self.risk_level.name,
            "confidence": self.confidence,
            "synced": self.synced
        }

class SystemMode(Enum):
    PASSIVE = "PASSIVE"         # Low power / Passive monitoring
    ACTIVE = "ACTIVE"           # Standard operation
    CRITICAL = "CRITICAL"       # High risk or critical battery
    CONSERVATIVE = "CONSERVATIVE" # Offline / Storage saving

@dataclass
class SystemStrategy:
    fps: int
    model_type: str # "tiny", "medium", "large"
    confirm_frames: int
    storage_policy: str # "all", "events_only", "critical_only"

    def to_dict(self):
        return {
            "fps": self.fps,
            "model_type": self.model_type,
            "confirm_frames": self.confirm_frames,
            "storage_policy": self.storage_policy
        }
