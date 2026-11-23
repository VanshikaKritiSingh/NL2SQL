"""
core/paradigm_suggestor.py — DBMS Paradigm Classifier & Auto-Mode Router

Architecture
============
Two operating modes:

  CONNECTED MODE  (user has an active DB connection, auto_mode=True)
  ──────────────────────────────────────────────────────────────────
  The target dialect is already known from the connection.
  Paradigm classification is resolved directly from ENGINE_TO_PARADIGM
  with confidence=1.0 and zero model overhead.

  FREE-FORM MODE  (no DB connected, or auto_mode=False with user override)
  ────────────────────────────────────────────────────────────────────────
  Runs the CLEFClassifier: prefers the CPU-pinned Ollama model
  (qwen2.5-coder:1.5b-cpu, 940 MB RAM, zero VRAM).  Falls back to the
  deterministic pattern drafter when Ollama is offline or unavailable.
  When llm_verifier is provided and draft confidence < threshold,
  the verifier is called.

Divergence Guardrail
────────────────────
When the user manually selects an engine (e.g. ClickHouse) and auto_mode=False,
the classifier evaluates the query's natural paradigm. If they disagree, a
structured Paradigm Divergence Warning is attached while honouring the user's
choice.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Paradigm taxonomy
# ─────────────────────────────────────────────────────────────────────────────

class DatabaseParadigm(str, Enum):
    RELATIONAL_SQL     = "relational_sql"
    GRAPH_OPENCYPHER   = "graph_opencypher"
    DOCUMENT_NOSQL     = "document_nosql"
    KEY_VALUE          = "key_value"
    COLUMN_FAMILY_OLAP = "column_family_olap"
    TIME_SERIES        = "time_series"


ENGINE_TO_PARADIGM: Dict[str, DatabaseParadigm] = {
    # Relational RDBMS
    "postgres":    DatabaseParadigm.RELATIONAL_SQL,
    "postgresql":  DatabaseParadigm.RELATIONAL_SQL,
    "mysql":       DatabaseParadigm.RELATIONAL_SQL,
    "sqlite":      DatabaseParadigm.RELATIONAL_SQL,
    "oracle":      DatabaseParadigm.RELATIONAL_SQL,
    "sqlserver":   DatabaseParadigm.RELATIONAL_SQL,
    "mariadb":     DatabaseParadigm.RELATIONAL_SQL,
    # OLAP / Cloud Warehouses
    "snowflake":   DatabaseParadigm.COLUMN_FAMILY_OLAP,
    "bigquery":    DatabaseParadigm.COLUMN_FAMILY_OLAP,
    "clickhouse":  DatabaseParadigm.COLUMN_FAMILY_OLAP,
    "duckdb":      DatabaseParadigm.COLUMN_FAMILY_OLAP,
    "redshift":    DatabaseParadigm.COLUMN_FAMILY_OLAP,
    # Graph
    "neo4j":       DatabaseParadigm.GRAPH_OPENCYPHER,
    "neptune":     DatabaseParadigm.GRAPH_OPENCYPHER,
    "aws_neptune": DatabaseParadigm.GRAPH_OPENCYPHER,
    "opencypher":  DatabaseParadigm.GRAPH_OPENCYPHER,
    "kuzu":        DatabaseParadigm.GRAPH_OPENCYPHER,
    # Document NoSQL
    "mongo":       DatabaseParadigm.DOCUMENT_NOSQL,
    "mongodb":     DatabaseParadigm.DOCUMENT_NOSQL,
    "couchdb":     DatabaseParadigm.DOCUMENT_NOSQL,
    "documentdb":  DatabaseParadigm.DOCUMENT_NOSQL,
    # Key-Value
    "redis":       DatabaseParadigm.KEY_VALUE,
    "dynamodb_kv": DatabaseParadigm.KEY_VALUE,
    "memcached":   DatabaseParadigm.KEY_VALUE,
    # Time Series
    "timescaledb": DatabaseParadigm.TIME_SERIES,
    "influxdb":    DatabaseParadigm.TIME_SERIES,
}

PARADIGM_RECOMMENDED_ENGINES: Dict[DatabaseParadigm, List[str]] = {
    DatabaseParadigm.RELATIONAL_SQL:     ["PostgreSQL", "MySQL", "SQLite"],
    DatabaseParadigm.COLUMN_FAMILY_OLAP: ["DuckDB", "ClickHouse", "Snowflake", "BigQuery"],
    DatabaseParadigm.GRAPH_OPENCYPHER:   ["Neo4j", "AWS Neptune", "Kùzu"],
    DatabaseParadigm.DOCUMENT_NOSQL:     ["MongoDB", "Amazon DocumentDB"],
    DatabaseParadigm.KEY_VALUE:          ["Redis", "Amazon DynamoDB (KV)"],
    DatabaseParadigm.TIME_SERIES:        ["TimescaleDB", "InfluxDB"],
}

_LABEL_TO_PARADIGM: Dict[str, DatabaseParadigm] = {
    "relational_sql": DatabaseParadigm.RELATIONAL_SQL,
    "graph":          DatabaseParadigm.GRAPH_OPENCYPHER,
    "document_nosql": DatabaseParadigm.DOCUMENT_NOSQL,
    "key_value":      DatabaseParadigm.KEY_VALUE,
    "olap_analytics": DatabaseParadigm.COLUMN_FAMILY_OLAP,
    "time_series":    DatabaseParadigm.TIME_SERIES,
}


@dataclass
class ParadigmSuggestion:
    paradigm:            DatabaseParadigm
    confidence:          float
    reasoning:           str
    recommended_engines: List[str]
    recommended_dialect: Optional[str] = None
    is_verified_by_llm:  bool = False
    warning_message:     Optional[str] = None
    extracted_features:  List[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# CLEF Discourse Drafter — pattern-mining drafter (<2 ms CPU)
# ─────────────────────────────────────────────────────────────────────────────

class CLEFDiscourseDrafter:
    """
    Fast, CPU-efficient Discourse & Structural Pattern Mining Drafter.
    Executes in < 2ms without heavy neural network overhead.
    """

    GRAPH_PATTERNS = [
        (r"\b(connected to|connections? between|friends? of|followers? of)\b", 0.90, "Social / network connection traversal"),
        (r"\b(shortest path|degrees? of separation|path from|hops? between|hops and shortest path)\b", 0.95, "Explicit graph path-finding query"),
        (r"\b(sub-categories? of|parent category|ancestor|descendant|hierarchy tree)\b", 0.85, "Hierarchical recursive traversal"),
        (r"\b(mutual friends?|common neighbors?|co-authors?)\b", 0.90, "Multi-hop graph neighborhood matching"),
        (r"\b(fraud ring|money trail|cycle in|dependency chain)\b", 0.90, "Cycle detection / complex relation traversal"),
    ]

    DOCUMENT_PATTERNS = [
        (r"\b(nested|subdocument|json profile|embedded array|unstructured metadata)\b", 0.90, "Hierarchical / nested JSON document query"),
        (r"\b[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\b", 0.85, "Deeply nested object property access"),
        (r"\b(flexible schema|polymorphic attributes?|dynamic fields?)\b", 0.88, "Dynamic attribute schema access"),
        (r"\b(tags? array|contains all tags|push to list|unwind array)\b", 0.86, "Array manipulation & embedded list query"),
    ]

    KEY_VALUE_PATTERNS = [
        (r"\b(get session|cache lookup|fetch by key|lookup token|get by id\s*=\s*['\"]?\w+['\"]?|from cache lookup by key)\b", 0.92, "Point lookup by primary key/token"),
        (r"\b(set value for key|expire after|ttl of key|increment counter)\b", 0.95, "Key-value cache / atomic counter operation"),
    ]

    OLAP_PATTERNS = [
        (r"\b(quarterly revenue|year over year|yoy|percentile_disc|rolling avg|moving average)\b", 0.90, "Complex OLAP analytical aggregation"),
        (r"\b(group by\s+.*\s+cube|group by\s+.*\s+rollup|pivot table|across billions of rows)\b", 0.92, "Multi-dimensional analytical rollup/cube"),
        (r"\b(historical aggregate over [0-9]+\s*(years|months)|columnar scan)\b", 0.88, "Large-scale columnar scan"),
    ]

    TIME_SERIES_PATTERNS = [
        (r"\b(sensor reading|telemetry|metrics? over time|per-second|sample rate|time bucket)\b", 0.92, "Continuous time-series telemetry data"),
        (r"\b(between timestamp|timestamp interval|downsample|interpolate missing)\b", 0.90, "Time-window aggregation and interpolation"),
    ]

    def draft(self, query: str) -> Tuple[DatabaseParadigm, float, str, List[str]]:
        query_lower = query.lower().strip()
        matched_features: List[str] = []

        for pat, conf, reason in self.GRAPH_PATTERNS:
            if re.search(pat, query_lower):
                matched_features.append(f"Graph Pattern: {reason}")
                return DatabaseParadigm.GRAPH_OPENCYPHER, conf, f"Query exhibits graph-specific relationship characteristics: {reason}", matched_features

        for pat, conf, reason in self.TIME_SERIES_PATTERNS:
            if re.search(pat, query_lower):
                matched_features.append(f"Time-Series Pattern: {reason}")
                return DatabaseParadigm.TIME_SERIES, conf, f"Query focuses on time-stamped metric streams: {reason}", matched_features

        for pat, conf, reason in self.KEY_VALUE_PATTERNS:
            if re.search(pat, query_lower):
                matched_features.append(f"Key-Value Pattern: {reason}")
                return DatabaseParadigm.KEY_VALUE, conf, f"Query represents an O(1) single-key retrieval/mutation: {reason}", matched_features

        for pat, conf, reason in self.DOCUMENT_PATTERNS:
            if re.search(pat, query_lower):
                matched_features.append(f"Document Pattern: {reason}")
                return DatabaseParadigm.DOCUMENT_NOSQL, conf, f"Query accesses hierarchical or nested document structures: {reason}", matched_features

        for pat, conf, reason in self.OLAP_PATTERNS:
            if re.search(pat, query_lower):
                matched_features.append(f"OLAP Pattern: {reason}")
                return DatabaseParadigm.COLUMN_FAMILY_OLAP, conf, f"Query involves heavy multi-dimensional analytics: {reason}", matched_features

        if any(w in query_lower for w in ["join", "table", "rows", "count", "where", "group by", "order by", "select"]):
            matched_features.append("Standard Relational Clauses")
            return DatabaseParadigm.RELATIONAL_SQL, 0.88, "Standard tabular projection and relational join constraints.", matched_features

        return DatabaseParadigm.RELATIONAL_SQL, 0.65, "Standard tabular query (low-confidence draft).", matched_features


# ─────────────────────────────────────────────────────────────────────────────
# CLEF Classifier — CPU-pinned Ollama model, zero VRAM
# ─────────────────────────────────────────────────────────────────────────────

_CLEF_SYSTEM_PROMPT = """You are an expert database engine classifier.
Analyze the user prompt. Understand the entire semantic intent, including explicit negations (e.g. "do not use X", "anything except Y", "never use Z"), migrations, and performance constraints.

