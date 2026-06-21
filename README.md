# Failure-Aware Web Interaction Trajectory Dataset

## Data Collection System

This project implements a comprehensive data collection system for building a failure-aware vision-based web interaction trajectory dataset.

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- 16GB+ RAM recommended
- 50GB+ free disk space

### Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd datacollection
```

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
```

## 📊 Project Status

**Overall Progress:** 67% (6/9 tasks completed)

| Task                              | Status      | Duration |
| --------------------------------- | ----------- | -------- |
| ✅ Task-01: Task Loader           | Completed   | 1 day    |
| ✅ Task-02: Browser Recorder      | Completed   | ~2 hours |
| ✅ Task-03: Metric Computation    | Completed   | ~2 hours |
| ✅ Task-04: Failure Labeling      | Completed   | ~2 hours |
| ✅ Task-05: Recovery Generation   | Completed   | ~3 hours |
| ✅ Task-06: Reflection Annotation | Completed   | ~3 hours |
| ⬜ Task-07: Data Cleaning         | Not Started | -        |
| ⬜ Task-08: Monitoring            | Not Started | -        |
| ⬜ Task-09: Documentation         | Not Started | -        |

**Latest:** Reflection Annotation with confidence scoring, memory signals, and 31/33 tests passing! 🎉

## ✅ Completed Tasks

### Task-06: Reflection Annotation

- **Confidence Estimation**: Before/after action scoring with 20+ factors (element detection, action history, page complexity, metrics)
- **Reflection Generation**: Template-based natural language explanations (success, failure, recovery, timeout, loop scenarios)
- **Memory Signals**: Automatic detection of novel failures, successful recoveries, high uncertainty, and surprising outcomes
- **5 Memory Types**: SUCCESS, FAILURE, RECOVERY, INSIGHT, NONE for learning system integration
- **Introspection Metadata**: Reasoning types (6), uncertainty sources (7), learning signals, context factors
- **Tests**: 31/33 passing (schema, confidence, reflection, memory, full annotation pipeline)

### Task-05: Recovery Generation

- **5 Recovery Strategies**: RETRY, BACKTRACK, ALTERNATIVE_TARGET, REPLAN, ABORT
- **9 Failure Mappings**: Smart strategy selection based on failure type
- **Multi-Strategy Workflows**: Sequential attempts until success or exhaustion
- **Statistics Tracking**: Success rates, timing, per-strategy effectiveness
- **Tests**: 31/31 passing (schema, selector, executors, engine, integration)

### Task-04: Failure Labeling

- **9 Failure Types**: PERCEPTION_ERROR, ACTION_MISMATCH, STATE_NO_CHANGE, LOOP_DETECTED, GOAL_MISALIGNMENT, TOOL_FAILURE, UI_VARIATION, REASONING_ERROR, NONE
- **13 Signal Types**: Visual, state, performance, exception, and UI signals
- **Confidence Scoring**: Weighted evidence aggregation with 0.0-1.0 confidence
- **Tests**: 25/25 passing (signal detection, classification, diagnostics, integration)

### Task-03: Metric Computation

- **Visual Metrics**: Pixel diff, SSIM, MSE with automatic change level classification
- **State Metrics**: SHA-256 and perceptual hashing, loop detection with deque-based tracking
- **Performance Metrics**: Execution times, stability waits, total step duration
- **Tests**: 36/36 passing (visual metrics, state hashing, loop detection, integration)

### Task-02: Browser Recorder

- **8 Action Types**: Navigate, click, type, scroll, select, wait, press_key, custom
- **Visual Recording**: Full-page screenshots with metadata
- **Action Logs**: Detailed execution logs with status, errors, performance metrics
- **Tests**: 33/33 passing (navigation, interactions, visual capture, trajectories)

### Task-01: Task Loader

- **3 Dataset Parsers**: Wave UI, Mind2Web, Visual WebArena with unified schema
- **Validation**: Pydantic models ensuring data quality
- **Filters**: Difficulty, action types, domain, configurable limits
- **Tests**: 14/14 passing (loading, validation, filtering, error handling)

## 📁 Project Structure

```
datacollection/
├── src/                          # Source code
│   ├── task_loader/             # Task loading & normalization
│   ├── browser_recorder/        # Browser automation
│   ├── state_capture/           # Screenshot & state capture
│   ├── failure_labeling/        # Failure detection & classification
│   ├── recovery_generation/     # Recovery strategy execution
│   └── monitoring/              # Logging & monitoring
├── tests/                       # Unit & integration tests
├── config/                      # Configuration files
├── dataset/                     # Dataset storage
│   ├── images/                 # Screenshots
│   ├── records/                # JSONL trajectory records
│   └── splits/                 # Train/val/test splits
├── docs/                        # Documentation
├── scripts/                     # Utility scripts
└── logs/                        # Log files
```

## 🎯 Dataset Sources

1. **Wave UI 25K**: https://huggingface.co/datasets/agentsea/wave-ui-25k
2. **Multimodal Mind2Web**: https://huggingface.co/datasets/osunlp/Multimodal-Mind2Web
3. **Visual WebArena**: https://github.com/web-arena-x/visualwebarena

## 📊 Usage

### Load Tasks

```python
from src.task_loader import TaskLoader

loader = TaskLoader(sources=['wave-ui', 'mind2web'])
tasks = loader.load_tasks(limit=100)
```

### Run Data Collection

```python
from src.orchestrator import Orchestrator

orchestrator = Orchestrator(config='config/default.yaml')
orchestrator.run(tasks)
```

## 📖 Documentation

- [Project Plan](docs/project-plan.md)
- [Architecture](docs/architecture-diagram.md)
- [Details](docs/Details.md)
- [Complete Work Log](docs/complete-work.md)

## 🧪 Testing

```bash
pytest tests/
```

## 📝 License

[Your License Here]

## 👥 Contributors

[Your Name]

## 📧 Contact

[Your Email]
