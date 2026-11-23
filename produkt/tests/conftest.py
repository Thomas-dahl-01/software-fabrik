"""Gør modulerne i produkt/ importérbare fra testene."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
