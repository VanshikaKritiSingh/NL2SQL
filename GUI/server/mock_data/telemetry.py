# mock_data/telemetry.py
from models.approval import CostEstimate, SecurityCheck


def get_mock_select_telemetry():
    cost = CostEstimate(
        estimated_rows=5,
        estimated_cost=1.25,
        scan_type="index_scan",
        warnings=[],
    )
    security = SecurityCheck(
        deadlock_risk="none",
        lock_level="row",
        privilege_ok=True,
        flags=["READ_ONLY", "SANDBOX_EXECUTABLE"],
    )
    return cost, security


def get_mock_update_telemetry():
    cost = CostEstimate(
        estimated_rows=150,
        estimated_cost=42.50,
        scan_type="full_table_scan",
        warnings=[
            "Full table scan on products table without WHERE clause",
            "Updates 150 rows in a single statement",
        ],
    )
    security = SecurityCheck(
        deadlock_risk="medium",
        lock_level="table",
        privilege_ok=True,
        flags=[
            "MUTATING_OPERATION",
            "CASCADE_LOCKS_POSSIBLE",
            "DOLT_CHECKPOINT_REQUIRED",
        ],
    )
    return cost, security


def get_mock_ddl_telemetry():
    cost = CostEstimate(
        estimated_rows=12000,
        estimated_cost=180.00,
        scan_type="full_table_scan",
        warnings=[
            "ALTER TABLE requires exclusive metadata lock on orders table",
            "Table contains 12,000 active rows",
        ],
    )
    security = SecurityCheck(
        deadlock_risk="high",
        lock_level="schema",
        privilege_ok=True,
        flags=[
            "DDL_SCHEMA_MODIFICATION",
            "EXCLUSIVE_METADATA_LOCK",
            "REPLICATION_LAG_RISK",
            "MIGRATION_VERSION_BUMP",
        ],
    )
    return cost, security
