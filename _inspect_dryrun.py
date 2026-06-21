import json

with open('dataset/dryrun/collected/mind2web.jsonl', encoding='utf-8') as f:
    lines = [l.strip() for l in f if l.strip()]

print(f'Trajectories in file: {len(lines)}')
print()

for i, line in enumerate(lines):
    t = json.loads(line)
    steps = t.get('steps', [])
    tid = t['task_id']
    print(f'--- Trajectory {i+1}: {tid} ---')
    print(f'  task_description : {t["task_description"][:70]}')
    print(f'  start_url        : {t["start_url"]}')
    print(f'  source           : {t.get("source","?")}')
    print(f'  status           : {t.get("status","?")}')
    print(f'  steps            : {len(steps)}')
    print(f'  annotated_at     : {t.get("annotated_at","(missing)")}')
    if steps:
        s = steps[0]
        print(f'  step[0] keys     : {list(s.keys())}')
        has_metrics  = bool(s.get("metrics"))
        has_failure  = bool(s.get("failure"))
        has_recovery = bool(s.get("recovery"))
        has_reflect  = "reflection" in s
        print(f'  annotations      : metrics={has_metrics}  failure={has_failure}  recovery={has_recovery}  reflection={has_reflect}')
        sb = s.get('screenshot_before','')
        sa = s.get('screenshot_after','')
        print(f'  screenshots      : before={bool(sb)}  after={bool(sa)}')
        # Show failure label
        ftype = s.get("failure", {}).get("failure_type", "?")
        print(f'  failure_type[0]  : {ftype}')
        # Show metrics
        vis = s.get("metrics", {}).get("visual", {})
        if vis:
            print(f'  pixel_diff_score : {vis.get("pixel_diff_score","?")}')
    print()
