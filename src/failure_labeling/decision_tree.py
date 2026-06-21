"""
Failure Classification Decision Tree
=====================================
Deterministic, ordered rule engine that maps per-step evidence to one of 9
failure types.

Decision order (first rule that fires wins):
  STEP 1  Tool / browser execution error  →  TOOL_FAILURE
  STEP 2  No visual change + URL unchanged →  STATE_NO_CHANGE
  STEP 3  Repeated state / URL loop        →  LOOP_DETECTED
  STEP 4  Element not visible / found      →  PERCEPTION_ERROR
  STEP 5  Wrong navigation / page          →  ACTION_MISMATCH
  STEP 6  Diverges from task goal         →  GOAL_MISALIGNMENT
  STEP 7  Logical mistake (DOM ok)        →  REASONING_ERROR
  FINAL   None of the above               →  UNKNOWN

Recovery strategy mapping (deterministic):
  TOOL_FAILURE       → RETRY
  STATE_NO_CHANGE    → REPLAN
  LOOP_DETECTED      → BACKTRACK
  PERCEPTION_ERROR   → ALTERNATIVE_TARGET
  ACTION_MISMATCH    → BACKTRACK
  GOAL_MISALIGNMENT  → REPLAN
  REASONING_ERROR    → REPLAN
  UNKNOWN            → RETRY
  none               → None

Usage
-----
    from failure_labeling.decision_tree import classify_step

    result = classify_step(step_dict, history)
    # result.failure_type, result.execution_outcome,
    # result.confidence, result.recovery_strategy, result.explanation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Constants ────────────────────────────────────────────────────────────────

# Thresholds (tuneable)
PIXEL_DIFF_THRESHOLD = 0.01   # below this  → "no visual change"
SSIM_THRESHOLD       = 0.99   # above this  → "no visual change"
LOOP_URL_REPEATS     = 3      # ≥ N same URL in recent history → loop
LOOP_HASH_REPEATS    = 3      # ≥ N same state hash in history → loop

# Canonical failure type strings (match existing FailureType enum .value)
FAILURE_TYPES = {
    "tool_failure",
    "state_no_change",
    "loop_detected",
    "perception_error",
    "action_mismatch",
    "goal_misalignment",
    "reasoning_error",
    "unknown",
    "none",
}

# Recovery strategy mapping
RECOVERY_STRATEGY: Dict[str, Optional[str]] = {
    "tool_failure":      "RETRY",
    "state_no_change":   "REPLAN",
    "loop_detected":     "BACKTRACK",
    "perception_error":  "ALTERNATIVE_TARGET",
    "action_mismatch":   "BACKTRACK",
    "goal_misalignment": "REPLAN",
    "reasoning_error":   "REPLAN",
    "unknown":           "RETRY",
    "none":              None,
}

# Severity mapping
SEVERITY: Dict[str, str] = {
    "tool_failure":      "high",
    "state_no_change":   "medium",
    "loop_detected":     "high",
    "perception_error":  "high",
    "action_mismatch":   "medium",
    "goal_misalignment": "medium",
    "reasoning_error":   "medium",
    "unknown":           "low",
    "none":              "low",
}


# ── Result dataclass ─────────────────────────────────────────────────────────

@dataclass
class FailureClassification:
    """Holds the result of a single step's failure classification."""

    # Required fields (no defaults)
    failure_type:      str           # one of FAILURE_TYPES
    execution_outcome: str           # "success" | "failure"
    confidence:        float         # 0.0 – 1.0
    explanation:       str           # human-readable reason
    severity:          str           # low / medium / high
    recoverable:       bool
    
    # Optional fields (with defaults)
    failure_subtype:   Optional[str] = None  # detailed subtype (PAGE_NOT_LOADED, ELEMENT_MISSING, etc.)
    recovery_strategy: Optional[str] = None  # from RECOVERY_STRATEGY map
    signals_fired:     List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_type":      self.failure_type,
            "failure_subtype":   self.failure_subtype,
            "execution_outcome": self.execution_outcome,
            "confidence":        round(self.confidence, 4),
            "recovery_strategy": self.recovery_strategy,
            "explanation":       self.explanation,
            "severity":          self.severity,
            "recoverable":       self.recoverable,
            "signals_fired":     self.signals_fired,
        }


# ── Internal helpers ─────────────────────────────────────────────────────────

def _normalise_failure_type(raw: Any) -> str:
    """Convert FailureType enum / string to lowercase snake_case value."""
    if raw is None:
        return "none"
    # FailureType inherits str but str() still gives "FailureType.X"
    if hasattr(raw, "value"):
        return str(raw.value).lower()
    s = str(raw)
    if "." in s:
        s = s.rsplit(".", 1)[-1]
    return s.lower()


