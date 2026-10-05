#!/usr/bin/env python3
"""
scripts/generate_dataset.py: CLI Entrypoint for Local Fine-Tuning Dataset Generation

Generates synthetic Text-to-Universal-SQL training & evaluation datasets locally.
The generated files are created in `offline/datasets/` and are strictly excluded from git.
"""

import os
import sys

# Ensure repository root is on PYTHONPATH
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from offline.datasets.prepare_dataset import main

if __name__ == "__main__":
    main()
