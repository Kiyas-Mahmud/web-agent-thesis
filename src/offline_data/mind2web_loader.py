"""
Multimodal Mind2Web dataset loader.

Loads trajectories and screenshots from HuggingFace dataset:
osunlp/Multimodal-Mind2Web

Contains ~2,000 tasks with ~50,000 steps, each with pre-captured screenshots.
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from PIL import Image
import io
import json

from .offline_schema import OfflineStep, OfflineTrajectory

logger = logging.getLogger(__name__)


class MultimodalMind2WebLoader:
    """
    Loader for Multimodal Mind2Web dataset from HuggingFace.
    
    Usage:
        loader = MultimodalMind2WebLoader(cache_dir="dataset/mind2web_offline")
        loader.download_dataset()
        trajectories = loader.load_trajectories(split="train", limit=100)
    """
    
    def __init__(self, cache_dir: str = "dataset/mind2web_offline", use_streaming: bool = False):
        """
        Initialize loader.
        
        Args:
            cache_dir: Directory to cache downloaded dataset
            use_streaming: If True, use streaming mode (False = full download, better for journals)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.dataset = None
        self.dataset_info = None
        self.use_streaming = use_streaming
        
        logger.info(f"MultimodalMind2WebLoader initialized (streaming={use_streaming})")
    
    def download_dataset(self, force_download: bool = False, max_retries: int = 3) -> bool:
        """
        Load Multimodal Mind2Web dataset from HuggingFace with robust error handling.
        
        If streaming mode is enabled (default), loads on-demand without full download.
        Otherwise, downloads full dataset to cache with retry logic.
        
        Args:
            force_download: If True, re-download even if cached (only for non-streaming)
            max_retries: Number of retry attempts for failed downloads (default: 3)
            
        Returns:
            True if successful, False otherwise
        """
        import time
        import os
        
        # Configure HTTP timeout and connection settings
        os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '180'  # 3 minute timeout per file (faster detection)
        os.environ['HF_HUB_ENABLE_HF_TRANSFER'] = '1'  # Use faster hf_transfer if available
        os.environ['REQUESTS_CA_BUNDLE'] = ''  # Fresh SSL connections
        os.environ['HF_HUB_HTTP_MAX_RETRIES'] = '5'  # Retry on connection failures
        
        try:
            from datasets import load_dataset
            import datasets
            
            # Enable progress bars
            datasets.logging.set_verbosity_info()
            
            if self.use_streaming:
                logger.info("Loading Multimodal Mind2Web in streaming mode...")
                logger.info("Dataset: osunlp/Multimodal-Mind2Web")
                logger.info("(No large download needed - data fetched on-demand)")
                
                # Load in streaming mode - no retries needed
                self.dataset = load_dataset(
                    "osunlp/Multimodal-Mind2Web",
                    streaming=True,
                    split="train"
                )
                
                logger.info(f"✅ Dataset loaded in streaming mode")
                
            else:
                logger.info("Downloading Multimodal Mind2Web from HuggingFace...")
                logger.info("Dataset: osunlp/Multimodal-Mind2Web")
                logger.info("WARNING: This will download ~8.4GB of data")
                logger.info(f"Retries enabled: {max_retries} attempts")
                logger.info(f"Timeout per file: 5 minutes")
                
                # Try downloading with retries
                last_error = None
                for attempt in range(max_retries):
                    try:
                        if attempt > 0:
                            logger.info(f"\n🔄 Retry attempt {attempt + 1}/{max_retries}...")
                            time.sleep(2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
                        
                        # Download dataset (avoid num_proc to prevent connection issues)
                        self.dataset = load_dataset(
                            "osunlp/Multimodal-Mind2Web",
                            cache_dir=str(self.cache_dir),
                            download_mode="force_redownload" if force_download else "reuse_cache_if_exists",
                        )
                        
                        # If we get here, download succeeded
                        logger.info(f"✅ Dataset downloaded successfully")
                        logger.info(f"Available splits: {list(self.dataset.keys())}")
                        
                        # Log dataset info
                        for split_name, split_data in self.dataset.items():
                            logger.info(f"  {split_name}: {len(split_data)} samples")
                        
                        return True
                        
                    except (TimeoutError, ConnectionError, OSError) as e:
                        last_error = e
                        error_type = type(e).__name__
                        logger.warning(f"⚠️  Download {error_type}: {str(e)[:100]}")
                        
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying in {2 ** (attempt + 1)} seconds...")
                        else:
                            logger.error(f"❌ All {max_retries} attempts failed")
                            raise
                    
                    except Exception as e:
                        # For other errors, don't retry
                        logger.error(f"Download failed with non-retryable error: {e}")
                        raise
                
                # If we exhausted all retries
                if last_error:
                    raise last_error
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            logger.info("\nTroubleshooting:")
            logger.info("1. Check internet connection")
            logger.info("2. Try: pip install --upgrade datasets huggingface-hub hf-transfer")
            logger.info("3. Check HuggingFace status: https://status.huggingface.co")
            logger.info("4. Try with streaming mode: MultimodalMind2WebLoader(use_streaming=True)")
            logger.info("5. Clear cache and retry: rm -rf ~/.cache/huggingface/")
            logger.info("6. Try loading from cache: use load_from_cache() method")
            return False
    
    def load_from_cache(self, splits_to_load=None) -> bool:
        """
        Load dataset from HuggingFace cache, one split at a time.
        
        Args:
            splits_to_load: List of splits to load. Defaults to all splits.
                           Example: ['test_domain', 'test_task', 'test_website']
        
        Returns:
            True if successful, False otherwise
        """
        try:
            from datasets import load_dataset, DatasetDict
            
            if splits_to_load is None:
                splits_to_load = ['train', 'test_domain', 'test_task', 'test_website']
            
            logger.info(f"Loading splits from HuggingFace cache: {splits_to_load}")
            
            dataset_dict = {}
            for split_name in splits_to_load:
                logger.info(f"  Loading {split_name}...")
                try:
                    ds = load_dataset(
                        "osunlp/Multimodal-Mind2Web",
                        split=split_name,
                    )
                    dataset_dict[split_name] = ds
                    logger.info(f"  {split_name}: {len(ds)} samples")
                except Exception as e:
                    logger.warning(f"  Failed to load {split_name}: {e}")
            
            if not dataset_dict:
                logger.error("No splits could be loaded!")
                return False
            
            self.dataset = DatasetDict(dataset_dict)
            
            logger.info(f"\nDataset loaded from cache:")
            for split_name, split_data in self.dataset.items():
                logger.info(f"   {split_name}: {len(split_data)} samples")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load from cache: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_trajectories(
        self, 
        split: str = "train", 
        limit: Optional[int] = None,
        filter_by_domain: Optional[List[str]] = None,
        filter_by_ids: Optional[List[str]] = None,
        load_screenshots: bool = False
    ) -> List[OfflineTrajectory]:
        """
        Load trajectories from dataset.
        
        Args:
            split: Dataset split ("train", "test_task", "test_website", "test_domain")
            limit: Maximum number of trajectories to load
            filter_by_domain: Only load trajectories from specific domains
            filter_by_ids: Only load trajectories with these annotation IDs (for batch processing)
            load_screenshots: Whether to load screenshots (memory intensive)
            
        Returns:
            List of OfflineTrajectory objects
        """
        if self.dataset is None:
            logger.error("Dataset not loaded. Call download_dataset() first.")
            return []
        
        # In streaming mode, dataset is already a single split
        if self.use_streaming:
            split_data = self.dataset
            logger.info(f"Loading trajectories in streaming mode (limit={limit if limit else 'all'})...")
        else:
            if split not in self.dataset:
                logger.error(f"Split '{split}' not found in dataset. Available: {list(self.dataset.keys())}")
                return []
            
            split_data = self.dataset[split]
            logger.info(f"Loading trajectories from split '{split}' ({len(split_data)} total)...")
        
        # Group actions by annotation_id (each annotation_id = 1 trajectory)
        logger.info("Grouping actions into trajectories by annotation_id...")
        from collections import defaultdict
        trajectory_groups = defaultdict(list)
        
        # Access the underlying arrow table
        arrow_table = split_data.data
        
        # Convert to pandas for easier processing (only metadata, not images)
        import pandas as pd
        # Select only non-image columns for grouping
        metadata_columns = ['annotation_id', 'website', 'domain', 'subdomain', 'confirmed_task', 
                           'action_uid', 'operation', 'pos_candidates', 'neg_candidates']
        available_columns = [col for col in metadata_columns if col in arrow_table.column_names]
        
        for idx in range(len(split_data)):
            sample_dict = {}
            for col in available_columns:
                sample_dict[col] = arrow_table[col][idx].as_py()
            
            annotation_id = sample_dict.get("annotation_id", f"unknown_{idx}")
            sample_dict['_row_index'] = idx  # Store index for later screenshot retrieval
            trajectory_groups[annotation_id].append(sample_dict)
        
        logger.info(f"Found {len(trajectory_groups)} unique trajectories")
        
        # Convert filter_by_ids to set for faster lookup
        ids_filter = set(filter_by_ids) if filter_by_ids else None
        
        trajectories = []
        tasks_processed = 0
        
        # Process each trajectory (group of actions)
        for annotation_id, actions in trajectory_groups.items():
            if limit and tasks_processed >= limit:
                break
            
            # Filter by annotation IDs if specified (for batch processing)
            if ids_filter and annotation_id not in ids_filter:
                continue
            
            # Filter by domain if specified
            if filter_by_domain:
                domain = actions[0].get("domain") if actions else None
                if domain not in filter_by_domain:
                    continue
            
            # Parse trajectory from grouped actions
            trajectory = self._parse_trajectory_from_actions(
                annotation_id, actions, arrow_table, load_screenshots
            )
            
            if trajectory and trajectory.steps:
                trajectories.append(trajectory)
                tasks_processed += 1
                
                if tasks_processed % 10 == 0:
                    logger.info(f"  Loaded {tasks_processed} trajectories...")
        
        logger.info(f"✅ Loaded {len(trajectories)} trajectories")
        return trajectories
    
    def _parse_trajectory_from_actions(
        self, 
        annotation_id: str, 
        actions: List[Dict[str, Any]],
        arrow_table,
        load_screenshots: bool = False
    ) -> Optional[OfflineTrajectory]:
        """
        Parse a trajectory from a list of action samples (Mind2Web format).
        Each action in the list is one step of the trajectory.
        
        Args:
            annotation_id: Unique trajectory ID
            actions: List of action samples (sorted by step number)
            arrow_table: Arrow table for loading screenshots
            load_screenshots: Whether to load screenshots
            
        Returns:
            OfflineTrajectory or None if invalid
        """
        try:
            if not actions:
                return None
            
            # Sort actions by action_uid to ensure correct order
            actions_sorted = sorted(actions, key=lambda x: x.get("action_uid", ""))
            
            # Get metadata from first action
            first = actions_sorted[0]
            website = first.get("website", "unknown")
            domain = first.get("domain", "unknown")
            subdomain = first.get("subdomain", "")
            confirmed_task = first.get("confirmed_task", "")
            
            # Parse each action into a step
            steps = []
            for step_idx, action in enumerate(actions_sorted):
                # Get next action for state_after loading
                next_action = actions_sorted[step_idx + 1] if step_idx + 1 < len(actions_sorted) else None
                
                step = self._parse_single_action_step(
                    annotation_id=annotation_id,
                    step_number=step_idx,
                    action_sample=action,
                    arrow_table=arrow_table,
                    load_screenshots=load_screenshots,
                    next_action_sample=next_action
                )
                if step:
                    steps.append(step)
            
            if not steps:
                return None
            
            # Create trajectory
            trajectory = OfflineTrajectory(
                task_id=annotation_id,
                website=website,
                domain=domain,
                confirmed_task=confirmed_task,
                steps=steps,
                num_steps=len(steps),
                is_complete=len(steps) > 0,
                gold_outcome="SUCCESS",
                source_dataset="multimodal_mind2web"
            )
            
            return trajectory
            
        except Exception as e:
            logger.warning(f"Failed to parse trajectory {annotation_id}: {e}")
            return None
    
    def _parse_single_action_step(
        self,
        annotation_id: str,
        step_number: int,
        action_sample: Dict[str, Any],
        arrow_table,
        load_screenshots: bool = False,
        next_action_sample: Optional[Dict[str, Any]] = None
    ) -> Optional[OfflineStep]:
        """
        Parse a single action sample into an OfflineStep.
        
        Args:
            annotation_id: Trajectory ID
            step_number: Step index
            action_sample: Action data from Mind2Web
            arrow_table: Arrow table for loading screenshots
            load_screenshots: Whether to load screenshots
            next_action_sample: Next action in sequence (for state_after)
            
        Returns:
            OfflineStep or None
        """
        try:
            # Extract fields
            action_uid = action_sample.get("action_uid", f"{annotation_id}_step_{step_number}")
            operation = action_sample.get("operation", {})
            
            # Parse operation if it's a JSON string
            if isinstance(operation, str):
                try:
                    import json
                    operation = json.loads(operation)
                except:
                    operation = {}
            
            operation_type = operation.get("op", "UNKNOWN") if isinstance(operation, dict) else "UNKNOWN"
            
            # Extract target element info
            pos_candidates = action_sample.get("pos_candidates", [])
            target_bbox = None
            target_text = ""
            action_coords = None
            
            if pos_candidates:
                # First positive candidate is the target
                target = pos_candidates[0] if isinstance(pos_candidates, list) else pos_candidates
                
                # pos_candidates might be JSON strings, parse if needed
                if isinstance(target, str):
                    try:
                        import json
                        target = json.loads(target)
                    except:
                        pass
                
                if isinstance(target, dict):
                    # Extract bbox from attributes
                    attributes = target.get("attributes")
                    if isinstance(attributes, str):
                        try:
                            import json
                            attributes = json.loads(attributes)
                        except:
                            pass
                    
                    if isinstance(attributes, dict):
                        bbox_str = attributes.get("bounding_box_rect", "")
                        target_text = attributes.get("text", "")
                        
                        # Parse bbox string format: "x,y,width,height"
                        if bbox_str and isinstance(bbox_str, str):
                            try:
                                parts = bbox_str.split(",")
                                if len(parts) == 4:
                                    x, y, width, height = map(float, parts)
                                    target_bbox = {"x": x, "y": y, "width": width, "height": height}
                                    action_coords = (int(x + width / 2), int(y + height / 2))
                            except:
                                pass
            
            # Get website and domain info
            website = action_sample.get("website", "unknown")
            domain = action_sample.get("domain", "unknown")
            confirmed_task = action_sample.get("confirmed_task", "")
            
            # Load screenshots if requested
            state_before = None
            state_after = None
            if load_screenshots and '_row_index' in action_sample:
                row_idx = action_sample['_row_index']
                try:
                    # Try to load screenshot from arrow table
                    # Mind2Web stores screenshots in 'screenshot' column
                    if 'screenshot' in arrow_table.column_names:
                        screenshot_data = arrow_table['screenshot'][row_idx].as_py()
                        if screenshot_data:
                            # Convert to PIL Image
                            if isinstance(screenshot_data, dict) and 'bytes' in screenshot_data:
                                # HuggingFace Image format
                                import io
                                state_before = Image.open(io.BytesIO(screenshot_data['bytes']))
                            elif isinstance(screenshot_data, bytes):
                                import io
                                state_before = Image.open(io.BytesIO(screenshot_data))
                            elif hasattr(screenshot_data, 'as_py'):
                                # Try converting Arrow format
                                screenshot_bytes = screenshot_data.as_py()
                                if isinstance(screenshot_bytes, bytes):
                                    import io
                                    state_before = Image.open(io.BytesIO(screenshot_bytes))
                except Exception as e:
                    logger.debug(f"Failed to load screenshot for step {step_number}: {e}")
                
                # Load state_after from next action's screenshot (for LOOP detection)
                if next_action_sample and '_row_index' in next_action_sample:
                    try:
                        next_row_idx = next_action_sample['_row_index']
                        if 'screenshot' in arrow_table.column_names:
                            next_screenshot_data = arrow_table['screenshot'][next_row_idx].as_py()
                            if next_screenshot_data:
                                # Convert to PIL Image
                                if isinstance(next_screenshot_data, dict) and 'bytes' in next_screenshot_data:
                                    import io
                                    state_after = Image.open(io.BytesIO(next_screenshot_data['bytes']))
                                elif isinstance(next_screenshot_data, bytes):
                                    import io
                                    state_after = Image.open(io.BytesIO(next_screenshot_data))
                                elif hasattr(next_screenshot_data, 'as_py'):
                                    screenshot_bytes = next_screenshot_data.as_py()
                                    if isinstance(screenshot_bytes, bytes):
                                        import io
                                        state_after = Image.open(io.BytesIO(screenshot_bytes))
                    except Exception as e:
                        logger.debug(f"Failed to load state_after for step {step_number}: {e}")
            
            # Create step (matching OfflineStep dataclass fields)
            step = OfflineStep(
                task_id=annotation_id,
                website=website,
                domain=domain,
                confirmed_task=confirmed_task,
                step_number=step_number,
                annotation_id=annotation_id,
                action_type=operation_type,
                action_target=target_text if target_text else f"element_{step_number}",
                action_uid=action_uid,
                action_coords=action_coords,
                action_text=operation.get("value") if isinstance(operation, dict) else None,
                state_before=state_before,
                state_after=state_after,
                target_bbox=target_bbox,
                candidate_bboxes=pos_candidates if isinstance(pos_candidates, list) else [],
                is_valid=True
            )
            
            return step
            
        except Exception as e:
            logger.warning(f"Failed to parse step {step_number} of {annotation_id}: {e}")
            return None
    
    def _parse_trajectory(self, sample: Dict[str, Any], sample_idx: int) -> Optional[OfflineTrajectory]:
        """
        Parse a single sample into OfflineTrajectory.
        
        Args:
            sample: Raw sample from dataset
            sample_idx: Index of sample in dataset
            
        Returns:
            OfflineTrajectory or None if invalid
        """
        try:
            # Extract task metadata
            task_id = sample.get("annotation_id", f"task_{sample_idx}")
            website = sample.get("website", "unknown")
            domain = sample.get("domain", "unknown")
            confirmed_task = sample.get("confirmed_task", "")
            
            # Parse actions (sequence of steps)
            actions = sample.get("actions", [])
            action_reprs = sample.get("action_reprs", [])
            operation_types = sample.get("operations", [])
            pos_candidates = sample.get("pos_candidates", [])
            
            # Images
            images = sample.get("images", [])
            
            # Parse each step
            steps = []
            for step_idx in range(len(actions)):
                step = self._parse_step(
                    task_id=task_id,
                    website=website,
                    domain=domain,
                    confirmed_task=confirmed_task,
                    step_number=step_idx,
                    action=actions[step_idx] if step_idx < len(actions) else {},
                    action_repr=action_reprs[step_idx] if step_idx < len(action_reprs) else "",
                    operation_type=operation_types[step_idx] if step_idx < len(operation_types) else "UNKNOWN",
                    pos_candidate=pos_candidates[step_idx] if step_idx < len(pos_candidates) else [],
                    state_before_img=images[step_idx] if step_idx < len(images) else None,
                    state_after_img=images[step_idx + 1] if step_idx + 1 < len(images) else None,
                )
                
                if step:
                    steps.append(step)
            
            # Create trajectory
            trajectory = OfflineTrajectory(
                task_id=task_id,
                website=website,
                domain=domain,
                confirmed_task=confirmed_task,
                steps=steps,
                num_steps=len(steps),
                is_complete=len(steps) > 0,
                gold_outcome="SUCCESS",
                source_dataset="multimodal_mind2web"
            )
            
            return trajectory
            
        except Exception as e:
            logger.warning(f"Failed to parse trajectory {sample_idx}: {e}")
            return None
    
    def _parse_step(
        self,
        task_id: str,
        website: str,
        domain: str,
        confirmed_task: str,
        step_number: int,
        action: Dict[str, Any],
        action_repr: str,
        operation_type: str,
        pos_candidate: List[Dict[str, Any]],
        state_before_img: Optional[Any],
        state_after_img: Optional[Any],
    ) -> Optional[OfflineStep]:
        """
        Parse a single step from raw data.
        
        Args:
            Various step metadata from dataset
            
        Returns:
            OfflineStep or None if invalid
        """
        try:
            # Parse action details
            action_uid = action.get("uid", "")
            action_target = action_repr
            
            # Parse bbox
            target_bbox = None
            if "pos" in action and action["pos"]:
                bbox_list = action["pos"]
                if len(bbox_list) >= 4:
                    target_bbox = {
                        "x": bbox_list[0],
                        "y": bbox_list[1],
                        "width": bbox_list[2] - bbox_list[0],
                        "height": bbox_list[3] - bbox_list[1]
                    }
            
            # Parse candidate bboxes
            candidate_bboxes = []
            for candidate in pos_candidate:
                if "pos" in candidate and candidate["pos"]:
                    bbox_list = candidate["pos"]
                    if len(bbox_list) >= 4:
                        candidate_bboxes.append({
                            "uid": candidate.get("uid", ""),
                            "x": bbox_list[0],
                            "y": bbox_list[1],
                            "width": bbox_list[2] - bbox_list[0],
                            "height": bbox_list[3] - bbox_list[1],
                            "attributes": candidate.get("attributes", {})
                        })
            
            # Convert images to PIL if available
            state_before = None
            state_after = None
            
            if state_before_img is not None:
                try:
                    if isinstance(state_before_img, Image.Image):
                        state_before = state_before_img
                    else:
                        # Handle different image formats from HuggingFace
                        state_before = Image.open(io.BytesIO(state_before_img))
                except:
                    pass
            
            if state_after_img is not None:
                try:
                    if isinstance(state_after_img, Image.Image):
                        state_after = state_after_img
                    else:
                        state_after = Image.open(io.BytesIO(state_after_img))
                except:
                    pass
            
            # Create step
            step = OfflineStep(
                task_id=task_id,
                website=website,
                domain=domain,
                confirmed_task=confirmed_task,
                step_number=step_number,
                annotation_id=f"{task_id}_step_{step_number}",
                action_type=operation_type,
                action_target=action_target,
                action_uid=action_uid,
                action_coords=None,  # Will be computed from bbox if needed
                action_text=action.get("value", None),
                state_before=state_before,
                state_after=state_after,
                target_bbox=target_bbox,
                candidate_bboxes=candidate_bboxes,
                url_before="",  # Not always available in dataset
                url_after="",
                is_valid=True
            )
            
            # Validation
            validation_errors = []
            if not state_before:
                validation_errors.append("Missing state_before screenshot")
            if not state_after:
                validation_errors.append("Missing state_after screenshot")
            if not target_bbox:
                validation_errors.append("Missing target_bbox")
            
            step.validation_errors = validation_errors
            step.is_valid = len(validation_errors) == 0
            
            return step
            
        except Exception as e:
            logger.warning(f"Failed to parse step {step_number}: {e}")
            return None
    
    def get_dataset_info(self) -> Dict[str, Any]:
        """
        Get dataset information and statistics.
        
        Returns:
            Dictionary with dataset metadata
        """
        if self.dataset is None:
            return {"error": "Dataset not loaded"}
        
        info = {
            "dataset_name": "osunlp/Multimodal-Mind2Web",
            "cache_dir": str(self.cache_dir),
            "splits": {},
        }
        
        # Handle both regular and streaming datasets
        if self.use_streaming:
            # Streaming mode - single split
            info["splits"]["train"] = {
                "num_samples": "Unknown (streaming)",
                "features": list(self.dataset.features.keys()) if hasattr(self.dataset, "features") else []
            }
        else:
            # Regular mode - multiple splits with .items()
            for split_name, split_data in self.dataset.items():
                info["splits"][split_name] = {
                    "num_samples": len(split_data),
                    "features": list(split_data.features.keys()) if hasattr(split_data, "features") else []
                }
        
        return info
    
    def validate_dataset(self, split: str = "train", num_samples: int = 10) -> Dict[str, Any]:
        """
        Validate dataset integrity by checking a sample of trajectories.
        
        Args:
            split: Dataset split to validate
            num_samples: Number of samples to check
            
        Returns:
            Validation report
        """
        logger.info(f"Validating {num_samples} samples from {split} split...")
        
        trajectories = self.load_trajectories(split=split, limit=num_samples)
        
        report = {
            "total_trajectories": len(trajectories),
            "total_steps": sum(t.num_steps for t in trajectories),
            "valid_steps": 0,
            "invalid_steps": 0,
            "missing_screenshots": 0,
            "missing_bboxes": 0,
            "validation_errors": []
        }
        
        for traj in trajectories:
            for step in traj.steps:
                if step.is_valid:
                    report["valid_steps"] += 1
                else:
                    report["invalid_steps"] += 1
                    report["validation_errors"].extend(step.validation_errors)
                
                if not step.state_before or not step.state_after:
                    report["missing_screenshots"] += 1
                if not step.target_bbox:
                    report["missing_bboxes"] += 1
        
        # Calculate percentages
        total_steps = report["total_steps"]
        if total_steps > 0:
            report["valid_step_percentage"] = (report["valid_steps"] / total_steps) * 100
            report["screenshot_coverage"] = (
                (total_steps - report["missing_screenshots"]) / total_steps
            ) * 100
            report["bbox_coverage"] = (
                (total_steps - report["missing_bboxes"]) / total_steps
            ) * 100
        
        logger.info(f"✅ Validation complete:")
        logger.info(f"  Valid steps: {report['valid_steps']}/{total_steps} ({report.get('valid_step_percentage', 0):.1f}%)")
        logger.info(f"  Screenshot coverage: {report.get('screenshot_coverage', 0):.1f}%")
        logger.info(f"  Bbox coverage: {report.get('bbox_coverage', 0):.1f}%")
        
        return report
