# test_backend.py - Automated verification test suite
import sys
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def run_tests():
    print("Running NL2SQL Backend API test suite...")

    # 1. Health check
    res = client.get("/")
    assert res.status_code == 200, f"Root failed: {res.text}"
    print("[OK] Root health check passed:", res.json()["service"])

    # 2. Schema check
    res = client.get("/api/schema/mysql")
    assert res.status_code == 200, f"Schema failed: {res.text}"
    data = res.json()
    assert len(data["tables"]) == 4, "Expected 4 tables"
    assert len(data["foreign_keys"]) == 3, "Expected 3 FKs"
    print("[OK] Schema endpoint passed (4 tables, 3 FKs)")

    # 3. SELECT query check (Auto mode)
    res = client.post("/api/query", json={
        "user_id": "test_vanshika",
        "query_text": "Show me all orders from last month",
        "target_dialect": "auto",
        "database_profile": "master_enterprise"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["result_data"]["row_count"] == 5
    select_query_id = data["query_id"]
    print("[OK] SELECT Query intake passed in Auto mode (status=completed, rows=5)")

    # 4. UPDATE query check (Gate trigger)
    res = client.post("/api/query", json={
        "user_id": "test_vanshika",
        "query_text": "Increase all product prices by 10%",
        "target_dialect": "postgres",
        "database_profile": "master_enterprise"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "approval_required"
    assert data["approval_payload"]["risk_tier"] == "high"
    print("[OK] UPDATE Query approval gate triggered (status=approval_required, risk=high)")

    # 5. DDL query check (DDL Diff trigger)
    res = client.post("/api/query", json={
        "user_id": "test_vanshika",
        "query_text": "Add a discount_code column to orders table",
        "target_dialect": "postgres",
        "database_profile": "master_enterprise"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "approval_required"
    assert data["approval_payload"]["diff_data"]["diff_type"] == "ddl"
    print("[OK] DDL Query approval gate triggered (status=approval_required, diff=ddl)")

    # 6. Approval decision endpoint
    query_id = data["query_id"]
    res = client.post(f"/api/approval/{query_id}", json={
        "query_id": query_id,
        "decision": "approve",
        "feedback": "LGTM",
        "user_id": "test_vanshika"
    })
    assert res.status_code == 200
    assert res.json()["status"] == "approved_executing"
    print("[OK] Approval decision passed (status=approved_executing)")

    # 7. Query history check
    res = client.get("/api/query/history/test_vanshika")
    assert res.status_code == 200
    hist = res.json()
    assert len(hist) >= 3
    print(f"[OK] Query history passed ({len(hist)} items logged)")

    # 8. Selective History Deletion check
    res = client.delete(f"/api/query/history/test_vanshika/{select_query_id}")
    assert res.status_code == 200
    res = client.get("/api/query/history/test_vanshika")
    updated_hist = res.json()
    assert len(updated_hist) == len(hist) - 1
    print("[OK] Selective single query deletion passed")

    # 9. Clear All History check
    res = client.delete("/api/query/history/test_vanshika")
    assert res.status_code == 200
    res = client.get("/api/query/history/test_vanshika")
    assert len(res.json()) == 0
    print("[OK] Clear all history passed")

    print("\nALL BACKEND ENDPOINTS AND INTEGRATION STUBS VERIFIED 100% OPERATIONAL!")

if __name__ == "__main__":
    run_tests()
