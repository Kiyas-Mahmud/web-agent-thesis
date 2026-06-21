"""
State Hash Computer

Computes state hashes and detects loops in browser interaction trajectories.
"""

from typing import Union, List, Dict, Optional
from pathlib import Path
import hashlib
import logging
from PIL import Image
from collections import deque

try:
    import imagehash
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False
    logging.warning("imagehash not available. Perceptual hashing will use fallback method.")

from .metric_schema import StateHashMetrics, MetricThresholds

logger = logging.getLogger(__name__)


class StateHashComputer:
    """
    Computes state hashes for loop detection and state tracking.
    
    Features:
    - SHA-256 cryptographic hash for exact state matching
    - Perceptual hash for similar state detection
    - Loop detection based on state history
    """
    
    def __init__(self, thresholds: MetricThresholds = None):
        """
        Initialize state hash computer.
        
        Args:
            thresholds: Metric thresholds for loop detection
        """
        self.thresholds = thresholds or MetricThresholds()
        
        # State tracking
        self.state_history: deque = deque(maxlen=self.thresholds.loop_history_size)
        self.state_counts: Dict[str, int] = {}
        self.perceptual_history: deque = deque(maxlen=self.thresholds.loop_history_size)
        
        # Previous hashes for diff computation
        self.prev_state_hash: Optional[str] = None
        self.prev_perceptual_hash: Optional[str] = None
        
        if not IMAGEHASH_AVAILABLE:
            logger.warning("Perceptual hashing using fallback method - install 'imagehash' for better results")
    
    def compute_hashes(
        self,
        img: Union[str, Path, Image.Image]
    ) -> StateHashMetrics:
        """
        Compute state hashes and check for loops.
        
        Args:
            img: Image to hash (path or PIL Image)
        
        Returns:
            StateHashMetrics object with hash information
        """
        # Load image
        if isinstance(img, (str, Path)):
            image = Image.open(img).convert('RGB')
        elif isinstance(img, Image.Image):
            image = img.convert('RGB')
        else:
            raise TypeError(f"Unsupported image type: {type(img)}")
        
        # Compute SHA-256 hash
        state_hash = self._compute_sha256_hash(image)
        
        # Compute perceptual hash
        perceptual_hash = self._compute_perceptual_hash(image)
        
        # Compute perceptual hash difference from previous state
        perceptual_hash_diff = None
        if self.prev_perceptual_hash:
            perceptual_hash_diff = self._hamming_distance(
                perceptual_hash,
                self.prev_perceptual_hash
            )
        
        # Check if duplicate state
        is_duplicate = state_hash == self.prev_state_hash
        
        # Update state tracking
        if state_hash not in self.state_counts:
            self.state_counts[state_hash] = 0
        self.state_counts[state_hash] += 1
        
        state_occurrences = self.state_counts[state_hash]
        
        # Add to history
        self.state_history.append(state_hash)
        self.perceptual_history.append(perceptual_hash)
        
        # Detect loops
        loop_detected = self._detect_loop(state_hash, state_occurrences)
        
        # Update previous hashes
        self.prev_state_hash = state_hash
        self.prev_perceptual_hash = perceptual_hash
        
        return StateHashMetrics(
            state_hash=state_hash,
            perceptual_hash=perceptual_hash,
            perceptual_hash_diff=perceptual_hash_diff,
            is_duplicate=is_duplicate,
            loop_detected=loop_detected,
            state_occurrences=state_occurrences
        )
    
    def _compute_sha256_hash(self, image: Image.Image) -> str:
        """
        Compute SHA-256 hash of image.
        
        Returns hex digest string.
        """
        # Get image bytes
        img_bytes = image.tobytes()
        
        # Compute hash
        hash_obj = hashlib.sha256(img_bytes)
        return hash_obj.hexdigest()
    
    def _compute_perceptual_hash(self, image: Image.Image) -> str:
        """
        Compute perceptual hash of image.
        
        Perceptual hashes are similar for visually similar images.
        """
        if IMAGEHASH_AVAILABLE:
            # Use imagehash library (difference hash is fast and effective)
            phash = imagehash.dhash(image, hash_size=8)
            return str(phash)
        else:
            # Fallback: simple thumbnail-based hash
            return self._compute_thumbnail_hash(image)
    
    def _compute_thumbnail_hash(self, image: Image.Image, size: int = 8) -> str:
        """
        Fallback perceptual hash using thumbnail method.
        
        Args:
            image: PIL Image
            size: Thumbnail size (size x size)
        
        Returns:
            Hex string representing hash
        """
        # Resize to small thumbnail
        thumb = image.resize((size, size), Image.LANCZOS).convert('L')
        
        # Get pixel data
        pixels = list(thumb.getdata())
        
        # Compute average
        avg = sum(pixels) / len(pixels)
        
        # Create binary hash (1 if pixel > avg, 0 otherwise)
        bits = ''.join('1' if p > avg else '0' for p in pixels)
        
        # Convert to hex
        hex_hash = hex(int(bits, 2))[2:].zfill(16)
        
        return hex_hash
    
    def _hamming_distance(self, hash1: str, hash2: str) -> int:
        """
        Compute Hamming distance between two hash strings.
        
        Returns number of differing bits.
        """
        if IMAGEHASH_AVAILABLE:
            try:
                # Use imagehash's built-in comparison
                import imagehash
                h1 = imagehash.hex_to_hash(hash1)
                h2 = imagehash.hex_to_hash(hash2)
                return h1 - h2
            except Exception as e:
                logger.warning(f"imagehash comparison failed: {e}")
        
        # Fallback: string-based comparison
        if len(hash1) != len(hash2):
            logger.warning(f"Hash length mismatch: {len(hash1)} vs {len(hash2)}")
            return len(hash1)  # Maximum distance
        
        # Convert hex to binary and compute distance
        try:
            bin1 = bin(int(hash1, 16))[2:].zfill(len(hash1) * 4)
            bin2 = bin(int(hash2, 16))[2:].zfill(len(hash2) * 4)
            distance = sum(b1 != b2 for b1, b2 in zip(bin1, bin2))
            return distance
        except ValueError:
            logger.error(f"Failed to compute Hamming distance for {hash1}, {hash2}")
            return 0
    
    def _detect_loop(self, state_hash: str, occurrences: int) -> bool:
        """
        Detect if we're in a loop based on state history.
        
        Args:
            state_hash: Current state hash
            occurrences: Number of times this state has been seen
        
        Returns:
            True if loop detected
        """
        # Method 1: State seen too many times
        if occurrences >= self.thresholds.loop_occurrence_threshold:
            logger.info(f"Loop detected: state {state_hash[:8]}... seen {occurrences} times")
            return True
        
        # Method 2: Check for recent repeated states in history
        if len(self.state_history) >= 4:
            recent_states = list(self.state_history)[-4:]
            unique_recent = set(recent_states)
            
            # If last 4 states contain only 1-2 unique states, likely looping
            if len(unique_recent) <= 2:
                logger.info(f"Loop detected: only {len(unique_recent)} unique states in recent history")
                return True
        
        return False
    
    def reset(self):
        """Reset state tracking (e.g., for new trajectory)"""
        self.state_history.clear()
        self.state_counts.clear()
        self.perceptual_history.clear()
        self.prev_state_hash = None
        self.prev_perceptual_hash = None
        logger.debug("State hash computer reset")
    
    def get_unique_state_count(self) -> int:
        """Get number of unique states visited"""
        return len(self.state_counts)
    
    def get_duplicate_count(self) -> int:
        """Get number of duplicate states (states seen more than once)"""
        return sum(1 for count in self.state_counts.values() if count > 1)
    
    def get_loop_count(self) -> int:
        """Get number of states that appear to be in loops"""
        return sum(1 for count in self.state_counts.values() 
                  if count >= self.thresholds.loop_occurrence_threshold)
    
    def get_state_summary(self) -> Dict[str, int]:
        """Get summary statistics about states"""
        return {
            'total_states': len(self.state_history),
            'unique_states': self.get_unique_state_count(),
            'duplicate_states': self.get_duplicate_count(),
            'loop_states': self.get_loop_count()
        }
