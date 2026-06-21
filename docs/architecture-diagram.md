# Data Collection Architecture Diagram

**Project:** Failure-Aware Web Interaction Trajectory Dataset  
**Last Updated:** February 19, 2026

---

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph "Task Source Layer"
        A1[Mind2Web]
        A2[MiniWoB++]
        A3[WebArena]
        A4[Custom Tasks]
    end

    subgraph "Orchestration Layer"
        B1[Task Scheduler]
        B2[Worker Manager]
        B3[Run Controller]
    end

    subgraph "Browser Execution Layer"
        C1[Browser Session]
        C2[Action Executor]
        C3[Wait Controller]
    end

    subgraph "State Capture Layer"
        D1[Screenshot Capture]
        D2[State Manager]
        D3[Metric Computation]
    end

    subgraph "Failure & Recovery Layer"
        E1[Failure Detector]
        E2[Failure Classifier]
        E3[Recovery Engine]
        E4[Reflection Generator]
    end

    subgraph "Storage Layer"
        F1[Image Storage]
        F2[JSONL Writer]
        F3[Metadata Store]
    end

    subgraph "Monitoring Layer"
        G1[Logger]
        G2[Metrics Collector]
        G3[Dashboard]
        G4[Alert System]
    end

    A1 & A2 & A3 & A4 --> B1
    B1 --> B2
    B2 --> B3
    B3 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> D1
    D1 --> D2
    D2 --> D3
    D3 --> E1
    E1 --> E2
    E2 --> E3
    E3 --> E4
    E4 --> F1 & F2 & F3

    C1 & C2 & D1 & E1 & E3 -.-> G1
    G1 --> G2
    G2 --> G3
    G3 --> G4

    style A1 fill:#e1f5ff
    style A2 fill:#e1f5ff
    style A3 fill:#e1f5ff
    style A4 fill:#e1f5ff
    style B1 fill:#fff4e6
    style B2 fill:#fff4e6
    style B3 fill:#fff4e6
    style C1 fill:#f3e5f5
    style C2 fill:#f3e5f5
    style C3 fill:#f3e5f5
    style D1 fill:#e8f5e9
    style D2 fill:#e8f5e9
    style D3 fill:#e8f5e9
    style E1 fill:#ffe0e0
    style E2 fill:#ffe0e0
    style E3 fill:#ffe0e0
    style E4 fill:#ffe0e0
    style F1 fill:#fff9c4
    style F2 fill:#fff9c4
    style F3 fill:#fff9c4
    style G1 fill:#e0f2f1
    style G2 fill:#e0f2f1
    style G3 fill:#e0f2f1
    style G4 fill:#e0f2f1
```

---

## 2. Detailed Data Flow

```mermaid
sequenceDiagram
    participant TL as Task Loader
    participant ORC as Orchestrator
    participant BR as Browser Recorder
    participant SC as State Capture
    participant FL as Failure Labeler
    participant RE as Recovery Engine
    participant ST as Storage
    participant MON as Monitor

    TL->>ORC: Load Task Queue
    ORC->>BR: Assign Task
    BR->>BR: Initialize Browser
    BR->>BR: Navigate to URL

    loop For Each Action
        BR->>SC: Capture Before State
        SC->>ST: Save Screenshot Before
        BR->>BR: Execute Action
        BR->>SC: Capture After State
        SC->>ST: Save Screenshot After
        SC->>SC: Compute Metrics
        SC->>FL: Send State + Metrics
        FL->>FL: Detect Failure?

        alt Failure Detected
            FL->>RE: Trigger Recovery
            RE->>RE: Select Strategy
            RE->>BR: Execute Recovery
            BR->>SC: Capture Recovery State
            RE->>ST: Log Recovery Attempt
        end

        SC->>ST: Write Step Record
        BR->>MON: Log Progress
    end

    BR->>ORC: Task Complete
    ORC->>MON: Update Statistics
    MON->>MON: Check Alerts
