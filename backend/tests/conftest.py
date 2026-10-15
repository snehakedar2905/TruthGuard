"""Pytest configuration and environment fixtures for TruthGuard."""

import os
import sys

# Ensure backend directory is in python search path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
