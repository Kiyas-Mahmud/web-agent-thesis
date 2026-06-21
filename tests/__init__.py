"""
Test configuration and pytest settings
"""

import sys
from pathlib import Path

# Add src to Python path for tests
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))
