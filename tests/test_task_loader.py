"""
Unit tests for Task Loader module
"""

import pytest
from pathlib import Path
from src.task_loader import Task, TaskMetadata, TaskLoader, TaskSource, TaskDifficulty, TaskCategory


class TestTaskSchema:
    """Test Task schema"""
    
    def test_task_creation(self):
        """Test creating a task object"""
        metadata = TaskMetadata(
            source=TaskSource.WAVE_UI,
            difficulty=TaskDifficulty.MEDIUM,
            category=TaskCategory.SEARCH
        )
        
        task = Task(
            task_id="test-001",
            task_description="Search for a product",
            website_domain="example.com",
            start_url="https://example.com",
            metadata=metadata
        )
        
        assert task.task_id == "test-001"
        assert task.website_domain == "example.com"
        assert task.metadata.source == TaskSource.WAVE_UI
    
    def test_task_to_dict(self):
        """Test converting task to dictionary"""
        metadata = TaskMetadata(
            source=TaskSource.MIND2WEB,
            difficulty=TaskDifficulty.EASY,
            category=TaskCategory.FORM_FILLING
        )
        
        task = Task(
            task_id="test-002",
            task_description="Fill out a form",
            website_domain="test.com",
            start_url="https://test.com/form",
            metadata=metadata
        )
        
        task_dict = task.to_dict()
        
        assert isinstance(task_dict, dict)
        assert task_dict['task_id'] == "test-002"
        assert task_dict['metadata']['source'] == "mind2web"
    
    def test_task_from_dict(self):
        """Test creating task from dictionary"""
        data = {
            "task_id": "test-003",
            "task_description": "Navigate to homepage",
            "website_domain": "example.org",
            "start_url": "https://example.org",
            "metadata": {
                "source": "custom",
                "difficulty": "hard",
                "category": "navigation"
            }
        }
        
        task = Task.from_dict(data)
        
        assert task.task_id == "test-003"
        assert task.metadata.difficulty == TaskDifficulty.HARD


class TestTaskLoader:
    """Test TaskLoader functionality"""
    
    @pytest.fixture
    def task_loader(self, tmp_path):
        """Create a TaskLoader instance for testing"""
        return TaskLoader(
            sources=['wave-ui'],  # Start with one source
            cache_dir=str(tmp_path),
            random_seed=42
        )
    
    def test_initialization(self, task_loader):
        """Test TaskLoader initialization"""
        assert task_loader is not None
        assert 'wave-ui' in task_loader.sources
    
    def test_get_statistics_empty(self, task_loader):
        """Test statistics on empty loader"""
        stats = task_loader.get_statistics()
        assert stats['total_tasks'] == 0
    
    def test_filter_by_domain(self, task_loader):
        """Test domain filtering"""
        # Create some test tasks
        metadata1 = TaskMetadata(
            source=TaskSource.WAVE_UI,
            difficulty=TaskDifficulty.EASY,
            category=TaskCategory.SEARCH
        )
        
        metadata2 = TaskMetadata(
            source=TaskSource.WAVE_UI,
            difficulty=TaskDifficulty.MEDIUM,
            category=TaskCategory.SEARCH
        )
        
        task1 = Task(
            task_id="test-1",
            task_description="Task 1",
            website_domain="example.com",
            start_url="https://example.com",
            metadata=metadata1
        )
        
        task2 = Task(
            task_id="test-2",
            task_description="Task 2",
            website_domain="test.com",
            start_url="https://test.com",
            metadata=metadata2
        )
        
        task_loader._tasks = [task1, task2]
        
        filtered = task_loader.filter_by_domain(['example.com'])
        assert len(filtered) == 1
        assert filtered[0].website_domain == 'example.com'
    
    def test_save_and_load_tasks(self, task_loader, tmp_path):
        """Test saving and loading tasks"""
        # Create a test task
        metadata = TaskMetadata(
            source=TaskSource.CUSTOM,
            difficulty=TaskDifficulty.MEDIUM,
            category=TaskCategory.OTHER
        )
        
        task = Task(
            task_id="test-save-1",
            task_description="Test save task",
            website_domain="save-test.com",
            start_url="https://save-test.com",
            metadata=metadata
        )
        
        task_loader._tasks = [task]
        
        # Save tasks
        save_path = tmp_path / "tasks.json"
        task_loader.save_tasks(str(save_path))
        
        assert save_path.exists()
        
        # Load tasks
        new_loader = TaskLoader(cache_dir=str(tmp_path))
        loaded_tasks = new_loader.load_from_file(str(save_path))
        
        assert len(loaded_tasks) == 1
        assert loaded_tasks[0].task_id == "test-save-1"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
