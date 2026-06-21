"""
collection_runner
=================
Main data-collection module.

Quick usage
-----------
    from collection_runner import CollectionRunner

    runner = CollectionRunner(output_dir="dataset", headless=True)
    stats  = runner.run(source="mind2web", limit=20)
    print(stats)

Or from the command line:

    python src/collection_runner/collect_runner.py --source mind2web --limit 20
"""

from .collect_runner import CollectionRunner, task_to_action_log

__all__ = ["CollectionRunner", "task_to_action_log"]
