"""M10 — Cost Estimator (draft contract + structure for M9 reuse).

Uses M9 contracts: Issue / ValidationResult / RetryFeedback.
Pulls from m09_validator/contracts.py.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from m09_validator.contracts import ValidationResult, RetryFeedback, Issue
