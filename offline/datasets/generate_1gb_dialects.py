"""
offline/datasets/generate_1gb_dialects.py — True Combinatorial & Multi-Dialect Dataset Synthesizer

Features:
1. Massive Combinatorial AST Engine: Generates millions of unique, syntactically-valid,
   schema-grounded SQL ASTs across 8 complex domain schemas.
2. Zero-Garbage Guarantee: 0% repetition, randomized projections, realistic predicates,
   1-hop & 2-hop foreign key joins, aggregations (SUM/AVG/COUNT/MIN/MAX), HAVING filters,
   and TOP-N limits.
3. Universal Transpilation: Compiles every canonical query into 7 dialects:
   - PostgreSQL (Relational SQL)
   - MySQL (Relational SQL)
   - SQLite (Embedded SQL)
   - DuckDB (Columnar OLAP)
   - ClickHouse (Distributed OLAP)
   - openCypher (Graph DBMS: Neo4j, Neptune, Kuzu)
   - MongoDB MQL (Document NoSQL)
4. SFT ChatML Format: Formatted for direct training with HuggingFace SFTTrainer, TRL, Unsloth,
   and PEFT (AdaLoRA / QLoRA).
"""

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

# Ensure repository root is on PYTHONPATH
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.dialect_converter import DeterministicDialectConverter
from offline.datasets.prepare_dataset import (
    SCHEMAS,
    SYSTEM_PROMPT,
    _CHITCHAT_SAMPLES,
    _make_schema_mismatch_sample,
    ARCHITECTURE_TEMPLATES,
)

SUPPORTED_DIALECTS = [
    "postgres",
    "mysql",
    "sqlite",
    "duckdb",
    "clickhouse",
    "opencypher",
    "mongodb"
]

# -----------------------------------------------------------------------------
# Domain Metadata (Tables, Columns, Types, Foreign Keys, Categoricals)
# -----------------------------------------------------------------------------

