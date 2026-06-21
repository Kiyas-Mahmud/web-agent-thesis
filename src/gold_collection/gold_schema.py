"""Schemas and label normalization for the leakage-safe gold dataset.

The gold dataset keeps two label layers:

1. A coarse label layer that matches the existing synthetic 70k model heads.
2. A fine observed label layer for real collection analysis and future models.

Only the coarse layer is exported for first-pass fine-tuning. Fine labels that
cannot be mapped safely are masked out of the 4-class failure-type loss.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator


OUTCOME_LABELS = ("SUCCESS", "FAILURE")
COARSE_FAILURE_LABELS = (
    "NONE",
    "ACTION_MISMATCH",
    "PERCEPTION_ERROR",
    "LOOP_DETECTED",
)
TRAINING_ACTION_LABELS = ("CLICK", "TYPE", "SELECT")
ACTION_LABELS = TRAINING_ACTION_LABELS + ("SCROLL", "NAVIGATE", "WAIT", "HOVER", "PRESS_KEY")
RECOVERY_LABELS = ("NONE", "RETRY", "REPLAN", "BACKTRACK", "ALTERNATIVE_TARGET", "ABORT")

# These fields may exist in audit files, but must never be included in model
# training export because they either leak labels or are post-outcome metadata.
FORBIDDEN_TRAINING_FIELDS = {
    "injection_type",
    "is_augmented",
    "agent_confidence_before",
    "failure_confidence",
    "visual_diff_score",
    "memory_update_flag",
    "recovery_success",
    "pixel_diff",
    "ssim",
    "page_status",
    "http_status",
    "error_message",
    "url_before",
    "url_after",
    "failure_type_fine",
    "label_source",
    "review_status",
    "reviewer_notes",
    "metadata",
}

FINE_TO_COARSE = {
    "none": "NONE",
    "perception_error": "PERCEPTION_ERROR",
    "loop_detected": "LOOP_DETECTED",
    "action_mismatch": "ACTION_MISMATCH",
    "goal_misalignment": "ACTION_MISMATCH",
    "reasoning_error": "ACTION_MISMATCH",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_token(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return text.replace("-", "_").replace(" ", "_")


def normalize_fine_failure(value: Any) -> str:
    token = normalize_token(value).lower()
    if token in {"", "success", "no_failure"}:
        return "none"
    return token


def map_fine_to_coarse(value: Any) -> Tuple[Optional[str], bool]:
    fine = normalize_fine_failure(value)
    coarse = FINE_TO_COARSE.get(fine)
    return coarse, coarse is not None


def normalize_outcome(value: Any, *, success: Optional[bool] = None) -> str:
    if success is not None:
        return "SUCCESS" if success else "FAILURE"
    token = normalize_token(value).upper()
    if token in OUTCOME_LABELS:
        return token
    if token in {"NONE", "SUCCESSFUL", "OK"}:
        return "SUCCESS"
    return "FAILURE"


def normalize_action(value: Any) -> str:
    token = normalize_token(value).upper()
    return token if token in ACTION_LABELS else "CLICK"


def normalize_recovery(value: Any) -> str:
    token = normalize_token(value).upper()
    if token in {"", "NULL", "NONE", "NO_RECOVERY"}:
        return "NONE"
    if token in {"WAIT_AND_RETRY", "SCROLL_AND_RETRY"}:
        return "RETRY"
    if token in RECOVERY_LABELS:
        return token
    return "RETRY"


def normalize_coordinates(value: Any) -> Optional[List[float]]:
    if value is None:
        return None
    if isinstance(value, dict):
        if "x" in value and "y" in value:
            return [float(value["x"]), float(value["y"])]
        return None
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return [float(value[0]), float(value[1])]
    return None


def normalize_bbox(value: Any) -> Optional[Dict[str, float]]:
    if not value:
        return None
    if isinstance(value, dict):
        keys = ("x", "y", "width", "height")
        if all(key in value for key in keys):
            return {key: float(value[key]) for key in keys}
    if isinstance(value, (list, tuple)) and len(value) == 4:
        x1, y1, x2_or_w, y2_or_h = [float(v) for v in value]
        width = x2_or_w if x2_or_w >= 0 else 0.0
        height = y2_or_h if y2_or_h >= 0 else 0.0
        return {"x": x1, "y": y1, "width": width, "height": height}
    return None


class GoldStep(BaseModel):
    """One leakage-safe gold dataset step."""

    sample_id: str
    task_id: str
    step_index: int
    source: str = "custom"
    website_domain: str = ""

    task_description: str = ""
    state_before: str
    state_after: str
    action_type: str
    action_type_eval_mask: bool = True
    action_target_desc: str = ""
    action_coordinates: Optional[List[float]] = None
    action_target_bbox: Optional[Dict[str, float]] = None

    url_before: Optional[str] = None
    url_after: Optional[str] = None
    page_status: Optional[str] = None
    http_status: Optional[int] = None
    error_message: Optional[str] = None
    pixel_diff: Optional[float] = None
    ssim: Optional[float] = None

    outcome_label: str
    failure_type_4: Optional[str] = None
    failure_type_4_eval_mask: bool = True
    failure_type_fine: str = "none"
    recovery_strategy_observed: str = "NONE"
    recovery_attempted: bool = False
    recovery_success_observed: Optional[bool] = None

    label_source: str = "auto"
    review_status: str = "pending"
    reviewer_notes: str = ""
    collected_at: str = Field(default_factory=utc_now_iso)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("outcome_label")
    @classmethod
    def _validate_outcome(cls, value: Any) -> str:
        outcome = normalize_outcome(value)
        if outcome not in OUTCOME_LABELS:
            raise ValueError(f"Unsupported outcome_label: {value}")
        return outcome

    @field_validator("failure_type_4")
    @classmethod
    def _validate_failure_type_4(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        token = normalize_token(value).upper()
        if token not in COARSE_FAILURE_LABELS:
            raise ValueError(f"Unsupported failure_type_4: {value}")
        return token

    @field_validator("failure_type_fine")
    @classmethod
    def _validate_fine_failure(cls, value: Any) -> str:
        return normalize_fine_failure(value)

    @field_validator("recovery_strategy_observed")
    @classmethod
    def _validate_recovery(cls, value: Any) -> str:
        return normalize_recovery(value)

    @field_validator("action_type")
    @classmethod
    def _validate_action(cls, value: Any) -> str:
        return normalize_action(value)

    @field_validator("action_coordinates")
    @classmethod
    def _validate_coordinates(cls, value: Any) -> Optional[List[float]]:
        return normalize_coordinates(value)

    @field_validator("action_target_bbox")
    @classmethod
    def _validate_bbox(cls, value: Any) -> Optional[Dict[str, float]]:
        return normalize_bbox(value)

    def model_record(self) -> Dict[str, Any]:
        """Return the leakage-safe record used by model training."""
        record = {
            "sample_id": self.sample_id,
            "task_id": self.task_id,
            "step_index": self.step_index,
            "source": self.source,
            "website_domain": self.website_domain,
            "task_description": self.task_description,
            "state_before": self.state_before,
            "state_after": self.state_after,
            "action_type": self.action_type,
            "action_type_eval_mask": self.action_type_eval_mask,
            "action_target_desc": self.action_target_desc,
            "action_coordinates": self.action_coordinates,
            "action_target_bbox": self.action_target_bbox,
            "outcome_label": self.outcome_label,
            "failure_type_4": self.failure_type_4,
            "failure_type_4_eval_mask": self.failure_type_4_eval_mask,
            "recovery_strategy": self.recovery_strategy_observed,
            "recovery_attempted": self.recovery_attempted,
        }
        leaked = set(record) & FORBIDDEN_TRAINING_FIELDS
        if leaked:
            raise ValueError(f"Training record contains forbidden fields: {sorted(leaked)}")
        return record

    def paths_exist(self, base_dir: Path) -> bool:
        return (base_dir / self.state_before).is_file() and (base_dir / self.state_after).is_file()


class GoldTrajectory(BaseModel):
    task_id: str
    source: str = "custom"
    task_description: str = ""
    website_domain: str = ""
    steps: List[GoldStep] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_step(self, step: GoldStep) -> None:
        self.steps.append(step)


def build_gold_step(
    *,
    task_id: str,
    step_index: int,
    state_before: str,
    state_after: str,
    action_type: Any,
    action_type_eval_mask: Optional[bool] = None,
    task_description: str = "",
    source: str = "custom",
    website_domain: str = "",
    action_target_desc: str = "",
    action_coordinates: Any = None,
    action_target_bbox: Any = None,
    url_before: Optional[str] = None,
    url_after: Optional[str] = None,
    page_status: Optional[str] = None,
    http_status: Optional[int] = None,
    error_message: Optional[str] = None,
    pixel_diff: Optional[float] = None,
    ssim: Optional[float] = None,
    outcome_label: Any = None,
    failure_type_fine: Any = "none",
    recovery_strategy_observed: Any = None,
    recovery_attempted: bool = False,
    recovery_success_observed: Optional[bool] = None,
    label_source: str = "auto",
    review_status: str = "pending",
    metadata: Optional[Dict[str, Any]] = None,
) -> GoldStep:
    fine = normalize_fine_failure(failure_type_fine)
    coarse, mask = map_fine_to_coarse(fine)
    outcome = normalize_outcome(outcome_label, success=(fine == "none") if outcome_label is None else None)
    normalized_action = normalize_action(action_type)
    if action_type_eval_mask is None:
        action_type_eval_mask = normalized_action in TRAINING_ACTION_LABELS
    if outcome == "SUCCESS":
        coarse = "NONE"
        mask = True
        fine = "none"

    return GoldStep(
        sample_id=f"{task_id}__step_{step_index:04d}",
        task_id=task_id,
        step_index=step_index,
        source=source,
        website_domain=website_domain,
        task_description=task_description,
        state_before=state_before,
        state_after=state_after,
        action_type=normalized_action,
        action_type_eval_mask=action_type_eval_mask,
        action_target_desc=action_target_desc or "",
        action_coordinates=action_coordinates,
        action_target_bbox=action_target_bbox,
        url_before=url_before,
        url_after=url_after,
        page_status=page_status,
        http_status=http_status,
        error_message=error_message,
        pixel_diff=pixel_diff,
        ssim=ssim,
        outcome_label=outcome,
        failure_type_4=coarse,
        failure_type_4_eval_mask=mask,
        failure_type_fine=fine,
        recovery_strategy_observed=normalize_recovery(recovery_strategy_observed),
        recovery_attempted=recovery_attempted,
        recovery_success_observed=recovery_success_observed,
        label_source=label_source,
        review_status=review_status,
        metadata=metadata or {},
    )
