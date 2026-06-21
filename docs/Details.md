# Failure-Aware Web Interaction Trajectory Dataset  
## Data Collection Project Plan & System Overview

---

# 1. Project Overview

## 1.1 Objective

The objective of this project is to design, implement, and deploy a structured data collection system to build a:

> **Failure-Aware Vision-Based Web Interaction Trajectory Dataset**

This dataset will support research on resilient autonomous web agents capable of:

- Detecting execution failures in real time
- Diagnosing root causes across perception, reasoning, UI variation, and tool errors
- Recovering adaptively using structured recovery strategies
- Verifying state transitions before continuing
- Learning from experience through reflection and memory signals

The dataset will capture structured state–action–transition records from real browser interactions and augment them with failure-aware annotations.

---

# 2. Project Scope

## 2.1 In Scope

- Real browser-based interaction capture (Playwright/Selenium)
- Screenshot-based state representation
- Failure detection and categorization
- Recovery strategy simulation
- Reflection and confidence annotation
- Structured JSONL dataset storage
- Monitoring and logging infrastructure
- Dataset versioning and reproducibility

## 2.2 Out of Scope

- Large-scale RL training at this stage
- Full production-grade web automation
- Distributed cloud orchestration (optional future extension)

---

# 3. Dataset Goals

## 3.1 Minimum Viable Dataset (MVD)

- 300–500 tasks
- 15,000–30,000 interaction steps
- 30–40% failure rate
- Recovery attempts for ≥ 50% of failures
- 10–20 domains
- 30% long-horizon tasks (>10 steps)

## 3.2 Target Q1-Level Dataset

- 1,000+ tasks
- 50,000–100,000 steps
- 40–50% failure rate
- ≥ 60% failures with recovery traces
- 30+ domains
- Domain-aware test split

---

# 4. System Architecture Overview

The data collection system follows a modular layered design:

Task Source Layer
↓
Orchestration Layer
↓
Browser Execution Layer
↓
State Capture Layer
↓
Failure & Recovery Labeling Layer
↓
Storage & Monitoring Layer


Each layer is independently testable and version-controlled.

---

# 5. Component-Level Design

## 5.1 Task Source Layer

### Inputs:
- Mind2Web
- MiniWoB++
- WebArena
- Custom defined tasks

### Output Format:
{
task_id,
task_description,
website_domain,
start_url
}


### Responsibilities:
- Normalize task definitions
- Provide consistent task schema
- Enable domain-aware sampling

---

## 5.2 Orchestration Layer

### Responsibilities:
- Manage browser workers
- Assign tasks
- Control execution loops
- Handle crash recovery
- Maintain run metadata

### Features:
- Parallel task execution
- Worker isolation
- Restart on failure
- Run manifest generation

---

## 5.3 Browser Execution Layer

### Built Using:
- Playwright (recommended)
- Selenium (alternative)

### Responsibilities:
- Launch browser sessions
- Open URLs
- Execute actions (CLICK, TYPE, SCROLL, SELECT, NAVIGATE)
- Capture screenshots
- Wait for stabilization

### Design Principles:
- Fixed viewport (e.g., 1280×720)
- Clean context per task
- Deterministic wait logic
- Headless mode for scaling

---

## 5.4 State Capture Layer

For each interaction step:

1. Capture `state_before`
2. Execute action
3. Capture `state_after`
4. Compute:
   - visual_diff_score
   - state hash

### Screenshot Policy:
- PNG format
- Consistent resolution
- Deterministic naming

---

## 5.5 Failure & Recovery Labeling Layer

### 5.5.1 Failure Detection

Using:
- Visual difference thresholds
- Loop detection via state hashing
- Browser exceptions
- Timeout signals

Produces:
- execution_outcome
- failure_confidence

---

### 5.5.2 Failure Diagnosis

Failure categories:

