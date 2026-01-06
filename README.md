# OceanViewer - Offline Marine Observation System

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Status](https://img.shields.io/badge/status-MVP-orange.svg)

[中文文档](README_CN.md)

## Overview

OceanViewer is an **edge-first** autonomous marine life monitoring system designed for vessel/offshore platforms. The system operates autonomously in network-constrained or completely offline environments, achieving real-time object detection, risk assessment, intelligent synchronization, and adaptive strategy scheduling through multi-agent collaboration.

### Key Features

- **🌊 Fully Offline Operation**: No continuous network connection required, all inference and storage completed locally
- **🤖 Multi-Agent Architecture**: 7 specialized agents working collaboratively with loosely coupled design
- **⚡ Adaptive Inference Scheduling**: Dynamically adjusts FPS and model size based on battery, risk, and network status
- **📡 Tiered Data Synchronization**: Intelligently selects sync strategy based on network quality (offline/intermittent/online)
- **🔒 Conservative Decision Mechanism**: Prioritizes system stability when uncertainty exceeds threshold
- **🚨 Local Real-time Alerts**: High-risk events trigger onboard alerts with 10-second cooldown to prevent flooding

---

## System Architecture

### Agent Collaboration Flow

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│ VisionAgent │─────▶│ BioConfirm   │─────▶│ RiskAgent   │
│  (Detect)   │      │   Agent      │      │ (Assessment)│
└─────────────┘      │  (Confirm)   │      └──────┬──────┘
                     └──────────────┘             │
                                                  ▼
       ┌──────────────────────────────────────────────┐
       │                                              │
       ▼                                              ▼
┌─────────────┐                              ┌──────────────┐
│ AlertAgent  │                              │  SyncAgent   │
│  (Alert)    │                              │   (Sync)     │
└─────────────┘                              └──────────────┘
       │                                              │
       │         ┌─────────────────┐                  │
       └────────▶│ StrategyAgent   │◀─────────────────┘
                 │  (Scheduling)   │
                 └────────┬────────┘
                          │
                          ▼
                  ┌──────────────┐
                  │NetStatusAgent│
                  │  (Monitor)   │
                  └──────────────┘
```

### Agent Responsibilities

| Agent           | Responsibility                                | Input                  | Output                       |
|-----------------|-----------------------------------------------|------------------------|------------------------------|
| **VisionAgent** | YOLOv11 object detection                      | Video frames           | Bounding boxes + confidence  |
| **BioConfirmAgent** | Biological feature verification               | Detection results      | Confirmed events             |
| **RiskAgent**   | Risk level assessment (LOW/MEDIUM/HIGH)       | Confirmed events       | Risk level + uncertainty     |
| **AlertAgent**  | High-risk local alerts (10s cooldown)         | Risk assessment        | Alert JSON                   |
| **SyncAgent**   | Tiered sync decision + rate limiting          | Risk events + network  | Sync decision                |
| **StrategyAgent** | Adaptive inference scheduling (FPS/model/storage) | Battery + risk + network + uncertainty | System strategy |
| **NetStatusAgent** | Network connectivity monitoring (sliding window + hysteresis) | Periodic checks | Network status |

---

## Quick Start

### Requirements

- **Python**: 3.8+
- **Dependencies**: See `requirements.txt`
- **Optional**: CUDA 11.8+ (GPU acceleration)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/dev-droid/oceanviewer.git
cd oceanviewer

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download YOLOv11 model weights (optional, auto-downloads by default)
# Place yolov11m.pt in project root
```

### Basic Usage

```bash
# Start system
python main.py

# Real-time logs output to oceanviewer.log and terminal
```

### Expected Output

```
2026-01-06 12:00:00 [VisionAgent] INFO: {"detections": 2, "confidence": 0.92, "processing_time_ms": 45}
2026-01-06 12:00:01 [RiskAgent] INFO: {"risk_level": "HIGH", "reason": "Large marine mammal detected", "uncertainty": 0.15}
2026-01-06 12:00:01 [AlertAgent] INFO: {"alert_type": "NAVIGATION_WARNING", "level": "HIGH", "message": "Large marine life detected - recommend speed reduction or course adjustment", "timestamp": 1704518401}
2026-01-06 12:00:01 [StrategyAgent] INFO: {"action": "increase_inference_rate", "from_fps": 5, "to_fps": 30, "reason": "Confirmed high risk (uncertainty: 0.15)"}
2026-01-06 12:00:02 [SyncAgent] INFO: Sync Decision for evt_001: ALLOWED (INTERMITTENT - HIGH PRIORITY (Rate OK))
```

---

## Industrial Deployment Guide

### 1. Production Configuration

#### 1.1 Hardware Recommendations

| Component | Minimum           | Recommended           |
|-----------|-------------------|-----------------------|
| **CPU**   | 4-core 2.5GHz     | 8-core 3.0GHz+        |
| **RAM**   | 8GB               | 16GB+                 |
| **GPU**   | -                 | NVIDIA T4 / RTX 3060  |
| **Storage** | 50GB SSD        | 200GB NVMe SSD        |
| **Network** | Intermittent satellite | 4G/5G/Satellite  |

#### 1.2 System Parameter Tuning

Edit `config.py`:

```python
# Network detection
PING_TARGET = "8.8.8.8"  # Change to satellite gateway IP
PING_INTERVAL = 30       # Recommend 60s for satellite

# Inference configuration
DEFAULT_FPS = 5          # Conservative starting point
YOLO_CONFIDENCE = 0.5    # Adjust based on false positive rate

# Sync rate limiting (in sync_agent.py)
HIGH_PRIORITY_GAP = 2.0  # High priority minimum interval (seconds)
STANDARD_GAP = 0.5       # Standard sync minimum interval
```

#### 1.3 Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persistent data volumes
VOLUME ["/app/data", "/app/logs"]

CMD ["python", "main.py"]
```

```bash
# Build image
docker build -t oceanviewer:latest .

# Run container
docker run -d \
  --name oceanviewer \
  --restart=unless-stopped \
  -v /data/oceanviewer:/app/data \
  -v /logs/oceanviewer:/app/logs \
  --device /dev/video0:/dev/video0 \  # Map camera
  oceanviewer:latest
```

### 2. GPU Acceleration

```bash
# Install CUDA version of PyTorch
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Verify GPU availability
python -c "import torch; print(torch.cuda.is_available())"
```

Edit `src/agents/vision_agent.py`:

```python
self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
self.model = YOLO("yolov11m.pt").to(self.device)
```

### 3. Data Persistence

System uses SQLite for event storage (`ocean_data.db`). Production recommendations:

```bash
# Regular database backup
0 2 * * * sqlite3 /app/data/ocean_data.db ".backup '/backup/ocean_$(date +\%Y\%m\%d).db'"

# Database optimization
sqlite3 ocean_data.db "VACUUM;"
sqlite3 ocean_data.db "ANALYZE;"
```

### 4. Log Management

```python
# Log rotation configuration (edit main.py)
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    "oceanviewer.log",
    maxBytes=50*1024*1024,  # 50MB
    backupCount=5
)
```

### 5. Monitoring & Alerting

#### 5.1 Prometheus Integration

```python
# Install prometheus_client
pip install prometheus-client