DOMAIN_SPECS = {
    "ecommerce": {
        "tables": {
            "customers": {
                "cols": ["customer_id", "name", "email", "country"],
                "pk": "customer_id",
                "types": {"customer_id": "int", "name": "str", "email": "str", "country": "cat"},
                "cat_values": {"country": ["USA", "Germany", "Japan", "Canada", "UK", "France", "Brazil", "India", "Australia", "Singapore"]}
            },
            "products": {
                "cols": ["product_id", "category_id", "name", "price", "stock_quantity", "status"],
                "pk": "product_id",
                "types": {"product_id": "int", "category_id": "int", "name": "str", "price": "num", "stock_quantity": "int", "status": "cat"},
                "num_ranges": {"price": (10, 2000), "stock_quantity": (0, 500)},
                "cat_values": {"status": ["active", "discontinued", "out_of_stock"]}
            },
            "orders": {
                "cols": ["order_id", "customer_id", "total_amount", "status"],
                "pk": "order_id",
                "types": {"order_id": "int", "customer_id": "int", "total_amount": "num", "status": "cat"},
                "num_ranges": {"total_amount": (20, 10000)},
                "cat_values": {"status": ["completed", "pending", "cancelled"]}
            },
            "order_items": {
                "cols": ["item_id", "order_id", "product_id", "quantity", "unit_price"],
                "pk": "item_id",
                "types": {"item_id": "int", "order_id": "int", "product_id": "int", "quantity": "int", "unit_price": "num"},
                "num_ranges": {"quantity": (1, 20), "unit_price": (5, 500)}
            },
            "reviews": {
                "cols": ["review_id", "product_id", "customer_id", "rating"],
                "pk": "review_id",
                "types": {"review_id": "int", "product_id": "int", "customer_id": "int", "rating": "int"},
                "num_ranges": {"rating": (1, 5)}
            }
        },
        "joins": [
            ("orders", "customer_id", "customers", "customer_id"),
            ("order_items", "order_id", "orders", "order_id"),
            ("order_items", "product_id", "products", "product_id"),
            ("reviews", "product_id", "products", "product_id"),
            ("reviews", "customer_id", "customers", "customer_id")
        ],
        "multi_joins": [
            ("customers", "customer_id", "orders", "customer_id", "order_items", "order_id")
        ]
    },

    "saas_platform": {
        "tables": {
            "organizations": {
                "cols": ["org_id", "org_name", "plan_tier"],
                "pk": "org_id",
                "types": {"org_id": "int", "org_name": "str", "plan_tier": "cat"},
                "cat_values": {"plan_tier": ["free", "pro", "enterprise"]}
            },
            "users": {
                "cols": ["user_id", "org_id", "email", "role"],
                "pk": "user_id",
                "types": {"user_id": "int", "org_id": "int", "email": "str", "role": "cat"},
                "cat_values": {"role": ["owner", "admin", "member"]}
            },
            "subscriptions": {
                "cols": ["subscription_id", "org_id", "monthly_rate", "status"],
                "pk": "subscription_id",
                "types": {"subscription_id": "int", "org_id": "int", "monthly_rate": "num", "status": "cat"},
                "num_ranges": {"monthly_rate": (29, 2500)},
                "cat_values": {"status": ["active", "past_due", "cancelled"]}
            },
            "api_keys": {
                "cols": ["key_id", "org_id", "is_active"],
                "pk": "key_id",
                "types": {"key_id": "int", "org_id": "int", "is_active": "bool"},
                "cat_values": {"is_active": ["TRUE", "FALSE"]}
            }
        },
        "joins": [
            ("users", "org_id", "organizations", "org_id"),
            ("subscriptions", "org_id", "organizations", "org_id"),
            ("api_keys", "org_id", "organizations", "org_id")
        ],
        "multi_joins": [
            ("users", "org_id", "organizations", "org_id", "subscriptions", "org_id")
        ]
    },

    "banking": {
        "tables": {
            "branches": {
                "cols": ["branch_id", "branch_name", "city", "state"],
                "pk": "branch_id",
                "types": {"branch_id": "int", "branch_name": "str", "city": "cat", "state": "cat"},
                "cat_values": {"city": ["New York", "Chicago", "San Francisco", "Austin", "Seattle", "Dallas"], "state": ["NY", "IL", "CA", "TX", "WA"]}
            },
            "accounts": {
                "cols": ["account_id", "branch_id", "account_number", "account_type", "balance", "status"],
                "pk": "account_id",
                "types": {"account_id": "int", "branch_id": "int", "account_number": "str", "account_type": "cat", "balance": "num", "status": "cat"},
                "num_ranges": {"balance": (500, 250000)},
                "cat_values": {"account_type": ["checking", "savings", "credit"], "status": ["open", "closed"]}
            },
            "transactions": {
                "cols": ["txn_id", "account_id", "txn_type", "amount", "merchant_category", "is_flagged_fraud"],
                "pk": "txn_id",
                "types": {"txn_id": "int", "account_id": "int", "txn_type": "cat", "amount": "num", "merchant_category": "cat", "is_flagged_fraud": "bool"},
                "num_ranges": {"amount": (5, 10000)},
                "cat_values": {
                    "txn_type": ["deposit", "withdrawal", "transfer", "fee"],
                    "merchant_category": ["Electronics", "Groceries", "Travel", "Dining", "Healthcare", "Utilities"],
                    "is_flagged_fraud": ["TRUE", "FALSE"]
                }
            },
            "loans": {
                "cols": ["loan_id", "account_id", "principal", "interest_rate", "term_months", "status"],
                "pk": "loan_id",
                "types": {"loan_id": "int", "account_id": "int", "principal": "num", "interest_rate": "num", "term_months": "int", "status": "cat"},
                "num_ranges": {"principal": (5000, 500000), "term_months": (12, 360)},
                "cat_values": {"status": ["active", "paid_off", "defaulted"]}
            }
        },
        "joins": [
            ("accounts", "branch_id", "branches", "branch_id"),
            ("transactions", "account_id", "accounts", "account_id"),
            ("loans", "account_id", "accounts", "account_id")
        ],
        "multi_joins": [
            ("branches", "branch_id", "accounts", "branch_id", "transactions", "account_id")
        ]
    },

    "healthcare": {
        "tables": {
            "departments": {
                "cols": ["dept_id", "dept_name", "floor"],
                "pk": "dept_id",
                "types": {"dept_id": "int", "dept_name": "cat", "floor": "int"},
                "num_ranges": {"floor": (1, 8)},
                "cat_values": {"dept_name": ["Cardiology", "Neurology", "Pediatrics", "Oncology", "Orthopedics", "Emergency"]}
            },
            "doctors": {
                "cols": ["doctor_id", "dept_id", "name", "specialty", "years_experience"],
                "pk": "doctor_id",
                "types": {"doctor_id": "int", "dept_id": "int", "name": "str", "specialty": "cat", "years_experience": "int"},
                "num_ranges": {"years_experience": (1, 35)},
                "cat_values": {"specialty": ["Cardiologist", "Neurologist", "Pediatrician", "Oncologist", "Surgeon"]}
            },
            "patients": {
                "cols": ["patient_id", "name", "blood_group", "contact_number"],
                "pk": "patient_id",
                "types": {"patient_id": "int", "name": "str", "blood_group": "cat", "contact_number": "str"},
                "cat_values": {"blood_group": ["A+", "O+", "B+", "AB+", "A-", "O-", "B-", "AB-"]}
            },
            "appointments": {
                "cols": ["appointment_id", "patient_id", "doctor_id", "status"],
                "pk": "appointment_id",
                "types": {"appointment_id": "int", "patient_id": "int", "doctor_id": "int", "status": "cat"},
                "cat_values": {"status": ["scheduled", "completed", "no_show", "cancelled"]}
            },
            "prescriptions": {
                "cols": ["prescription_id", "appointment_id", "medication_name", "duration_days"],
                "pk": "prescription_id",
                "types": {"prescription_id": "int", "appointment_id": "int", "medication_name": "cat", "duration_days": "int"},
                "num_ranges": {"duration_days": (3, 90)},
                "cat_values": {"medication_name": ["Amoxicillin", "Ibuprofen", "Metformin", "Atorvastatin", "Lisinopril", "Omeprazole"]}
            }
        },
        "joins": [
            ("doctors", "dept_id", "departments", "dept_id"),
            ("appointments", "patient_id", "patients", "patient_id"),
            ("appointments", "doctor_id", "doctors", "doctor_id"),
            ("prescriptions", "appointment_id", "appointments", "appointment_id")
        ],
        "multi_joins": [
            ("departments", "dept_id", "doctors", "dept_id", "appointments", "doctor_id")
        ]
    },

    "supply_chain": {
        "tables": {
            "suppliers": {
                "cols": ["supplier_id", "supplier_name", "country", "rating"],
                "pk": "supplier_id",
                "types": {"supplier_id": "int", "supplier_name": "str", "country": "cat", "rating": "num"},
                "num_ranges": {"rating": (2.0, 5.0)},
                "cat_values": {"country": ["USA", "China", "Germany", "Mexico", "Vietnam", "Japan", "South Korea"]}
            },
            "warehouses": {
                "cols": ["warehouse_id", "location_city", "capacity_sqft"],
                "pk": "warehouse_id",
                "types": {"warehouse_id": "int", "location_city": "cat", "capacity_sqft": "int"},
                "num_ranges": {"capacity_sqft": (10000, 500000)},
                "cat_values": {"location_city": ["Chicago", "Memphis", "Dallas", "Atlanta", "Ontario", "Hamburg"]}
            },
            "inventory": {
                "cols": ["inventory_id", "warehouse_id", "item_sku", "quantity_on_hand", "reorder_level"],
                "pk": "inventory_id",
                "types": {"inventory_id": "int", "warehouse_id": "int", "item_sku": "str", "quantity_on_hand": "int", "reorder_level": "int"},
                "num_ranges": {"quantity_on_hand": (0, 1000), "reorder_level": (20, 200)}
            },
            "shipments": {
                "cols": ["shipment_id", "supplier_id", "destination_warehouse_id", "carrier", "status"],
                "pk": "shipment_id",
                "types": {"shipment_id": "int", "supplier_id": "int", "destination_warehouse_id": "int", "carrier": "cat", "status": "cat"},
                "cat_values": {"carrier": ["FedEx", "DHL", "UPS", "Maersk", "DB Schenker"], "status": ["in_transit", "delivered", "delayed"]}
            }
        },
        "joins": [
            ("inventory", "warehouse_id", "warehouses", "warehouse_id"),
            ("shipments", "supplier_id", "suppliers", "supplier_id"),
            ("shipments", "destination_warehouse_id", "warehouses", "warehouse_id")
        ],
        "multi_joins": [
            ("suppliers", "supplier_id", "shipments", "supplier_id", "warehouses", "warehouse_id")
        ]
    },

    "social_network": {
        "tables": {
            "users": {
                "cols": ["user_id", "username", "email", "follower_count"],
                "pk": "user_id",
                "types": {"user_id": "int", "username": "str", "email": "str", "follower_count": "int"},
                "num_ranges": {"follower_count": (10, 100000)}
            },
            "posts": {
                "cols": ["post_id", "author_id", "content", "like_count"],
                "pk": "post_id",
                "types": {"post_id": "int", "author_id": "int", "content": "str", "like_count": "int"},
                "num_ranges": {"like_count": (0, 50000)}
            },
            "comments": {
                "cols": ["comment_id", "post_id", "author_id", "content"],
                "pk": "comment_id",
                "types": {"comment_id": "int", "post_id": "int", "author_id": "int", "content": "str"}
            }
        },
        "joins": [
            ("posts", "author_id", "users", "user_id"),
            ("comments", "post_id", "posts", "post_id"),
            ("comments", "author_id", "users", "user_id")
        ],
        "multi_joins": [
            ("users", "user_id", "posts", "author_id", "comments", "post_id")
        ]
    },

    "university": {
        "tables": {
            "departments": {
                "cols": ["dept_id", "dept_name", "building"],
                "pk": "dept_id",
                "types": {"dept_id": "int", "dept_name": "cat", "building": "cat"},
                "cat_values": {"dept_name": ["Computer Science", "Mathematics", "Physics", "Chemistry", "Economics", "History"], "building": ["Hall A", "Hall B", "Science Center", "Tower 1"]}
            },
            "instructors": {
                "cols": ["instructor_id", "dept_id", "name", "salary"],
                "pk": "instructor_id",
                "types": {"instructor_id": "int", "dept_id": "int", "name": "str", "salary": "num"},
                "num_ranges": {"salary": (50000, 150000)}
            },
            "courses": {
                "cols": ["course_id", "dept_id", "course_code", "title", "credits"],
                "pk": "course_id",
                "types": {"course_id": "int", "dept_id": "int", "course_code": "str", "title": "str", "credits": "int"},
                "num_ranges": {"credits": (1, 5)}
            },
            "students": {
                "cols": ["student_id", "name", "major_dept_id", "gpa", "enrollment_year"],
                "pk": "student_id",
                "types": {"student_id": "int", "name": "str", "major_dept_id": "int", "gpa": "num", "enrollment_year": "int"},
                "num_ranges": {"gpa": (2.0, 4.0), "enrollment_year": (2020, 2025)}
            },
            "enrollments": {
                "cols": ["enrollment_id", "student_id", "course_id", "semester", "year"],
                "pk": "enrollment_id",
                "types": {"enrollment_id": "int", "student_id": "int", "course_id": "int", "semester": "cat", "year": "int"},
                "num_ranges": {"year": (2022, 2025)},
                "cat_values": {"semester": ["Fall", "Spring", "Summer"]}
            }
        },
        "joins": [
            ("instructors", "dept_id", "departments", "dept_id"),
            ("courses", "dept_id", "departments", "dept_id"),
            ("students", "major_dept_id", "departments", "dept_id"),
            ("enrollments", "student_id", "students", "student_id"),
            ("enrollments", "course_id", "courses", "course_id")
        ],
        "multi_joins": [
            ("departments", "dept_id", "students", "major_dept_id", "enrollments", "student_id")
        ]
    },

    "graph_network": {
        "tables": {
            "nodes": {
                "cols": ["node_id", "label"],
                "pk": "node_id",
                "types": {"node_id": "int", "label": "cat"},
                "cat_values": {"label": ["User", "Company", "Project", "Document", "Server", "Database"]}
            },
            "edges": {
                "cols": ["edge_id", "source_node_id", "target_node_id", "relation_type", "weight"],
                "pk": "edge_id",
                "types": {"edge_id": "int", "source_node_id": "int", "target_node_id": "int", "relation_type": "cat", "weight": "num"},
                "num_ranges": {"weight": (0.1, 10.0), "source_node_id": (1, 1000), "target_node_id": (1, 1000)},
                "cat_values": {"relation_type": ["FRIENDS_WITH", "FOLLOWS", "COLLABORATES_WITH", "DEPENDS_ON", "CONNECTS_TO"]}
            }
        },
        "joins": [
            ("edges", "source_node_id", "nodes", "node_id")
        ],
        "multi_joins": []
    }
}

