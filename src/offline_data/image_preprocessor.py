"""
Image preprocessing utilities for offline augmentation.

Provides functions for:
- Masking bounding boxes (TARGET_MISSING injection)
- Computing visual differences (state change detection)
- Image noise injection
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from typing import Dict, Tuple, Optional
from skimage.metrics import structural_similarity as ssim


def _parse_bbox(bbox) -> Optional[Dict[str, float]]:
    """
    Parse and validate a bounding box.
    Handles JSON strings and dict formats.
    
    Args:
        bbox: Bbox as dict or JSON string
        
    Returns:
        Parsed bbox dict or None if invalid
    """
    if isinstance(bbox, str):
        try:
            import json
            bbox = json.loads(bbox)
        except:
            return None
    
    if not isinstance(bbox, dict):
        return None
    
    # Check for required keys
    if not all(k in bbox for k in ["x", "y", "width", "height"]):
        return None
    
    return bbox


def mask_bbox(
    image: Image.Image, 
    bbox: Dict[str, float], 
    mask_type: str = "blur"
) -> Image.Image:
    """
    Mask a bounding box region in an image.
    
    Args:
        image: PIL Image to modify
        bbox: Bounding box dict with {x, y, width, height}
        mask_type: Type of masking ("blur", "black", "noise")
        
    Returns:
        Modified PIL Image with masked region
    """
    # Parse and validate bbox
    bbox = _parse_bbox(bbox)
    if not bbox:
        return image.copy()  # Return unmodified if invalid
    
    img = image.copy()
    
    x = int(bbox["x"])
    y = int(bbox["y"])
    width = int(bbox["width"])
    height = int(bbox["height"])
    
    # Extract region
    region = img.crop((x, y, x + width, y + height))
    
    if mask_type == "blur":
        # Apply strong blur
        region = region.filter(ImageFilter.GaussianBlur(radius=20))
    
    elif mask_type == "black":
        # Fill with black
        draw = ImageDraw.Draw(region)
        draw.rectangle([0, 0, width, height], fill=(0, 0, 0))
    
    elif mask_type == "noise":
        # Add random noise
        region_array = np.array(region)
        noise = np.random.randint(0, 50, region_array.shape, dtype=np.uint8)
        region_array = np.clip(region_array + noise, 0, 255).astype(np.uint8)
        region = Image.fromarray(region_array)
    
    # Paste modified region back
    img.paste(region, (x, y))
    
    return img


def compute_pixel_diff(img1: Image.Image, img2: Image.Image) -> float:
    """
    Compute pixel-wise difference between two images.
    
    Args:
        img1: First image
        img2: Second image
        
    Returns:
        Normalized pixel difference (0.0 = identical, 1.0 = completely different)
    """
    # Resize to same dimensions if needed
    if img1.size != img2.size:
        img2 = img2.resize(img1.size)
    
    # Convert to numpy arrays
    arr1 = np.array(img1).astype(np.float32)
    arr2 = np.array(img2).astype(np.float32)
    
    # Compute mean absolute difference
    diff = np.abs(arr1 - arr2).mean()
    
    # Normalize to 0-1
    normalized_diff = diff / 255.0
    
    return float(normalized_diff)


def compute_ssim(img1: Image.Image, img2: Image.Image) -> float:
    """
    Compute Structural Similarity Index (SSIM) between two images.
    Memory-optimized: downsamples large images to prevent memory errors.
    
    Args:
        img1: First image
        img2: Second image
        
    Returns:
        SSIM score (1.0 = identical, 0.0 = completely different)
    """
    MAX_DIMENSION = 800  # Reduced for LOW MEMORY systems
    
    # Downsample if images are too large
    def downsample_if_needed(img):
        width, height = img.size
        max_dim = max(width, height)
        
        if max_dim > MAX_DIMENSION:
            # Calculate scaling factor
            scale = MAX_DIMENSION / max_dim
            new_width = int(width * scale)
            new_height = int(height * scale)
            return img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return img
    
    # Downsample both images
    img1 = downsample_if_needed(img1)
    img2 = downsample_if_needed(img2)
    
    # Resize to same dimensions if needed (after downsampling)
    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)
    
    # Convert to grayscale numpy arrays
    arr1 = np.array(img1.convert('L'))
    arr2 = np.array(img2.convert('L'))
    
    # Compute SSIM with reduced memory usage
    try:
        score, _ = ssim(arr1, arr2, full=True)
        return float(score)
    except MemoryError:
        # Fallback: use smaller dimension if still fails
        if max(arr1.shape) > 512:
            img1_small = img1.resize((512, 512), Image.Resampling.LANCZOS)
            img2_small = img2.resize((512, 512), Image.Resampling.LANCZOS)
            arr1 = np.array(img1_small.convert('L'))
            arr2 = np.array(img2_small.convert('L'))
            score, _ = ssim(arr1, arr2, full=True)
            return float(score)
        raise


def compute_visual_metrics(
    img1: Image.Image, 
    img2: Image.Image
) -> Dict[str, float]:
    """
    Compute multiple visual comparison metrics.
    
    Args:
        img1: First image (state_before)
        img2: Second image (state_after)
        
    Returns:
        Dict with pixel_diff and ssim scores
    """
    return {
        "pixel_diff": compute_pixel_diff(img1, img2),
        "ssim": compute_ssim(img1, img2)
    }


def add_noise(image: Image.Image, epsilon: float = 0.001) -> Image.Image:
    """
    Add imperceptible noise to an image.
    Memory-optimized: downsamples large images before processing.
    
    Args:
        image: PIL Image
        epsilon: Noise magnitude (0.001 = barely noticeable)
        
    Returns:
        Modified PIL Image
    """
    MAX_DIMENSION = 512  # Downsample to prevent memory errors
    
    # Downsample if image is too large
    original_size = image.size
    if max(image.size) > MAX_DIMENSION:
        ratio = MAX_DIMENSION / max(image.size)
        new_size = (int(image.width * ratio), int(image.height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    # Use float32 instead of float64 (50% memory reduction)
    img_array = np.array(image).astype(np.float32)
    
    # Add small random noise
    noise = np.random.randn(*img_array.shape).astype(np.float32) * epsilon * 255
    img_array = np.clip(img_array + noise, 0, 255).astype(np.uint8)
    
    noisy_image = Image.fromarray(img_array)
    
    # Resize back to original size if needed
    if original_size != noisy_image.size:
        noisy_image = noisy_image.resize(original_size, Image.Resampling.LANCZOS)
    
    return noisy_image


def shift_bbox(
    bbox: Dict[str, float], 
    shift_x: int, 
    shift_y: int,
    image_width: int,
    image_height: int
) -> Dict[str, float]:
    """
    Shift a bounding box by (shift_x, shift_y) pixels.
    Clamps to image boundaries.
    
    Args:
        bbox: Original bounding box
        shift_x: Horizontal shift (pixels)
        shift_y: Vertical shift (pixels)
        image_width: Image width for clamping
        image_height: Image height for clamping
        
    Returns:
        Shifted bounding box
    """
    # Parse and validate bbox
    bbox = _parse_bbox(bbox)
    if not bbox:
        return {"x": 0, "y": 0, "width": 0, "height": 0}  # Return zero bbox if invalid
    
    new_bbox = bbox.copy()
    
    new_x = bbox["x"] + shift_x
    new_y = bbox["y"] + shift_y
    
    # Clamp to image boundaries
    new_x = max(0, min(new_x, image_width - bbox["width"]))
    new_y = max(0, min(new_y, image_height - bbox["height"]))
    
    new_bbox["x"] = new_x
    new_bbox["y"] = new_y
    
    return new_bbox


def get_bbox_center(bbox: Dict[str, float]) -> Tuple[int, int]:
    """
    Get the center coordinates of a bounding box.
    
    Args:
        bbox: Bounding box dict
        
    Returns:
        (center_x, center_y) tuple
    """
    # Parse and validate bbox
    bbox = _parse_bbox(bbox)
    if not bbox:
        return (0, 0)  # Return origin if invalid
    
    center_x = int(bbox["x"] + bbox["width"] / 2)
    center_y = int(bbox["y"] + bbox["height"] / 2)
    
    return (center_x, center_y)


def bbox_overlaps(bbox1: Dict[str, float], bbox2: Dict[str, float]) -> bool:
    """
    Check if two bounding boxes overlap.
    
    Args:
        bbox1: First bounding box
        bbox2: Second bounding box
        
    Returns:
        True if boxes overlap, False otherwise
    """
    # Validate and parse bboxes
    bbox1 = _parse_bbox(bbox1)
    bbox2 = _parse_bbox(bbox2)
    
    if not bbox1 or not bbox2:
        return False
    
    x1_min = bbox1["x"]
    y1_min = bbox1["y"]
    x1_max = bbox1["x"] + bbox1["width"]
    y1_max = bbox1["y"] + bbox1["height"]
    
    x2_min = bbox2["x"]
    y2_min = bbox2["y"]
    x2_max = bbox2["x"] + bbox2["width"]
    y2_max = bbox2["y"] + bbox2["height"]
    
    # Check for overlap
    overlap_x = not (x1_max < x2_min or x2_max < x1_min)
    overlap_y = not (y1_max < y2_min or y2_max < y1_min)
    
    return overlap_x and overlap_y


def find_alternative_target(
    target_bbox: Dict[str, float],
    candidate_bboxes: list[Dict[str, float]],
    avoid_overlap: bool = True
) -> Optional[Dict[str, float]]:
    """
    Find an alternative target bbox from candidates.
    
    Args:
        target_bbox: Original target bbox to avoid
        candidate_bboxes: List of candidate bboxes
        avoid_overlap: If True, prefer non-overlapping candidates
        
    Returns:
        Alternative bbox or None if no suitable alternative
    """
    if not candidate_bboxes:
        return None
    
    # Filter valid candidates using centralized parser
    valid_candidates = []
    for bbox in candidate_bboxes:
        parsed = _parse_bbox(bbox)
        if parsed:
            valid_candidates.append(parsed)
    
    if not valid_candidates:
        return None
    
    # Filter out original target
    alternatives = [
        bbox for bbox in valid_candidates 
        if bbox != target_bbox
    ]
    
    if not alternatives:
        return None
    
    # If avoiding overlap, prefer non-overlapping
    if avoid_overlap:
        non_overlapping = [
            bbox for bbox in alternatives
            if not bbox_overlaps(bbox, target_bbox)
        ]
        if non_overlapping:
            return non_overlapping[0]
    
    # Return first alternative
    return alternatives[0]
