"""
Simple validation script to verify Task Loader implementation
Run without requiring external dependencies
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.task_loader import Task, TaskMetadata, TaskLoader, TaskSource, TaskDifficulty, TaskCategory


def test_task_schema():
    """Test basic Task schema functionality"""
    print("\n" + "=" * 60)
    print("Testing Task Schema")
    print("=" * 60)
    
    try:
        # Create metadata
        metadata = TaskMetadata(
            source=TaskSource.WAVE_UI,
            difficulty=TaskDifficulty.MEDIUM,
            category=TaskCategory.SEARCH
        )
        print("✓ TaskMetadata created successfully")
        
        # Create task
        task = Task(
            task_id="test-001",
            task_description="Search for a product on Amazon",
            website_domain="amazon.com",
            start_url="https://amazon.com",
            metadata=metadata
        )
        print("✓ Task object created successfully")
        
        # Test to_dict
        task_dict = task.to_dict()
        assert isinstance(task_dict, dict)
        assert task_dict['task_id'] == "test-001"
        print("✓ Task.to_dict() works correctly")
        
        # Test from_dict
        task2 = Task.from_dict(task_dict)
        assert task2.task_id == task.task_id
        assert task2.website_domain == task.website_domain
        print("✓ Task.from_dict() works correctly")
        
        # Test string representation
        task_str = str(task)
        assert "test-001" in task_str
        print("✓ Task.__str__() works correctly")
        
        print("\n✅ All Task Schema tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Task Schema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_loader():
    """Test TaskLoader initialization and basic functionality"""
    print("\n" + "=" * 60)
    print("Testing TaskLoader")
    print("=" * 60)
    
    try:
        # Initialize TaskLoader
        loader = TaskLoader(
            sources=['wave-ui'],
            cache_dir='.cache',
            random_seed=42
        )
        print("✓ TaskLoader initialized successfully")
        
        # Test statistics on empty loader
        stats = loader.get_statistics()
        assert stats['total_tasks'] == 0
        print("✓ get_statistics() works on empty loader")
        
        # Create and add test tasks
        tasks = []
        for i in range(5):
            metadata = TaskMetadata(
                source=TaskSource.WAVE_UI,
                difficulty=TaskDifficulty.EASY if i < 2 else TaskDifficulty.MEDIUM,
                category=TaskCategory.SEARCH
            )
            
            task = Task(
                task_id=f"test-{i:03d}",
                task_description=f"Test task {i}",
                website_domain=f"domain{i % 2}.com",  # Alternate between 2 domains
                start_url=f"https://domain{i % 2}.com",
                metadata=metadata
            )
            tasks.append(task)
        
        loader._tasks = tasks
        print(f"✓ Created {len(tasks)} test tasks")
        
        # Test get_statistics with tasks
        stats = loader.get_statistics()
        assert stats['total_tasks'] == 5
        assert 'wave-ui' in stats['sources']
        print("✓ get_statistics() works with tasks")
        print(f"  - Total tasks: {stats['total_tasks']}")
        print(f"  - Domains: {list(stats['domains'].keys())}")
        print(f"  - Difficulties: {stats['difficulties']}")
        
        # Test filter_by_domain
        filtered = loader.filter_by_domain(['domain0.com'])
        assert len(filtered) == 3  # Tasks 0, 2, 4
        print(f"✓ filter_by_domain() works correctly (filtered: {len(filtered)})")
        
        # Test filter_by_difficulty
        easy_tasks = loader.filter_by_difficulty(TaskDifficulty.EASY)
        assert len(easy_tasks) == 2
        print(f"✓ filter_by_difficulty() works correctly (easy tasks: {len(easy_tasks)})")
        
        # Test sample_balanced
        sampled = loader.sample_balanced(3, by='domain')
        assert len(sampled) <= 3
        print(f"✓ sample_balanced() works correctly (sampled: {len(sampled)})")
        
        # Test save and load
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            loader.save_tasks(temp_path)
            print(f"✓ save_tasks() successfully saved to {temp_path}")
            
            loader2 = TaskLoader(cache_dir='.cache')
            loaded = loader2.load_from_file(temp_path)
            assert len(loaded) == 5
            assert loaded[0].task_id == tasks[0].task_id
            print(f"✓ load_from_file() successfully loaded {len(loaded)} tasks")
            
        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)
        
        print("\n✅ All TaskLoader tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ TaskLoader test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests"""
    print("\n" + "=" * 60)
    print("Task Loader Validation Suite")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Task Schema", test_task_schema()))
    results.append(("Task Loader", test_task_loader()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All validation tests passed!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run example script: python scripts/example_task_loader.py")
        print("3. Download datasets to test full functionality")
    else:
        print("\n⚠️ Some tests failed. Please review the errors above.")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
