"""
Log Parser

Converts external action logs into the BrowserRecorder's Action format.

Supported input formats
───────────────────────
1. Generic JSON / JSONL  – our own ActionLog schema
2. Mind2Web              – {confirmed_task, website, actions: [{operation, pos_candidates}]}
3. WebArena              – {intent, start_url, actions: [{action_type, element, args}]}

Usage
─────
    parser = LogParser()
    logs: List[ActionLog] = parser.load_file("logs/tasks.jsonl")
    actions: List[Action]  = parser.to_actions(logs[0])
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .replay_schema import ActionLog, LogAction

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# FORMAT DETECTORS
# ─────────────────────────────────────────────────────────────

def _is_mind2web(obj: Dict[str, Any]) -> bool:
    """Return True when the object looks like a Mind2Web annotation."""
    return "confirmed_task" in obj and "actions" in obj and "website" in obj


def _is_webarena(obj: Dict[str, Any]) -> bool:
    """Return True when the object looks like a WebArena task config."""
    return "intent" in obj and "start_url" in obj and "actions" in obj


def _is_action_log(obj: Dict[str, Any]) -> bool:
    """Return True when the object matches our own ActionLog schema."""
    return "task_id" in obj and "start_url" in obj and "actions" in obj


# ─────────────────────────────────────────────────────────────
# FORMAT CONVERTERS
# ─────────────────────────────────────────────────────────────

def _convert_mind2web(obj: Dict[str, Any]) -> ActionLog:
    """
    Convert a Mind2Web annotation dict to ActionLog.

    Mind2Web structure (simplified):
    {
      "confirmed_task": "Search for flights ...",
      "website": "https://booking.com",
      "actions": [
        {
          "action_type": "click",
          "pos_candidates": [{"tag_name": "input", "attributes": {"id": "sb_destination"}}]
        },
        ...
      ]
    }
    """
    task_id = obj.get("annotation_id") or obj.get("task_id") or f"mind2web_{hash(obj['confirmed_task']) & 0xFFFF:04x}"
    start_url = obj.get("website", "about:blank")
    if not start_url.startswith("http"):
        start_url = "https://" + start_url

    log_actions: List[LogAction] = []
    for raw in obj.get("actions", []):
        atype_raw = str(raw.get("action_type", "CLICK")).upper()

        # Map Mind2Web action type strings to ours
        atype_map = {
            "CLICK": "CLICK",
            "TYPE": "TYPE",
            "SELECT": "SELECT",
            "SCROLL": "SCROLL",
            "NAVIGATE": "NAVIGATE",
        }
        atype = atype_map.get(atype_raw, "CLICK")

        # Attempt to extract CSS selector from first positive candidate
        target: Optional[str] = None
        candidates = raw.get("pos_candidates", [])
        if candidates:
            cand = candidates[0]
            attrs = cand.get("attributes", {})
            tag = cand.get("tag_name", "")
            if attrs.get("id"):
                target = f"#{attrs['id']}"
            elif attrs.get("class"):
                cls = attrs["class"].split()[0] if attrs["class"] else ""
                target = f"{tag}.{cls}" if cls else tag
            else:
                target = tag or None

        value = raw.get("value") or raw.get("typed_text")

        log_actions.append(LogAction(
            action_type=atype,
            target=target,
            value=value,
            description=raw.get("description"),
        ))

    return ActionLog(
        task_id=task_id,
        start_url=start_url,
        task_description=obj.get("confirmed_task"),
        source="mind2web",
        actions=log_actions,
        metadata={"raw_keys": list(obj.keys())},
    )


def _convert_webarena(obj: Dict[str, Any]) -> ActionLog:
    """
    Convert a WebArena task config to ActionLog.

    WebArena structure (simplified):
    {
      "task_id": 42,
      "intent": "Find the cheapest ...",
      "start_url": "https://...",
      "actions": [
        {"action_type": "click", "element": "#btn-submit", "args": []},
        {"action_type": "type",  "element": "#query",      "args": ["laptop"]},
        ...
      ]
    }
    """
    task_id = str(obj.get("task_id") or f"webarena_{hash(obj.get('intent','')) & 0xFFFF:04x}")
    start_url = obj.get("start_url", "about:blank")

    atype_map = {
        "click":     "CLICK",
        "type":      "TYPE",
        "scroll":    "SCROLL",
        "select":    "SELECT",
        "navigate":  "NAVIGATE",
        "press":     "PRESS_KEY",
        "goto":      "NAVIGATE",
    }

    log_actions: List[LogAction] = []
    for raw in obj.get("actions", []):
        raw_type = str(raw.get("action_type", "click")).lower()
        atype = atype_map.get(raw_type, raw_type.upper())

        target = raw.get("element") or raw.get("selector")
        args = raw.get("args", [])
        value = args[0] if args else raw.get("value")
        key = raw.get("key") or (args[0] if atype == "PRESS_KEY" and args else None)

        log_actions.append(LogAction(
            action_type=atype,
            target=target,
            value=value,
            key=key,
            description=raw.get("description"),
        ))

    return ActionLog(
        task_id=task_id,
        start_url=start_url,
        task_description=obj.get("intent"),
        source="webarena",
        actions=log_actions,
        metadata={"task_id_original": obj.get("task_id")},
    )


def _convert_generic(obj: Dict[str, Any]) -> ActionLog:
    """
    Convert a generic dict (already ActionLog-compatible) to ActionLog.
    Allows extra fields and tolerates minor schema deviations.
    """
    actions_raw = obj.get("actions", [])
    actions: List[LogAction] = []

    for item in actions_raw:
        if isinstance(item, dict):
            # Normalise key names
            atype = (
                item.get("action_type")
                or item.get("type")
                or item.get("action")
                or "CLICK"
            ).upper()

            target = item.get("target") or item.get("selector") or item.get("element")
            value  = item.get("value") or item.get("text") or item.get("input")
            key    = item.get("key")
            scroll = item.get("scroll_amount") or item.get("scroll")

            actions.append(LogAction(
                action_type=atype,
                target=target,
                value=value,
                key=key,
                scroll_amount=int(scroll) if scroll is not None else None,
                timeout=item.get("timeout"),
                description=item.get("description"),
            ))
        else:
            logger.warning(f"Skipping non-dict action entry: {item}")

    return ActionLog(
        task_id=obj["task_id"],
        start_url=obj["start_url"],
        task_description=obj.get("task_description"),
        source=obj.get("source", "custom"),
        actions=actions,
        metadata=obj.get("metadata", {}),
    )


# ─────────────────────────────────────────────────────────────
# MAIN PARSER CLASS
# ─────────────────────────────────────────────────────────────

class LogParser:
    """
    Parse action log files into a list of ActionLog objects.

    Supported file formats
    ──────────────────────
    • .json   – single task OR list of tasks
    • .jsonl  – one task per line

    Usage
    ─────
        parser = LogParser()
        logs = parser.load_file("my_tasks.jsonl")
        print(f"Loaded {len(logs)} tasks")
    """

    # ── file loading ──────────────────────────────────────────

    def load_file(self, path: str | Path) -> List[ActionLog]:
        """
        Load and parse an action log file.

        Raises
        ------
        FileNotFoundError   if the file does not exist
        ValueError          if the file content cannot be parsed
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Log file not found: {path}")

        suffix = path.suffix.lower()

        try:
            if suffix == ".jsonl":
                return self._load_jsonl(path)
            else:
                return self._load_json(path)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Cannot parse log file {path}: {exc}") from exc

    def load_dict(self, obj: Dict[str, Any]) -> ActionLog:
        """Parse a single dict (already in memory) into an ActionLog."""
        return self._convert_single(obj)

    def load_dicts(self, objs: List[Dict[str, Any]]) -> List[ActionLog]:
        """Parse a list of dicts into ActionLog objects."""
        result: List[ActionLog] = []
        for i, obj in enumerate(objs):
            try:
                result.append(self._convert_single(obj))
            except Exception as exc:
                logger.warning(f"Skipping entry {i} ({exc})")
        return result

    # ── Action conversion ─────────────────────────────────────

    def to_actions(self, log: ActionLog):
        """
        Convert an ActionLog into BrowserRecorder Action objects.

        Returns
        -------
        List[browser_recorder.action_schema.Action]
        """
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from browser_recorder.action_schema import Action, ActionType

        actions = []
        for la in log.actions:
            try:
                # Validate action_type against enum
                try:
                    atype = ActionType(la.action_type.upper())
                except ValueError:
                    logger.warning(
                        f"Unknown action type '{la.action_type}' in task "
                        f"'{log.task_id}' – defaulting to CLICK"
                    )
                    atype = ActionType.CLICK

                action = Action(
                    action_type=atype,
                    target=la.target,
                    value=la.value,
                    key=la.key,
                    scroll_amount=la.scroll_amount,
                    timeout=la.timeout or 30_000,
                    description=la.description,
                )
                actions.append(action)
            except Exception as exc:
                logger.warning(f"Cannot convert log action to Action: {la} ({exc})")

        return actions

    # ── private helpers ───────────────────────────────────────

    def _load_json(self, path: Path) -> List[ActionLog]:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)

        if isinstance(data, list):
            return self.load_dicts(data)
        if isinstance(data, dict):
            return [self._convert_single(data)]
        raise ValueError(f"Expected a JSON object or array, got {type(data)}")

    def _load_jsonl(self, path: Path) -> List[ActionLog]:
        logs: List[ActionLog] = []
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    obj = json.loads(line)
                    logs.append(self._convert_single(obj))
                except Exception as exc:
                    logger.warning(f"Skipping JSONL line {lineno}: {exc}")
        return logs

    def _convert_single(self, obj: Dict[str, Any]) -> ActionLog:
        """Auto-detect format and convert."""
        if _is_mind2web(obj):
            log = _convert_mind2web(obj)
            logger.debug(f"Parsed as Mind2Web: {log.task_id}")
        elif _is_webarena(obj):
            log = _convert_webarena(obj)
            logger.debug(f"Parsed as WebArena: {log.task_id}")
        elif _is_action_log(obj):
            log = _convert_generic(obj)
            logger.debug(f"Parsed as generic ActionLog: {log.task_id}")
        else:
            # Last-resort: assume generic but fill required fields with defaults
            if "task_id" not in obj:
                obj["task_id"] = f"unknown_{hash(str(obj)) & 0xFFFF:04x}"
            if "start_url" not in obj:
                obj["start_url"] = "about:blank"
            if "actions" not in obj:
                obj["actions"] = []
            log = _convert_generic(obj)
            logger.warning(f"Unrecognised log format, parsed as generic: {log.task_id}")

        return log