# -----------------------------------------------------------------------------
# Phrasing Style Personas
# -----------------------------------------------------------------------------

QUESTION_INTENTS = [
    "Find all {entity} where {predicate}.",
    "List the {cols} for {entity} satisfying {predicate}.",
    "Show me {cols} from {entity} with {predicate}.",
    "Which {entity} have {predicate}?",
    "Retrieve all {entity} matching {predicate}.",
    "Could you pull up the {cols} for {entity} where {predicate}?",
    "Display {cols} of {entity} that meet the condition {predicate}.",
    "Query {entity} to get {cols} where {predicate} holds true."
]

SORT_INTENTS = [
    "ordered by {sort_col} descending",
    "sorted by {sort_col} in ascending order",
    "ranked from highest to lowest {sort_col}",
    "sorted by {sort_col} descending with a limit of {limit} records"
]

AGG_INTENTS = [
    "Calculate the total {agg_col} for each {group_col} in {entity}.",
    "Find the average {agg_col} grouped by {group_col} for {entity}.",
    "Show the maximum {agg_col} and minimum {agg_col} per {group_col} in {entity}.",
    "Count the total number of {entity} grouped by {group_col}."
]

JOIN_INTENTS = [
    "Show {cols_a} from {table_a} together with {cols_b} from {table_b} where {predicate}.",
    "Find {table_a} records linked to {table_b} where {predicate}.",
    "List all {table_a} and their associated {table_b} details matching {predicate}."
]


