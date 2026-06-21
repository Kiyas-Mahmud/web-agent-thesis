"""
Annotation processing utilities for Mind2Web dataset.

Provides functions for:
- Parsing action annotations
- Extracting target elements
- Finding alternative targets
- Action transformation
"""

from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


def parse_action_repr(action_repr: str) -> Dict[str, Any]:
    """
    Parse action representation string into structured format.
    
    Example: "CLICK [1234] <button id='submit'>Submit</button>"
    
    Args:
        action_repr: Action representation string
        
    Returns:
        Dict with parsed action info
    """
    parts = action_repr.split(None, 2)
    
    parsed = {
        "operation": parts[0] if len(parts) > 0 else "UNKNOWN",
        "uid": "",
        "element_html": ""
    }
    
    if len(parts) > 1:
        # Try to extract UID from [1234] format
        if parts[1].startswith("[") and parts[1].endswith("]"):
            parsed["uid"] = parts[1][1:-1]
    
    if len(parts) > 2:
        parsed["element_html"] = parts[2]
    
    return parsed


def extract_target_bbox(action: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """
    Extract target bounding box from action annotation.
    
    Args:
        action: Action dict from Mind2Web
        
    Returns:
        Bounding box dict or None
    """
    if "pos" not in action or not action["pos"]:
        return None
    
    bbox_list = action["pos"]
    if len(bbox_list) < 4:
        return None
    
    return {
        "x": float(bbox_list[0]),
        "y": float(bbox_list[1]),
        "width": float(bbox_list[2] - bbox_list[0]),
        "height": float(bbox_list[3] - bbox_list[1])
    }


def extract_candidate_bboxes(
    pos_candidates: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Extract all candidate bounding boxes from annotation.
    
    Args:
        pos_candidates: List of candidate elements with positions
        
    Returns:
        List of candidate bbox dicts with metadata
    """
    candidates = []
    
    for candidate in pos_candidates:
        if "pos" not in candidate or not candidate["pos"]:
            continue
        
        bbox_list = candidate["pos"]
        if len(bbox_list) < 4:
            continue
        
        candidate_info = {
            "uid": candidate.get("uid", ""),
            "x": float(bbox_list[0]),
            "y": float(bbox_list[1]),
            "width": float(bbox_list[2] - bbox_list[0]),
            "height": float(bbox_list[3] - bbox_list[1]),
            "tag_name": candidate.get("tag", ""),
            "attributes": candidate.get("attributes", {}),
            "is_target": candidate.get("is_original_target", False)
        }
        
        candidates.append(candidate_info)
    
    return candidates


def find_alternative_targets(
    target_uid: str,
    candidate_bboxes: List[Dict[str, Any]],
    same_type_only: bool = True
) -> List[Dict[str, Any]]:
    """
    Find alternative target elements from candidates.
    
    Args:
        target_uid: UID of original target
        candidate_bboxes: List of candidate bboxes
        same_type_only: Only return candidates of same tag type
        
    Returns:
        List of alternative target candidates
    """
    # Find original target
    target = None
    for candidate in candidate_bboxes:
        if candidate["uid"] == target_uid:
            target = candidate
            break
    
    if target is None:
        # Return all non-target candidates
        return [c for c in candidate_bboxes if c["uid"] != target_uid]
    
    # Filter candidates
    alternatives = []
    target_tag = target.get("tag_name", "")
    
    for candidate in candidate_bboxes:
        if candidate["uid"] == target_uid:
            continue
        
        if same_type_only and candidate.get("tag_name") != target_tag:
            continue
        
        alternatives.append(candidate)
    
    return alternatives


def swap_action_type(action_type: str) -> str:
    """
    Swap action type for WRONG_OPERATION injection.
    
    Args:
        action_type: Original action type
        
    Returns:
        Swapped action type
    """
    swaps = {
        "CLICK": "TYPE",
        "TYPE": "CLICK",
        "SELECT": "CLICK",
        "HOVER": "CLICK",
        "PRESS": "TYPE",
        "SCROLL": "CLICK"
    }
    
    return swaps.get(action_type, "CLICK")


def validate_action(action: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate action annotation completeness.
    
    Args:
        action: Action dict
        
    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    
    if "uid" not in action or not action["uid"]:
        errors.append("Missing action UID")
    
    if "pos" not in action or not action["pos"]:
        errors.append("Missing position information")
    elif len(action["pos"]) < 4:
        errors.append("Incomplete position bbox (need 4 coordinates)")
    
    is_valid = len(errors) == 0
    
    return is_valid, errors


def get_action_summary(
    action_type: str,
    action_target: str,
    action_text: Optional[str] = None
) -> str:
    """
    Generate human-readable action summary.
    
    Args:
        action_type: Type of action
        action_target: Target element description
        action_text: Text to type (if TYPE action)
        
    Returns:
        Summary string
    """
    if action_type == "TYPE" and action_text:
        return f"{action_type} '{action_text}' into {action_target}"
    else:
        return f"{action_type} {action_target}"


def compute_bbox_distance(
    bbox1: Dict[str, float],
    bbox2: Dict[str, float]
) -> float:
    """
    Compute Euclidean distance between bbox centers.
    
    Args:
        bbox1: First bounding box
        bbox2: Second bounding box
        
    Returns:
        Distance in pixels
    """
    center1_x = bbox1["x"] + bbox1["width"] / 2
    center1_y = bbox1["y"] + bbox1["height"] / 2
    
    center2_x = bbox2["x"] + bbox2["width"] / 2
    center2_y = bbox2["y"] + bbox2["height"] / 2
    
    distance = ((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2) ** 0.5
    
    return float(distance)


def find_closest_candidate(
    target_bbox: Dict[str, float],
    candidate_bboxes: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Find the closest candidate bbox to target.
    
    Args:
        target_bbox: Target bounding box
        candidate_bboxes: List of candidate bboxes
        
    Returns:
        Closest candidate or None
    """
    if not candidate_bboxes:
        return None
    
    closest = None
    min_distance = float('inf')
    
    for candidate in candidate_bboxes:
        distance = compute_bbox_distance(target_bbox, candidate)
        if distance < min_distance:
            min_distance = distance
            closest = candidate
    
    return closest


def extract_action_context(
    step_number: int,
    trajectory_steps: List[Dict[str, Any]],
    context_window: int = 2
) -> Dict[str, Any]:
    """
    Extract context from surrounding steps.
    
    Args:
        step_number: Current step index
        trajectory_steps: All steps in trajectory
        context_window: Number of steps before/after to include
        
    Returns:
        Context dict with previous and next actions
    """
    context = {
        "prev_actions": [],
        "next_actions": []
    }
    
    # Previous actions
    start_idx = max(0, step_number - context_window)
    for i in range(start_idx, step_number):
        if i < len(trajectory_steps):
            context["prev_actions"].append({
                "step": i,
                "action_type": trajectory_steps[i].get("action_type", "UNKNOWN"),
                "action_target": trajectory_steps[i].get("action_target", "")
            })
    
    # Next actions
    end_idx = min(len(trajectory_steps), step_number + context_window + 1)
    for i in range(step_number + 1, end_idx):
        if i < len(trajectory_steps):
            context["next_actions"].append({
                "step": i,
                "action_type": trajectory_steps[i].get("action_type", "UNKNOWN"),
                "action_target": trajectory_steps[i].get("action_target", "")
            })
    
    return context
