# DBMS Connectors & Live Socket Quickstart Guide

This document provides exact connection parameters, default ports, required pip packages, and sample attach payloads for every supported database connector in the NL2SQL engine.

---

## 1. Supported DBMS Matrix

| DBMS | Connector Type | Default Port | Driver / Package | Query Dialect |
|---|---|---|---|---|
| **SQLite** | `sqlite` | N/A (embedded) | Standard library (`sqlite3`) | SQLite SQL |
| **PostgreSQL** | `postgres` | `5432` | `psycopg2` / `psycopg` | PostgreSQL |
| **MySQL** | `mysql` | `3306` | `pymysql` / `mysql-connector-python` | MySQL |
| **DuckDB** | `duckdb` | N/A (in-process) | `duckdb` | DuckDB OLAP SQL |
| **ClickHouse** | `clickhouse` | `8123` | Stdlib HTTP (`urllib`) | ClickHouse SQL |
| **MongoDB** | `mongodb` | `27017` | `pymongo` | MongoDB MQL / Aggregation |
| **Neo4j** | `neo4j` | `7687` | `neo4j` (Bolt) | openCypher |
| **Redis** | `redis` | `6379` | `redis` | Redis CLI commands |
| **Cassandra** | `cassandra` | `9042` | `cassandra-driver` | CQL |
| **DynamoDB** | `dynamodb` | `8000` / AWS | `boto3` | PartiQL SQL |

---

## 2. Attaching a Database (REST API)

### SQLite (Embedded / Local File or In-Memory)
```bash
curl -X POST http://127.0.0.1:8000/api/connections/attach \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_alice",
    "connector_type": "sqlite",
    "database": ":memory:"
  }'
```

### PostgreSQL
```bash
curl -X POST http://127.0.0.1:8000/api/connections/attach \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_alice",
    "connector_type": "postgres",
    "host": "localhost",
    "port": 5432,
    "database": "production_db",
    "username": "pg_user",
    "password": "your_secure_password",
    "ssl_mode": "prefer"
  }'
```

### MySQL
```bash
curl -X POST http://127.0.0.1:8000/api/connections/attach \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_alice",
    "connector_type": "mysql",
    "host": "127.0.0.1",
    "port": 3306,
    "database": "ecommerce",
    "username": "root",
    "password": "password"
  }'
```

### MongoDB
```bash
curl -X POST http://127.0.0.1:8000/api/connections/attach \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_alice",
    "connector_type": "mongodb",
    "host": "127.0.0.1",
    "port": 27017,
    "database": "analytics_logs"
  }'
```

### Neo4j Graph Database
```bash
curl -X POST http://127.0.0.1:8000/api/connections/attach \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_alice",
    "connector_type": "neo4j",
    "host": "localhost",
    "port": 7687,
    "database": "neo4j",
    "username": "neo4j",
    "password": "neo4j_password"
  }'
```

### Redis Key-Value Store
```bash
curl -X POST http://127.0.0.1:8000/api/connections/attach \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_alice",
    "connector_type": "redis",
    "host": "127.0.0.1",
    "port": 6379,
    "database": "0"
  }'
```

---

## 3. Schema Introspection & Detach

### Introspect Live Schema from Attached Socket:
```bash
curl http://127.0.0.1:8000/api/connections/schema/user_alice
```

### Detach Database:
```bash
curl -X DELETE http://127.0.0.1:8000/api/connections/user_alice
```