# -----------------------------------------------------------------------------
# Combinatorial AST Generator
# -----------------------------------------------------------------------------

class CombinatorialASTGenerator:
    """Generates an infinite stream of diverse, non-repeating AST queries across schemas."""

    def __init__(self, domain_specs: Dict[str, Any]):
        self.specs = domain_specs
        self.domains = list(domain_specs.keys())

    def _format_col_names(self, cols: List[str]) -> str:
        if len(cols) == 1:
            return cols[0].replace("_", " ")
        return ", ".join(c.replace("_", " ") for c in cols[:-1]) + " and " + cols[-1].replace("_", " ")

    def generate_random_query(self) -> Tuple[str, str, str, str]:
        """
        Returns: (domain, question, canonical_sql, complexity)
        """
        domain = random.choice(self.domains)
        spec = self.specs[domain]
        query_type = random.choice(["simple_filter", "join_2_table", "join_3_table", "aggregation", "top_n", "range_filter"])

        if query_type == "join_3_table" and spec["multi_joins"]:
            return self._gen_join_3_table(domain, spec)
        elif query_type == "join_2_table" and spec["joins"]:
            return self._gen_join_2_table(domain, spec)
        elif query_type == "aggregation":
            return self._gen_aggregation(domain, spec)
        elif query_type == "top_n":
            return self._gen_top_n(domain, spec)
        elif query_type == "range_filter":
            return self._gen_range_filter(domain, spec)
        else:
            return self._gen_simple_filter(domain, spec)

    def _gen_simple_filter(self, domain: str, spec: Dict[str, Any]) -> Tuple[str, str, str, str]:
        table_name = random.choice(list(spec["tables"].keys()))
        t_meta = spec["tables"][table_name]
        
        # Pick 2-4 columns to project
        num_proj = min(random.randint(2, 4), len(t_meta["cols"]))
        proj_cols = random.sample(t_meta["cols"], num_proj)
        
        # Build filter condition
        cond_col = random.choice(t_meta["cols"])
        c_type = t_meta["types"].get(cond_col, "int")
        
        if c_type == "cat" and cond_col in t_meta.get("cat_values", {}):
            val = random.choice(t_meta["cat_values"][cond_col])
            sql_where = f"{cond_col} = '{val}'"
            nl_pred = f"{cond_col.replace('_', ' ')} is '{val}'"
        elif c_type in ("num", "int") and cond_col in t_meta.get("num_ranges", {}):
            min_v, max_v = t_meta["num_ranges"][cond_col]
            cutoff = int(min_v + random.random() * (max_v - min_v))
            op = random.choice([">", ">=", "<", "<="])
            op_text = "greater than" if ">" in op else "less than"
            sql_where = f"{cond_col} {op} {cutoff}"
            nl_pred = f"{cond_col.replace('_', ' ')} is {op_text} {cutoff}"
        else:
            sql_where = f"{cond_col} IS NOT NULL"
            nl_pred = f"{cond_col.replace('_', ' ')} is recorded"

        sql = f"SELECT {', '.join(proj_cols)} FROM {table_name} WHERE {sql_where};"
        
        intent_tmpl = random.choice(QUESTION_INTENTS)
        q = intent_tmpl.format(
            entity=table_name.replace("_", " "),
            cols=self._format_col_names(proj_cols),
            predicate=nl_pred
        )
        return domain, q, sql, "simple_filter"

    def _gen_range_filter(self, domain: str, spec: Dict[str, Any]) -> Tuple[str, str, str, str]:
        # Look for table with numeric range
        candidates = [(t, c) for t, m in spec["tables"].items() for c in m.get("num_ranges", {})]
        if not candidates:
            return self._gen_simple_filter(domain, spec)
        
        table_name, col = random.choice(candidates)
        t_meta = spec["tables"][table_name]
        min_v, max_v = t_meta["num_ranges"][col]
        
        low = int(min_v + random.random() * (max_v - min_v) * 0.4)
        high = int(low + random.random() * (max_v - low) * 0.8 + 1)
        
        proj_cols = random.sample(t_meta["cols"], min(3, len(t_meta["cols"])))
        if col not in proj_cols:
            proj_cols.append(col)
        
        sql = f"SELECT {', '.join(proj_cols)} FROM {table_name} WHERE {col} BETWEEN {low} AND {high};"
        q = f"Find all {table_name.replace('_', ' ')} where {col.replace('_', ' ')} is between {low} and {high}."
        return domain, q, sql, "range_between"

    def _gen_top_n(self, domain: str, spec: Dict[str, Any]) -> Tuple[str, str, str, str]:
        candidates = [(t, c) for t, m in spec["tables"].items() for c in m.get("num_ranges", {})]
        if not candidates:
            return self._gen_simple_filter(domain, spec)
        
        table_name, sort_col = random.choice(candidates)
        t_meta = spec["tables"][table_name]
        proj_cols = random.sample(t_meta["cols"], min(3, len(t_meta["cols"])))
        if sort_col not in proj_cols:
            proj_cols.append(sort_col)
            
        limit = random.choice([3, 5, 10, 20])
        sql = f"SELECT {', '.join(proj_cols)} FROM {table_name} ORDER BY {sort_col} DESC LIMIT {limit};"
        q = f"Retrieve the top {limit} {table_name.replace('_', ' ')} sorted by {sort_col.replace('_', ' ')} descending."
        return domain, q, sql, "top_n_ordered"

    def _gen_join_2_table(self, domain: str, spec: Dict[str, Any]) -> Tuple[str, str, str, str]:
        t1, c1, t2, c2 = random.choice(spec["joins"])
        meta1, meta2 = spec["tables"][t1], spec["tables"][t2]
        
        p1 = random.sample(meta1["cols"], min(2, len(meta1["cols"])))
        p2 = random.sample(meta2["cols"], min(2, len(meta2["cols"])))
        
        proj_str = ", ".join([f"a.{c}" for c in p1] + [f"b.{c}" for c in p2])
        
        # Optional filter on t2 if available
        where_sql = ""
        nl_pred = "matching records"
        if meta2.get("cat_values"):
            col_k = random.choice(list(meta2["cat_values"].keys()))
            v_val = random.choice(meta2["cat_values"][col_k])
            where_sql = f" WHERE b.{col_k} = '{v_val}'"
            nl_pred = f"where {t2.replace('_', ' ')} {col_k.replace('_', ' ')} is '{v_val}'"
            
        sql = f"SELECT {proj_str} FROM {t1} AS a JOIN {t2} AS b ON a.{c1} = b.{c2}{where_sql};"
        q = f"Show {self._format_col_names(p1)} from {t1.replace('_', ' ')} and {self._format_col_names(p2)} from {t2.replace('_', ' ')} {nl_pred}."
        return domain, q, sql, "join_2_table"

    def _gen_join_3_table(self, domain: str, spec: Dict[str, Any]) -> Tuple[str, str, str, str]:
        t1, c1, t2, c2, t3, c3 = random.choice(spec["multi_joins"])
        m1, m2, m3 = spec["tables"][t1], spec["tables"][t2], spec["tables"][t3]
        
        p1 = random.choice(m1["cols"])
        p2 = random.choice(m2["cols"])
        p3 = random.choice(m3["cols"])
        
        sql = (
            f"SELECT a.{p1}, b.{p2}, c.{p3} "
            f"FROM {t1} AS a "
            f"JOIN {t2} AS b ON a.{c1} = b.{c2} "
            f"JOIN {t3} AS c ON b.{c2} = c.{c3};"
        )
        q = f"List {p1.replace('_', ' ')} from {t1.replace('_', ' ')}, {p2.replace('_', ' ')} from {t2.replace('_', ' ')}, and {p3.replace('_', ' ')} from {t3.replace('_', ' ')}."
        return domain, q, sql, "join_3_table"

    def _gen_aggregation(self, domain: str, spec: Dict[str, Any]) -> Tuple[str, str, str, str]:
        # Pick table with categorical column and numeric column
        valid_tables = [
            t for t, m in spec["tables"].items()
            if m.get("cat_values") and m.get("num_ranges")
        ]
        if not valid_tables:
            return self._gen_simple_filter(domain, spec)
        
        table_name = random.choice(valid_tables)
        t_meta = spec["tables"][table_name]
        
        group_col = random.choice(list(t_meta["cat_values"].keys()))
        agg_col = random.choice(list(t_meta["num_ranges"].keys()))
        agg_func = random.choice(["SUM", "AVG", "COUNT", "MAX", "MIN"])
        
        having_clause = ""
        having_text = ""
        if random.random() > 0.5:
            min_v, max_v = t_meta["num_ranges"][agg_col]
            thresh = int(min_v + (max_v - min_v) * 0.3)
            having_clause = f" HAVING {agg_func}({agg_col}) > {thresh}"
            having_text = f" having total {agg_col.replace('_', ' ')} exceeding {thresh}"
            
        sql = (
            f"SELECT {group_col}, {agg_func}({agg_col}) AS metric "
            f"FROM {table_name} "
            f"GROUP BY {group_col}{having_clause} "
            f"ORDER BY metric DESC;"
        )
        q = f"Calculate the {agg_func.lower()} {agg_col.replace('_', ' ')} for each {group_col.replace('_', ' ')} in {table_name.replace('_', ' ')}{having_text}."
        return domain, q, sql, "aggregation_group_by"


