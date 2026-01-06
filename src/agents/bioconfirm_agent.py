from src.core.event_bus import EventBus
from src.core.types import OceanEvent, RiskLevel, VisionLabel
import logging
import time
import math
import json
from collections import deque

logger = logging.getLogger("BioConfirmAgent")

class TrackCandidate:
    def __init__(self, metadata, first_timestamp):
        self.id = metadata.get('frame_id', 0) # Use frame_id as temp initial ID, or strictly internal uuid
        self.history = deque(maxlen=20)
        self.history.append(metadata)
        self.first_seen = first_timestamp
        self.last_seen = first_timestamp
        self.confirmed = False
        
    def add_observation(self, metadata, timestamp):
        self.history.append(metadata)
        self.last_seen = timestamp
        
    def check_consistency(self, min_frames):
        # 1. Multi-frame requirement
        if len(self.history) < min_frames: 
            return False
            
        # 2. Motion Consistency
        # Calculate variance of motion vectors
        motions = [h.get('motion', [0,0]) for h in self.history]
        dxs = [m[0] for m in motions]
        dys = [m[1] for m in motions]
        
        # Simple Logic: If standard deviation is low, motion is "smooth" -> Living/Vessel
        # If standard deviation is high, motion is "chaotic" -> Waves/Foam
        
        def variance(data):
            if not data: return 0
            mean = sum(data) / len(data)
            return sum((x - mean) ** 2 for x in data) / len(data)
            
        var_x = variance(dxs)
        var_y = variance(dys)
        
        # Threshold for "chaos" (Waves are chaotic)
        if var_x > 5.0 or var_y > 5.0:
            return False
            
        # 3. Exclude "Non-Living" labels specifically if we want, but user said "Is it living?"
        # The Vision agent outputs "non_living_object", we should theoretically filter that out upstream 
        # OR handle here. If Vision says "non_living", we probably shouldn't confirm it as "Bio".
        latest_label = self.history[-1].get('raw_label')
        if latest_label == "non_living_object":
            return False

        return True

class BioConfirmAgent:
    def __init__(self, event_bus: EventBus):
        self.bus = event_bus
        self.bus.subscribe("vision_detection", self.on_vision_detection)
        self.bus.subscribe("system_strategy_update", self.on_strategy_update)
        
        self.tracks = [] 
        self.required_consecutive_frames = 4 # Default
        
        # Config
        self.MATCH_THRESHOLD = 50 
        self.MAX_DROPOUT = 2.0 

    def on_strategy_update(self, strategy: dict):
        new_frames = strategy.get("confirm_frames", 4)
        if new_frames != self.required_consecutive_frames:
            logger.info(f"Adjusting Confirmation Threshold: {self.required_consecutive_frames} -> {new_frames}")
            self.required_consecutive_frames = new_frames

    def on_vision_detection(self, event: OceanEvent):
        # Determine if this detection matches an existing track
        det_box = event.metadata.get("box")
        det_center = ((det_box[0] + det_box[2])/2, (det_box[1] + det_box[3])/2)
        timestamp = time.time()
        
        matched_track = None
        for track in self.tracks:
            # Get last known center
            last_meta = track.history[-1]
            last_box = last_meta.get("box")
            last_center = ((last_box[0] + last_box[2])/2, (last_box[1] + last_box[3])/2)
            
            dist = math.hypot(det_center[0] - last_center[0], det_center[1] - last_center[1])
            
            if dist < self.MATCH_THRESHOLD:
                matched_track = track
                break
        
        if matched_track:
            # Inject confidence into metadata for history tracking
            meta_with_conf = event.metadata.copy()
            meta_with_conf['confidence'] = event.confidence
            matched_track.add_observation(meta_with_conf, timestamp)
            
            # Re-evaluate
            if not matched_track.confirmed:
                if matched_track.check_consistency(self.required_consecutive_frames):
                    matched_track.confirmed = True
                    self._publish_confirmation(event, matched_track)
                else:
                    logger.info(f"BioConfirm: Track {matched_track.id} updated but Unconfirmed (Frames: {len(matched_track.history)})")
        else:
            # Single frame cannot be confirmed
            logger.info(f"BioConfirm: New Candidate initialized (Unconfirmed)")
            
            meta_with_conf = event.metadata.copy()
            meta_with_conf['confidence'] = event.confidence
            new_track = TrackCandidate(meta_with_conf, timestamp)
            self.tracks.append(new_track)

        # Cleanup old tracks
        self.tracks = [t for t in self.tracks if timestamp - t.last_seen < self.MAX_DROPOUT]

    def _publish_confirmation(self, original_event, track):
        # Calculate average confidence
        avg_confidence = sum([m.get("confidence", 0) for m in track.history]) / len(track.history)
        
        # Latest category
        category = track.history[-1].get("raw_label", "unknown")
        
        output_payload = {
            "confirmed": True,
            "category": category,
            "confidence": round(avg_confidence, 2),
            "evidence_frames": len(track.history)
        }
        
        # STRICT JSON OUTPUT
        logger.info(json.dumps(output_payload))
        
        # Retain original ID or assign a persistent Track ID? 
        # For now, pass the event downstream as "Confirmed"
        # We might want to enrich the event metadata with the evidence count
        original_event.metadata["evidence_frames"] = len(track.history)
        self.bus.publish("confirmed_event", original_event)
