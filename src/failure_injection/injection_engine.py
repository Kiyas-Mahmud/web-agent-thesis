"""
Failure injection framework for offline augmentation.

Provides base classes and configuration for systematic failure injection.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import random
import logging

from ..offline_data.offline_schema import (
    OfflineStep,
    OfflineTrajectory,
    AugmentedStep,
    AugmentedTrajectory
)

logger = logging.getLogger(__name__)


@dataclass
class InjectionConfig:
    """
    Configuration for failure injection.
    
    Controls injection probabilities and distributions.
    """
    
    # Overall injection probability (0.0 - 1.0)
    injection_rate: float = 0.6  # 60% of steps will have failures injected
    
    # Target distribution (should sum to 1.0)
    target_distribution: Dict[str, float] = field(default_factory=lambda: {
        "clean_success": 0.40,      # 40% clean steps
        "recoverable_failure": 0.30, # 30% recoverable failures
        "non_recoverable": 0.15,     # 15% non-recoverable
        "ambiguous": 0.15            # 15% ambiguous
    })
    
    # Per-failure-type probabilities (for recoverable failures)
    failure_type_distribution: Dict[str, float] = field(default_factory=lambda: {
        "TARGET_MISSING": 0.27,      # 27% of failures
        "MISCLICK": 0.23,            # 23%
        "WRONG_OPERATION": 0.20,     # 20%
        "NO_STATE_CHANGE": 0.17,     # 17%
        "LOOP": 0.13                 # 13%
    })
    
    # Recovery success rates (per failure type)
    recovery_success_rates: Dict[str, float] = field(default_factory=lambda: {
        "TARGET_MISSING": 0.65,      # 65% recovery success
        "MISCLICK": 0.55,            # 55%
        "WRONG_OPERATION": 0.60,     # 60%
        "NO_STATE_CHANGE": 0.45,     # 45%
        "LOOP": 0.75                 # 75%
    })
    
    # Injection parameters
    misclick_distance_range: tuple[int, int] = (50, 200)  # Pixel shift range
    blur_radius: int = 20  # For TARGET_MISSING masking
    loop_length: int = 3  # Number of repetitions for LOOP
    
    # Randomization seed
    random_seed: Optional[int] = None
    
    def __post_init__(self):
        if self.random_seed is not None:
            random.seed(self.random_seed)


class FailureInjector(ABC):
    """
    Base class for failure injectors.
    
    Each injector implements one failure type:
    - TARGET_MISSING
    - MISCLICK
    - WRONG_OPERATION
    - NO_STATE_CHANGE
    - LOOP
    """
    
    def __init__(self, config: InjectionConfig):
        """
        Initialize injector.
        
        Args:
            config: Injection configuration
        """
        self.config = config
        self.injection_count = 0
        self.success_count = 0
    
    @property
    @abstractmethod
    def injection_type(self) -> str:
        """Return the type of failure this injector creates."""
        pass
    
    @property
    @abstractmethod
    def failure_type(self) -> str:
        """Return the failure classification type."""
        pass
    
    @property
    @abstractmethod
    def failure_subtype(self) -> str:
        """Return the failure classification subtype."""
        pass
    
    @abstractmethod
    def can_inject(self, step: OfflineStep) -> bool:
        """
        Check if this injector can be applied to the given step.
        
        Args:
            step: Offline step to check
            
        Returns:
            True if injection is possible, False otherwise
        """
        pass
    
    @abstractmethod
    def inject(
        self, 
        step: OfflineStep,
        trajectory: OfflineTrajectory
    ) -> AugmentedStep:
        """
        Inject failure into the step.
        
        Args:
            step: Original offline step
            trajectory: Full trajectory context
            
        Returns:
            AugmentedStep with injected failure
        """
        pass
    
    def _create_augmented_step(
        self,
        original_step: OfflineStep,
        execution_outcome: str = "FAILURE",
        **kwargs
    ) -> AugmentedStep:
        """
        Create an AugmentedStep with base metadata.
        
        Args:
            original_step: Original offline step
            execution_outcome: SUCCESS, FAILURE, or PARTIAL
            **kwargs: Additional fields for AugmentedStep
            
        Returns:
            AugmentedStep with base fields populated
        """
        augmented = AugmentedStep(
            original_step=original_step,
            is_augmented=True,
            injection_type=self.injection_type,
            failure_type=self.failure_type,
            failure_subtype=self.failure_subtype,
            failure_confidence=0.95,  # High confidence for synthetic failures
            execution_outcome=execution_outcome,
            injection_config={
                "injector": self.__class__.__name__,
                "injection_count": self.injection_count
            }
        )
        
        # Apply any additional fields from kwargs
        for key, value in kwargs.items():
            if hasattr(augmented, key):
                setattr(augmented, key, value)
        
        self.injection_count += 1
        
        return augmented
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get injector statistics.
        
        Returns:
            Statistics dict
        """
        return {
            "injection_type": self.injection_type,
            "total_injections": self.injection_count,
            "successful_injections": self.success_count,
            "success_rate": (
                self.success_count / self.injection_count 
                if self.injection_count > 0 else 0
            )
        }