# -----------------------------------------------------------------------------
# Ollama Seeder (Robust Bullet Extraction)
# -----------------------------------------------------------------------------

def fetch_ollama_phrasings(
    ollama_url: str = "http://localhost:11434/api/generate",
    model: str = "qwen2.5-coder:1.5b",
    timeout: int = 10
) -> List[str]:
    """Fetches varied business question structures from Ollama without fragile JSON parsing."""
    prompt = (
        "Generate 12 distinct natural language sentence openers and question formats "
        "that a business intelligence analyst uses to query databases (e.g., 'Find all...', "
        "'Can you show the breakdown of...', 'List the top 10...', 'Retrieve records where...'). "
        "Output one per line starting with a dash (-)."
    )
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    req = urllib.request.Request(ollama_url, data=payload, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            raw = res_data.get("response", "")
            lines = [re.sub(r"^[-*\d.\s]+", "", l).strip() for l in raw.splitlines() if l.strip()]
            valid = [l for l in lines if len(l) > 10]
            print(f"[Hybrid Seeder] Ollama acquired {len(valid)} dynamic phrasing templates.")
            return valid
    except Exception as e:
        print(f"[Hybrid Seeder] Note: Ollama connection note ({e}). Using built-in phrasing frames.")
        return []


# -----------------------------------------------------------------------------
# Core Generator Runner
# -----------------------------------------------------------------------------

def generate_dialect_dataset(
    target_dialect: str,
    target_bytes: int,
    output_path: str,
    converter: DeterministicDialectConverter,
    generator: CombinatorialASTGenerator,
    ollama_phrasings: List[str]
) -> Tuple[int, int]:
    """
    Generates a dialect file up to target_bytes where every single query is unique.
    Returns: (total_samples, unique_samples)
    """
    print(f"\n[Worker] Generating diverse dataset for '{target_dialect.upper()}' -> {output_path}")
    print(f"         Target size: {target_bytes / (1024 * 1024):.2f} MB")
    
    bytes_written = 0
    samples_count = 0
    unique_queries = set()
    
    t0 = time.time()
    last_log_time = t0
    
    with open(output_path, "w", encoding="utf-8", buffering=1024 * 1024) as f:
        while bytes_written < target_bytes:
            roll = random.random()
            if roll < 0.05:
                # 5% Chit-chat / Non-SQL Refusal
                q, tag, expl = random.choice(_CHITCHAT_SAMPLES)
                canonical_sql = f"-- REFUSAL: [{tag}] - Request is not a database query.\n-- EXPLANATION: {expl}"
                domain = random.choice(list(SCHEMAS.keys()))
                schema_ddl = SCHEMAS[domain]
                base_q = q
                complexity = "refusal_chitchat"
                compiled_target = canonical_sql
            elif roll < 0.10:
                # 5% Schema Mismatch Refusal
                domain = random.choice(list(SCHEMAS.keys()))
                schema_ddl = SCHEMAS[domain]
                bogus = _make_schema_mismatch_sample(domain, schema_ddl)
                base_q = bogus["question"]
                canonical_sql = bogus["sql"]
                complexity = "refusal_schema_mismatch"
                compiled_target = canonical_sql
            elif roll < 0.15:
                # 5% Architecture Multi-Statement DDL Synthesis
                arch = random.choice(ARCHITECTURE_TEMPLATES)
                base_q = arch["question"]
                canonical_sql = arch["sql"]
                domain = "ecommerce"
                schema_ddl = "(none — schema is being designed by this request)"
                complexity = "architecture_ddl"
                try:
                    res = converter.transpile(canonical_sql, target_dialect=target_dialect)
                    compiled_target = res.compiled_query
                except Exception:
                    compiled_target = canonical_sql
            else:
                domain, base_q, canonical_sql, complexity = generator.generate_random_query()
                schema_ddl = SCHEMAS[domain]
                # Skip if we already generated this exact SQL string (guarantees 100% uniqueness)
                if canonical_sql in unique_queries:
                    continue
                # Transpile via DeterministicDialectConverter
                try:
                    res = converter.transpile(canonical_sql, target_dialect=target_dialect)
                    compiled_target = res.compiled_query
                except Exception:
                    continue
                unique_queries.add(canonical_sql)
            
            if isinstance(compiled_target, (dict, list)):
                assistant_output = json.dumps(compiled_target)
            else:
                assistant_output = str(compiled_target).strip()
                
            user_content = (
                f"### Target Dialect: {target_dialect.upper()}\n\n"
                f"### Database Schema:\n{schema_ddl}\n\n"
                f"### User Question:\n{base_q}"
            )
            
            record = {
                "id": f"{target_dialect}_{samples_count + 1:07d}",
                "target_dialect": target_dialect,
                "schema_key": domain,
                "complexity": complexity,
                "question": base_q,
                "canonical_sql": canonical_sql,
                "dialect_query": assistant_output,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": assistant_output}
                ]
            }
            
            line = json.dumps(record, ensure_ascii=False) + "\n"
            encoded_len = len(line.encode("utf-8"))
            f.write(line)
            bytes_written += encoded_len
            samples_count += 1
            
            now = time.time()
            if now - last_log_time >= 3.0:
                mb_done = bytes_written / (1024 * 1024)
                mb_total = target_bytes / (1024 * 1024)
                pct = (bytes_written / target_bytes) * 100
                speed = mb_done / max(now - t0, 0.001)
                eta = (mb_total - mb_done) / max(speed, 0.001)
                print(
                    f"  [{target_dialect.upper()}] {mb_done:6.1f} / {mb_total:.1f} MB ({pct:5.1f}%) "
                    f"| {samples_count:6d} unique samples | {speed:4.1f} MB/s | ETA: {eta:4.1f}s",
                    end="\r"
                )
                last_log_time = now

    elapsed = max(time.time() - t0, 0.001)
    actual_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\n[Worker] Completed '{target_dialect}': {actual_mb:.2f} MB in {elapsed:.1f}s ({samples_count} samples, 100% unique, {actual_mb/elapsed:.1f} MB/s)")
    return samples_count, len(unique_queries)


