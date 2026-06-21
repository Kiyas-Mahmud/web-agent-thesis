"""
monitoring
==========
Structured logging, metrics tracking, run manifests, alerts, and a
terminal dashboard for the data-collection pipeline.

Quick usage
-----------
    from monitoring import (
        configure_logging,
        get_logger,
        ManifestManager,
        MetricsTracker,
        AlertSystem,
        ProgressDashboard,
        AlertThresholds,
    )

    configure_logging(run_id="run_abc123", log_dir="dataset/logs", debug=False)
    log = get_logger("MyComponent")
    log.info("ready")
"""

from .structured_logger import configure_logging, get_logger, ComponentLogger
from .run_manifest      import ManifestManager
from .metrics_tracker   import MetricsTracker
from .alert_system      import AlertSystem
from .dashboard         import ProgressDashboard
from .monitor_schema    import (
    AlertThresholds,
    AlertEvent,
    AlertLevel,
    LogEvent,
    LogLevel,
    RunCounters,
    RunManifest,
    TaskRecord,
    TaskStatus,
    StepRecord,
)

__all__ = [
    # logging
    "configure_logging",
    "get_logger",
    "ComponentLogger",
    # run management
    "ManifestManager",
    # metrics
    "MetricsTracker",
    # alerts
    "AlertSystem",
    "AlertThresholds",
    "AlertEvent",
    "AlertLevel",
    # dashboard
    "ProgressDashboard",
    # schemas
    "LogEvent",
    "LogLevel",
    "RunCounters",
    "RunManifest",
    "TaskRecord",
    "TaskStatus",
    "StepRecord",
]
