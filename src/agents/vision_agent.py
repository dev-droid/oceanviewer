from src.core.event_bus import EventBus
from src.core.types import OceanEvent, RiskLevel, EventType, Evidence, VisionLabel
import threading
import time
import datetime
import uuid
import logging
import random
import json

logger = logging.getLogger("VisionAgent")

class VisionAgent:
    def __init__(self, event_bus: EventBus):
        self.bus = event_bus
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._inference_loop)
        self.fps = 3 # Default start FPS
        self.model_type = "medium"
        self.frame_id = 100000 
        
        # Subscribe
        self.bus.subscribe("system_strategy_update", self.on_strategy_update)

    def on_strategy_update(self, strategy: dict):
        new_fps = strategy.get("fps", 15)
        new_model = strategy.get("model_type", "medium")
        
        if new_model != self.model_type:
            logger.info(f"Switching Model: {self.model_type} -> {new_model}")
            self.model_type = new_model

        if new_fps != self.fps:
            logger.info(f"Adjusting FPS: {self.fps} -> {new_fps}")
            self.fps = new_fps

    def start(self):
        logger.info("Vision Model Loaded. Starting Inference (Local Only)...")
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join()

    def _inference_loop(self):
        while not self._stop_event.is_set():
            # 1. Capture Frame (Dynamic Rate)
            current_sleep = 1.0 / max(self.fps, 1) # Prevent div by zero
            time.sleep(current_sleep)
            self.frame_id += 1
            
            # 2. Run Inference
            detections = self._mock_model_inference()
            
            # 3. Output logic (Always log if there's a detection, or maybe structured log for every frame? 
            # User request showed a specific format for "Output". Usually implies when something is found.)
            if detections:
                output_payload = {
                    "detections": detections,
                    "frame_id": self.frame_id
                }
                logger.info(json.dumps(output_payload))
                
                # Publish event for internal system (mapping back to internal types)
                # We take the primary/highest confidence detection for the event bus for now
                if len(detections) > 0:
                     self._publish_internal_event(detections[0])

    def _mock_model_inference(self):
        # SIMULATION ONLY: mimicking a local model
        
        # To test BioConfirm, we need COHERENCE.
        # Let's simulate:
        # 1. 50% chance of "No Object"
        # 2. If Object, it moves slightly from previous position
        
        if not hasattr(self, 'sim_target'):
            self.sim_target = None
            
        if self.sim_target is None:
            # Maybe spawn a new target
            if random.random() < 0.2: # Increased spawn rate for testing
                self.sim_target = {
                    "cat": VisionLabel.LARGE_MARINE_LIFE,
                    "box": [100, 100, 260, 260], # Width 160 > 150
                    "life": 15 # Lasts longer
                }
        
        if self.sim_target:
            # Move it (Collision course: dy >= -1.0 means moving down or holding y?)
            # RiskAgent: if dy >= -1.0: HIGH (Close proximity)
            # We use dy = 2.0 (moving down/closer)
            dx = 2
            dy = 2 
            b = self.sim_target["box"]
            self.sim_target["box"] = [b[0]+dx, b[1]+dy, b[2]+dx, b[3]+dy]
            self.sim_target["life"] -= 1
            
            detection_res = [{
                "category": self.sim_target["cat"].value,
                "confidence": 0.9,
                "bbox": self.sim_target["box"],
                "motion": [float(dx), float(dy)]
            }]
            
            if self.sim_target["life"] <= 0:
                self.sim_target = None
                
            return detection_res
            
        return []

    def _publish_internal_event(self, primary_detection):
        # Internal packaging for other agents
        event = OceanEvent(
            event_id=f"DET_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.datetime.now(),
            event_type=EventType.UNKNOWN, 
            risk_level=RiskLevel.UNKNOWN,
            confidence=primary_detection["confidence"],
            evidence=Evidence(image_paths=["/tmp/mock_det.jpg"]),
            metadata={
                "raw_label": primary_detection["category"],
                "box": primary_detection["bbox"],
                "motion": primary_detection["motion"],
                "frame_id": self.frame_id
            }
        )
        self.bus.publish("vision_detection", event)
