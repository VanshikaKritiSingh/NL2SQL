"""cost_estimator — Query Cost Estimation and Blast-Radius Evaluation Subsystem.

Provides:
1. `HeuristicCostEngine`: AST-based analytical cost & row scan estimator.
2. `PostgresAdapter`: Live PostgreSQL EXPLAIN JSON parser.
3. `Thresholds`: Configurable decision thresholds.
4. `CostReport`: Normalized cost and risk assessment report.
"""

from .contracts import CostReport, PlanAdapter, PlanRunner, SchemaProvider
from .thresholds import Thresholds, ThresholdsError, load_thresholds, DEFAULT_THRESHOLDS
from .engine import HeuristicCostEngine

__all__ = [
    "CostReport",
    "PlanAdapter",
    "PlanRunner",
    "SchemaProvider",
    "Thresholds",
    "ThresholdsError",
    "load_thresholds",
    "DEFAULT_THRESHOLDS",
    "HeuristicCostEngine",
]