```

---

## 3. Component Dependencies

```mermaid
graph LR
    subgraph "External Dependencies"
        EXT1[Playwright]
        EXT2[PIL/Pillow]
        EXT3[OpenCV]
        EXT4[NumPy]
    end

    subgraph "Core Components"
        TASK[Task Loader]
        BROWSER[Browser Recorder]
        STATE[State Capture]
        METRIC[Metric Computer]
        FAILURE[Failure Labeler]
        RECOVERY[Recovery Engine]
        STORAGE[Storage Manager]
        MONITOR[Monitor]
    end

    EXT1 --> BROWSER
    EXT2 --> STATE
    EXT3 --> METRIC
    EXT4 --> METRIC

    TASK --> BROWSER
    BROWSER --> STATE
    STATE --> METRIC
    METRIC --> FAILURE
    FAILURE --> RECOVERY
    RECOVERY --> BROWSER

    BROWSER --> STORAGE
    STATE --> STORAGE
    FAILURE --> STORAGE
    RECOVERY --> STORAGE

    BROWSER --> MONITOR
    FAILURE --> MONITOR
    RECOVERY --> MONITOR
    STORAGE --> MONITOR

    style TASK fill:#e1f5ff
    style BROWSER fill:#f3e5f5
    style STATE fill:#e8f5e9
    style METRIC fill:#e8f5e9
    style FAILURE fill:#ffe0e0
    style RECOVERY fill:#ffe0e0
    style STORAGE fill:#fff9c4
    style MONITOR fill:#e0f2f1
```

---

## 4. Storage Architecture

```mermaid
graph TB
    subgraph "Dataset Root"
        ROOT[dataset/]
    end

    subgraph "Images"
        IMG[images/]
        TASK1[task_001/]
        TASK2[task_002/]
        BEFORE[before_0001.png]
        AFTER[after_0001.png]
    end

    subgraph "Records"
        REC[records/]
        JSON1[task_001.jsonl]
        JSON2[task_002.jsonl]
    end

    subgraph "Splits"
        SPLIT[splits/]
        TRAIN[train.jsonl]
        VAL[val.jsonl]
        TEST[test.jsonl]
        META[metadata.json]
    end

    subgraph "Monitoring"
        MON[monitoring/]
        LOGS[logs/]
        STATS[stats/]
        MANIFEST[run_manifest.json]
    end

    subgraph "Documentation"
        DOCS[docs/]
        README[README.md]
        SCHEMA[SCHEMA.md]
    end

    ROOT --> IMG
    ROOT --> REC
    ROOT --> SPLIT
    ROOT --> MON
    ROOT --> DOCS

    IMG --> TASK1 & TASK2
    TASK1 --> BEFORE & AFTER

    REC --> JSON1 & JSON2

    SPLIT --> TRAIN & VAL & TEST & META

    MON --> LOGS & STATS & MANIFEST

    DOCS --> README & SCHEMA

    style ROOT fill:#fff9c4
    style IMG fill:#e3f2fd
    style REC fill:#e3f2fd
    style SPLIT fill:#f3e5f5
    style MON fill:#e0f2f1
    style DOCS fill:#fff4e6
```

---

## 5. Failure Detection & Recovery Pipeline

```mermaid
graph LR
    START[Action Executed] --> CAPTURE[Capture After State]
    CAPTURE --> COMPUTE[Compute Metrics]

    COMPUTE --> DECIDE{Check Metrics}

    DECIDE -->|visual_diff < 0.05| NOCHANGE[STATE_NO_CHANGE]
    DECIDE -->|loop detected| LOOP[LOOP_DETECTED]
    DECIDE -->|exception| TOOL[TOOL_FAILURE]
    DECIDE -->|timeout| TIMEOUT[TIMEOUT]
    DECIDE -->|normal| SUCCESS[SUCCESS]

    NOCHANGE --> CLASSIFY[Classify Failure Type]
    LOOP --> CLASSIFY
    TOOL --> CLASSIFY
    TIMEOUT --> CLASSIFY

    CLASSIFY --> SELECT[Select Recovery Strategy]

    SELECT --> RETRY{Strategy?}
    RETRY -->|RETRY| EXEC1[Retry Same Action]
    RETRY -->|BACKTRACK| EXEC2[Revert to Previous State]
    RETRY -->|ALTERNATIVE| EXEC3[Try Different Element]
    RETRY -->|REPLAN| EXEC4[Generate New Plan]
    RETRY -->|ABORT| EXEC5[Terminate Task]

    EXEC1 & EXEC2 & EXEC3 & EXEC4 --> EVAL[Evaluate Recovery]
    EXEC5 --> END[End]

    EVAL --> CHECK{Success?}
    CHECK -->|Yes| RECORD1[Record Success]
    CHECK -->|No| RECORD2[Record Failure]

    SUCCESS --> CONTINUE[Continue to Next Action]
    RECORD1 --> CONTINUE
    RECORD2 --> CONTINUE

    style START fill:#e1f5ff
    style SUCCESS fill:#c8e6c9
    style NOCHANGE fill:#ffccbc
    style LOOP fill:#ffccbc
    style TOOL fill:#ffccbc
    style TIMEOUT fill:#ffccbc
    style EXEC1 fill:#fff9c4
    style EXEC2 fill:#fff9c4
    style EXEC3 fill:#fff9c4
    style EXEC4 fill:#fff9c4
    style EXEC5 fill:#ffccbc
    style RECORD1 fill:#c8e6c9
    style RECORD2 fill:#ffcdd2
