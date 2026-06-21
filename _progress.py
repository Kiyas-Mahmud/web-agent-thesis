"""Quick progress check"""
import json
from pathlib import Path

# Read collected data
p = Path('dataset/collected/mind2web_training.jsonl')
if not p.exists():
    print('⏳ Collection not started yet')
    exit()

steps = [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
tasks_completed = len(set(s['task_id'] for s in steps))
total_tasks = 10

print()
print('=' * 60)
print('          📊 COLLECTION PROGRESS')
print('=' * 60)
print()
print(f'  ✅ Tasks Completed:     {tasks_completed} / {total_tasks}')
print(f'  ⏳ Tasks Remaining:     {total_tasks - tasks_completed}')
print()

# Progress bar
bar_filled = '█' * tasks_completed
bar_empty = '░' * (total_tasks - tasks_completed)
percentage = tasks_completed * 10
print(f'  Progress: [{bar_filled}{bar_empty}] {percentage}%')
print()
print(f'  📝 Total Steps Collected:    {len(steps)}')
print()
print('=' * 60)
print()

if tasks_completed < total_tasks:
    print(f'  🔄 Still collecting... {total_tasks - tasks_completed} tasks to go!')
else:
    print('  ✅ All 10 tasks completed! Ready for full 200-task run.')
print()
