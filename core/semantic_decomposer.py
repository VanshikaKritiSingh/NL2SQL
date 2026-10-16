"""
core/semantic_decomposer.py — Intent Classifier & Architecture Decomposer

Three responsibilities:
1. QUERY INTENT CLASSIFICATION
   Determines which of three modes a natural-language input belongs to:
   - SQL_QUERY     : User wants a database query (the normal path).
   - REFUSAL       : Input is conversational / general-knowledge / completely
                     out-of-domain — e.g. "hi", "who is the president of India".
   - ARCHITECTURE  : User describes an entire system or DB design in natural
                     language and wants a full multi-table DDL + ER metadata
                     synthesised in one shot.

2. SCHEMA-MISMATCH GUARD
   Given the linked schema context and the generated SQL, checks whether all
   referenced tables/columns are actually present. If not, returns a
   structured `-- REFUSAL: [SCHEMA_MISMATCH]` token so the downstream
   orchestrator skips hallucinated results.

3. ARCHITECTURE SYNTHESIS
   Parses free-form natural language describing a database design and emits:
   - A multi-statement CREATE TABLE DDL (canonical ANSI/PostgreSQL).
   - Structured entity metadata ready to drive the ER Diagram panel directly.
   - A per-dialect DDL translation dict via DeterministicDialectConverter.

All three features are deterministic (no LLM calls) and run in < 20 ms.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import sqlglot
from sqlglot import exp

# ─────────────────────────────────────────────────────────────────────────────
# Public constants
# ─────────────────────────────────────────────────────────────────────────────

# Tags understood by the GUI refusal handler
REFUSAL_NON_SQL    = "NON_SQL_QUERY"
REFUSAL_SCHEMA_ERR = "SCHEMA_MISMATCH"
REFUSAL_GENERAL_KN = "GENERAL_KNOWLEDGE"

# Mode labels
MODE_SQL_QUERY   = "SQL_QUERY"
MODE_REFUSAL     = "REFUSAL"
MODE_ARCHITECTURE = "ARCHITECTURE"


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class IntentResult:
    mode: str                    # MODE_SQL_QUERY | MODE_REFUSAL | MODE_ARCHITECTURE
    refusal_tag: Optional[str]   # populated when mode == MODE_REFUSAL
    refusal_comment: str         # the `-- REFUSAL: …` SQL comment string (or "")
    explanation: str             # human-readable reason (never shown raw to end-user)
    confidence: float            # 0.0 – 1.0


@dataclass
class EntitySpec:
    name: str
    columns: List[Dict[str, Any]] = field(default_factory=list)
    # [{name, type, pk, fk_ref}]

    def to_ddl(self) -> str:
        col_defs: List[str] = []
        for c in self.columns:
            pk_str  = " PRIMARY KEY" if c.get("pk") else ""
            fk_str  = f" REFERENCES {c['fk_ref']}" if c.get("fk_ref") else ""
            col_defs.append(f"  {c['name']} {c['type']}{pk_str}{fk_str}")
        return f"CREATE TABLE {self.name} (\n" + ",\n".join(col_defs) + "\n);"


@dataclass
class ArchitectureResult:
    entities: List[EntitySpec]
    canonical_ddl: str                      # full multi-statement ANSI DDL
    dialect_ddl: Dict[str, str]             # {dialect: ddl_string, …}
    er_tables: List[Dict[str, Any]]         # ready for SchemaInfo.tables on the frontend
    foreign_keys: List[Dict[str, str]]      # [{from_table, from_column, to_table, to_column}]


# ─────────────────────────────────────────────────────────────────────────────
# Intent classifier
# ─────────────────────────────────────────────────────────────────────────────

# Greetings / chit-chat patterns
_CHITCHAT_PATTERNS = re.compile(
    r"^(hi|hello|hey|sup|howdy|greetings|what(?:'s| is) up|good (morning|afternoon|evening)|"
    r"how are you|who are you|what are you|tell me about yourself|"
    r"who (?:is|was) (?:the )?(?:president|prime minister|ceo|founder)|"
    r"what (?:is|was) (?:the )?(?:capital of|population of|currency of)|"
    r"do you (?:know|like|think)|can you (?:help|explain|tell)|"
    r"(?:thanks|thank you|bye|goodbye|see you))[?!., ]*$",
    re.IGNORECASE,
)

# Strong SQL intent signals
_SQL_VERB_PATTERNS = re.compile(
    r"\b(show|list|find|get|fetch|retrieve|select|count|sum|average|avg|"
    r"how many|top \d+|insert|update|delete|create table|alter table|"
    r"drop table|group by|order by|where|join|having|distinct)\b",
    re.IGNORECASE,
)

# Architecture / design signals
_ARCH_PATTERNS = re.compile(
    r"\b(design|build|create|model|set up|setup|schema|architect|structure|"
    r"database for|system for|entity|entities|tables? for|relationship|"
    r"foreign key|many[- ]to[- ]many|one[- ]to[- ]many|erd|normaliz|"
    r"make a db|make a database|define (?:the )?(tables?|schema)|"
    r"i need (?:a|an) (?:database|schema|data model)|"
    r"build (?:me )?(?:a|an) (?:database|schema))\b",
    re.IGNORECASE,
)

# General knowledge patterns (capitals, facts, bios, definitions)
_GENERAL_KN_PATTERNS = re.compile(
    r"\b(what (?:is|are|was|were)|who (?:is|was|are)|when (?:did|was|is)|"
    r"where (?:is|was)|why (?:is|does)|how (?:does|do|did)|"
    r"define|explain|describe|tell me|capital of|meaning of|"
    r"history of|biography|invention|discovery)\b",
    re.IGNORECASE,
)


class SemanticIntentClassifier:
    """
    Rule-based intent classifier.  Runs in < 1 ms, no dependencies.
    Order of priority: ARCHITECTURE > SQL_QUERY > REFUSAL(General Knowledge)
                                                  > REFUSAL(Chit-chat)
    """

    def classify(self, query: str) -> IntentResult:
        q = query.strip()
        q_lower = q.lower()

        # Very short inputs with no SQL nouns → chit-chat
        if len(q.split()) <= 3:
            if not _SQL_VERB_PATTERNS.search(q):
                return IntentResult(
                    mode=MODE_REFUSAL,
                    refusal_tag=REFUSAL_NON_SQL,
                    refusal_comment=self._make_comment(
                        REFUSAL_NON_SQL,
                        "Input is too short and contains no SQL-relevant vocabulary.",
                    ),
                    explanation="Short chit-chat input.",
                    confidence=0.95,
                )

        # Architecture intent takes priority
        if _ARCH_PATTERNS.search(q) and len(q.split()) > 6:
            # Only classify as architecture if the user does NOT already have
            # a strong DML/SELECT verb (which implies a query, not a design request)
            has_select = bool(re.search(r"\b(select|from|where|show|list|find)\b", q_lower))
            has_create = bool(re.search(r"\bcreate\s+table\b", q_lower))
            if not (has_select and not has_create):
                return IntentResult(
                    mode=MODE_ARCHITECTURE,
                    refusal_tag=None,
                    refusal_comment="",
                    explanation="Architecture design intent detected.",
                    confidence=0.88,
                )

        # Chit-chat greeting check
        if _CHITCHAT_PATTERNS.match(q):
            return IntentResult(
                mode=MODE_REFUSAL,
                refusal_tag=REFUSAL_NON_SQL,
                refusal_comment=self._make_comment(
                    REFUSAL_NON_SQL,
                    "Input is a conversational greeting, not a database query.",
                ),
                explanation="Greeting / chit-chat input.",
                confidence=0.97,
            )

        # General knowledge question with NO SQL verbs
        if _GENERAL_KN_PATTERNS.search(q) and not _SQL_VERB_PATTERNS.search(q):
            return IntentResult(
                mode=MODE_REFUSAL,
                refusal_tag=REFUSAL_GENERAL_KN,
                refusal_comment=self._make_comment(
                    REFUSAL_GENERAL_KN,
                    "Input appears to be a general knowledge question, not a database query.",
                ),
                explanation="General knowledge question with no SQL verbs.",
                confidence=0.90,
            )

        # Default: treat as SQL query
        return IntentResult(
            mode=MODE_SQL_QUERY,
            refusal_tag=None,
            refusal_comment="",
            explanation="Standard SQL query intent.",
            confidence=0.85,
        )

    @staticmethod
    def _make_comment(tag: str, detail: str) -> str:
        return (
            f"-- REFUSAL: [{tag}] - Request is not a database query.\n"
            f"-- EXPLANATION: {detail}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Schema-mismatch guard
# ─────────────────────────────────────────────────────────────────────────────

class SchemaMismatchGuard:
    """
    Verifies that every table/column reference in a generated SQL string
    actually exists in the linked schema context.

    Returns a refusal comment string if any unknown table or column is found,
    otherwise returns an empty string (clean pass).
    """

    @staticmethod
    def check(sql: str, known_tables: Dict[str, List[str]]) -> str:
        """
        known_tables: {table_name_lower: [col_name_lower, …]}
        Returns refusal comment or "".
        """
        try:
            ast = sqlglot.parse_one(sql, read="postgres")
        except Exception:
            return ""  # let validator handle syntax errors

        if ast is None:
            return ""

        # Skip database/schema level operations and table creations
        if isinstance(ast, exp.Drop) and str(getattr(ast, "kind", "")).upper() in ("DATABASE", "SCHEMA"):
            return ""
        if isinstance(ast, exp.Create):
            return ""

        # Collect all referenced tables
        unknown_tables: List[str] = []
        table_alias_map: Dict[str, str] = {}     # alias → real_table

        for tbl in ast.find_all(exp.Table):
            t_name = tbl.name.lower()
            if not t_name:
                continue
            alias = (tbl.alias or t_name).lower()
            table_alias_map[alias] = t_name
            if t_name and t_name not in known_tables:
                unknown_tables.append(t_name)

        if unknown_tables:
            missing = ", ".join(sorted(set(unknown_tables)))
            available = ", ".join(sorted(known_tables.keys())[:8])
            return (
                f"-- REFUSAL: [{REFUSAL_SCHEMA_ERR}] - Generated query references unknown table(s): {missing}.\n"
                f"-- AVAILABLE TABLES: {available}\n"
                f"-- HINT: Please connect a database that contains these tables or rephrase your query."
            )

        # Collect unknowncolumns (only when a table qualifier is present)
        unknown_cols: List[str] = []
        for col in ast.find_all(exp.Column):
            c_name = col.name.lower()
            if not c_name or c_name == "*":
                continue
            tbl_ref = col.table.lower() if col.table else None
            if tbl_ref and tbl_ref in table_alias_map:
                real_tbl = table_alias_map[tbl_ref]
                if real_tbl in known_tables:
                    if c_name not in known_tables[real_tbl]:
                        unknown_cols.append(f"{tbl_ref}.{c_name}")

        if unknown_cols:
            missing = ", ".join(sorted(set(unknown_cols)))
            return (
                f"-- REFUSAL: [{REFUSAL_SCHEMA_ERR}] - Generated query references unknown column(s): {missing}.\n"
                f"-- HINT: Verify column names against the connected database schema."
            )

        return ""  # all clear


# ─────────────────────────────────────────────────────────────────────────────
# Architecture natural-language parser
# ─────────────────────────────────────────────────────────────────────────────

# Common entity extraction patterns
_ENTITY_KEYWORDS = re.compile(
    r"\b(?:table|entity|entities|model|resource|object)\b",
    re.IGNORECASE,
)

# Column type heuristics
_TYPE_HINTS: Dict[str, str] = {
    "name":        "VARCHAR(255) NOT NULL",
    "email":       "VARCHAR(255) NOT NULL",
    "password":    "VARCHAR(255) NOT NULL",
    "phone":       "VARCHAR(50)",
    "address":     "VARCHAR(500)",
    "url":         "VARCHAR(500)",
    "slug":        "VARCHAR(255)",
    "status":      "VARCHAR(50) DEFAULT 'active'",
    "title":       "VARCHAR(255) NOT NULL",
    "description": "TEXT",
    "content":     "TEXT",
    "body":        "TEXT",
    "notes":       "TEXT",
    "comment":     "TEXT",
    "bio":         "TEXT",
    "date":        "DATE",
    "time":        "TIME",
    "timestamp":   "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "created_at":  "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "updated_at":  "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "price":       "DECIMAL(10,2) NOT NULL",
    "cost":        "DECIMAL(10,2)",
    "amount":      "DECIMAL(10,2) NOT NULL",
    "salary":      "DECIMAL(12,2)",
    "balance":     "DECIMAL(15,2) DEFAULT 0.00",
    "rating":      "DECIMAL(3,2)",
    "score":       "DECIMAL(5,2)",
    "count":       "INTEGER DEFAULT 0",
    "quantity":    "INTEGER NOT NULL",
    "stock":       "INTEGER DEFAULT 0",
    "age":         "INTEGER",
    "year":        "INTEGER",
    "number":      "INTEGER",
    "is_":         "BOOLEAN DEFAULT FALSE",
    "has_":        "BOOLEAN DEFAULT FALSE",
    "active":      "BOOLEAN DEFAULT TRUE",
    "enabled":     "BOOLEAN DEFAULT TRUE",
    "approved":    "BOOLEAN DEFAULT FALSE",
    "verified":    "BOOLEAN DEFAULT FALSE",
}

# Relationship signals in natural language
_RELATION_PATTERNS = [
    # "users can have many orders"
    (re.compile(r"(\w+)\s+(?:can\s+)?have\s+many\s+(\w+)", re.IGNORECASE), "one_to_many"),
    # "each order belongs to a user"
    (re.compile(r"(?:each\s+)?(\w+)\s+belongs?\s+to\s+(?:a\s+)?(\w+)", re.IGNORECASE), "belongs_to"),
    # "products and orders (many-to-many)"
    (re.compile(r"(\w+)\s+and\s+(\w+)\s+(?:many[- ]to[- ]many|m2m|m:n)", re.IGNORECASE), "many_to_many"),
    # "orders reference users"
    (re.compile(r"(\w+)\s+(?:reference|references|link|links|connect|connects)\s+(\w+)", re.IGNORECASE), "one_to_many"),
]

# Common system/domain entity vocabularies
_DOMAIN_ENTITY_HINTS: Dict[str, List[str]] = {
    "ecommerce":  ["users", "products", "orders", "order_items", "reviews", "categories", "carts", "payments"],
    "blog":       ["users", "posts", "comments", "tags", "post_tags", "categories"],
    "lms":        ["students", "teachers", "courses", "enrollments", "lessons", "assignments", "grades"],
    "hospital":   ["patients", "doctors", "appointments", "prescriptions", "departments", "rooms"],
    "social":     ["users", "posts", "likes", "followers", "messages", "notifications"],
    "crm":        ["contacts", "leads", "deals", "tasks", "notes", "companies", "pipelines"],
    "inventory":  ["products", "suppliers", "warehouses", "stock_levels", "purchase_orders", "categories"],
    "hr":         ["employees", "departments", "positions", "salaries", "leaves", "attendance"],
    "banking":    ["customers", "accounts", "transactions", "branches", "loans", "cards"],
}

# Domain detection keywords
_DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "ecommerce":  ["shop", "store", "checkout", "cart", "product", "order", "payment", "shipping", "customer"],
    "blog":       ["blog", "post", "article", "comment", "author", "publish", "tag", "category"],
    "lms":        ["course", "student", "teacher", "enroll", "lesson", "assignment", "grade", "school", "university"],
    "hospital":   ["patient", "doctor", "appointment", "prescription", "medical", "clinic", "hospital"],
    "social":     ["follower", "like", "friend", "share", "notification", "social", "profile", "feed"],
    "crm":        ["lead", "deal", "pipeline", "contact", "company", "crm", "sales"],
    "inventory":  ["inventory", "warehouse", "supplier", "stock", "sku", "purchase order"],
    "hr":         ["employee", "department", "salary", "leave", "attendance", "payroll", "hr", "recruit"],
    "banking":    ["bank", "account", "loan", "transaction", "branch", "deposit", "withdrawal"],
}


def _col_type(col_name: str) -> str:
    """Infer ANSI SQL type from column name heuristics."""
    cn = col_name.lower()
    # Prefix matches
    if cn.startswith("is_") or cn.startswith("has_"):
        return "BOOLEAN DEFAULT FALSE"
    # Exact & partial matches
    for hint, sql_type in _TYPE_HINTS.items():
        if hint in cn:
            return sql_type
    # Fallback
    return "VARCHAR(255)"


def _to_snake(name: str) -> str:
    """Normalise a free-text entity/column name to snake_case."""
    n = name.strip().lower()
    n = re.sub(r"[^a-z0-9 _]", "", n)
    n = re.sub(r"\s+", "_", n)
    n = re.sub(r"_+", "_", n).strip("_")
    # Pluralise table names
    return n


def _pluralise(name: str) -> str:
    """Simple English plural for table names."""
    if name.endswith("y") and not name.endswith("ey") and not name.endswith("ay"):
        return name[:-1] + "ies"
    if name.endswith(("s", "sh", "ch", "x", "z")):
        return name + "es"
    return name + "s"


class NLArchitectureParser:
    """
    Parses free-form natural language describing a database schema and
    produces a multi-entity ArchitectureResult with DDL + ER metadata.
    """

    def parse(self, query: str) -> ArchitectureResult:
        domain = self._detect_domain(query)
        explicit_entities = self._extract_explicit_entities(query)
        relations = self._extract_relations(query)
        entities = self._assemble_entities(domain, explicit_entities, relations, query)
        canonical_ddl = self._build_ddl(entities)
        dialect_ddl = self._transpile_all(canonical_ddl)
        er_tables = self._build_er_tables(entities)
        foreign_keys = self._collect_fks(entities)
        return ArchitectureResult(
            entities=entities,
            canonical_ddl=canonical_ddl,
            dialect_ddl=dialect_ddl,
            er_tables=er_tables,
            foreign_keys=foreign_keys,
        )

    # ── private helpers ──────────────────────────────────────────────────────

    def _detect_domain(self, text: str) -> Optional[str]:
        scores: Dict[str, int] = {}
        t_lower = text.lower()
        for domain, kws in _DOMAIN_KEYWORDS.items():
            hits = sum(1 for kw in kws if kw in t_lower)
            if hits:
                scores[domain] = hits
        return max(scores, key=scores.__getitem__) if scores else None

    def _extract_explicit_entities(self, text: str) -> List[str]:
        """Extract entity/table names that the user explicitly mentions."""
        found: List[str] = []
        # "a users table", "table for products", "entity called X"
        for m in re.finditer(
            r"\b(?:table(?:s)?\s+(?:for|of|called)?\s*|entity\s+(?:called\s+)?|entities?\s+(?:called\s+)?)(\w+)",
            text,
            re.IGNORECASE,
        ):
            found.append(_pluralise(_to_snake(m.group(1))))

        # standalone nouns in sentences like "I need users, products, and orders"
        needs_match = re.search(r"(?:need|include|have|consist of|comprise)\s+([\w, ]+?)(?:\.|$)", text, re.IGNORECASE)
        if needs_match:
            nouns = re.split(r"[,\s]+(?:and\s+)?", needs_match.group(1))
            for n in nouns:
                n_clean = _to_snake(n.strip().rstrip("s"))
                if len(n_clean) > 2:
                    found.append(_pluralise(n_clean))

        return list(dict.fromkeys(e for e in found if len(e) > 2))

    def _extract_relations(self, text: str) -> List[Tuple[str, str, str]]:
        """Returns list of (entity_a, relationship_type, entity_b)."""
        rels: List[Tuple[str, str, str]] = []
        for pattern, rel_type in _RELATION_PATTERNS:
            for m in pattern.finditer(text):
                a = _pluralise(_to_snake(m.group(1)))
                b = _pluralise(_to_snake(m.group(2)))
                rels.append((a, rel_type, b))
        return rels

    def _assemble_entities(
        self,
        domain: Optional[str],
        explicit: List[str],
        relations: List[Tuple[str, str, str]],
        text: str,
    ) -> List[EntitySpec]:
        # Start from either explicit mentions or domain defaults
        entity_names: List[str] = []
        if explicit:
            entity_names = explicit
        elif domain and domain in _DOMAIN_ENTITY_HINTS:
            entity_names = _DOMAIN_ENTITY_HINTS[domain][:6]
        else:
            # fallback: a minimal system
            entity_names = ["users", "items", "records"]

        # Derive from relation pairs too
        for a, _, b in relations:
            for name in (a, b):
                if name not in entity_names:
                    entity_names.append(name)

        entities: List[EntitySpec] = []
        pk_registry: Dict[str, str] = {}  # entity_name → pk_col_name

        for ent_name in entity_names:
            sing = ent_name.rstrip("s")  # rough singularise for PK name
            pk_name = f"{sing}_id"
            pk_registry[ent_name] = pk_name
            cols: List[Dict[str, Any]] = [
                {"name": pk_name, "type": "SERIAL", "pk": True, "fk_ref": None},
            ]
            # Infer domain-appropriate columns
            cols.extend(self._infer_columns(ent_name, text, pk_name))
            entities.append(EntitySpec(name=ent_name, columns=cols))

        # Wire FK columns from relations
        for entity in entities:
            for a, rel_type, b in relations:
                if entity.name == a and rel_type in ("one_to_many", "many_to_many"):
                    referenced = b
                    ref_pk = pk_registry.get(referenced, f"{referenced.rstrip('s')}_id")
                    fk_col = ref_pk
                    if not any(c["name"] == fk_col for c in entity.columns):
                        entity.columns.append({
                            "name": fk_col,
                            "type": "INTEGER NOT NULL",
                            "pk": False,
                            "fk_ref": f"{referenced}({ref_pk})",
                        })
                elif entity.name == a and rel_type == "belongs_to":
                    referenced = b
                    ref_pk = pk_registry.get(referenced, f"{referenced.rstrip('s')}_id")
                    fk_col = ref_pk
                    if not any(c["name"] == fk_col for c in entity.columns):
                        entity.columns.append({
                            "name": fk_col,
                            "type": "INTEGER NOT NULL",
                            "pk": False,
                            "fk_ref": f"{referenced}({ref_pk})",
                        })

        # Add junction tables for many-to-many
        junction_entities: List[EntitySpec] = []
        for a, rel_type, b in relations:
            if rel_type == "many_to_many":
                junc_name = f"{a.rstrip('s')}_{b.rstrip('s')}s"
                if not any(e.name == junc_name for e in entities + junction_entities):
                    a_pk = pk_registry.get(a, f"{a.rstrip('s')}_id")
                    b_pk = pk_registry.get(b, f"{b.rstrip('s')}_id")
                    junction_entities.append(EntitySpec(
                        name=junc_name,
                        columns=[
                            {"name": f"{junc_name}_id", "type": "SERIAL", "pk": True, "fk_ref": None},
                            {"name": a_pk, "type": "INTEGER NOT NULL", "pk": False, "fk_ref": f"{a}({a_pk})"},
                            {"name": b_pk, "type": "INTEGER NOT NULL", "pk": False, "fk_ref": f"{b}({b_pk})"},
                        ],
                    ))
        entities.extend(junction_entities)
        return entities

    @staticmethod
    def _infer_columns(entity: str, text: str, pk_name: str) -> List[Dict[str, Any]]:
        """Add sensible default columns based on entity name."""
        standard: Dict[str, List[Dict[str, Any]]] = {
            "users":         [{"name":"username","type":"VARCHAR(100) NOT NULL","pk":False,"fk_ref":None},
                              {"name":"email","type":"VARCHAR(255) NOT NULL","pk":False,"fk_ref":None},
                              {"name":"password_hash","type":"VARCHAR(255) NOT NULL","pk":False,"fk_ref":None},
                              {"name":"status","type":"VARCHAR(50) DEFAULT 'active'","pk":False,"fk_ref":None},
                              {"name":"created_at","type":"TIMESTAMP DEFAULT CURRENT_TIMESTAMP","pk":False,"fk_ref":None}],
            "products":      [{"name":"name","type":"VARCHAR(255) NOT NULL","pk":False,"fk_ref":None},
                              {"name":"price","type":"DECIMAL(10,2) NOT NULL","pk":False,"fk_ref":None},
                              {"name":"stock_quantity","type":"INTEGER DEFAULT 0","pk":False,"fk_ref":None},
                              {"name":"status","type":"VARCHAR(50) DEFAULT 'active'","pk":False,"fk_ref":None}],
            "orders":        [{"name":"status","type":"VARCHAR(50) DEFAULT 'pending'","pk":False,"fk_ref":None},
                              {"name":"total_amount","type":"DECIMAL(10,2) NOT NULL","pk":False,"fk_ref":None},
                              {"name":"created_at","type":"TIMESTAMP DEFAULT CURRENT_TIMESTAMP","pk":False,"fk_ref":None}],
            "order_items":   [{"name":"quantity","type":"INTEGER NOT NULL","pk":False,"fk_ref":None},
                              {"name":"unit_price","type":"DECIMAL(10,2) NOT NULL","pk":False,"fk_ref":None}],
            "categories":    [{"name":"name","type":"VARCHAR(100) NOT NULL","pk":False,"fk_ref":None},
                              {"name":"description","type":"TEXT","pk":False,"fk_ref":None}],
            "posts":         [{"name":"title","type":"VARCHAR(255) NOT NULL","pk":False,"fk_ref":None},
                              {"name":"body","type":"TEXT NOT NULL","pk":False,"fk_ref":None},
                              {"name":"published_at","type":"TIMESTAMP","pk":False,"fk_ref":None}],
            "comments":      [{"name":"body","type":"TEXT NOT NULL","pk":False,"fk_ref":None},
                              {"name":"created_at","type":"TIMESTAMP DEFAULT CURRENT_TIMESTAMP","pk":False,"fk_ref":None}],
            "reviews":       [{"name":"rating","type":"INTEGER NOT NULL","pk":False,"fk_ref":None},
                              {"name":"comment","type":"TEXT","pk":False,"fk_ref":None},
                              {"name":"created_at","type":"TIMESTAMP DEFAULT CURRENT_TIMESTAMP","pk":False,"fk_ref":None}],
            "payments":      [{"name":"amount","type":"DECIMAL(10,2) NOT NULL","pk":False,"fk_ref":None},
                              {"name":"method","type":"VARCHAR(50)","pk":False,"fk_ref":None},
                              {"name":"status","type":"VARCHAR(50) DEFAULT 'pending'","pk":False,"fk_ref":None},
                              {"name":"processed_at","type":"TIMESTAMP","pk":False,"fk_ref":None}],
            "employees":     [{"name":"name","type":"VARCHAR(255) NOT NULL","pk":False,"fk_ref":None},
                              {"name":"email","type":"VARCHAR(255) NOT NULL","pk":False,"fk_ref":None},
                              {"name":"salary","type":"DECIMAL(12,2)","pk":False,"fk_ref":None},
                              {"name":"hired_at","type":"DATE","pk":False,"fk_ref":None}],
            "departments":   [{"name":"name","type":"VARCHAR(100) NOT NULL","pk":False,"fk_ref":None}],
            "courses":       [{"name":"title","type":"VARCHAR(255) NOT NULL","pk":False,"fk_ref":None},
                              {"name":"description","type":"TEXT","pk":False,"fk_ref":None},
                              {"name":"credits","type":"INTEGER DEFAULT 3","pk":False,"fk_ref":None}],
            "enrollments":   [{"name":"enrolled_at","type":"TIMESTAMP DEFAULT CURRENT_TIMESTAMP","pk":False,"fk_ref":None},
                              {"name":"status","type":"VARCHAR(50) DEFAULT 'active'","pk":False,"fk_ref":None}],
            "tasks":         [{"name":"title","type":"VARCHAR(255) NOT NULL","pk":False,"fk_ref":None},
                              {"name":"status","type":"VARCHAR(50) DEFAULT 'pending'","pk":False,"fk_ref":None},
                              {"name":"due_date","type":"DATE","pk":False,"fk_ref":None}],
            "transactions":  [{"name":"amount","type":"DECIMAL(12,2) NOT NULL","pk":False,"fk_ref":None},
                              {"name":"txn_type","type":"VARCHAR(50)","pk":False,"fk_ref":None},
                              {"name":"created_at","type":"TIMESTAMP DEFAULT CURRENT_TIMESTAMP","pk":False,"fk_ref":None}],
            "accounts":      [{"name":"account_number","type":"VARCHAR(50) NOT NULL","pk":False,"fk_ref":None},
                              {"name":"balance","type":"DECIMAL(15,2) DEFAULT 0.00","pk":False,"fk_ref":None},
                              {"name":"status","type":"VARCHAR(50) DEFAULT 'active'","pk":False,"fk_ref":None}],
        }
        return standard.get(entity, [
            {"name": "name", "type": "VARCHAR(255) NOT NULL", "pk": False, "fk_ref": None},
            {"name": "created_at", "type": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "pk": False, "fk_ref": None},
        ])

    @staticmethod
    def _build_ddl(entities: List[EntitySpec]) -> str:
        return "\n\n".join(e.to_ddl() for e in entities)

    @staticmethod
    def _transpile_all(ddl: str) -> Dict[str, str]:
        from core.dialect_converter import DeterministicDialectConverter
        converter = DeterministicDialectConverter()
        dialects = ["postgres", "mysql", "sqlite", "duckdb", "clickhouse"]
        result: Dict[str, str] = {}
        for dialect in dialects:
            try:
                stmts = [s for s in sqlglot.parse(ddl, read="postgres") if s is not None]
                translated = "\n\n".join(
                    s.sql(dialect) + ";" for s in stmts
                )
                result[dialect] = translated
            except Exception as exc:
                result[dialect] = f"-- Transpilation error for {dialect}: {exc}"
        return result

    @staticmethod
    def _build_er_tables(entities: List[EntitySpec]) -> List[Dict[str, Any]]:
        """Builds a list compatible with the frontend SchemaInfo.tables type."""
        er_tables: List[Dict[str, Any]] = []
        for ent in entities:
            columns = []
            for c in ent.columns:
                columns.append({
                    "name": c["name"],
                    "data_type": c["type"].split()[0],
                    "is_primary_key": c.get("pk", False),
                    "is_foreign_key": bool(c.get("fk_ref")),
                    "fk_references": c.get("fk_ref"),
                    "nullable": "NOT NULL" not in c["type"],
                })
            er_tables.append({"name": ent.name, "columns": columns})
        return er_tables

    @staticmethod
    def _collect_fks(entities: List[EntitySpec]) -> List[Dict[str, str]]:
        fks: List[Dict[str, str]] = []
        for ent in entities:
            for c in ent.columns:
                if c.get("fk_ref"):
                    ref = c["fk_ref"]  # e.g. "users(user_id)"
                    m = re.match(r"(\w+)\((\w+)\)", ref)
                    if m:
                        fks.append({
                            "from_table":  ent.name,
                            "from_column": c["name"],
                            "to_table":    m.group(1),
                            "to_column":   m.group(2),
                        })
        return fks


# ─────────────────────────────────────────────────────────────────────────────
# Unified public façade
# ─────────────────────────────────────────────────────────────────────────────

class SemanticDecomposer:
    """
    One-stop entry point used by orchestrator and PEFT connector.

    Usage:
        decomposer = SemanticDecomposer()

        # Classify
        intent = decomposer.classify("hi")            # → REFUSAL
        intent = decomposer.classify("Show top 5…")  # → SQL_QUERY
        intent = decomposer.classify("Design a blog db")  # → ARCHITECTURE

        # Schema-mismatch check
        refusal_str = decomposer.check_schema_mismatch(generated_sql, known_tables)

        # Architecture synthesis
        arch = decomposer.synthesize_architecture("Build a hospital management DB…")
    """

    def __init__(self) -> None:
        self._classifier  = SemanticIntentClassifier()
        self._mismatch    = SchemaMismatchGuard()
        self._arch_parser = NLArchitectureParser()

    def classify(self, query: str) -> IntentResult:
        return self._classifier.classify(query)

    def check_schema_mismatch(
        self,
        sql: str,
        known_tables: Dict[str, List[str]],
    ) -> str:
        """Returns a refusal SQL comment or '' if clean."""
        return self._mismatch.check(sql, known_tables)

    def synthesize_architecture(self, query: str) -> ArchitectureResult:
        return self._arch_parser.parse(query)


# Singleton
default_decomposer = SemanticDecomposer()
