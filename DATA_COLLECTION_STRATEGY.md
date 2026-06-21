# Efficient Data Collection Strategy Analysis

**Date:** March 11, 2026  
**Current Status:** 7,775 steps collected, script crashed at ~108 trajectories during 70k generation  
**Target:** 70,000+ steps without crashes

---

## Problem Analysis

### Why the Script Crashed

**Root Cause:** Memory allocation failure in `add_noise()` function
```
numpy._core._exceptions._ArrayMemoryError: Unable to allocate 244 MiB 
for array with shape (8343, 1280, 3) and data type float64
```

**Failure Point:** NO_STATE_CHANGE injector → image_preprocessor.py line 214
- Trying to allocate 244 MiB for a **single image operation**
- Image shape: (8343, 1280, 3) = ~10,800 pixels height (abnormally tall)
- Data type: float64 (8 bytes per value) = 8343 × 1280 × 3 × 8 bytes = 256 MB

### Current Resource Usage (7k Dataset)

| Metric | Value |
|--------|-------|
| **Total steps** | 7,775 |
| **Total images** | 14,226 files |
| **Disk usage** | 1.26 GB |
| **Avg image size** | 93.1 KB (JPEG) |
| **Image format** | 512px width, 70% quality |
| **Memory per batch** | ~3-4 GB (30 trajectories) |

---

## Efficient Collection Strategies

### Option 1: **Smaller Image Resolution** ⭐ RECOMMENDED

**Current:** 512px width → 93 KB/image  
**Proposed:** 256px or 384px width

| Width | Est. Size | Disk for 70k | Memory Impact |
|-------|-----------|--------------|---------------|
| 512px | 93 KB | 13 GB | High (current) |
| 384px | 52 KB (-44%) | 7.3 GB | Medium |
| 256px | 23 KB (-75%) | 3.2 GB | Low ✅ |

**Pros:**
- ✅ 44-75% memory reduction
- ✅ Faster processing (less pixel data)
- ✅ Still sufficient for visual tasks (256px is standard for many vision models)
- ✅ No code changes needed (just config parameter)

**Cons:**
- ⚠️ Loss of fine visual details
- ⚠️ May affect bounding box precision

**Implementation:**
```python
IMAGE_WIDTH = 256  # Change from 512
IMAGE_QUALITY = 60  # Reduce from 70
```

---

### Option 2: **Skip Memory-Intensive Injectors** ⭐ ALREADY IMPLEMENTED

**Problem Injector:** NO_STATE_CHANGE (uses `add_noise()` → 244 MB allocation)

**Current Solution (generate_70k_light.py):**
- ✅ Skip NO_STATE_CHANGE injector
- ✅ Use only: TARGET_MISSING, MISCLICK, WRONG_OPERATION, LOOP
- ✅ Increase injection rates (70-80%) to compensate

**Pros:**
- ✅ Avoids memory errors
- ✅ Still covers 4 out of 5 failure types (80% coverage)
- ✅ Higher injection rates maintain failure distribution

**Cons:**
- ❌ Missing 1 failure type (NO_STATE_CHANGE was 16.3% of original dataset)

**Recommendation:** Acceptable trade-off for memory safety

---

### Option 3: **Smaller Batch Sizes** ⚠️ PARTIAL SOLUTION

**Current attempts:**
- 30 trajectories → crashed
- 10 trajectories → crashed
- 5 trajectories → partial success (108 trajs before crash)

**Analysis:**
- Batch size helps but doesn't solve root cause
- Memory leak or cumulative allocation still occurs
- Single problematic image (8343px tall) can crash even batch size = 1

**Pros:**
- ✅ Reduces peak memory usage
- ✅ Better garbage collection opportunities

**Cons:**
- ❌ Doesn't prevent crashes from single large images
- ❌ Slower processing (more batches = more overhead)
- ❌ Still hit memory limits eventually

**Recommendation:** Keep batch size = 5-10 as safety measure, but not primary solution

---

### Option 4: **Process Only One Split at a Time** ✅ VIABLE

**Strategy:**
Instead of 5 passes × 4 splits = 20 iterations, do:
- Generate all data from ONE split at a time
- Save intermediate results
- Move to next split

**Workflow:**
```
Pass 1: train split → save → cleanup
Pass 2: test_domain → save → cleanup  
Pass 3: test_task → save → cleanup
Pass 4: test_website → save → cleanup
Merge all → 70k dataset
```

**Pros:**
- ✅ Smaller memory footprint per run
- ✅ Can restart from checkpoint if crash
- ✅ Easier to debug which split has problems
- ✅ Progressive disk saving reduces data loss

**Cons:**
- ⚠️ More manual steps (4 separate runs)
- ⚠️ Need merging script at the end

---

### Option 5: **Use Existing 7k + Add More Passes** ⭐ PRAGMATIC

**Calculation:**
- Current: 7,775 steps (1,009 trajectories from train split)
- Available: 1,013 more trajectories (test splits: 378+337+298)  
  = ~7,900 additional clean steps

