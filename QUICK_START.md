# Quick Start Guide - Dataset Generation

## ✅ What's Done

1. **LOOP Injector Fixed** - `state_after` loading implemented
2. **Quality Gate Script** - Validates dataset quality before scaling
3. **Test Scripts Updated** - Full step details saved for validation

## 🚀 Next Steps

### Step 3: Test with 200 Tasks (VERIFY LOOP WORKS)

**Before scaling to 1,000 tasks, we need to verify LOOP is working correctly on a larger sample.**

Run:
```bash
run_step3_test_200_tasks.bat
```

This will:
- Generate 200 tasks (~1,400 steps)
- Run quality gate validation
- Open HTML report in browser

**Quality Gate Checks:**
- ✅ Failure rate: 40-60%
- ✅ LOOP failures: ≥5%
- ✅ Recovery strategies: >0%
- ✅ No missing data
- ✅ All 5 failure types present

**If any gate FAILS, DO NOT proceed to next step!**

---

### Step 4: Regenerate 100-Task Pilot

**Only after Step 3 passes!**

Run:
```bash
run_step4_regenerate_pilot.bat
```

This regenerates the pilot with LOOP fixes and validates it.

---

### Step 5: Generate Full 1,000-Task Dataset

**Only after Step 4 passes!**

Run:
```bash
run_step5_generate_1000_tasks.bat
```

This will:
- Generate ~7,000 steps
- Take 10-15 minutes
- Require ~10GB disk space
- Use ~4-5GB RAM

---

## 🎯 Or Use Master Script

Run:
```bash
run_pipeline.bat
```

This provides an interactive menu to run all steps sequentially.

---

## 📊 Expected Results

### 200-Task Test (Step 3)
- Trajectories: ~200
- Steps: ~1,400
- Failures: ~840 (60%)
- LOOP: ~42-84 (5-10%)

### 100-Task Pilot (Step 4)
- Trajectories: ~86-100
- Steps: ~550-700
- Failures: ~330-420 (60%)
- LOOP: ~17-42 (5-10%)

### 1,000-Task Full (Step 5)
- Trajectories: ~860-1,000
- Steps: ~6,000-7,000
- Failures: ~3,600-4,200 (60%)
- LOOP: ~180-420 (5-10%)

---

## ⚠️ Troubleshooting

### LOOP percentage too low (<5%)
- Check: `state_after` screenshots loading correctly
- Check: SSIM computation working
- Solution: Regenerate with `--load-screenshots` flag

### Failure rate outside 40-60%
- Check: Injection config weights balanced
- Solution: Adjust `InjectionConfig` in test script

### Recovery strategies missing
- Check: All injectors implement recovery logic
- Check: Serialization saving recovery fields

### Memory issues
- Symptoms: Script crashes, system slow
- Solution: Close other programs, run smaller batches

---

## 📁 Output Structure

```
output/
├── test_200_tasks/
│   ├── summary.json                    # Statistics
│   ├── augmented_trajectories.json     # Full dataset
│   └── quality_report.html             # Validation results
├── pilot_100_with_loop/
│   ├── summary.json
│   ├── augmented_trajectories.json
│   └── quality_report.html
└── dataset_1000_full/
    ├── summary.json
    ├── augmented_trajectories.json
    └── quality_report.html
```

---

## 🔍 Validation Commands

Check LOOP percentage manually:
```bash
python -c "import json; s=json.load(open('output/test_200_tasks/summary.json')); d=s['failure_distribution']; loop_pct=(d.get('LOOP',0)/s['augmented_steps']*100); print(f'LOOP: {d.get(\"LOOP\",0)} ({loop_pct:.1f}%)')"
```

View full statistics:
```bash
python -c "import json; s=json.load(open('output/test_200_tasks/summary.json')); print(json.dumps(s, indent=2))"
```

---

## 📋 Quality Gate Thresholds

| Gate | Threshold | Why |
|------|-----------|-----|
| Failure Rate | 40-60% | Balanced dataset |
| LOOP Presence | ≥5% | All failure types represented |
| Recovery Strategies | >0% | Every failure needs recovery |
| Missing Data | 0 | Complete dataset |
| All Failure Types | 5/5 | Comprehensive coverage |

---

## ✅ When to Proceed

**From Step 3 → Step 4:**
- All quality gates PASS ✅
- LOOP ≥5% confirmed ✅
- HTML report shows green checkmarks ✅

**From Step 4 → Step 5:**
- Pilot quality gates PASS ✅
- Distribution matches Step 3 (±10%) ✅
- Ready to commit to full generation ✅

---

## 🎯 After Step 5 Complete

Next phases (see TODO_COMPLETE.md):
1. **Comprehensive QA** - Automated + manual validation
2. **Baseline Models** - Rule-based + vision classifier (CRITICAL for Q1)
3. **Documentation** - Dataset card, README, examples
4. **Q1 Paper** - Full manuscript with baseline results

---

**Start now:**
```bash
run_step3_test_200_tasks.bat
```

Check the quality report after completion to verify LOOP is working!
