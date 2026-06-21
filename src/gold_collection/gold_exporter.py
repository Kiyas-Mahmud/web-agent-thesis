"""Export leakage-safe gold dataset files for model fine-tuning."""

from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .gold_schema import FORBIDDEN_TRAINING_FIELDS, GoldStep


@dataclass
class GoldExportConfig:
    input_audit: str = "output/gold_dataset/gold_audit.jsonl"
    output_dir: str = "output/gold_dataset"
    train_ratio: float = 0.60
    val_ratio: float = 0.20
    test_ratio: float = 0.20
    seed: int = 42
    approved_only: bool = False
    anonymize_ids: bool = True
    include_source_domain: bool = False


class GoldExporter:
    def __init__(self, config: GoldExportConfig | None = None):
        self.config = config or GoldExportConfig()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self) -> Dict[str, Any]:
        steps = self.load_audit_steps(Path(self.config.input_audit))
        if self.config.approved_only:
            steps = [step for step in steps if step.review_status == "approved"]

        split_rows = self._split_by_task(steps)
        for split_name, rows in split_rows.items():
            self._assert_no_forbidden_fields(rows)
            path = self.output_dir / f"split_{split_name}.json"
            with path.open("w", encoding="utf-8") as f:
                json.dump(rows, f, indent=2, ensure_ascii=False)

        summary = self._summary(split_rows)
        with (self.output_dir / "gold_export_summary.json").open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        return summary

    def load_audit_steps(self, path: Path) -> List[GoldStep]:
        if not path.is_file():
            raise FileNotFoundError(f"Gold audit file not found: {path}")
        steps: List[GoldStep] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    steps.append(GoldStep(**json.loads(line)))
        return steps

    def _split_by_task(self, steps: List[GoldStep]) -> Dict[str, List[Dict[str, Any]]]:
        by_task: Dict[str, List[GoldStep]] = defaultdict(list)
        for step in steps:
            by_task[step.task_id].append(step)

        task_ids = sorted(by_task)
        task_aliases = {
            task_id: f"gold_task_{idx:06d}"
            for idx, task_id in enumerate(task_ids, start=1)
        }
        rng = random.Random(self.config.seed)
        rng.shuffle(task_ids)

        n = len(task_ids)
        train_end = int(n * self.config.train_ratio)
        val_end = train_end + int(n * self.config.val_ratio)
        split_tasks = {
            "train": set(task_ids[:train_end]),
            "val": set(task_ids[train_end:val_end]),
            "test": set(task_ids[val_end:]),
        }

        split_rows = {"train": [], "val": [], "test": []}
        for split_name, ids in split_tasks.items():
            for task_id in sorted(ids):
                for step in by_task[task_id]:
                    row = step.model_record()
                    if self.config.anonymize_ids:
                        task_alias = task_aliases[task_id]
                        row["task_id"] = task_alias
                        row["sample_id"] = f"{task_alias}__step_{step.step_index:04d}"
                    if not self.config.include_source_domain:
                        row.pop("source", None)
                        row.pop("website_domain", None)
                    split_rows[split_name].append(row)
        return split_rows

    def _assert_no_forbidden_fields(self, rows: Iterable[Dict[str, Any]]) -> None:
        for idx, row in enumerate(rows):
            leaked = set(row) & FORBIDDEN_TRAINING_FIELDS
            if leaked:
                raise ValueError(f"Row {idx} contains forbidden fields: {sorted(leaked)}")

    def _summary(self, split_rows: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        all_rows = [row for rows in split_rows.values() for row in rows]
        task_sets = {
            split_name: {row["task_id"] for row in rows}
            for split_name, rows in split_rows.items()
        }
        return {
            "total_rows": len(all_rows),
            "splits": {name: len(rows) for name, rows in split_rows.items()},
            "tasks": {name: len(tasks) for name, tasks in task_sets.items()},
            "task_overlap": {
                "train_val": len(task_sets["train"] & task_sets["val"]),
                "train_test": len(task_sets["train"] & task_sets["test"]),
                "val_test": len(task_sets["val"] & task_sets["test"]),
            },
            "outcome": dict(Counter(row["outcome_label"] for row in all_rows).most_common()),
            "failure_type_4": dict(Counter(row["failure_type_4"] for row in all_rows).most_common()),
            "failure_type_4_eval_mask_false": sum(
                1 for row in all_rows if not row["failure_type_4_eval_mask"]
            ),
            "recovery_strategy": dict(Counter(row["recovery_strategy"] for row in all_rows).most_common()),
            "forbidden_fields_removed": sorted(FORBIDDEN_TRAINING_FIELDS),
        }
