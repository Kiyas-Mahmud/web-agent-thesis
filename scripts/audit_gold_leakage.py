"""Audit gold train/val/test exports for simple leakage baselines.

This is intentionally conservative: if a cheap rule can solve the labels from
IDs, task text, or action text, the export is not thesis-safe for multimodal
claims.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gold_collection.gold_schema import FORBIDDEN_TRAINING_FIELDS  # noqa: E402


LEAK_KEYWORDS = re.compile(
    r"missing|non[- ]?existent|not found|does not exist|perception failure|failure|failed",
    re.IGNORECASE,
)


def load_json(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def mcc(predictions: list[str], labels: list[str]) -> float:
    tp = sum(p == "FAILURE" and y == "FAILURE" for p, y in zip(predictions, labels))
    tn = sum(p == "SUCCESS" and y == "SUCCESS" for p, y in zip(predictions, labels))
    fp = sum(p == "FAILURE" and y == "SUCCESS" for p, y in zip(predictions, labels))
    fn = sum(p == "SUCCESS" and y == "FAILURE" for p, y in zip(predictions, labels))
    denom = (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
    return ((tp * tn) - (fp * fn)) / math.sqrt(denom) if denom else 0.0


def text_rule_report(rows: list[dict[str, Any]], fields: list[str]) -> dict[str, Any]:
    labels = [row["outcome_label"] for row in rows]
    reports: dict[str, Any] = {}
    for field in fields:
        preds = [
            "FAILURE" if LEAK_KEYWORDS.search(str(row.get(field, ""))) else "SUCCESS"
            for row in rows
        ]
        reports[field] = {
            "accuracy": sum(p == y for p, y in zip(preds, labels)) / len(labels) if labels else 0.0,
            "mcc": mcc(preds, labels),
            "keyword_hits": sum(
                1 for row in rows if LEAK_KEYWORDS.search(str(row.get(field, "")))
            ),
        }
    preds = [
        "FAILURE"
        if LEAK_KEYWORDS.search(" ".join(str(row.get(field, "")) for field in fields))
        else "SUCCESS"
        for row in rows
    ]
    reports["combined"] = {
        "accuracy": sum(p == y for p, y in zip(preds, labels)) / len(labels) if labels else 0.0,
        "mcc": mcc(preds, labels),
        "keyword_hits": sum(p == "FAILURE" for p in preds),
    }
    return reports


def row_tokens(row: dict[str, Any]) -> set[str]:
    text = " ".join(
        str(row.get(field, ""))
        for field in ("task_description", "action_target_desc", "action_type")
    ).lower()
    return set(re.findall(r"[a-z0-9_]+", text))


def semantic_shortcut_report(
    split_rows: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    rows = [row for split in split_rows.values() for row in split]
    token_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        for token in row_tokens(row):
            token_counts[token][row["outcome_label"]] += 1

    pure_tokens = {
        token: dict(counts)
        for token, counts in token_counts.items()
        if sum(counts.values()) >= 2 and len(counts) == 1
    }

    train = split_rows.get("train", [])
    train_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in train:
        for token in row_tokens(row):
            train_counts[token][row["outcome_label"]] += 1
    train_failure_only = {
        token
        for token, counts in train_counts.items()
        if counts["FAILURE"] >= 1 and counts["SUCCESS"] == 0
    }

    split_scores = {}
    for split_name, split in split_rows.items():
        labels = [row["outcome_label"] for row in split]
        preds = [
            "FAILURE" if row_tokens(row) & train_failure_only else "SUCCESS"
            for row in split
        ]
        split_scores[split_name] = {
            "accuracy": sum(p == y for p, y in zip(preds, labels)) / len(labels)
            if labels
            else 0.0,
            "mcc": mcc(preds, labels) if labels else 0.0,
        }

    classifier_scores: dict[str, dict[str, float]] = {}
    try:
        from sklearn.feature_extraction.text import CountVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, matthews_corrcoef
        from sklearn.pipeline import make_pipeline

        train_text = [
            " ".join(
                str(row.get(field, ""))
                for field in ("task_description", "action_target_desc", "action_type")
            )
            for row in train
        ]
        train_labels = [row["outcome_label"] for row in train]
        if len(set(train_labels)) > 1:
            model = make_pipeline(
                CountVectorizer(ngram_range=(1, 2)),
                LogisticRegression(max_iter=1000, class_weight="balanced"),
            )
            model.fit(train_text, train_labels)
            for split_name, split in split_rows.items():
                text = [
                    " ".join(
                        str(row.get(field, ""))
                        for field in ("task_description", "action_target_desc", "action_type")
                    )
                    for row in split
                ]
                labels = [row["outcome_label"] for row in split]
                preds = model.predict(text)
                classifier_scores[split_name] = {
                    "accuracy": float(accuracy_score(labels, preds)),
                    "mcc": float(matthews_corrcoef(labels, preds)),
                }
    except Exception as exc:  # noqa: BLE001 - sklearn may not be installed.
        classifier_scores["skipped"] = {"reason": str(exc)}

    return {
        "pure_tokens": pure_tokens,
        "train_failure_only_tokens": sorted(train_failure_only),
        "train_failure_only_rule": split_scores,
        "text_classifier": classifier_scores,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit gold exports for leakage.")
    parser.add_argument("--base-dir", type=Path, default=Path("output/gold_dataset"))
    parser.add_argument("--fail-on-perfect", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    split_rows = {
        split_name: load_json(args.base_dir / f"split_{split_name}.json")
        for split_name in ("train", "val", "test")
    }
    rows = [row for split in split_rows.values() for row in split]
    if not rows:
        print("No exported split rows found.")
        return 1

    print("Rows")
    print(f"  total: {len(rows)}")
    for split_name, split in split_rows.items():
        print(f"  {split_name}: {len(split)}")

    print("Labels")
    print(f"  outcome: {dict(Counter(row['outcome_label'] for row in rows).most_common())}")
    print(f"  failure_type_4: {dict(Counter(str(row['failure_type_4']) for row in rows).most_common())}")

    leaked = sorted({field for row in rows for field in row if field in FORBIDDEN_TRAINING_FIELDS})
    print("Forbidden Fields")
    print(f"  found: {leaked}")

    fields = ["sample_id", "task_id", "task_description", "action_target_desc", "action_type"]
    reports = text_rule_report(rows, fields)
    print("Text Leakage Rules")
    perfect = False
    for field, report in reports.items():
        print(
            f"  {field}: accuracy={report['accuracy']:.4f}, "
            f"mcc={report['mcc']:.4f}, keyword_hits={report['keyword_hits']}"
        )
        perfect = perfect or report["accuracy"] >= 1.0

    semantic = semantic_shortcut_report(split_rows)
    print("Semantic Shortcut Rules")
    pure_failure_tokens = {
        token: counts
        for token, counts in semantic["pure_tokens"].items()
        if "FAILURE" in counts and "SUCCESS" not in counts
    }
    print(f"  pure_failure_tokens: {pure_failure_tokens}")
    print(f"  train_failure_only_tokens: {semantic['train_failure_only_tokens']}")
    for split_name, score in semantic["train_failure_only_rule"].items():
        print(
            f"  train_failure_only_rule[{split_name}]: "
            f"accuracy={score['accuracy']:.4f}, mcc={score['mcc']:.4f}"
        )
    for split_name, score in semantic["text_classifier"].items():
        if "reason" in score:
            print(f"  text_classifier[{split_name}]: skipped={score['reason']}")
        else:
            print(
                f"  text_classifier[{split_name}]: "
                f"accuracy={score['accuracy']:.4f}, mcc={score['mcc']:.4f}"
            )

    print("Verdict")
    blockers = []
    if leaked:
        blockers.append("export contains forbidden fields")
    if perfect:
        blockers.append("a keyword text rule solves outcome perfectly")
    if pure_failure_tokens:
        blockers.append("some semantic tokens appear only in failure rows")
    if any(
        score.get("mcc", 0.0) >= 0.8
        for score in semantic["train_failure_only_rule"].values()
    ):
        blockers.append("a train-learned token rule is a strong outcome predictor")
    if any(
        score.get("mcc", 0.0) >= 0.8
        for score in semantic["text_classifier"].values()
        if "mcc" in score
    ):
        blockers.append("a text-only classifier is a strong outcome predictor")
    if blockers:
        for blocker in blockers:
            print(f"  BLOCKER: {blocker}")
        return 1 if args.fail_on_perfect else 0
    print("  NO OBVIOUS TEXT LEAKAGE FOUND")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
