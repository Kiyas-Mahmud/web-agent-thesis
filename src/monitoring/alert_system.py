"""
Alert System
============
Checks live RunCounters + storage stats against configurable thresholds
and fires AlertEvents to both the log and stdout.

Usage
-----
    from monitoring import AlertSystem, AlertThresholds

    alerts = AlertSystem(output_dir="dataset")
    fired  = alerts.check(counters, dataset_size_gb=1.4)
    for a in fired:
        print(a.level, a.alert_type, a.message)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from .monitor_schema import AlertEvent, AlertLevel, AlertThresholds, RunCounters

logger = logging.getLogger("dc.AlertSystem")


class AlertSystem:
    """
    Evaluates thresholds after every completed task and emits AlertEvents.

    All fired alerts are written to  dataset/logs/alerts.jsonl  and also
    printed to stderr with colour coding.
    """

    def __init__(
        self,
        output_dir:  str | Path               = "dataset",
        thresholds:  AlertThresholds | None   = None,
    ):
        self.thresholds  = thresholds or AlertThresholds()
        self._alert_file = Path(output_dir) / "logs" / "alerts.jsonl"
        self._alert_file.parent.mkdir(parents=True, exist_ok=True)
        self._fired: List[AlertEvent] = []   # history this session

    # ─────────────────────────────────────────────────────────────────────
    # Main check
    # ─────────────────────────────────────────────────────────────────────

    def check(
        self,
        counters:        RunCounters,
        dataset_size_gb: float = 0.0,
    ) -> List[AlertEvent]:
        """
        Evaluate all thresholds.  Returns only the *newly fired* alerts
        (not repeats already seen this run).

        Call after every task_finished().
        """
        thr = self.thresholds
        new_alerts: List[AlertEvent] = []

        # Don't alert based on too-few observations
        if counters.tasks_processed < thr.min_tasks_before_alert:
            return new_alerts

        # ── Failure rate too HIGH ─────────────────────────────────────
        if counters.failure_rate > thr.failure_rate_high:
            new_alerts.append(AlertEvent(
                level         = AlertLevel.CRITICAL,
                alert_type    = "FAILURE_RATE_HIGH",
                message       = (
                    f"Task failure rate {counters.failure_rate:.1%} exceeds "
                    f"critical threshold {thr.failure_rate_high:.0%}. "
                    "Check parser / replay configuration."
                ),
                current_value = counters.failure_rate,
                threshold     = thr.failure_rate_high,
            ))

        # ── Failure rate suspiciously LOW ─────────────────────────────
        elif counters.failure_rate < thr.failure_rate_low and counters.tasks_processed >= 50:
            new_alerts.append(AlertEvent(
                level         = AlertLevel.WARNING,
                alert_type    = "FAILURE_RATE_LOW",
                message       = (
                    f"Task failure rate {counters.failure_rate:.1%} is very low "
                    f"(threshold {thr.failure_rate_low:.0%}). "
                    "Failure detection may not be working."
                ),
                current_value = counters.failure_rate,
                threshold     = thr.failure_rate_low,
            ))

        # ── Recovery rate LOW ─────────────────────────────────────────
        if (
            counters.recoveries_attempted >= 5
            and counters.recovery_rate < thr.recovery_rate_low
        ):
            new_alerts.append(AlertEvent(
                level         = AlertLevel.WARNING,
                alert_type    = "RECOVERY_RATE_LOW",
                message       = (
                    f"Recovery success rate {counters.recovery_rate:.1%} is below "
                    f"threshold {thr.recovery_rate_low:.0%}."
                ),
                current_value = counters.recovery_rate,
                threshold     = thr.recovery_rate_low,
            ))

        # ── Step error rate HIGH ──────────────────────────────────────
        if counters.step_failure_rate > thr.error_rate_high:
            new_alerts.append(AlertEvent(
                level         = AlertLevel.WARNING,
                alert_type    = "STEP_ERROR_RATE_HIGH",
                message       = (
                    f"Step error rate {counters.step_failure_rate:.1%} exceeds "
                    f"threshold {thr.error_rate_high:.0%}."
                ),
                current_value = counters.step_failure_rate,
                threshold     = thr.error_rate_high,
            ))

        # ── Storage WARNING ───────────────────────────────────────────
        if dataset_size_gb >= thr.storage_critical_gb:
            new_alerts.append(AlertEvent(
                level         = AlertLevel.CRITICAL,
                alert_type    = "STORAGE_CRITICAL",
                message       = (
                    f"Dataset size {dataset_size_gb:.1f} GB exceeds critical "
                    f"limit {thr.storage_critical_gb:.0f} GB."
                ),
                current_value = dataset_size_gb,
                threshold     = thr.storage_critical_gb,
            ))
        elif dataset_size_gb >= thr.storage_warning_gb:
            new_alerts.append(AlertEvent(
                level         = AlertLevel.WARNING,
                alert_type    = "STORAGE_WARNING",
                message       = (
                    f"Dataset size {dataset_size_gb:.1f} GB exceeds warning "
                    f"limit {thr.storage_warning_gb:.0f} GB."
                ),
                current_value = dataset_size_gb,
                threshold     = thr.storage_warning_gb,
            ))

        # ── De-duplicate against already-fired alerts ─────────────────
        existing_types = {a.alert_type for a in self._fired}
        truly_new = [a for a in new_alerts if a.alert_type not in existing_types]

        for alert in truly_new:
            self._fire(alert)

        return truly_new

    # ─────────────────────────────────────────────────────────────────────
    # Firing logic
    # ─────────────────────────────────────────────────────────────────────

    _COLORS = {
        AlertLevel.INFO:     "\033[32m",
        AlertLevel.WARNING:  "\033[33m",
        AlertLevel.CRITICAL: "\033[31m",
    }
    _RESET = "\033[0m"

    def _fire(self, alert: AlertEvent) -> None:
        color = self._COLORS.get(alert.level, "")
        ts    = alert.timestamp[:19].replace("T", " ")
        print(
            f"{color}[ALERT {alert.level}]{self._RESET}  "
            f"{ts}  {alert.alert_type}  {alert.message}"
        )

        # Log via stdlib
        log_level = logging.WARNING if alert.level == AlertLevel.WARNING else logging.CRITICAL
        logger.log(log_level, f"ALERT {alert.alert_type}: {alert.message}")

        # Persist to JSONL
        try:
            with self._alert_file.open("a", encoding="utf-8") as fh:
                fh.write(alert.model_dump_json() + "\n")
        except Exception as exc:
            logger.warning(f"Could not write alert file: {exc}")

        self._fired.append(alert)

    # ─────────────────────────────────────────────────────────────────────
    # History
    # ─────────────────────────────────────────────────────────────────────

    def all_alerts(self) -> List[AlertEvent]:
        return list(self._fired)

    def has_critical(self) -> bool:
        return any(a.level == AlertLevel.CRITICAL for a in self._fired)
