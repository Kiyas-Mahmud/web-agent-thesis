# Failure-Aware Web Interaction Trajectory Dataset

## Project Plan & Task Tracking

**Project Start Date:** February 19, 2026  
**Expected Completion:** Q1 2026  
**Project Lead:** [Your Name]

---

## 1. Executive Summary

This project aims to build a **Failure-Aware Vision-Based Web Interaction Trajectory Dataset** to support research on resilient autonomous web agents. The system will capture 50,000–100,000 interaction steps across 1,000+ tasks with structured failure annotations and recovery strategies.

---

## 2. Project Phases Overview

| Phase       | Task ID               | Task Name                       | Status         | Priority  | Duration  |
| ----------- | --------------------- | ------------------------------- | -------------- | --------- | --------- |
| **Phase 1** | [Task-01](task-01.md) | Task Loader Implementation      | ✅ Completed   | 🔴 High   | 1 day     |
| **Phase 2** | [Task-02](task-02.md) | Browser Recorder Implementation | ✅ Completed   | 🔴 High   | ~2 hours  |
| **Phase 3** | [Task-03](task-03.md) | Metric Computation              | ✅ Completed   | 🟡 Medium | ~2 hours  |
| **Phase 4** | [Task-04](task-04.md) | Failure Labeling                | ✅ Completed   | 🔴 High   | ~2 hours  |
| **Phase 5** | [Task-05](task-05.md) | Recovery Generation             | ⬜ Not Started | 🟡 Medium | 1-2 weeks |
| **Phase 6** | [Task-06](task-06.md) | Reflection Annotation           | ⬜ Not Started | 🟢 Low    | 1 week    |
| **Phase 7** | [Task-07](task-07.md) | Data Cleaning & Splitting       | ⬜ Not Started | 🟡 Medium | 1 week    |
| **Phase 8** | [Task-08](task-08.md) | Monitoring & Infrastructure     | ⬜ Not Started | 🟡 Medium | Ongoing   |
| **Phase 9** | [Task-09](task-09.md) | Documentation & Validation      | ⬜ Not Started | 🟢 Low    | 1 week    |

**Status Legend:**

- ⬜ Not Started
- 🔄 In Progress
- ✅ Completed
- ⚠️ Blocked
- 🔴 High Priority | 🟡 Medium Priority | 🟢 Low Priority

---

## 3. Milestone Tracking

### Milestone 1: Foundation Setup (Weeks 1-2)

- ✅ Project structure initialized
- ✅ Development environment configured
- ✅ Task loader implemented
- [ ] Basic browser automation working

**Target Date:** Week 2  
**Status:** 🔄 In Progress (75% complete)

### Milestone 2: Core Data Collection (Weeks 3-5)

- [ ] Browser recorder fully functional
- [ ] Screenshot capture working
- [ ] State capture layer implemented
- [ ] Metric computation operational

**Target Date:** Week 5  
**Status:** ⬜ Not Started

### Milestone 3: Failure Awareness (Weeks 6-8)

- [ ] Failure detection implemented
- [ ] Recovery strategies integrated
- [ ] Reflection layer added
- [ ] MVD achieved (300-500 tasks)

**Target Date:** Week 8  
**Status:** ⬜ Not Started

### Milestone 4: Production Ready (Weeks 9-10)

- [ ] Data cleaning pipeline complete
- [ ] Train/val/test splits generated
- [ ] Monitoring dashboard operational
- [ ] Full documentation delivered

**Target Date:** Week 10  
**Status:** ⬜ Not Started

---

## 4. Dataset Targets

### 4.1 Minimum Viable Dataset (MVD)

- [ ] 300–500 tasks
- [ ] 15,000–30,000 interaction steps
- [ ] 30–40% failure rate
- [ ] Recovery attempts for ≥ 50% of failures
- [ ] 10–20 domains
- [ ] 30% long-horizon tasks (>10 steps)

**Status:** 0% Complete

### 4.2 Target Q1-Level Dataset

- [ ] 1,000+ tasks
- [ ] 50,000–100,000 steps
- [ ] 40–50% failure rate
- [ ] ≥ 60% failures with recovery traces
- [ ] 30+ domains
- [ ] Domain-aware test split

**Status:** 0% Complete

---

## 5. Resource Allocation

### 5.1 Hardware Requirements

- **CPU:** 6–12 cores
- **RAM:** 16–32GB
- **Storage:** 50–80GB allocated
- **GPU:** 1× 24GB (for future training)

