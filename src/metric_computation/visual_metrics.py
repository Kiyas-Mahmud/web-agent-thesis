"""
Visual Metrics Computer

Computes visual difference scores between before/after screenshots.
"""

from typing import Union, Tuple
from pathlib import Path
import time
import logging
import numpy as np
from PIL import Image

try:
    from skimage.metrics import structural_similarity as ssim
    SSIM_AVAILABLE = True
except ImportError:
    SSIM_AVAILABLE = False
    logging.warning("scikit-image not available. SSIM computation will be disabled.")

from .metric_schema import VisualMetrics, ChangeLevel, MetricThresholds

logger = logging.getLogger(__name__)


class VisualMetricsComputer:
    """
    Computes visual difference metrics between images.
    
    Supports:
    - Pixel-level difference
    - Structural Similarity Index (SSIM)
    - Mean Squared Error (MSE)
    """
    
    def __init__(self, thresholds: MetricThresholds = None):
        """
        Initialize visual metrics computer.
        
        Args:
            thresholds: Metric thresholds for change classification
        """
        self.thresholds = thresholds or MetricThresholds()
        
        if not SSIM_AVAILABLE:
            logger.warning("SSIM computation unavailable - install scikit-image")
    
    def compute_metrics(
        self,
        img1: Union[str, Path, Image.Image],
        img2: Union[str, Path, Image.Image]
    ) -> VisualMetrics:
        """
        Compute all visual metrics between two images.
        
        Args:
            img1: First image (path or PIL Image)
            img2: Second image (path or PIL Image)
        
        Returns:
            VisualMetrics object with all computed metrics
        """
        start_time = time.time()
        
        # Load images
        image1 = self._load_image(img1)
        image2 = self._load_image(img2)
        
        # Ensure same size
        if image1.size != image2.size:
            logger.warning(f"Image size mismatch: {image1.size} vs {image2.size}. Resizing.")
            image2 = image2.resize(image1.size, Image.LANCZOS)
        
        # Convert to numpy arrays
        arr1 = np.array(image1)
        arr2 = np.array(image2)
        
        # Compute pixel difference
        pixel_diff = self._compute_pixel_diff(arr1, arr2)
        
        # Compute MSE
        mse = self._compute_mse(arr1, arr2)
        
        # Compute SSIM
        if SSIM_AVAILABLE:
            ssim_score = self._compute_ssim(arr1, arr2)
        else:
            # Fallback: estimate SSIM from pixel diff
            ssim_score = 1.0 - pixel_diff
        
        # Classify change level
        change_level = self.thresholds.classify_visual_change(pixel_diff, ssim_score)
        
        computation_time = (time.time() - start_time) * 1000  # Convert to ms
        
        return VisualMetrics(
            pixel_diff_score=pixel_diff,
            ssim_score=ssim_score,
            mse=mse,
            change_level=change_level,
            computation_time_ms=computation_time
        )
    
    def _load_image(self, img: Union[str, Path, Image.Image]) -> Image.Image:
        """Load image from path or return PIL Image"""
        if isinstance(img, (str, Path)):
            return Image.open(img).convert('RGB')
        elif isinstance(img, Image.Image):
            return img.convert('RGB')
        else:
            raise TypeError(f"Unsupported image type: {type(img)}")
    
    def _compute_pixel_diff(self, arr1: np.ndarray, arr2: np.ndarray) -> float:
        """
        Compute normalized pixel-level difference.
        
        Returns value between 0 (identical) and 1 (completely different).
        """
        # Compute absolute difference
        diff = np.abs(arr1.astype(float) - arr2.astype(float))
        
        # Normalize to 0-1 range
        # Maximum possible difference is 255 per pixel per channel
        max_diff = 255.0
        normalized_diff = np.mean(diff) / max_diff
        
        return float(normalized_diff)
    
    def _compute_mse(self, arr1: np.ndarray, arr2: np.ndarray) -> float:
        """
        Compute Mean Squared Error between images.
        """
        mse = np.mean((arr1.astype(float) - arr2.astype(float)) ** 2)
        return float(mse)
    
    def _compute_ssim(self, arr1: np.ndarray, arr2: np.ndarray) -> float:
        """
        Compute Structural Similarity Index.
        
        Returns value between -1 and 1 (1 = identical).
        """
        try:
            # Convert to grayscale for SSIM computation
            if len(arr1.shape) == 3:
                gray1 = np.mean(arr1, axis=2)
                gray2 = np.mean(arr2, axis=2)
            else:
                gray1 = arr1
                gray2 = arr2
            
            # Compute SSIM
            ssim_value = ssim(
                gray1,
                gray2,
                data_range=255.0
            )
            
            return float(ssim_value)
            
        except Exception as e:
            logger.error(f"SSIM computation failed: {e}")
            # Fallback to pixel diff-based estimate
            pixel_diff = self._compute_pixel_diff(arr1, arr2)
            return 1.0 - pixel_diff
    
    def compute_diff_mask(
        self,
        img1: Union[str, Path, Image.Image],
        img2: Union[str, Path, Image.Image],
        threshold: int = 30
    ) -> np.ndarray:
        """
        Compute binary difference mask showing changed regions.
        
        Args:
            img1: First image
            img2: Second image
            threshold: Pixel difference threshold (0-255)
        
        Returns:
            Binary mask where 1 = changed, 0 = unchanged
        """
        image1 = self._load_image(img1)
        image2 = self._load_image(img2)
        
        if image1.size != image2.size:
            image2 = image2.resize(image1.size, Image.LANCZOS)
        
        arr1 = np.array(image1)
        arr2 = np.array(image2)
        
        # Compute per-pixel difference
        diff = np.abs(arr1.astype(float) - arr2.astype(float))
        
        # Average across color channels
        if len(diff.shape) == 3:
            diff = np.mean(diff, axis=2)
        
        # Create binary mask
        mask = (diff > threshold).astype(np.uint8)
        
        return mask
    
    def get_change_regions(
        self,
        img1: Union[str, Path, Image.Image],
        img2: Union[str, Path, Image.Image],
        threshold: int = 30
    ) -> Tuple[int, float]:
        """
        Get statistics about changed regions.
        
        Args:
            img1: First image
            img2: Second image
            threshold: Pixel difference threshold
        
        Returns:
            Tuple of (num_changed_pixels, percentage_changed)
        """
        mask = self.compute_diff_mask(img1, img2, threshold)
        
        num_changed = np.sum(mask)
        total_pixels = mask.size
        percentage_changed = (num_changed / total_pixels) * 100.0
        
        return int(num_changed), float(percentage_changed)
    
    def visualize_diff(
        self,
        img1: Union[str, Path, Image.Image],
        img2: Union[str, Path, Image.Image],
        output_path: Union[str, Path] = None
    ) -> Image.Image:
        """
        Create visualization of differences between images.
        
        Args:
            img1: First image
            img2: Second image
            output_path: Optional path to save visualization
        
        Returns:
            PIL Image showing difference visualization
        """
        image1 = self._load_image(img1)
        image2 = self._load_image(img2)
        
        if image1.size != image2.size:
            image2 = image2.resize(image1.size, Image.LANCZOS)
        
        arr1 = np.array(image1)
        arr2 = np.array(image2)
        
        # Compute absolute difference
        diff = np.abs(arr1.astype(float) - arr2.astype(float))
        
        # Amplify differences for visualization
        diff = np.clip(diff * 3, 0, 255).astype(np.uint8)
        
        # Create PIL image
        diff_img = Image.fromarray(diff)
        
        # Save if output path provided
        if output_path:
            diff_img.save(output_path)
            logger.info(f"Difference visualization saved to {output_path}")
        
        return diff_img
