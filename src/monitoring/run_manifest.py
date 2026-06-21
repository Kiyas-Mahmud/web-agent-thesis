"""
Run Manifest
============
Captures a reproducibility snapshot at the start of every collection run
and updates it when the run finishes.

What is captured
----------------
- Unique run_id
- Git commit hash + branch (if inside a git repo)
- Python version + installed packages
- Hardware info (CPU, RAM, disk)
- Safe subset of environment variables
- Run configuration dict
- Final RunCounters

Files written
-------------
  dataset/logs/manifests/run_<run_id>.json   ← one per run
  dataset/logs/manifests/latest.json         ← always points to the last run
"""

from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .monitor_schema import EnvironmentInfo, RunCounters, RunManifest

logger = logging.getLogger("dc.RunManifest")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _git_info() -> tuple[Optional[str], Optional[str]]:
    """Return (commit_hash, branch_name) or (None, None) if not a git repo."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        return commit, branch
    except Exception:
        return None, None


def _installed_packages() -> Dict[str, str]:
    """Return {package_name: version} for every installed dist."""
    try:
        import importlib.metadata as meta
        return {d.metadata["Name"]: d.version for d in meta.distributions()}
    except Exception:
        return {}


def _hardware_info() -> Dict[str, Any]:
    """CPU count, total RAM (GB), disk info."""
    info: Dict[str, Any] = {
        "cpu_count": os.cpu_count(),
        "platform":  platform.platform(),
        "machine":   platform.machine(),
    }
    try:
        import psutil
        vm = psutil.virtual_memory()
        info["ram_total_gb"] = round(vm.total / 1e9, 2)
        info["ram_available_gb"] = round(vm.available / 1e9, 2)
        du = psutil.disk_usage(str(Path.cwd()))
        info["disk_total_gb"]  = round(du.total  / 1e9, 2)
        info["disk_free_gb"]   = round(du.free   / 1e9, 2)
    except ImportError:
        pass
    return info


_SAFE_ENV_KEYS = {
    "PYTHONPATH", "VIRTUAL_ENV", "CONDA_DEFAULT_ENV",
    "COMPUTERNAME", "OS", "PROCESSOR_ARCHITECTURE",
    "PATH",  # truncated
}


def _safe_env() -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k in _SAFE_ENV_KEYS:
        v = os.environ.get(k)
        if v:
            out[k] = v[:200]   # truncate very long PATH etc.
    return out


# ─────────────────────────────────────────────────────────────────────────────
# ManifestManager
# ─────────────────────────────────────────────────────────────────────────────

class ManifestManager:
    """
    Create, update, and persist the run manifest.

    Usage
    -----
        mgr = ManifestManager(run_id="run_abc123", output_dir="dataset", config={...})
        mgr.save()              # called at start

        # ... run finishes ...
        mgr.finalise(counters)
        mgr.save()              # called at end
    """

    def __init__(
        self,
        run_id:     str,
        output_dir: str | Path,
        config:     Dict[str, Any] | None = None,
    ):
        self._dir = Path(output_dir) / "logs" / "manifests"
        self._dir.mkdir(parents=True, exist_ok=True)

        commit, branch = _git_info()

        env = EnvironmentInfo(
            python_version = sys.version,
            platform       = platform.platform(),
            packages       = _installed_packages(),
            hardware       = _hardware_info(),
            env_variables  = _safe_env(),
        )

        self.manifest = RunManifest(
            run_id     = run_id,
            start_time = datetime.utcnow().isoformat(),
            git_commit = commit,
            git_branch = branch,
            config     = config or {},
            environment= env,
        )

        logger.info(
            f"Run manifest created  run_id={run_id}  "
            f"git={commit or 'n/a'}@{branch or 'n/a'}"
        )

    # ── Persistence ───────────────────────────────────────────────────────

    def save(self) -> Path:
        """Write manifest to JSON. Returns the file path."""
        path = self._dir / f"{self.manifest.run_id}.json"
        path.write_text(
            self.manifest.model_dump_json(indent=2), encoding="utf-8"
        )
        # Also write latest.json symlink equivalent (plain copy on Windows)
        latest = self._dir / "latest.json"
        latest.write_text(
            self.manifest.model_dump_json(indent=2), encoding="utf-8"
        )
        return path

    def finalise(self, counters: RunCounters) -> None:
        """Call when the run finishes to record end_time and results."""
        self.manifest.end_time = datetime.utcnow().isoformat()
        self.manifest.results  = counters
        logger.info(
            f"Run finalised  tasks={counters.tasks_processed}  "
            f"failure_rate={counters.failure_rate:.1%}"
        )

    @classmethod
    def load_latest(cls, output_dir: str | Path) -> Optional[RunManifest]:
        """Load the most recent manifest from disk (or None)."""
        path = Path(output_dir) / "logs" / "manifests" / "latest.json"
        if not path.exists():
            return None
        return RunManifest.model_validate_json(path.read_text(encoding="utf-8"))

    def __repr__(self) -> str:  # noqa: D105
        return f"ManifestManager(run_id={self.manifest.run_id!r})"