**Status:** ⬜ Pending Setup

### 5.2 Software Stack

- [ ] Playwright/Selenium installed
- [ ] Python environment configured
- [ ] Storage infrastructure ready
- [ ] Monitoring tools setup

**Status:** ⬜ Pending

---

## 6. Risk Management

| Risk                | Probability | Impact | Mitigation                 | Status     |
| ------------------- | ----------- | ------ | -------------------------- | ---------- |
| Browser instability | High        | High   | Auto-restart workers       | 🟡 Monitor |
| Low failure rate    | Medium      | High   | Inject controlled failures | ⬜ Plan    |
| Storage overflow    | Medium      | Medium | Compression pipeline       | ⬜ Plan    |
| Data imbalance      | High        | Medium | Balanced sampling          | ⬜ Plan    |
| UI variability      | High        | High   | Multi-domain testing       | ⬜ Plan    |

---

## 7. Weekly Progress Tracker

### Week 1 (Feb 19 - Feb 25, 2026)

**Goals:**

- ✅ Initialize project structure
- ✅ Complete Task-01: Task Loader Implementation
- ✅ Complete Task-02: Browser Recorder Implementation
- ✅ Complete Task-03: Metric Computation

**Status:** Current Week  
**Progress:** 100% (Tasks 01, 02, and 03 completed ahead of schedule!)

### Week 2 (Feb 26 - Mar 3, 2026)

**Goals:**

- [ ] Complete Task-01
- [ ] Begin Task-02: Browser Recorder

**Status:** Upcoming  
**Progress:** 0%

---

## 8. Deliverables Checklist

- [ ] **Structured Failure-Aware Dataset v1.0**
  - [ ] JSONL records
  - [ ] Screenshot images
  - [ ] Train/val/test splits
- [ ] **Documentation**
  - [ ] Dataset documentation
  - [ ] Collection protocol guide
  - [ ] Reproducibility guide
  - [ ] Architecture diagram
- [ ] **Monitoring Report**
  - [ ] Daily statistics
  - [ ] Quality metrics
  - [ ] Failure distribution analysis
- [ ] **Code Repository**
  - [ ] Clean, documented codebase
  - [ ] Unit tests
  - [ ] Configuration files
  - [ ] README with setup instructions

---

## 9. Success Criteria

✅ **Project is successful when:**

1. Dataset contains structured failure transitions
2. Recovery traces are meaningful and diverse
3. Failure types are balanced and reproducible
4. Dataset can train failure-aware models
5. Documentation supports external replication

---

## 10. Communication & Reporting

### Daily Updates

- Log progress in task-specific .md files
- Update this project-plan.md status
- Commit changes to version control

### Weekly Reviews

- Review milestone progress
- Assess risks and blockers
- Adjust timeline if needed

### Final Report

- Comprehensive dataset analysis
- Lessons learned
- Future recommendations

---

## 11. Quick Links

- [Details.md](Details.md) - Full project specification
- [architecture-diagram.md](architecture-diagram.md) - System architecture
- [Task-01: Task Loader](task-01.md)
- [Task-02: Browser Recorder](task-02.md)
- [Task-03: Metric Computation](task-03.md)
- [Task-04: Failure Labeling](task-04.md)
- [Task-05: Recovery Generation](task-05.md)
- [Task-06: Reflection Annotation](task-06.md)
- [Task-07: Data Cleaning & Splitting](task-07.md)
- [Task-08: Monitoring & Infrastructure](task-08.md)
- [Task-09: Documentation & Validation](task-09.md)

---

## 12. Notes & Updates

### 2026-02-19

✅ Project plan created

- ✅ Task files initialized
- ✅ Architecture diagram designed
- ✅ Task-01 completed successfully!
  - Project structure created
  - Task Loader fully implemented
  - All tests passing (14/14)
- ✅ Task-02 completed successfully! (~2 hours)
  - Browser Recorder fully implemented
  - All tests passing (33/33)
- ✅ Task-03 completed successfully! (~2 hours)
  - Metric Computation fully implemented
  - All tests passing (36/36)
- ✅ Task-04 completed successfully! (~2 hours)
  - Failure Labeling system fully implemented
  - 9 failure types with rule-based classification
  - All tests passing (25/25)
- Ready for Task-05 (Recovery Generation)

---

**Last Updated:** February 19, 2026  
**Next Review:** February 26, 2026