class InjectionPipeline:
    """
    Orchestrates multiple failure injectors to create augmented dataset.
    """
    
    def __init__(self, config: InjectionConfig):
        """
        Initialize injection pipeline.
        
        Args:
            config: Injection configuration
        """
        self.config = config
        self.injectors: List[FailureInjector] = []
        self.statistics = {
            "total_steps_processed": 0,
            "clean_steps": 0,
            "injected_failures": 0,
            "injection_type_counts": {}
        }
        
        logger.info(f"InjectionPipeline initialized with {config.injection_rate*100:.0f}% injection rate")
    
    def register_injector(self, injector: FailureInjector):
        """
        Register a failure injector.
        
        Args:
            injector: FailureInjector instance
        """
        self.injectors.append(injector)
        logger.info(f"Registered injector: {injector.injection_type}")
    
    def augment_trajectory(
        self, 
        trajectory: OfflineTrajectory
    ) -> AugmentedTrajectory:
        """
        Augment a trajectory with injected failures.
        
        Args:
            trajectory: Original offline trajectory
            
        Returns:
            AugmentedTrajectory with injected failures
        """
        augmented_steps = []
        
        for step in trajectory.steps:
            self.statistics["total_steps_processed"] += 1
            
            # Decide whether to inject failure
            if random.random() < self.config.injection_rate:
                # Select injector based on failure type distribution
                injector = self._select_injector(step)
                
                if injector:
                    # Inject failure
                    augmented_step = injector.inject(step, trajectory)
                    augmented_steps.append(augmented_step)
                    
                    self.statistics["injected_failures"] += 1
                    injection_type = injector.injection_type
                    self.statistics["injection_type_counts"][injection_type] = (
                        self.statistics["injection_type_counts"].get(injection_type, 0) + 1
                    )
                else:
                    # No suitable injector, keep clean
                    augmented_steps.append(self._create_clean_step(step))
                    self.statistics["clean_steps"] += 1
            else:
                # Keep step clean
                augmented_steps.append(self._create_clean_step(step))
                self.statistics["clean_steps"] += 1
        
        # Create augmented trajectory
        augmented_trajectory = AugmentedTrajectory(
            original_trajectory=trajectory,
            augmented_steps=augmented_steps,
            injection_probability=self.config.injection_rate,
            target_distribution=self.config.target_distribution,
            generation_config={
                "injection_rate": self.config.injection_rate,
                "num_injectors": len(self.injectors)
            }
        )
        
        return augmented_trajectory
    
    def _select_injector(self, step: OfflineStep) -> Optional[FailureInjector]:
        """
        Select appropriate injector based on failure type distribution.
        
        Args:
            step: Step to inject into
            
        Returns:
            Selected injector or None
        """
        # Get applicable injectors
        applicable_injectors = [
            injector for injector in self.injectors
            if injector.can_inject(step)
        ]
        
        if not applicable_injectors:
            return None
        
        # Weight by failure type distribution
        weights = []
        for injector in applicable_injectors:
            weight = self.config.failure_type_distribution.get(
                injector.injection_type, 
                1.0 / len(self.injectors)
            )
            weights.append(weight)
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(applicable_injectors)
        
        normalized_weights = [w / total_weight for w in weights]
        
        # Random selection based on weights
        selected = random.choices(applicable_injectors, weights=normalized_weights, k=1)[0]
        
        return selected
    
    def _create_clean_step(self, step: OfflineStep) -> AugmentedStep:
        """
        Create augmented step without injection (clean copy).
        
        Args:
            step: Original step
            
        Returns:
            AugmentedStep marked as clean
        """
        return AugmentedStep(
            original_step=step,
            is_augmented=False,
            execution_outcome="SUCCESS"
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get pipeline statistics.
        
        Returns:
            Statistics dict
        """
        stats = self.statistics.copy()
        
        # Add per-injector statistics
        stats["injector_statistics"] = [
            injector.get_statistics() for injector in self.injectors
        ]
        
        # Compute actual distribution
        total = stats["total_steps_processed"]
        if total > 0:
            stats["actual_distribution"] = {
                "clean_success": stats["clean_steps"] / total,
                "injected_failures": stats["injected_failures"] / total
            }
            
            stats["actual_failure_distribution"] = {}
            for injection_type, count in stats["injection_type_counts"].items():
                stats["actual_failure_distribution"][injection_type] = (
                    count / stats["injected_failures"] 
                    if stats["injected_failures"] > 0 else 0
                )
        
        return stats