def _is_tool_error(result: Dict[str, Any]) -> tuple[bool, str, float, str]:
    """
    STEP 1 — Did a browser/tool-level error occur?
    Returns (matched, explanation, confidence, subtype).
    """
    error = result.get("error") or ""
    element_found = result.get("element_found", True)
    success = result.get("success", True)
    exec_ms = result.get("execution_time_ms", 0.0)

    tool_keywords = [
        "timeout", "net::", "err_", "navigation failed",
        "navigation error", "dns", "refused", "unreachable",
        "network error", "failed to navigate",
    ]

    # Explicit error message mentioning tool/browser/network issues
    if error:
        err_lower = error.lower()
        # Timeout on selector (element not found) is PERCEPTION, not tool
        # Only flag as TOOL if it's navigation/network related
        if any(kw in err_lower for kw in ["net::", "err_", "dns", "refused",
                                           "unreachable", "failed to navigate",
                                           "network error"]):
            subtype = "NETWORK_ERROR"
            if "dns" in err_lower:
                subtype = "DNS_ERROR"
            return True, f"Network/navigation error: {error[:100]}", 0.95, subtype

        # Execution timeout and element was never found  → could be PERCEPTION
        # We'll let PERCEPTION check handle element-not-found specifically.
        # But if it timed out with a page-load type error, it's TOOL_FAILURE.
        if "timeout" in err_lower and any(kw in err_lower for kw in
                ["page", "load", "navigate", "waitfor"]):
            return True, f"Page load timeout: {error[:100]}", 0.90, "TIMEOUT"

    # Action failed and no element found at all
    if not success and element_found is False and error:
        # Timeout waiting for selector - this is PERCEPTION_ERROR (selector not found)
        # Let PERCEPTION step handle it
        pass

    return False, "", 0.0, ""


def _is_state_no_change(
    metrics: Dict[str, Any],
    url_before: str,
    url_after: str,
) -> tuple[bool, str, float, str]:
    """
    STEP 2 — Did the page stay exactly the same after the action?
    Returns: (fired, explanation, confidence, subtype)
    """
    vis = metrics.get("visual") or {}
    pixel_diff = vis.get("pixel_diff_score", None)
    ssim = vis.get("ssim_score", None)

    if pixel_diff is None:
        return False, "", 0.0, ""

    urls_same = (url_before or "") == (url_after or "")
    no_visual = pixel_diff < PIXEL_DIFF_THRESHOLD
    high_ssim = ssim is not None and ssim > SSIM_THRESHOLD

    if no_visual and high_ssim and urls_same:
        conf = 0.85 + (SSIM_THRESHOLD - pixel_diff) * 0.1
        subtype = "NO_VISUAL_RESPONSE"
        return True, (
            f"No state change detected: pixel_diff={pixel_diff:.4f}, "
            f"ssim={ssim:.4f}, URL unchanged"
        ), min(conf, 0.95), subtype

    return False, "", 0.0, ""


def _is_loop(
    step: Dict[str, Any],
    history: List[Dict[str, Any]],
) -> tuple[bool, str, float, str]:
    """
    STEP 3 — Is the agent stuck in a loop?
    Checks URL repetition and state-hash repetition in recent history.
    Returns: (fired, explanation, confidence, subtype)
    """
    cur_url = step.get("url_after") or step.get("url_before") or ""
    sh = (step.get("metrics") or {}).get("state_hash") or {}
    cur_hash = sh.get("state_hash") or ""
    loop_detected_flag = sh.get("loop_detected", False)
    state_occurrences = sh.get("state_occurrences", 1)

    # State hash explicitly reports loop
    if loop_detected_flag and state_occurrences >= LOOP_HASH_REPEATS:
        return True, (
            f"Loop detected: state hash repeated {state_occurrences}x"
        ), 0.92, "STATE_LOOP"

    # Count same URL in history
    if cur_url and history:
        url_count = sum(
            1 for s in history
            if (s.get("url_after") or s.get("url_before") or "") == cur_url
        )
        if url_count >= LOOP_URL_REPEATS:
            return True, (
                f"URL loop: {cur_url!r} seen {url_count}x in recent steps"
            ), 0.88, "URL_LOOP"

    return False, "", 0.0, ""