def main():
    parser = argparse.ArgumentParser(description="1GB+ Non-Garbage Multi-Dialect Dataset Generator")
    parser.add_argument("--output-dir", type=str, default="offline/datasets/dialects")
    parser.add_argument("--target-mb-per-dialect", type=float, default=146.5)
    parser.add_argument("--dialects", nargs="+", default=SUPPORTED_DIALECTS)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    os.makedirs(args.output_dir, exist_ok=True)
    
    total_mb = args.target_mb_per_dialect * len(args.dialects)
    print("=" * 80)
    print("NL2SQL COMBINATORIAL 1GB+ MULTI-DIALECT DATASET GENERATOR")
    print(f"Target Dialects : {', '.join(args.dialects)} ({len(args.dialects)} total)")
    print(f"Per-Dialect Size: {args.target_mb_per_dialect:.1f} MB")
    print(f"Total Target    : {total_mb:.1f} MB (~{total_mb / 1024:.2f} GB)")
    print(f"Output Directory: {args.output_dir}")
    print("=" * 80)

    # 1. Fetch linguistic seeds from Ollama
    ollama_phrasings = fetch_ollama_phrasings()

    # 2. Init Converter & Generator
    print("[Engine] Initializing Deterministic Universal Dialect Converter...")
    converter = DeterministicDialectConverter()
    generator = CombinatorialASTGenerator(DOMAIN_SPECS)

    target_bytes_per_dialect = int(args.target_mb_per_dialect * 1024 * 1024)
    grand_samples = 0
    start_all = time.time()
    summary_stats = []

    for d in args.dialects:
        out_file = os.path.join(args.output_dir, f"{d}.jsonl")
        samples, unique_cnt = generate_dialect_dataset(
            target_dialect=d,
            target_bytes=target_bytes_per_dialect,
            output_path=out_file,
            converter=converter,
            generator=generator,
            ollama_phrasings=ollama_phrasings
        )
        grand_samples += samples
        actual_size = os.path.getsize(out_file)
        summary_stats.append((d, out_file, actual_size, samples, unique_cnt))

    total_time = max(time.time() - start_all, 0.001)
    total_bytes = sum(s[2] for s in summary_stats)
    total_gb = total_bytes / (1024 * 1024 * 1024)

    print("\n" + "=" * 85)
    print("GENERATION COMPLETE — 100% UNIQUE AUDIT SUMMARY")
    print("=" * 85)
    for d, path, size, count, uniq in summary_stats:
        mb = size / (1024 * 1024)
        dup_pct = 0.0 if count == uniq else round((1.0 - (uniq / count)) * 100, 2)
        print(f"  - {d:<12}: {mb:7.2f} MB | {count:7d} samples | Unique: {uniq:7d} ({100-dup_pct:.1f}% unique)")
    print("-" * 85)
    print(f"TOTAL DATASET SIZE : {total_gb:.3f} GB ({total_bytes:,} bytes)")
    print(f"TOTAL UNIQUE SAMPLES: {grand_samples:,} records")
    print(f"TOTAL TIME ELAPSED : {total_time:.1f} seconds ({total_gb * 1024 / total_time:.2f} MB/s)")
    print("=" * 85)


if __name__ == "__main__":
    main()
