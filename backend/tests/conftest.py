"""Test configuration — add backend/ to sys.path for module imports."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
