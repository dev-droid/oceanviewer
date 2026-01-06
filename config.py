# OceanViewer System Configuration
# STRICT ADHERENCE TO OFFSHORE CONSTRAINTS REQUIRED

# --- System Identity ---
SYSTEM_ID = "OV_NODE_001"
VERSION = "0.1.0-MVP"

# --- Resource Constraints ---
MAX_STORAGE_GB = 500  # Max local storage
MIN_BATTERY_LEVEL = 20  # Percentage

# --- Inference Policies ---
DEFAULT_FPS = 3
BOOST_FPS = 10
CONFIDENCE_THRESHOLD_LOW = 0.5
CONFIDENCE_THRESHOLD_HIGH = 0.85

# --- Risk Policies ---
# "Better to be unsure than to create false alarms"
PREFER_UNKNOWN_OVER_FALSE_POSITIVE = True
AUTO_CONFIRM_FRAMES = 5 # Number of consistent frames required for high confidence

# --- Data Retention ---
KEEP_LOGS_DAYS = 30
KEEP_EVIDENCE_DAYS = 7 # Rolling window for non-critical
KEEP_CRITICAL_FOREVER = True # Until manual offload