def _is_perception_error(result: Dict[str, Any], error: str) -> tuple[bool, str, float, str]:
    """
    STEP 4 — Could the agent see/find the target element?
    Returns: (fired, explanation, confidence, subtype)
    """
    element_found = result.get("element_found", True)
    success = result.get("success", True)

    if not success and element_found is False:
        subtype = "ELEMENT_MISSING"
        if "timeout" in error.lower():
            subtype = "SELECTOR_TIMEOUT"
        return True, (
            f"Element not found or not visible: selector timed out"
            + (f" ({error[:80]})" if error else "")
        ), 0.92, subtype

    # Timeout error that contains selector language
    if error:
        err_lower = error.lower()
        if any(kw in err_lower for kw in [
            "not found", "no element", "selector", "locator",
            "not visible", "not interactable", "element.*not",
            "could not find", "element is not",
        ]):
            subtype = "ELEMENT_MISSING"
            if "visible" in err_lower or "interactable" in err_lower:
                subtype = "ELEMENT_NOT_VISIBLE"
            elif "selector" in err_lower or "locator" in err_lower:
                subtype = "SELECTOR_ERROR"
            return True, f"Element perception issue: {error[:100]}", 0.88, subtype

    return False, "", 0.0, ""


def _is_action_mismatch(
    step: Dict[str, Any],
    url_before: str,
    url_after: str,
    task_description: str,
) -> tuple[bool, str, float]:
    """
    STEP 5 — Did the action navigate to an irrelevant page?
    A simple heuristic: URL changed but the new URL domain is unrelated
    to any keyword from the task description.
    """
    if url_before == url_after:
        return False, "", 0.0, ""

    if not task_description or not url_after:
        return False, "", 0.0, ""

    # Extract domain from url_after
    try:
        after_domain = url_after.split("://", 1)[1].split("/")[0].lower()
        before_domain = (url_before or "").split("://", 1)[-1].split("/")[0].lower()
    except (IndexError, AttributeError):
        return False, "", 0.0, ""

    # If domains differ and the new domain doesn't appear in the task
    if after_domain != before_domain:
        task_words = set(task_description.lower().split())
        domain_parts = set(after_domain.replace("www.", "").split("."))
        if not task_words.intersection(domain_parts):
            return True, (
                f"Navigation to unrelated domain: {after_domain} "
                f"not related to task"
            ), 0.65, "UNRELATED_DOMAIN"

    return False, "", 0.0, ""


def _is_goal_misalignment(
    step: Dict[str, Any],
    task_description: str,
) -> tuple[bool, str, float, str]:
    """
    STEP 6 — Check if action_type is fundamentally wrong for the task.
    Heuristic: NAVIGATE on a task that only needs CLICK/TYPE may indicate
    the agent is wandering. Very conservative (low confidence).
    """
    action_type = (step.get("action") or {}).get("action_type", "").upper()
    if not task_description or not action_type:
        return False, "", 0.0, ""

    # If this is a TYPE step but the action typed nothing
    value = (step.get("action") or {}).get("value") or ""
    if action_type == "TYPE" and not value:
        return True, "TYPE action with empty value — possible goal misalignment", 0.55, "EMPTY_VALUE"

    return False, "", 0.0, ""


def _is_reasoning_error(result: Dict[str, Any], error: str) -> tuple[bool, str, float, str]:
    """
    STEP 7 — Catch-all for logical mistakes where DOM and tool are OK
    but output is still wrong.  Currently: action failed without a clear
    sensor or tool explanation.
    """
    success = result.get("success", True)
    if not success and not error:
        return True, "Action failed without a detectable sensor signal", 0.50, "NO_ERROR_SIGNAL"
    return False, "", 0.0, ""


# ── Public API ────────────────────────────────────────────────────────────────