# Add to main.py
from prometheus_client import start_http_server, Counter, Gauge

detection_counter = Counter('ocean_detections_total', 'Total detections')
risk_gauge = Gauge('ocean_risk_level', 'Current risk level')

# Start metrics endpoint
start_http_server(8000)
```

#### 5.2 Health Check Endpoint

```python
# healthcheck.py
import sqlite3
import sys

try:
    conn = sqlite3.connect("ocean_data.db", timeout=5)
    conn.close()
    sys.exit(0)
except:
    sys.exit(1)
```

```bash
# Add health check in container
HEALTHCHECK --interval=30s --timeout=5s \
  CMD python healthcheck.py || exit 1
```

### 6. Satellite Uplink Integration

Edit `_execute_system_sync` in `src/agents/sync_agent.py`:

```python
def _execute_system_sync(self, event: OceanEvent):
    try:
        # Call satellite modem API
        response = requests.post(
            "http://satellite-modem/api/transmit",
            json=event.to_dict(),
            timeout=30
        )
        if response.status_code == 200:
            self.storage.mark_synced(event.event_id)
            logger.info(f"Uplink SUCCESS: {event.event_id}")
    except Exception as e:
        logger.error(f"Uplink FAILED: {e}")
        # Event remains local for retry
```

### 7. Security Hardening

```bash
# 1. Use environment variables for sensitive configuration
export SATELLITE_API_KEY="your_key_here"
export DB_ENCRYPTION_KEY="your_encryption_key"

# 2. Database encryption (use SQLCipher)
pip install pysqlcipher3

# 3. Limit container privileges
docker run --security-opt=no-new-privileges:true \
  --cap-drop=ALL \
  --cap-add=NET_ADMIN \  # Only necessary permissions
  oceanviewer:latest
```

---

## Testing

```bash
# Run unit tests
python -m pytest tests/ -v

# Test network status switching
python tests/test_netstatus_logic.py

# Test sync logic
python tests/test_sync_logic.py

# Test strategy priority
python tests/test_priority_simulation.py
```

---

## Troubleshooting

### Issue 1: GPU Not Recognized

```bash
# Check CUDA version
nvidia-smi

# Reinstall matching PyTorch
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Issue 2: Database Locked

```bash
# Check processes
lsof ocean_data.db

# Force unlock
fuser -k ocean_data.db
```

### Issue 3: Memory Leak

```python
# Add to vision_agent.py
import gc
gc.collect()
torch.cuda.empty_cache()  # GPU environment
```

---

## Performance Benchmarks

| Scenario              | FPS  | Latency | CPU Usage | GPU Usage |
|-----------------------|------|---------|-----------|-----------|
| Offline conservative  | 5    | 200ms   | 25%       | -         |
| Online balanced       | 15   | 67ms    | 45%       | 30%       |
| High-risk response    | 30   | 33ms    | 80%       | 60%       |

Test Environment: Intel i7-10700K, NVIDIA RTX 3060, Ubuntu 22.04

---

## Roadmap

- [x] MVP: 7-Agent collaborative architecture
- [x] Adaptive strategy scheduling
- [x] Tiered data synchronization
- [ ] Real-time video stream integration
- [ ] GPU acceleration optimization
- [ ] Satellite communication module integration
- [ ] Web console
- [ ] Multi-node federated learning

---

## Contributing

Issues and Pull Requests welcome! Please follow:

1. Fork this repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file

---

## Contact

**Developer**: dev-droid  
**Project Homepage**: https://github.com/dev-droid/oceanviewer

---

## Acknowledgments

- [Ultralytics YOLOv11](https://github.com/ultralytics/ultralytics) - Object detection model
- [SQLite](https://www.sqlite.org/) - Embedded database
- [PyTorch](https://pytorch.org/) - Deep learning framework
