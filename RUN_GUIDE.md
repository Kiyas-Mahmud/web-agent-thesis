# Run Guide — Failure-Aware Web Interaction Trajectory Dataset

End-to-end instructions to set up the environment, download the source data, and
generate + validate the failure-aware dataset.

> **Note on repo size:** The raw HuggingFace downloads (`dataset/mind2web_offline/`,
> `dataset/test_*`), generated `output/`, and the `.venv*` folders are **git-ignored**
> (tens of GB, re-downloadable). The repo holds **code, configs, and docs only**.

---

## 1. Prerequisites

- Python **3.8+** (3.10+ recommended)
- **16 GB+ RAM**
- **~50 GB free disk** (raw Mind2Web ≈ 38 GB + generated output)
- Internet (first run downloads the Mind2Web dataset from HuggingFace)

---

## 2. Setup

```bash
# 1. Clone
git clone https://github.com/Kiyas-Mahmud/web-agent-thesis.git
cd web-agent-thesis        # repo folder (a.k.a. datacollection)

# 2. Create + activate a virtual environment
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (cmd):       .venv\Scripts\activate.bat
# macOS / Linux:       source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
playwright install chromium      # only needed for live browser recording
```

---

## 3. Download source data (one-time, large)

Pulls the full Multimodal-Mind2Web dataset (train + test_domain + test_task +
test_website) into `dataset/mind2web_offline/`. **~38 GB, 10–30 min.**

```bash
python download_test_splits.py
```

Verify the cache loaded:

```bash
python -c "from src.offline_data import MultimodalMind2WebLoader as L; l=L(cache_dir='dataset/mind2web_offline'); print('OK' if l.load_from_cache() else 'FAILED')"
```

---

## 4. Generate the dataset

The pipeline loads real Mind2Web trajectories, injects labeled failures
(TARGET_MISSING, MISCLICK, WRONG_OPERATION, NO_STATE_CHANGE, LOOP), and attaches
recovery strategies.

### Quick path — 200-task smoke test (3–5 min)

```bash
python run_test_200.py
```

Generates → validates → opens an HTML quality report. Use this first to confirm
the pipeline works before scaling up.

### Manual / arbitrary size

```bash
# Generate N tasks
python scripts/test_downloaded_data.py --num-tasks 1000 --output-dir output/dataset_1000

# Validate against quality gates -> HTML report
python scripts/validate_quality_gate.py \
    --summary      output/dataset_1000/summary.json \
    --trajectories output/dataset_1000/augmented_trajectories.json \
    --output       output/dataset_1000/quality_report.html
```

Output layout per run:

```
output/<run-name>/
├── summary.json                  # statistics
├── augmented_trajectories.json   # full dataset
└── quality_report.html           # validation report
```

---

## 5. Quality gates (must all PASS before scaling)

| Gate                | Threshold | Why                          |
| ------------------- | --------- | ---------------------------- |
| Failure rate        | 40–60 %   | Balanced dataset             |
| LOOP presence       | ≥ 5 %     | All failure types represented|
| Recovery strategies | > 0 %     | Every failure has a recovery |
| Missing data        | 0         | Complete dataset             |
| Failure types       | 5 / 5     | Comprehensive coverage       |

Quick LOOP check:

```bash
python -c "import json; s=json.load(open('output/dataset_1000/summary.json')); d=s['failure_distribution']; loop=d.get('LOOP',0); tot=s['augmented_steps']; print(f'LOOP: {loop} ({loop/tot*100:.1f}%)')"
```

---

## 6. Tests

```bash
pytest tests/
```

---

## 7. Troubleshooting

| Symptom                       | Fix                                                                 |
| ----------------------------- | ------------------------------------------------------------------- |
| LOOP < 5 %                    | Confirm `state_after` screenshots load (re-run with screenshots on).|
| Failure rate outside 40–60 %  | Adjust `InjectionConfig` weights in `scripts/test_downloaded_data.py`.|
| Recovery strategies 0/0       | No augmented steps found — check serialization in the test script.  |
| Out of memory / crash         | Close other apps; generate in smaller batches.                      |
| `dataset/mind2web_offline` missing | Re-run `python download_test_splits.py`.                       |

---

## Pipeline at a glance

```
download_test_splits.py        → dataset/mind2web_offline/   (raw Mind2Web)
scripts/test_downloaded_data.py → output/<run>/              (inject failures + recovery)
scripts/validate_quality_gate.py → quality_report.html       (gate the result)
```

See [README.md](README.md) for module-level architecture and
[QUICK_START.md](QUICK_START.md) / [RUN_THIS_NOW.md](RUN_THIS_NOW.md) for the
step-by-step scaling workflow.
