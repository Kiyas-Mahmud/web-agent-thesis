"""Deep inspection of dry-run data quality."""
import json, sys
from pathlib import Path

sys.path.insert(0, 'src')

# ── 1. Read the collected JSONL ────────────────────────────────────────────
path = Path('dataset/dryrun/collected/mind2web.jsonl')
if not path.exists():
    print("ERROR: no dry-run data found. Run the dry-run first.")
    sys.exit(1)

trajectories = [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]
print(f"{'='*65}")
print(f"  COLLECTED TRAJECTORIES: {len(trajectories)}")
print(f"{'='*65}\n")

total_steps = 0
ok_steps    = 0

for i, traj in enumerate(trajectories):
    steps   = traj.get('steps', [])
    task_id = traj.get('task_id', '?')
    print(f"TRAJECTORY {i+1}: {task_id}")
    print(f"  Goal   : {traj.get('task_description','')[:72]}")
    print(f"  URL    : {traj.get('start_url','?')} ")
    print(f"  Source : {traj.get('source','?')}  Status: {traj.get('status','?')}")
    print(f"  Steps  : {len(steps)}")

    step_ok  = 0
    step_fail= 0
    step_detail_lines = []

    for s in steps:
        action     = s.get('action', {})
        result     = s.get('result', {})
        atype      = action.get('action_type', '?')
        target     = action.get('target', '')
        success    = result.get('success', False)
        err        = result.get('error', '') or ''
        ftype      = s.get('failure', {}).get('failure_type', '?')
        sb         = bool(s.get('screenshot_before'))
        sa         = bool(s.get('screenshot_after'))
        has_refl   = 'reflection' in s

        if success:
            step_ok += 1
        else:
            step_fail += 1

        short_err = (err[:55] + '…') if len(err) > 55 else err
        icon = '✅' if success else '❌'
        step_detail_lines.append(
            f"    {icon} {atype:<12} target={str(target)[:30]:<30}  "
            f"failure={ftype:<20}  "
            f"screenshots={'OK' if sb and sa else 'MISSING'}  "
            f"reflection={'Y' if has_refl else 'N'}"
            + (f"\n       ERR: {short_err}" if not success and short_err else "")
        )

    for dl in step_detail_lines:
        print(dl)

    total_steps += len(steps)
    ok_steps    += step_ok

    # Screenshot sizes
    img_dir = Path(f'dataset/dryrun/images/{task_id}')
    screenshots = list(img_dir.glob('*.png')) if img_dir.exists() else []
    sizes = [p.stat().st_size for p in screenshots]
    blank = sum(1 for sz in sizes if sz < 10_000)   # < 10KB = likely blank/error page
    real  = sum(1 for sz in sizes if sz >= 10_000)
    avg_kb = (sum(sizes) / len(sizes) / 1024) if sizes else 0

    print(f"\n  Screenshots: {len(sizes)} total  |  real_content={real}  blank/failed={blank}  avg={avg_kb:.0f} KB")

    # Show first step's metric detail
    if steps:
        vis = steps[0].get('metrics', {}).get('visual', {})
        print(f"  Visual metrics[step0]: pixel_diff={vis.get('pixel_diff_score','?')}  "
              f"ssim={vis.get('ssim_score','?')}  change_level={vis.get('change_level','?')}")

    print()

# ── 2. Overall summary ────────────────────────────────────────────────────
print(f"{'='*65}")
print(f"  OVERALL QUALITY CHECK")
print(f"{'='*65}")
print(f"  Total steps         : {total_steps}")
print(f"  Successful steps    : {ok_steps}  ({ok_steps/max(1,total_steps):.0%})")
print(f"  Failed steps        : {total_steps - ok_steps}  ({(total_steps-ok_steps)/max(1,total_steps):.0%})")

all_steps = [s for t in trajectories for s in t.get('steps', [])]
have_screenshots = sum(1 for s in all_steps if s.get('screenshot_before') or s.get('screenshot_after'))
have_metrics     = sum(1 for s in all_steps if s.get('metrics'))
have_failure_lbl = sum(1 for s in all_steps if s.get('failure', {}).get('failure_type'))
have_reflection  = sum(1 for s in all_steps if s.get('reflection'))

print(f"  With screenshots    : {have_screenshots}/{len(all_steps)}")
print(f"  With metrics        : {have_metrics}/{len(all_steps)}")
print(f"  With failure labels : {have_failure_lbl}/{len(all_steps)}")
print(f"  With reflection     : {have_reflection}/{len(all_steps)}")

# ── 3. Why failure rate = 100% in monitoring ─────────────────────────────
print(f"\n  NOTE: monitoring showed 100% failure rate.")
print(f"  This is because replay_status='partial' (some steps timed out)")
print(f"  counts as failure in MetricsTracker.failure_rate.")
print(f"  'partial' = page loaded + some actions succeeded + some failed.")
print(f"  For the thesis this is EXPECTED and DESIRED —")
print(f"  we are specifically collecting failure trajectories!\n")

# ── 4. Root cause breakdown ───────────────────────────────────────────────
error_types = {}
for s in all_steps:
    err = s.get('result', {}).get('error', '') or ''
    if 'Timeout' in err:
        error_types['Timeout (selector not found)'] = error_types.get('Timeout (selector not found)', 0) + 1
    elif 'Navigation' in err or 'ERR_' in err:
        error_types['Navigation error'] = error_types.get('Navigation error', 0) + 1
    elif not err and not s.get('result', {}).get('success', True):
        error_types['Unknown failure'] = error_types.get('Unknown failure', 0) + 1
    elif not err:
        error_types['Success'] = error_types.get('Success', 0) + 1

print("  Step error breakdown:")
for k, v in sorted(error_types.items(), key=lambda x: -x[1]):
    print(f"    {k}: {v} steps")
print()
