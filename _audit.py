"""Full audit of the collected data and codebase state."""
import json, sys
from pathlib import Path

sys.path.insert(0, "src")

p = Path("dataset/dryrun/collected/mind2web.jsonl")
if not p.exists():
    print("ERROR: no file at", p)
    sys.exit(1)

lines = [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
print(f"=== JSONL: {len(lines)} lines (trajectories) ===\n")

for i, raw in enumerate(lines):
    t = json.loads(raw)
    steps = t.get("steps", [])
    print(f"Trajectory {i}: task_id={t.get('task_id')}  steps={len(steps)}  status={t.get('status')}")
    print(f"  top-level keys: {list(t.keys())}")
    if steps:
        s0 = steps[0]
        print(f"  step[0] keys:   {list(s0.keys())}")
        fail = s0.get("failure", {})
        print(f"  failure_type value (raw): {repr(fail.get('failure_type'))}")
        print(f"  outcome value   (raw): {repr(fail.get('outcome'))}")
        refl = s0.get("reflection")
        if refl:
            print(f"  reflection keys: {list(refl.keys())}")
            print(f"  reflection_text: {str(refl.get('reflection_text',''))[:80]}")
            print(f"  confidence_before: {refl.get('agent_confidence_before')}")
        else:
            print("  reflection: MISSING")
        metrics = s0.get("metrics", {})
        vis = metrics.get("visual", {})
        print(f"  pixel_diff={vis.get('pixel_diff_score')}  ssim={vis.get('ssim_score')}")
        print(f"  screenshot_before: {str(s0.get('screenshot_before',''))[:50]}")
    print()

# ─── Check recovery field ───────────────────────────────────────────────────
print("=== RECOVERY FIELD SAMPLE ===")
for raw in lines:
    t = json.loads(raw)
    for s in t.get("steps", [])[:3]:
        print(f"  recovery: {s.get('recovery')}")
    break

# ─── Show what spec wants vs what we have ──────────────────────────────────
print()
print("=== SPEC vs ACTUAL GAP ANALYSIS ===")
spec_keys = [
    "task_id", "step_id", "state_before", "state_after",
    "pixel_diff", "ssim",
    "url_before", "url_after",
    "action_type", "action_target_desc", "action_coordinates",
    "execution_outcome", "failure_type", "failure_confidence",
    "recovery_strategy", "recovery_success",
    "agent_confidence_before", "reflection_text",
]

if lines:
    t = json.loads(lines[0])
    steps = t.get("steps", [])
    if steps:
        s = steps[2] if len(steps) > 2 else steps[0]
        # Flatten manually as spec wants
        flat = {
            "task_id": t.get("task_id"),
            "step_id": s.get("step_id"),
            "state_before": s.get("screenshot_before"),
            "state_after": s.get("screenshot_after"),
            "pixel_diff": s.get("metrics", {}).get("visual", {}).get("pixel_diff_score"),
            "ssim": s.get("metrics", {}).get("visual", {}).get("ssim_score"),
            "url_before": s.get("url_before"),
            "url_after": s.get("url_after"),
            "action_type": s.get("action", {}).get("action_type"),
            "action_target_desc": s.get("action", {}).get("target"),
            "action_coordinates": None,  # not in replay output
            "execution_outcome": "SUCCESS" if s.get("result", {}).get("success") else "FAILURE",
            "failure_type": s.get("failure", {}).get("failure_type"),
            "failure_confidence": s.get("failure", {}).get("confidence"),
            "recovery_strategy": s.get("recovery", {}).get("strategy"),
            "recovery_success": s.get("recovery", {}).get("success"),
            "agent_confidence_before": s.get("reflection", {}).get("agent_confidence_before") if s.get("reflection") else None,
            "reflection_text": s.get("reflection", {}).get("reflection_text") if s.get("reflection") else None,
        }

        for k in spec_keys:
            v = flat.get(k)
            status = "OK" if v is not None else "MISSING"
            print(f"  {status:8} {k}: {repr(v)[:70]}")
