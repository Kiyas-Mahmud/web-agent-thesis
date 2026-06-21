# Dataset Backup & Storage Guide

**Purpose:** This guide explains which files/folders to move for data-only storage.

---

## 📦 Essential Files (MUST MOVE for Dataset Storage)

### ⭐ **Primary Dataset (1.01 GB)**
```
output/dataset_70k_safe/
├── augmented_trajectories.json    [6.8 MB]  ← Main dataset file
├── summary.json                   [1.2 KB]  ← Metadata & statistics
├── images/                        [1.01 GB] ← All screenshots (43,623 files)
│   ├── task_0000/
│   │   ├── step_0000_before.jpg
│   │   ├── step_0000_after.jpg
│   │   └── ...
│   ├── task_0001/
│   └── ... (3,027 task folders)
└── progress/                      [0.4 MB]  ← Checkpoint files (optional)
```

**Action:** Copy the entire `output/dataset_70k_safe/` folder.

---

## 🔄 Optional Files (for Raw Data / Reproducibility)

### Source Data Records (0.30 MB)
```
dataset/records/
├── mind2web-00000.jsonl
├── mind2web-00001.jsonl
└── ... (40 JSONL files)
```
**Purpose:** Intermediate batch files from original Mind2Web data.  
**Action:** Copy if you need the raw source data.

### Cached Mind2Web Data (Size varies)
```
dataset/mind2web_offline/
└── [Cached HuggingFace dataset files]
```
**Purpose:** Offline copy of Mind2Web dataset from HuggingFace.  
**Action:** Copy only if you don't have internet access and need to regenerate data.

### Dataset Images (Source)
```
dataset/images/
├── mind2web-00000/
├── mind2web-00001/
└── ... (40 folders)
```
**Purpose:** Original source images before processing.  
**Action:** Copy if you need unprocessed source images.

---

## ❌ Files to EXCLUDE (Not Data)

### Code Files (Don't move)
- `src/` - Source code
- `tests/` - Test files
- `scripts/` - Utility scripts
- `old_scripts/` - Deprecated code
- `*.py` files (60+ Python scripts)
- `*.bat` files (batch scripts)

### Configuration Files (Don't move)
- `config/` - Configuration files
- `requirements.txt` - Dependencies
- `pytest.ini` - Test config
- `.env` files

### Documentation Files (Optional)
- `*.md` files (README, TODO, reports)
- `docs/` - Documentation folder

### Log Files (Usually not needed)
- `logs/` - Execution logs
- `dataset_generation*.log` files

### Cache & Temp Files (Don't move)
- `.cache/` - Temporary cache
- `__pycache__/` - Python cache
- `.venv/`, `.venv-1/`, `.venv-2/` - Virtual environments

---

## 📋 Storage Scenarios

### Scenario 1: **Final Dataset Only** (Recommended for ML Training)
**Size:** ~1.01 GB  
**Files to move:**
```
output/dataset_70k_safe/
```
**Use case:** Training ML models, sharing dataset with others.

---

### Scenario 2: **Dataset + Source Data** (For Reproducibility)
**Size:** ~1.01 GB + varies  
**Files to move:**
```
output/dataset_70k_safe/
dataset/records/
dataset/mind2web_offline/
```
**Use case:** Full backup, ability to regenerate dataset.

---

### Scenario 3: **Complete Archive** (Everything)
**Size:** ~1.5-2 GB (depends on cache)  
**Files to move:**
```
output/
dataset/
```
**Use case:** Complete project backup including all intermediate data.

---

## 🚀 Quick Commands

### Copy Essential Data Only (Recommended)
```powershell
# Create backup folder
New-Item -ItemType Directory -Path "E:\Backup\WebAgent_Dataset" -Force

# Copy main dataset
Copy-Item -Path "E:\University\thesis\datacollection\output\dataset_70k_safe" `
          -Destination "E:\Backup\WebAgent_Dataset\" `
          -Recurse -Force

# Verify
Get-ChildItem "E:\Backup\WebAgent_Dataset\dataset_70k_safe" -Recurse | 
  Measure-Object -Property Length -Sum
```

### Copy Dataset + Summary Report
```powershell
# Copy dataset
Copy-Item -Path "E:\University\thesis\datacollection\output\dataset_70k_safe" `
          -Destination "E:\Backup\WebAgent_Dataset\" `
          -Recurse -Force

# Copy project report
Copy-Item -Path "E:\University\thesis\datacollection\PROJECT_ARCHITECTURE_REPORT.md" `
          -Destination "E:\Backup\WebAgent_Dataset\"

# Copy README
Copy-Item -Path "E:\University\thesis\datacollection\README.md" `
          -Destination "E:\Backup\WebAgent_Dataset\"
```

### Create Compressed Archive
```powershell
# Compress dataset to ZIP (takes time!)
Compress-Archive -Path "E:\University\thesis\datacollection\output\dataset_70k_safe" `
                 -DestinationPath "E:\Backup\dataset_70k_safe.zip" `
                 -CompressionLevel Optimal

# Check compressed size
Get-Item "E:\Backup\dataset_70k_safe.zip" | 
  Select-Object Name, @{Name="SizeMB";Expression={[math]::Round($_.Length/1MB,2)}}
```

---

## 📊 Storage Size Summary

| Category | Size | Files | Required? |
|----------|------|-------|-----------|
| **Main Dataset** | 1.01 GB | 43,625 | ✅ YES |
| Source Records | 0.30 MB | 40 | ⚠️ Optional |
| Cached Data | Varies | Many | ⚠️ Optional |
| Code/Config | ~5 MB | 100+ | ❌ NO |
| Logs | ~10 MB | 10+ | ❌ NO |

---

## ✅ Recommended Storage Strategy

**For ML Training / Sharing:**
1. ✅ Move `output/dataset_70k_safe/` → This is your complete dataset
2. ✅ Include `PROJECT_ARCHITECTURE_REPORT.md` for documentation
3. ✅ Include `README.md` for overview
4. ❌ Exclude everything else (code, logs, cache)

**Total Size:** ~1.01 GB (easily portable)

---

## 🔍 Verification Checklist

After copying, verify you have:
- [ ] `augmented_trajectories.json` (6.8 MB, 23,325 steps)
- [ ] `summary.json` (metadata)
- [ ] `images/` folder (43,623 .jpg files)
- [ ] All images load correctly
- [ ] JSON files are valid (can be parsed)

**Verification command:**
```powershell
# Check JSON is valid
Get-Content "E:\Backup\WebAgent_Dataset\dataset_70k_safe\augmented_trajectories.json" | 
  ConvertFrom-Json | Measure-Object

# Count images
Get-ChildItem "E:\Backup\WebAgent_Dataset\dataset_70k_safe\images" -Recurse -Filter "*.jpg" | 
  Measure-Object
```

---

## 📝 Notes

1. **JSON Format:** The `augmented_trajectories.json` is a single JSON file containing all 23,325 steps with metadata.

2. **Images:** Each step has 2 images (before/after), organized by task folders.

3. **Self-Contained:** The dataset is fully self-contained. You don't need any code to use it - just load the JSON and reference the images.

4. **Portability:** The dataset can be moved to any location. Just update image paths if needed (they're relative to the JSON file).

5. **Backup Recommendation:** Keep at least 2 copies (original + backup) before deleting any source data.

---

**Generated:** March 31, 2026  
**Dataset Version:** 1.0  
**Total Size:** 1.01 GB (23,325 steps, 43,623 images)
