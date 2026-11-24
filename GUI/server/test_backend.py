# test_backend.py - Automated verification test suite
import sys
from fastapi.testclient import TestClient
from main import app, API_AUTH_TOKEN

client = TestClient(app, headers={"Authorization": f"Bearer {API_AUTH_TOKEN}"})

def testBackendApiEndpointsAndIntegrationLifecycle():
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

    # 4. Disconnected Mutating Query check (No DBMS connected -> No human approval gate!)
    res_disc = client.post("/api/query", json={
        "user_id": "test_vanshika",
        "query_text": "Increase all product prices by 10%",
        "target_dialect": "postgres",
        "database_profile": "master_enterprise"
    })
    assert res_disc.status_code == 200
    disc_data = res_disc.json()
    assert disc_data["status"] == "completed", f"Expected completed, got {disc_data['status']}"
    assert disc_data["approval_payload"] is None
    print("[OK] Disconnected mutating query passed directly without approval gate (status=completed, no live commit target)")

    # Attach a live socket for subsequent live DB tests
    attach_res = client.post("/api/connections/attach", json={
        "user_id": "test_vanshika",
        "connector_type": "sqlite",
        "database": ":memory:"
    })
    assert attach_res.status_code == 200
    assert attach_res.json()["ok"] is True

    # 5. Connected DDL query check (Live DBMS attached -> Gate triggers!)
    res = client.post("/api/query", json={
        "user_id": "test_vanshika",
        "query_text": "Create a new table called audit_records with id and notes",
        "target_dialect": "sqlite",
        "database_profile": ":memory:"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "approval_required"
    assert data["approval_payload"]["diff_data"]["diff_type"] == "ddl"
    print("[OK] DDL Query approval gate triggered on live DBMS (status=approval_required, diff=ddl)")

    # 6. Approval decision endpoint (approve execution on live DBMS)
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

    # 8. Query history check
    res = client.get("/api/query/history/test_vanshika")
    assert res.status_code == 200
    hist = res.json()
    assert len(hist) >= 3
    print(f"[OK] Query history passed ({len(hist)} items logged)")

    # 9. Selective History Deletion check
    res = client.delete(f"/api/query/history/test_vanshika/{select_query_id}")
    assert res.status_code == 200
    res = client.get("/api/query/history/test_vanshika")
    updated_hist = res.json()
    assert len(updated_hist) == len(hist) - 1
    print("[OK] Selective single query deletion passed")

    # 10. Clear All History check
    res = client.delete("/api/query/history/test_vanshika")
    assert res.status_code == 200
    res = client.get("/api/query/history/test_vanshika")
    assert len(res.json()) == 0
    print("[OK] Clear all history passed")

    # Detach test socket
    client.post("/api/connections/detach", json={"user_id": "test_vanshika"})

    # 10. Myspire Connector Dependencies & Connection tests
    res = client.get("/api/connections/check-deps/sqlite")
    assert res.status_code == 200
    assert res.json()["all_installed"] is True
    print("[OK] Check deps (sqlite) passed:", res.json()["message"])

    res = client.get("/api/connections/check-deps/mysql")
    assert res.status_code == 200
    print("[OK] Check deps (mysql) passed, all_installed:", res.json()["all_installed"])

    res = client.post("/api/connections/install-deps", json={"connector_type": "sqlite"})
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert res.json()["already_installed"] is True
    print("[OK] Install deps (sqlite auto-setup) passed")

    res = client.post("/api/connections/test", json={
        "connector_type": "sqlite",
        "database": ":memory:"
    })
    assert res.status_code == 200
    assert res.json()["ok"] is True
    print("[OK] Test connection (sqlite :memory:) passed, dialect:", res.json()["dialect"])

    print("\nALL BACKEND ENDPOINTS AND INTEGRATION STUBS VERIFIED 100% OPERATIONAL!")

if __name__ == "__main__":
    testBackendApiEndpointsAndIntegrationLifecycle()
