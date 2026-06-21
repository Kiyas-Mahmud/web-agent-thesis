"""
Dataset Parsers

Parsers for different data sources that normalize tasks into the unified schema.
"""

from typing import List, Optional, Dict, Any
import logging
from pathlib import Path
from abc import ABC, abstractmethod
import os

from .task_schema import Task, TaskMetadata, TaskSource, TaskDifficulty, TaskCategory

logger = logging.getLogger(__name__)


def _load_hf_token():
    """Load HF_TOKEN from .env file if not already in environment."""
    if os.environ.get("HF_TOKEN"):
        return  # already set
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("HF_TOKEN=") and not line.startswith("#"):
                token = line.split("=", 1)[1].strip()
                if token and token != "your_token_here":
                    os.environ["HF_TOKEN"] = token
                    logger.info("HF_TOKEN loaded from .env")
                break


_load_hf_token()


class BaseParser(ABC):
    """Base class for dataset parsers"""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def parse(self) -> List[Task]:
        """Parse dataset and return list of Task objects"""
        pass
    
    @abstractmethod
    def download(self) -> bool:
        """Download dataset if needed"""
        pass


class MiniWoBParser(BaseParser):
    """
    Parser for MiniWoB++ tasks (local environment).
    https://github.com/Farama-Foundation/miniwob-plusplus

    MiniWoB++ tasks are tiny HTML pages served by a local web server.
    This parser does NOT scrape HuggingFace — it generates Task objects
    from the known MiniWoB task catalog, pointing start_url at the local server.

    Role in the thesis pipeline:
      Controlled failure laboratory. Tasks are simple and deterministic,
      making them ideal for testing loop detection, wrong-click recovery,
      and action-mismatch labeling.

    Usage:
      1. Start MiniWoB server: `python -m miniwob.server --port 7860`
         (or use the Gymnasium env which serves HTML pages automatically)
      2. Call parser.parse() to get Task objects
      3. Tasks will have start_url = "http://localhost:{port}/miniwob/{name}.html"
    """

    # Curated subset of MiniWoB tasks grouped by failure type they exercise
    TASK_CATALOG = [
        # Navigation / click failures
        {"name": "click-button",         "desc": "Click the button to proceed.",          "category": "navigation"},
        {"name": "click-button-sequence", "desc": "Click buttons in the correct sequence.", "category": "navigation"},
        {"name": "click-checkboxes",      "desc": "Check all the checkboxes.",             "category": "interaction"},
        {"name": "click-dialog",          "desc": "Close the dialog by clicking the button.", "category": "interaction"},
        {"name": "click-link",            "desc": "Click the link that matches the text.",  "category": "navigation"},
        {"name": "click-option",          "desc": "Select the option from the dropdown.",   "category": "interaction"},
        {"name": "click-tab",             "desc": "Click the correct tab.",                "category": "navigation"},
        {"name": "click-test",            "desc": "Click the element on the page.",         "category": "interaction"},
        {"name": "click-widget",          "desc": "Click the widget with the given label.",  "category": "interaction"},
        # Form filling failures
        {"name": "enter-date",            "desc": "Enter the date in the form field.",      "category": "form_filling"},
        {"name": "enter-password",        "desc": "Enter the password in the input field.", "category": "form_filling"},
        {"name": "enter-text",            "desc": "Type the given text into the input.",    "category": "form_filling"},
        {"name": "enter-text-dynamic",    "desc": "Type the dynamically shown text.",       "category": "form_filling"},
        {"name": "enter-time",            "desc": "Enter the time into the input field.",   "category": "form_filling"},
        {"name": "focus-text",            "desc": "Click and focus the text field.",        "category": "form_filling"},
        {"name": "focus-text-2",          "desc": "Click and focus the correct text area.", "category": "form_filling"},
        # Search failures
        {"name": "search-engine",         "desc": "Use the search box to find the item.",  "category": "search"},
        {"name": "find-word",             "desc": "Find and click the specified word.",     "category": "search"},
        # Multi-step / loop-prone
        {"name": "book-flight",           "desc": "Book a flight with the given parameters.", "category": "form_filling"},
        {"name": "count-shape",           "desc": "Count the shapes and enter the number.",  "category": "interaction"},
        {"name": "use-slider",            "desc": "Drag the slider to the target value.",   "category": "interaction"},
        {"name": "use-spinner",           "desc": "Adjust the spinner to the target value.", "category": "interaction"},
        {"name": "email-inbox",           "desc": "Manage the inbox: read or delete emails.","category": "interaction"},
        {"name": "login-user",            "desc": "Log in with the given credentials.",     "category": "form_filling"},
        {"name": "navigate-tree",         "desc": "Navigate the tree to the target node.",  "category": "navigation"},
    ]

    def __init__(self, cache_dir: str, port: int = 7860, task_limit: int = 200):
        super().__init__(cache_dir)
        self.port = port
        self.task_limit = task_limit
        self.base_url = f"http://localhost:{port}/miniwob"

    def download(self) -> bool:
        """MiniWoB++ tasks are local — nothing to download."""
        return True

    def parse(self) -> List[Task]:
        """
        Generate Task objects from the MiniWoB task catalog.
        Each task points at the local MiniWoB server URL.
        """
        _cat_map = {
            "navigation":    TaskCategory.NAVIGATION,
            "form_filling":  TaskCategory.FORM_FILLING,
            "search":        TaskCategory.SEARCH,
            "interaction":   TaskCategory.INTERACTION,
        }

        tasks: List[Task] = []
        catalog = self.TASK_CATALOG[: self.task_limit]

        for idx, entry in enumerate(catalog):
            name = entry["name"]
            metadata = TaskMetadata(
                source=TaskSource.MINIWOB,
                difficulty=TaskDifficulty.EASY,
                category=_cat_map.get(entry["category"], TaskCategory.OTHER),
                original_id=name,
                additional_info={
                    "task_name": name,
                    "port": self.port,
                    "environment": "miniwob",
                },
            )
            tasks.append(Task(
                task_id=f"miniwob-{idx:05d}",
                task_description=entry["desc"],
                website_domain=f"localhost:{self.port}",
                start_url=f"{self.base_url}/{name}.html",
                metadata=metadata,
            ))

        logger.info(
            f"Generated {len(tasks)} MiniWoB tasks — "
            f"start MiniWoB server on port {self.port} before replaying"
        )
        return tasks