def classify_step(
    step: Dict[str, Any],
    history: Optional[List[Dict[str, Any]]] = None,
    task_description: str = "",
) -> FailureClassification:
    """
    Classify one step using the ordered decision tree.

    Parameters
    ----------
    step : dict
        A fully annotated step dict (after _annotate_metrics has run).
        Expected keys: action, result, metrics, url_before, url_after.
    history : list of previous step dicts (used for loop detection)
    task_description : the task goal text (used for GOAL_MISALIGNMENT)

    Returns
    -------
    FailureClassification
    """
    history = history or []
    result  = step.get("result") or {}
    success = result.get("success", True)

    # ── Success fast-path ────────────────────────────────────────────────────
    if success:
        return FailureClassification(
            failure_type      = "none",
            execution_outcome = "SUCCESS",
            confidence        = 1.0,
            recovery_strategy = None,
            explanation       = "Step executed successfully",
            severity          = "low",
            recoverable       = True,
            signals_fired     = [],
        )

    # ── Failure path — run ordered decision tree ─────────────────────────────
    error    = str(result.get("error") or "")
    metrics  = step.get("metrics") or {}
    url_before = str(step.get("url_before") or "")
    url_after  = str(step.get("url_after")  or "")

    signals: List[str] = []

    # STEP 0 — Error page detection (CHECK FIRST before all other checks)
    is_error_page = result.get("is_error_page", False)
    page_status = result.get("page_status", "")
    
    if is_error_page or page_status == "ERROR_PAGE":
        signals.append("ERROR_PAGE_LOADED")
        
        # Determine subtype based on page status and navigation error
        subtype = "PAGE_NOT_LOADED"
        if page_status == "TIMEOUT":
            subtype = "TIMEOUT"
        elif "dns" in str(result.get("navigation_error", "")).lower():
            subtype = "DNS_ERROR"
        elif result.get("http_status", 0) >= 500:
            subtype = "SERVER_ERROR"
        elif result.get("http_status", 0) >= 400:
            subtype = "CLIENT_ERROR"
        
        explanation = f"Navigation failed - landed on error page (page_status: {page_status})"
        if result.get("navigation_error"):
            explanation += f" - {result.get('navigation_error')}"
        
        return _make_result("tool_failure", 0.95, explanation, signals, failure_subtype=subtype)

    # STEP 1 — Tool / browser error
    fired, explanation, conf, subtype = _is_tool_error(result)
    if fired:
        ft = "tool_failure"
        signals.append("TOOL_ERROR")
        return _make_result(ft, conf, explanation, signals, failure_subtype=subtype)

    # STEP 2 — Perception error (check before state change, since missing elements often cause no visual change)
    fired, explanation, conf, subtype = _is_perception_error(result, error)
    if fired:
        signals.append("ELEMENT_NOT_FOUND")
        return _make_result("perception_error", conf, explanation, signals, failure_subtype=subtype)

    # STEP 3 — No visual change
    fired, explanation, conf, subtype = _is_state_no_change(metrics, url_before, url_after)
    if fired:
        signals.append("NO_VISUAL_CHANGE")
        # Check for loop before returning STATE_NO_CHANGE
        fired_loop, loop_expl, loop_conf, loop_subtype = _is_loop(step, history)
        if fired_loop:
            signals.append("LOOP_DETECTED")
            return _make_result("loop_detected", loop_conf, loop_expl, signals, failure_subtype=loop_subtype)
        return _make_result("state_no_change", conf, explanation, signals, failure_subtype=subtype)

    # STEP 4 — Loop (visible change but still looping)
    fired, explanation, conf, subtype = _is_loop(step, history)
    if fired:
        signals.append("LOOP_DETECTED")
        return _make_result("loop_detected", conf, explanation, signals, failure_subtype=subtype)

    # STEP 5 — Action mismatch
    fired, explanation, conf, subtype = _is_action_mismatch(step, url_before, url_after, task_description)
    if fired:
        signals.append("WRONG_NAVIGATION")
        return _make_result("action_mismatch", conf, explanation, signals, failure_subtype=subtype)

    # STEP 6 — Goal misalignment
    fired, explanation, conf, subtype = _is_goal_misalignment(step, task_description)
    if fired:
        signals.append("GOAL_DIVERGENCE")
        return _make_result("goal_misalignment", conf, explanation, signals, failure_subtype=subtype)

    # STEP 7 — Reasoning error
    fired, explanation, conf, subtype = _is_reasoning_error(result, error)
    if fired:
        signals.append("REASONING_ERROR")
        return _make_result("reasoning_error", conf, explanation, signals, failure_subtype=subtype)

    # FINAL — Unknown
    signals.append("UNKNOWN")
    return _make_result(
        "unknown", 0.40,
        "Could not classify failure with available evidence",
        signals,
    )


def _make_result(
    failure_type: str,
    confidence: float,
    explanation: str,
    signals: List[str],
    failure_subtype: Optional[str] = None,
) -> FailureClassification:
    return FailureClassification(
        failure_type      = failure_type,
        failure_subtype   = failure_subtype,
        execution_outcome = "FAILURE",
        confidence        = round(confidence, 4),
        recovery_strategy = RECOVERY_STRATEGY.get(failure_type, "RETRY"),
        explanation       = explanation,
        severity          = SEVERITY.get(failure_type, "low"),
        recoverable       = failure_type not in ("unknown",),
        signals_fired     = signals,
    )
