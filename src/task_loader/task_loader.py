"""
Task Loader

Main class for loading and managing tasks from multiple sources.
"""

from typing import List, Optional, Dict, Any
import logging
from pathlib import Path
import json
import random

from .task_schema import Task, TaskSource, TaskDifficulty, TaskCategory
from .parsers import MiniWoBParser, Mind2WebParser, WebArenaParser

logger = logging.getLogger(__name__)


class TaskLoader:
    """
    TaskLoader handles loading and normalizing tasks from multiple sources.
    
    Supports:
    - Wave UI 25K
    - Multimodal Mind2Web
    - Visual WebArena
    - Custom tasks
    """
    
    def __init__(
        self,
        sources: Optional[List[str]] = None,
        cache_dir: Optional[str] = None,
        random_seed: int = 42
    ):
        """
        Initialize TaskLoader.
        
        Args:
            sources: List of data sources to use (e.g., ['wave-ui', 'mind2web'])
            cache_dir: Directory to cache downloaded datasets
            random_seed: Random seed for reproducibility
        """
        self.sources = sources or ['mind2web', 'miniwob', 'webarena']
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / '.cache' / 'web_trajectory_data'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.random_seed = random_seed
        random.seed(random_seed)
        
        # Initialize parsers
        self._parsers: Dict[str, Any] = {}
        self._initialize_parsers()
        
        # Storage for loaded tasks
        self._tasks: List[Task] = []
        
        logger.info(f"TaskLoader initialized with sources: {self.sources}")
    
    def _initialize_parsers(self):
        """Initialize parsers for each data source"""
        parser_map = {
            'mind2web': Mind2WebParser,
            'miniwob':  MiniWoBParser,
            'webarena': WebArenaParser,
            # legacy aliases
            'wave-ui':          MiniWoBParser,
            'visual-webarena':  WebArenaParser,
        }
        
        for source in self.sources:
            if source in parser_map:
                self._parsers[source] = parser_map[source](cache_dir=str(self.cache_dir))
                logger.info(f"Initialized parser for {source}")
            else:
                logger.warning(f"Unknown source: {source}")
    
    def load_tasks(
        self,
        limit: Optional[int] = None,
        sources: Optional[List[str]] = None,
        shuffle: bool = True
    ) -> List[Task]:
        """
        Load tasks from specified sources.
        
        Args:
            limit: Maximum number of tasks to load (None for all)
            sources: Override default sources
            shuffle: Whether to shuffle tasks after loading
        
        Returns:
            List of Task objects
        """
        sources_to_use = sources if sources is not None else self.sources
        all_tasks = []
        
        for source in sources_to_use:
            if source not in self._parsers:
                logger.warning(f"Parser not initialized for {source}, skipping")
                continue
            
            try:
                parser = self._parsers[source]
                tasks = parser.parse()
                all_tasks.extend(tasks)
                logger.info(f"Loaded {len(tasks)} tasks from {source}")
            except Exception as e:
                logger.error(f"Error loading tasks from {source}: {e}")
        
        # Shuffle if requested
        if shuffle:
            random.shuffle(all_tasks)
        
        # Apply limit
        if limit is not None:
            all_tasks = all_tasks[:limit]
        
        self._tasks = all_tasks
        logger.info(f"Total loaded tasks: {len(all_tasks)}")
        
        return all_tasks
    
    def filter_by_domain(self, domains: List[str]) -> List[Task]:
        """
        Filter tasks by website domain.
        
        Args:
            domains: List of domains to include
        
        Returns:
            Filtered list of tasks
        """
        filtered = [task for task in self._tasks if task.website_domain in domains]
        logger.info(f"Filtered to {len(filtered)} tasks from domains: {domains}")
        return filtered
    
    def filter_by_difficulty(self, difficulty: TaskDifficulty) -> List[Task]:
        """
        Filter tasks by difficulty level.
        
        Args:
            difficulty: Difficulty level to filter by
        
        Returns:
            Filtered list of tasks
        """
        filtered = [
            task for task in self._tasks 
            if task.metadata.difficulty == difficulty
        ]
        logger.info(f"Filtered to {len(filtered)} tasks with difficulty: {difficulty}")
        return filtered
    
    def filter_by_category(self, category: TaskCategory) -> List[Task]:
        """
        Filter tasks by category.
        
        Args:
            category: Category to filter by
        
        Returns:
            Filtered list of tasks
        """
        filtered = [
            task for task in self._tasks 
            if task.metadata.category == category
        ]
        logger.info(f"Filtered to {len(filtered)} tasks with category: {category}")
        return filtered
    
    def sample_balanced(
        self,
        n: int,
        by: str = 'domain'
    ) -> List[Task]:
        """
        Sample tasks in a balanced way.
        
        Args:
            n: Number of tasks to sample
            by: Balance criterion ('domain', 'difficulty', 'category')
        
        Returns:
            Balanced sample of tasks
        """
        if not self._tasks:
            logger.warning("No tasks loaded")
            return []
        
        # Group tasks by criterion
        groups: Dict[str, List[Task]] = {}
        for task in self._tasks:
            if by == 'domain':
                key = task.website_domain
            elif by == 'difficulty':
                key = task.metadata.difficulty.value
            elif by == 'category':
                key = task.metadata.category.value
            else:
                logger.warning(f"Unknown balance criterion: {by}")
                return random.sample(self._tasks, min(n, len(self._tasks)))
            
            if key not in groups:
                groups[key] = []
            groups[key].append(task)
        
        # Sample evenly from each group
        samples_per_group = max(1, n // len(groups))
        sampled = []
        
        for group_tasks in groups.values():
            sample_size = min(samples_per_group, len(group_tasks))
            sampled.extend(random.sample(group_tasks, sample_size))
        
        # If we need more samples, randomly add from all tasks
        if len(sampled) < n:
            remaining = [t for t in self._tasks if t not in sampled]
            additional = min(n - len(sampled), len(remaining))
            sampled.extend(random.sample(remaining, additional))
        
        # Ensure exact count
        sampled = sampled[:n]
        
        logger.info(f"Sampled {len(sampled)} tasks balanced by {by}")
        return sampled
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about loaded tasks.
        
        Returns:
            Dictionary with statistics
        """
        if not self._tasks:
            return {"total_tasks": 0}
        
        stats = {
            "total_tasks": len(self._tasks),
            "sources": {},
            "domains": {},
            "difficulties": {},
            "categories": {},
        }
        
        for task in self._tasks:
            # Count by source
            source = task.metadata.source
            stats["sources"][source] = stats["sources"].get(source, 0) + 1
            
            # Count by domain
            domain = task.website_domain
            stats["domains"][domain] = stats["domains"].get(domain, 0) + 1
            
            # Count by difficulty
            diff = task.metadata.difficulty.value
            stats["difficulties"][diff] = stats["difficulties"].get(diff, 0) + 1
            
            # Count by category
            cat = task.metadata.category.value
            stats["categories"][cat] = stats["categories"].get(cat, 0) + 1
        
        return stats
    
    def save_tasks(self, output_path: str):
        """
        Save loaded tasks to a JSON file.
        
        Args:
            output_path: Path to save tasks
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(
                [task.to_dict() for task in self._tasks],
                f,
                indent=2,
                ensure_ascii=False
            )
        
        logger.info(f"Saved {len(self._tasks)} tasks to {output_path}")
    
    def load_from_file(self, input_path: str) -> List[Task]:
        """
        Load tasks from a saved JSON file.
        
        Args:
            input_path: Path to load tasks from
        
        Returns:
            List of loaded tasks
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self._tasks = [Task.from_dict(task_dict) for task_dict in data]
        logger.info(f"Loaded {len(self._tasks)} tasks from {input_path}")
        
        return self._tasks
