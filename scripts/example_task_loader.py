"""
Example script demonstrating how to use the TaskLoader
"""

import logging
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.task_loader import TaskLoader, TaskDifficulty, TaskCategory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main demonstration"""
    
    print("=" * 60)
    print("Task Loader Example")
    print("=" * 60)
    
    # Initialize TaskLoader with Wave UI dataset
    print("\n1. Initializing TaskLoader with Wave UI dataset...")
    loader = TaskLoader(
        sources=['wave-ui'],  # Start with Wave UI
        cache_dir='.cache',
        random_seed=42
    )
    
    # Load a small sample of tasks
    print("\n2. Loading tasks (limit: 10)...")
    try:
        tasks = loader.load_tasks(limit=10)
        print(f"   ✓ Loaded {len(tasks)} tasks")
        
        # Display first task
        if tasks:
            print("\n3. Example Task:")
            print(f"   Task ID: {tasks[0].task_id}")
            print(f"   Description: {tasks[0].task_description[:100]}...")
            print(f"   Domain: {tasks[0].website_domain}")
            print(f"   URL: {tasks[0].start_url}")
            print(f"   Source: {tasks[0].metadata.source}")
            print(f"   Difficulty: {tasks[0].metadata.difficulty}")
            print(f"   Category: {tasks[0].metadata.category}")
        
    except Exception as e:
        print(f"   ✗ Error loading tasks: {e}")
        print("\n   Note: This is expected if HuggingFace datasets is not installed")
        print("   Install with: pip install datasets")
        return
    
    # Get statistics
    print("\n4. Dataset Statistics:")
    stats = loader.get_statistics()
    print(f"   Total tasks: {stats['total_tasks']}")
    print(f"   Sources: {stats['sources']}")
    print(f"   Domains: {list(stats['domains'].keys())[:5]}...")  # Show first 5
    print(f"   Difficulties: {stats['difficulties']}")
    print(f"   Categories: {stats['categories']}")
    
    # Filter by difficulty
    print("\n5. Filtering Tasks:")
    easy_tasks = loader.filter_by_difficulty(TaskDifficulty.EASY)
    print(f"   Easy tasks: {len(easy_tasks)}")
    
    # Sample balanced tasks
    print("\n6. Sampling Balanced Tasks:")
    if len(tasks) >= 5:
        balanced = loader.sample_balanced(5, by='domain')
        print(f"   Sampled {len(balanced)} tasks balanced by domain")
        for task in balanced:
            print(f"   - {task.task_id}: {task.website_domain}")
    
    # Save tasks
    print("\n7. Saving Tasks:")
    output_path = "dataset/task_samples.json"
    loader.save_tasks(output_path)
    print(f"   ✓ Saved tasks to {output_path}")
    
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == '__main__':
    main()