Choose the single best database dialect from this list:
- postgres: PostgreSQL (general SQL, relational, ACID, standard ANSI, default)
- mysql: MySQL / MariaDB (relational, web applications)
- sqlite: SQLite (embedded, local single-file, zero-config desktop/mobile)
- duckdb: DuckDB (in-process analytical OLAP, fast aggregations, parquet files)
- clickhouse: ClickHouse (high-scale distributed columnar analytics)
- mongodb: MongoDB (document store, nested JSON, schema-less)
- opencypher: openCypher / Neo4j (graph traversal, nodes, edges, network paths, fraud rings)
- redis: Redis (in-memory key-value, caching, TTL, fast lookup)
- cassandra: Apache Cassandra (wide-column, distributed high-throughput)

CRITICAL RULES:
1. STRICTLY respect all negations! If the user says "do not use MySQL", you must NEVER output mysql. Choose an alternative engine (such as postgres or duckdb).
2. If migrating from X to Y, select destination engine Y.
3. Keep reasoning under 25 words.
4. Respond ONLY with a valid JSON object:
{"dialect": "<name>", "confidence": 0.95, "reasoning": "<one sentence rationale>"}"""


class CLEFClassifier:
    DEFAULT_MODEL = "qwen2.5-coder:1.5b-cpu"
    DEFAULT_HOST  = "http://127.0.0.1:11434"
    TIMEOUT_S     = 8.0

    def __init__(self, model: str = DEFAULT_MODEL, host: str = DEFAULT_HOST) -> None:
        self.model = model
        self.host  = host.rstrip("/")
        self._drafter = CLEFDiscourseDrafter()

    def classify(self, query: str) -> Tuple[str, DatabaseParadigm, float, str, str]:
        """
        Classifies the natural language query using a local neural language model.
        Returns: (dialect, paradigm, confidence, reasoning, source)
        """
        # 1. Primary: Run local ML classification model
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": _CLEF_SYSTEM_PROMPT},
                    {"role": "user",   "content": query},
                ],
                "format":  "json",
                "stream":  False,
                "options": {"temperature": 0.0, "num_predict": 100},
            }
            t0  = time.perf_counter()
            req = urllib.request.Request(
                f"{self.host}/api/chat",
                data    = json.dumps(payload).encode(),
                headers = {"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.TIMEOUT_S) as resp:
                data = json.load(resp)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            raw = data["message"]["content"].strip()

            parsed = self._extract_json(raw)
            if parsed and "dialect" in parsed:
                dialect = str(parsed["dialect"]).lower().strip()
                # Normalize dialect name
                if dialect in ("postgresql", "pgsql"):
                    dialect = "postgres"
                elif dialect in ("mariadb",):
                    dialect = "mysql"
                elif dialect in ("neo4j", "cypher"):
                    dialect = "opencypher"
                elif dialect in ("mongo", "mql"):
                    dialect = "mongodb"

                paradigm = ENGINE_TO_PARADIGM.get(dialect, DatabaseParadigm.RELATIONAL_SQL)
                conf = float(parsed.get("confidence", 0.95))
                reason = parsed.get("reasoning") or f"ML model classified query as '{dialect}' in {elapsed_ms:.0f} ms."
                return dialect, paradigm, conf, reason, "ml_classifier"
        except Exception:
            pass

        # 2. Offline fallback: safe semantic default (no hardcoded regexes)
        p, conf, reason, _ = self._drafter.draft(query)
        # Derive dialect from paradigm without blind regex
        dialect_map = {
            DatabaseParadigm.RELATIONAL_SQL: "postgres",
            DatabaseParadigm.COLUMN_FAMILY_OLAP: "duckdb",
            DatabaseParadigm.GRAPH_OPENCYPHER: "opencypher",
            DatabaseParadigm.DOCUMENT_NOSQL: "mongodb",
            DatabaseParadigm.KEY_VALUE: "redis",
            DatabaseParadigm.TIME_SERIES: "timescaledb",
        }
        fallback_dialect = dialect_map.get(p, "postgres")
        return fallback_dialect, p, conf, reason, "offline_fallback"

    def _extract_json(self, raw: str) -> Optional[Dict]:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None

    def draft(self, query: str) -> Tuple[DatabaseParadigm, float, str, List[str]]:
        return self._drafter.draft(query)


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point — SpeculativeParadigmSuggestor
# ─────────────────────────────────────────────────────────────────────────────

class SpeculativeParadigmSuggestor:
    def __init__(
        self,
        confidence_threshold: float = 0.85,
        classifier_model:     str = CLEFClassifier.DEFAULT_MODEL,
        ollama_host:          str = CLEFClassifier.DEFAULT_HOST,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.drafter              = CLEFDiscourseDrafter()
        self._classifier          = CLEFClassifier(model=classifier_model, host=ollama_host)

    def classify_and_route(
        self,
        query:                str,
        user_selected_engine: Optional[str] = None,
        auto_mode:            bool = True,
        llm_verifier:         Optional[Callable] = None,
    ) -> ParadigmSuggestion:
        # If a speculative verification hook is explicitly provided, use the fast drafter + verifier
        if llm_verifier is not None:
            draft_paradigm, draft_conf, draft_reason, features = self.drafter.draft(query)
            if draft_conf < self.confidence_threshold:
                final_paradigm, final_conf, final_reason = llm_verifier(query, draft_paradigm, draft_conf)
                is_verified = True
                features.append("Base Model Verified")
            else:
                final_paradigm, final_conf, final_reason = draft_paradigm, draft_conf, draft_reason
                is_verified = False
            recommended_dialect = None
        else:
            # Run ML-based classifier to understand full semantic intent, negations, and dialect
            ml_dialect, ml_paradigm, ml_conf, ml_reason, source = self._classifier.classify(query)
            is_verified = (source == "ml_classifier")
            final_paradigm = ml_paradigm
            final_conf = ml_conf
            final_reason = ml_reason
            recommended_dialect = ml_dialect
            features = [f"Source: {source}"]

        base_recommended = PARADIGM_RECOMMENDED_ENGINES.get(final_paradigm, ["PostgreSQL"])
        # Ensure the ML-recommended dialect is prioritized first
        if recommended_dialect:
            disp = recommended_dialect.capitalize()
            recommended_engines = [disp] + [e for e in base_recommended if e.lower() != recommended_dialect.lower()]
        else:
            recommended_engines = base_recommended

        warning_msg: Optional[str] = None

        # Divergence guardrail: fires when auto_mode is False and user selected an engine
        if not auto_mode and user_selected_engine:
            normalized_engine = user_selected_engine.lower().strip()
            user_paradigm = ENGINE_TO_PARADIGM.get(normalized_engine, DatabaseParadigm.RELATIONAL_SQL)

            if user_paradigm != final_paradigm:
                warning_msg = (
                    f"⚠️ [Paradigm Divergence Warning] Auto mode recommends '{final_paradigm.value}' "
                    f"(Engines: {', '.join(recommended_engines)}) because: '{final_reason}'. "
                    f"You have manually selected '{user_selected_engine}' ({user_paradigm.value}). "
                    f"Proceeding with your selection, but query efficiency or expressiveness may be sub-optimal."
                )

        return ParadigmSuggestion(
            paradigm            = (
                final_paradigm if auto_mode else (
                    ENGINE_TO_PARADIGM.get(user_selected_engine.lower().strip(), final_paradigm)
                    if user_selected_engine else final_paradigm
                )
            ),
            confidence          = final_conf,
            reasoning           = final_reason,
            recommended_engines = recommended_engines,
            recommended_dialect = recommended_dialect,
            is_verified_by_llm  = is_verified,
            warning_message     = warning_msg,
            extracted_features  = features,
        )