```

---

## 6. Monitoring & Observability Flow

```mermaid
graph TB
    subgraph "Data Sources"
        DS1[Browser Events]
        DS2[Action Logs]
        DS3[Failure Events]
        DS4[System Metrics]
    end

    subgraph "Collection"
        COL1[Event Logger]
        COL2[Metrics Collector]
    end

    subgraph "Processing"
        PROC1[Aggregator]
        PROC2[Statistics Engine]
    end

    subgraph "Storage"
        STORE1[Log Files]
        STORE2[Time Series DB]
    end

    subgraph "Visualization"
        VIZ1[Dashboard]
        VIZ2[Reports]
        VIZ3[Alerts]
    end

    DS1 & DS2 --> COL1
    DS3 & DS4 --> COL2

    COL1 --> PROC1
    COL2 --> PROC2

    PROC1 --> STORE1
    PROC2 --> STORE2

    STORE1 & STORE2 --> VIZ1
    STORE1 & STORE2 --> VIZ2
    PROC2 --> VIZ3

    style DS1 fill:#e1f5ff
    style DS2 fill:#e1f5ff
    style DS3 fill:#e1f5ff
    style DS4 fill:#e1f5ff
    style COL1 fill:#fff4e6
    style COL2 fill:#fff4e6
    style PROC1 fill:#e8f5e9
    style PROC2 fill:#e8f5e9
    style STORE1 fill:#fff9c4
    style STORE2 fill:#fff9c4
    style VIZ1 fill:#e0f2f1
    style VIZ2 fill:#e0f2f1
    style VIZ3 fill:#ffccbc
```

---

## 7. Parallel Worker Architecture

```mermaid
graph TB
    SCHEDULER[Task Scheduler] --> QUEUE[Task Queue]

    QUEUE --> W1[Worker 1<br/>Browser Instance]
    QUEUE --> W2[Worker 2<br/>Browser Instance]
    QUEUE --> W3[Worker 3<br/>Browser Instance]
    QUEUE --> WN[Worker N<br/>Browser Instance]

    W1 --> TASK1[Processing Task_042]
    W2 --> TASK2[Processing Task_087]
    W3 --> TASK3[Processing Task_123]
    WN --> TASKN[Processing Task_N]

    TASK1 & TASK2 & TASK3 & TASKN --> STORAGE[Shared Storage]

    W1 & W2 & W3 & WN --> MONITOR[Central Monitor]

    MONITOR --> DASHBOARD[Live Dashboard]

    style SCHEDULER fill:#fff4e6
    style QUEUE fill:#e1f5ff
    style W1 fill:#f3e5f5
    style W2 fill:#f3e5f5
    style W3 fill:#f3e5f5
    style WN fill:#f3e5f5
    style STORAGE fill:#fff9c4
    style MONITOR fill:#e0f2f1
    style DASHBOARD fill:#c8e6c9
```

---

## 8. Technology Stack

```mermaid
mindmap
  root((Data Collection<br/>System))
    Browser Automation
      Playwright
      Chromium
      Headless Mode
    Image Processing
      PIL/Pillow
      OpenCV
      imagehash
    Data Processing
      Python 3.8+
      NumPy
      Pandas
    Storage
      JSONL Files
      PNG Images
      Local Filesystem
    Monitoring
      structlog
      psutil
      Flask/Streamlit
    Testing
      pytest
      unittest
      integration tests
    Version Control
      Git
      GitHub
      Docker optional
```

---

## Notes

- **Modularity**: Each layer is independently testable
- **Scalability**: Parallel workers can be added easily
- **Observability**: Comprehensive logging and monitoring
- **Reproducibility**: Git commit tracking and environment snapshots
- **Extensibility**: Easy to add new task sources or recovery strategies

---

**Architecture Version:** 1.0  
**Compatible with:** Project Plan v1.0  
**Last Review:** February 19, 2026