class Mind2WebParser(BaseParser):
    """
    Parser for Multimodal Mind2Web dataset from HuggingFace.
    https://huggingface.co/datasets/osunlp/Multimodal-Mind2Web

    Dataset structure (each row = ONE action step):
      annotation_id  — groups rows into a single task
      confirmed_task — human-readable task description
      website        — site name, e.g. "booking.com"
      domain         — high-level domain, e.g. "Travel"
      operation      — {op: CLICK|TYPE|SELECT, value: str}
      pos_candidates — list of {tag, attributes (JSON str), backend_node_id}

    Strategy: stream rows, group by annotation_id, emit one Task per group.
    No data is downloaded — only text fields are consumed from the stream.
    """

    def __init__(self, cache_dir: str, split: str = "train", task_limit: int = 200):
        super().__init__(cache_dir)
        self.dataset_name = "osunlp/Multimodal-Mind2Web"
        self.split = split
        self.task_limit = task_limit   # max number of TASKS (not rows) to collect
        self._dataset = None

    def download(self) -> bool:
        """Open a streaming connection to Mind2Web (no full download)."""
        try:
            from datasets import load_dataset

            logger.info(f"Opening streaming connection to {self.dataset_name} [{self.split}]...")
            self._dataset = load_dataset(
                self.dataset_name,
                split=self.split,
                streaming=True,
            )
            logger.info("Streaming connection established.")
            return True
        except Exception as e:
            logger.error(f"Error connecting to {self.dataset_name}: {e}")
            return False

    def parse(self) -> List[Task]:
        """
        Stream rows from Mind2Web, group by annotation_id, return Task list.

        Each Task carries:
          - task_id            : "mind2web-<annotation_id>"
          - task_description   : confirmed_task text
          - start_url          : https://<website>
          - website_domain     : domain field (e.g. "Travel")
          - metadata.raw_actions: list of raw operation dicts for the replay layer
        """
        if self._dataset is None:
            if not self.download():
                return []

        # Group rows by annotation_id
        # Dict[annotation_id -> dict with task info + accumulated actions]
        task_map: Dict[str, Dict[str, Any]] = {}
        order: List[str] = []   # preserve insertion order

        try:
            for row in self._dataset:
                try:
                    ann_id = row.get("annotation_id", "")
                    if not ann_id:
                        continue

                    if ann_id not in task_map:
                        if len(task_map) >= self.task_limit:
                            break
                        task_map[ann_id] = {
                            "annotation_id": ann_id,
                            "confirmed_task": row.get("confirmed_task", ""),
                            "website": row.get("website", ""),
                            "domain": row.get("domain", "unknown"),
                            "subdomain": row.get("subdomain", ""),
                            "actions": [],
                        }
                        order.append(ann_id)

                    # Accumulate action — operation may be a dict or a JSON string
                    raw_op = row.get("operation", {}) or {}
                    if isinstance(raw_op, str):
                        try:
                            import json as _json
                            raw_op = _json.loads(raw_op)
                        except Exception:
                            raw_op = {}
                    pos = row.get("pos_candidates", []) or []
                    task_map[ann_id]["actions"].append({
                        "op": raw_op.get("op", ""),
                        "value": raw_op.get("value", ""),
                        "pos_candidates": pos,
                        "action_uid": row.get("action_uid", ""),
                    })
                except Exception as row_err:
                    logger.debug(f"Skipping malformed row: {row_err}")
                    continue

        except Exception as e:
            logger.error(f"Error streaming Mind2Web: {e}")

        # Convert grouped data to Task objects
        tasks: List[Task] = []
        for idx, ann_id in enumerate(order):
            entry = task_map[ann_id]
            raw_actions = entry["actions"]

            website = entry["website"].strip()
            if website.startswith("http"):
                start_url = website
            elif website:
                # Mind2Web stores bare names like "united", "ign", "discogs".
                # Add .com when there is no dot in the name.
                domain = website if "." in website else f"{website}.com"
                start_url = f"https://www.{domain}"
            else:
                start_url = "https://example.com"

            metadata = TaskMetadata(
                source=TaskSource.MIND2WEB,
                difficulty=self._classify_difficulty(len(raw_actions)),
                category=self._classify_category(entry["confirmed_task"]),
                domain_category=entry["domain"],
                original_id=ann_id,
                additional_info={
                    "subdomain": entry["subdomain"],
                    "raw_actions": raw_actions,
                    "action_count": len(raw_actions),
                },
            )

            task = Task(
                task_id=f"mind2web-{idx:05d}",
                task_description=entry["confirmed_task"],
                website_domain=entry["domain"],
                start_url=start_url,
                metadata=metadata,
            )
            tasks.append(task)

        logger.info(f"Parsed {len(tasks)} tasks from Mind2Web (streamed, no download)")
        return tasks

    # ── helpers ──────────────────────────────────────────────────────────────

    def _classify_difficulty(self, num_actions: int) -> TaskDifficulty:
        if num_actions <= 3:
            return TaskDifficulty.EASY
        elif num_actions <= 7:
            return TaskDifficulty.MEDIUM
        return TaskDifficulty.HARD

    def _classify_category(self, task_description: str) -> TaskCategory:
        desc_lower = task_description.lower()
        if any(w in desc_lower for w in ["search", "find", "look for"]):
            return TaskCategory.SEARCH
        elif any(w in desc_lower for w in ["form", "submit", "register", "fill"]):
            return TaskCategory.FORM_FILLING
        elif any(w in desc_lower for w in ["shop", "buy", "cart", "purchase"]):
            return TaskCategory.SHOPPING
        elif any(w in desc_lower for w in ["information", "details", "show", "check"]):
            return TaskCategory.INFORMATION_RETRIEVAL
        return TaskCategory.INTERACTION