**Strategy:**
1. Keep existing 7,775 steps ✅
2. Add test splits (7,900 steps) ≈ 15,675 clean total
3. Apply **multiple passes** with different injection rates

| Passes | Clean Steps | Augmented (70% rate) | Total |
|--------|-------------|----------------------|-------|
| 3 passes | 15,675 × 3 = 47,025 | 32,918 | 79,943 ✅ |
| 4 passes | 15,675 × 4 = 62,700 | 43,890 | 106,590 ✅ |

**Pros:**
- ✅ Don't lose existing validated 7k dataset
- ✅ Incremental approach (add test data separately)
- ✅ Can reach 80-100k with 3-4 passes
- ✅ Less risky (build on solid foundation)

**Cons:**
- ⚠️ Still need to process test splits without crashes

---

### Option 6: **Lower Injection Rates, More Passes** 💡 SMART

**Problem:** High injection rates (70-80%) + all splits at once = memory overload

**Alternative:**
- Use moderate injection rate (50-60%)
- More passes (5-6) to reach 70k
- Smaller batch size (3-5 trajectories)

**Example:**
- Clean steps from all splits: 14,193
- 5 passes with 55% injection: 14,193 × 5 × 1.55 = ~110k steps ✅

**Pros:**
- ✅ Lower memory per pass
- ✅ More data variation (different random seeds)
- ✅ Better failure type distribution

**Cons:**
- ⚠️ Longer processing time (more passes)
- ⚠️ Still need other optimizations (image size, skip NO_STATE_CHANGE)

---

### Option 7: **Fix add_noise() Function** 🔧 ROOT CAUSE FIX

**Problem:** `add_noise()` creates float64 array for entire image
```python
noise = np.random.randn(*img_array.shape) * epsilon * 255  # 244 MB for 1 image!
```

**Solution:** Pre-downsample images before noise operation
```python
def add_noise(image: Image.Image, epsilon: float = 0.001) -> Image.Image:
    # Downsample to max 512px before processing
    if max(image.size) > 512:
        ratio = 512 / max(image.size)
        new_size = (int(image.width * ratio), int(image.height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    img_array = np.array(image).astype(np.float32)  # float32, not float64
    noise = np.random.randn(*img_array.shape).astype(np.float32) * epsilon * 255
    noisy = np.clip(img_array + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(noisy)
```

**Benefits:**
- ✅ Fixes root cause directly
- ✅ Can re-enable NO_STATE_CHANGE injector
- ✅ Handles abnormally large images (8343px tall)
- ✅ Uses float32 instead of float64 (50% memory reduction)

---

## Recommended Combined Approach

### **Strategy: Multi-Layer Optimization**

1. **Fix add_noise() function** (root cause)
   - Pre-downsample to 512px max
   - Use float32 instead of float64
   - Implementation: 30 minutes

2. **Reduce image resolution**
   - Change `IMAGE_WIDTH = 256` or `384`
   - Change `IMAGE_QUALITY = 60`
   - 44-75% memory reduction

3. **Process splits separately**
   - Train split → 7,775 steps (already done ✅)
   - Test_domain → ~3k steps
   - Test_task → ~3k steps  
   - Test_website → ~2k steps
   - Apply 3 augmentation passes to each

4. **Use lightweight injectors**
   - TARGET_MISSING, MISCLICK, WRONG_OPERATION, LOOP
   - Skip NO_STATE_CHANGE (even if fixed, it's memory-heavy)

5. **Small batches with cleanup**
   - Batch size = 5 trajectories
   - Aggressive gc.collect() every trajectory
   - Save progress every batch

### **Expected Results:**

| Component | Steps | Passes | With 70% Aug | Total |
|-----------|-------|--------|--------------|-------|
| Train (existing) | 7,775 | 1 | 12,440 | 12,440 ✅ |
| Test splits | 6,418 | 3 | 10,910 × 3 | 32,730 |
| **TOTAL** | - | - | - | **45,170** |

**To reach 70k:** Need 4 passes on test splits or add more test data.

---

## Implementation Priority

### **Phase 1: Quick Wins (1-2 hours)**
1. ✅ Reduce image size to 256px
2. ✅ Fix add_noise() function  
3. ✅ Use batch size = 5
4. ⚠️ Test with 100 trajectories first

### **Phase 2: Incremental Collection (per split)**
1. Process train split (reuse existing 7,775 or regenerate)
2. Process test_domain split separately
3. Process test_task split separately
4. Process test_website split separately
5. Merge all splits

### **Phase 3: Scale Up**
1. Apply multiple augmentation passes
2. Monitor memory usage
3. Generate 70k+ dataset progressively

---

## Conclusion

**Best Approach:** Combine Options 1, 2, 4, and 7

✅ **Fix add_noise()** - eliminates root cause  
✅ **Reduce image size to 256px** - 75% memory reduction  
✅ **Process one split at a time** - safe checkpointing  
✅ **Skip NO_STATE_CHANGE** - avoid memory-intensive operations  
✅ **Small batches (5-10)** - safety net  

**Expected:** Successfully generate 70k+ steps in 4 separate runs (~6-8 hours total)

**Risk:** Low - multiple layers of protection against memory errors
