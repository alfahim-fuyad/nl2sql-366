# tests/conftest.py

import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(ROOT_DIR, "core")

sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, CORE_DIR)