class WebArenaParser(BaseParser):
    """
    Parser for WebArena task configurations.
    https://github.com/web-arena-x/webarena

    WebArena tasks are complex, long-horizon tasks across realistic web apps
    (fake Reddit, GitLab, shopping site). Executing them requires running
    the WebArena Docker environment.

    THIS PARSER: reads task config JSON files from GitHub only.
    It outputs Task objects with task_description + start_url
    but does NOT execute the Docker environment.

    Role in the thesis pipeline:
      Long-horizon evaluation — use task descriptions + start URLs to plan
      trajectories once the environment is available.

    Config files live at:
      https://github.com/web-arena-x/webarena/tree/main/config_files
    Each file: task_id, intent, start_url, sites[], require_login, ...
    """

    TASK_CONFIG_URL = (
        "https://raw.githubusercontent.com/web-arena-x/webarena/"
        "main/config_files/test.raw.json"
    )

    def __init__(self, cache_dir: str, task_limit: int = 200):
        super().__init__(cache_dir)
        self.task_limit = task_limit
        self._raw: List[Dict[str, Any]] = []
        self._cache_file = self.cache_dir / "webarena_tasks.json"

    def download(self) -> bool:
        """Download WebArena task config JSON from GitHub (text only, no Docker)."""
        # Return cached copy if available
        if self._cache_file.exists():
            try:
                import json as _json
                self._raw = _json.loads(self._cache_file.read_text(encoding="utf-8"))
                logger.info(f"WebArena tasks loaded from cache ({len(self._raw)} tasks)")
                return True
            except Exception:
                pass  # re-download

        try:
            import urllib.request
            logger.info(f"Downloading WebArena task configs from GitHub...")
            with urllib.request.urlopen(self.TASK_CONFIG_URL, timeout=30) as resp:
                import json as _json
                self._raw = _json.loads(resp.read().decode("utf-8"))
            self._cache_file.write_text(
                __import__("json").dumps(self._raw, indent=2), encoding="utf-8"
            )
            logger.info(f"Downloaded {len(self._raw)} WebArena task configs")
            return True
        except Exception as e:
            logger.warning(
                f"Could not download WebArena configs ({e}). "
                f"Using built-in fallback task list."
            )
            self._raw = self._fallback_tasks()
            return True

    def parse(self) -> List[Task]:
        """Convert raw WebArena config dicts into Task objects."""
        if not self._raw:
            self.download()

        tasks: List[Task] = []
        for idx, cfg in enumerate(self._raw[: self.task_limit]):
            task_desc = cfg.get("intent", cfg.get("task", ""))
            start_url  = cfg.get("start_url", "")
            sites      = cfg.get("sites", [])
            domain     = sites[0] if sites else "webarena"

            from urllib.parse import urlparse as _up
            parsed = _up(start_url)
            domain_str = parsed.netloc or domain or "webarena"

            metadata = TaskMetadata(
                source=TaskSource.WEBARENA,
                difficulty=TaskDifficulty.HARD,
                category=self._classify_category(task_desc),
                domain_category=domain,
                original_id=str(cfg.get("task_id", idx)),
                additional_info={
                    "sites": sites,
                    "require_login": cfg.get("require_login", False),
                    "require_reset": cfg.get("require_reset", False),
                    "environment": "webarena-docker",
                },
            )
            tasks.append(Task(
                task_id=f"webarena-{idx:05d}",
                task_description=task_desc,
                website_domain=domain_str,
                start_url=start_url or "http://localhost:9999",
                metadata=metadata,
            ))

        logger.info(f"Parsed {len(tasks)} WebArena tasks (config-only, no Docker needed)")
        return tasks

    def _classify_category(self, desc: str) -> TaskCategory:
        d = desc.lower()
        if any(w in d for w in ["search", "find", "look for"]): return TaskCategory.SEARCH
        if any(w in d for w in ["post", "submit", "fill", "create"]): return TaskCategory.FORM_FILLING
        if any(w in d for w in ["buy", "order", "cart"]): return TaskCategory.SHOPPING
        if any(w in d for w in ["navigate", "go to", "open"]): return TaskCategory.NAVIGATION
        return TaskCategory.INTERACTION

    def _fallback_tasks(self) -> List[Dict[str, Any]]:
        """Minimal built-in task list used when GitHub is unreachable."""
        return [
            {"task_id": 0,  "intent": "Find the cheapest product in the store.",       "start_url": "http://localhost:7770", "sites": ["shopping"]},
            {"task_id": 1,  "intent": "Post a comment on the top Reddit thread.",       "start_url": "http://localhost:9999", "sites": ["reddit"]},
            {"task_id": 2,  "intent": "Create a new issue in the repository.",          "start_url": "http://localhost:8023", "sites": ["gitlab"]},
            {"task_id": 3,  "intent": "Search for a user by their username.",           "start_url": "http://localhost:9999", "sites": ["reddit"]},
            {"task_id": 4,  "intent": "Find all open pull requests for a project.",      "start_url": "http://localhost:8023", "sites": ["gitlab"]},
            {"task_id": 5,  "intent": "Add item to cart and proceed to checkout.",      "start_url": "http://localhost:7770", "sites": ["shopping"]},
        ]
