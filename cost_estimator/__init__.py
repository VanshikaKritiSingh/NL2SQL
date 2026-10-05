"""Cost Estimator (pure contract + structure for validator reuse).

Uses validator contracts: Issue / ValidationResult / RetryFeedback.
Pulls from validator/contracts.py.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from validator.contracts import ValidationResult, RetryFeedback, Issue