- PERCEPTION_ERROR
- ACTION_MISMATCH
- STATE_NO_CHANGE
- LOOP_DETECTED
- GOAL_MISALIGNMENT
- TOOL_FAILURE
- UI_VARIATION
- REASONING_ERROR
- NONE

Diagnosis uses:
- Visual metrics
- Grounding mismatch detection
- Task objective heuristics

---

### 5.5.3 Recovery Engine

If failure occurs, attempt:

- RETRY
- BACKTRACK
- ALTERNATIVE_TARGET
- REPLAN
- ABORT

Record:
- recovery_strategy
- recovery_success

---

### 5.5.4 Reflection & Memory Signals

Add:

- agent_confidence_before
- reflection_text
- memory_update_flag

These support learning-based resilience research.

---

# 6. Storage Architecture

## 6.1 Directory Structure

dataset/
images/{task_id}/
before_{step_id}.png
after_{step_id}.png
records/{task_id}.jsonl
splits/train.jsonl
splits/val.jsonl
splits/test.jsonl
docs/


## 6.2 Storage Estimate

Assuming:
- 100,000 images
- 300KB each

Total ≈ 30GB

Recommended storage: 50–80GB

---

# 7. Hardware Requirements

## 7.1 Data Collection Phase

CPU:
- 6–12 cores recommended

RAM:
- 16–32GB

GPU:
- Not required

Storage:
- 50GB minimum

---

## 7.2 Training Phase

GPU:
- 1× 24GB GPU minimum (RTX 3090/4090/A5000)
- A100 40GB preferred

RAM:
- 32GB recommended

Storage:
- +50GB for models and logs

---

# 8. Monitoring & Observability

## 8.1 What to Monitor

- Total tasks processed
- Steps per task
- Failure rate
- Recovery success rate
- Loop frequency
- Tool failure rate
- Storage growth

## 8.2 Logging

Maintain:
- Per-task JSONL logs
- Run manifest file
- Git commit hash
- Environment config snapshot

Generate:
- Daily monitoring report

---

# 9. Step-by-Step Execution Plan

## Phase 1 — Task Loader Implementation
Deliver:
- Unified task schema
- Source integration

## Phase 2 — Browser Recorder Implementation
Deliver:
- Raw trajectory logs
- Screenshot storage

## Phase 3 — Metric Computation
Deliver:
- visual_diff_score
- state hashes

## Phase 4 — Failure Labeling
Deliver:
- execution_outcome
- failure_type
- failure_confidence

## Phase 5 — Recovery Generation
Deliver:
- recovery_strategy
- recovery_success

## Phase 6 — Reflection Annotation
Deliver:
- confidence
- explanation
- memory flag

## Phase 7 — Data Cleaning & Splitting
Deliver:
- Train/val/test splits
- Schema validation

---

# 10. Risk Management

## Potential Risks

- Browser instability
- Dynamic UI variability
- Excessive storage growth
- Low failure rate
- Data imbalance

## Mitigation

- Auto-restart workers
- Inject controlled failures
- Compression pipeline
- Balance dataset distribution
- Monitor daily statistics

---

# 11. Deliverables

1. Structured Failure-Aware Dataset v1.0
2. Dataset documentation
3. Collection protocol documentation
4. Monitoring report
5. Reproducibility guide

---

# 12. Success Criteria

The data collection project is successful if:

- The dataset contains structured failure transitions
- Recovery traces are meaningful and diverse
- Failure types are balanced and reproducible
- Dataset can train failure-aware models
- Documentation supports external replication

---

# 13. Future Extensions

- Distributed data collection
- Multi-agent interaction capture
- Cross-platform (mobile/desktop) integration
- Real-time labeling pipeline
- Reinforcement learning feedback loops

---

# 14. Conclusion

This data collection system is designed not merely to record web interactions but to capture structured failure-aware trajectories that enable research in resilient autonomous web agents.

The architecture emphasizes:

- Modularity
- Reproducibility
- Observability
- Scalability
- Research-grade annotation quality

This foundation supports the development of failure-aware, adaptive, and introspective web automation systems.
