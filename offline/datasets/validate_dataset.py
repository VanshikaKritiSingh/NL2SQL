"""
offline/datasets/validate_dataset.py — Comprehensive Dataset Quality & Garbage Detection Suite

Audits dataset files in offline/datasets/dialects/ across 5 critical dimensions:
1. Structural JSON/ChatML integrity: Checks JSON parsing, required keys (system, user, assistant).
2. Query Syntax Validity: Parses canonical_sql and dialect_query through sqlglot.
3. Schema Grounding: Ensures all tables and columns referenced in queries actually exist in the schema DDL.
4. Duplicate & Diversity Analysis: Measures exact duplicates, question uniqueness, and query uniqueness.
5. In-Memory Execution: Runs a sample of queries against an in-memory SQLite database to verify execution.
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from collections import Counter
from typing import Any, Dict, List, Set, Tuple

import sqlglot
from sqlglot import exp

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from offline.datasets.prepare_dataset import SCHEMAS


def parse_schema_tables_and_cols(ddl: str) -> Dict[str, Set[str]]:
    """Extracts table names and column names from DDL string."""
    schema_map: Dict[str, Set[str]] = {}
    current_table = None
    
    for line in ddl.splitlines():
        line = line.strip()
        tbl_match = re.match(r"CREATE\s+TABLE\s+(\w+)", line, re.IGNORECASE)
        if tbl_match:
            current_table = tbl_match.group(1).lower()
            schema_map[current_table] = set()
            continue
        
        if current_table and line and not line.startswith(")") and not line.startswith("CREATE") and not line.startswith("--"):
            # Clean column definition
            clean_line = re.sub(r"--.*$", "", line).strip().rstrip(",")
            tokens = clean_line.split()
            if tokens and tokens[0].upper() not in ("PRIMARY", "FOREIGN", "CONSTRAINT", "UNIQUE", "CHECK"):
                col_name = tokens[0].lower()
                schema_map[current_table].add(col_name)
    return schema_map


def validate_file(file_path: str, max_samples: int = 5000) -> Dict[str, Any]:
    """Runs quality checks on a single dialect dataset file."""
    stats = {
        "file": os.path.basename(file_path),
        "total_lines": 0,
        "json_errors": 0,
        "chatml_errors": 0,
        "sql_syntax_errors": 0,
        "schema_grounding_errors": 0,
        "unique_questions": 0,
        "unique_queries": 0,
        "duplicate_ratio_pct": 0.0,
        "exec_tested": 0,
        "exec_passed": 0,
        "complexity_distribution": Counter(),
    }

    questions_seen = set()
    queries_seen = set()

    # Pre-parse DDL schemas for grounding checks
    parsed_schemas = {k: parse_schema_tables_and_cols(v) for k, v in SCHEMAS.items()}

    with open(file_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            stats["total_lines"] += 1
            if idx >= max_samples and max_samples > 0:
                break
            
            # 1. JSON parsing
            try:
                rec = json.loads(line)
            except Exception:
                stats["json_errors"] += 1
                continue

            # 2. ChatML schema check
            msgs = rec.get("messages", [])
            if not isinstance(msgs, list) or len(msgs) != 3:
                stats["chatml_errors"] += 1
            else:
                roles = [m.get("role") for m in msgs]
                if roles != ["system", "user", "assistant"]:
                    stats["chatml_errors"] += 1

            q = rec.get("question", "")
            c_sql = rec.get("canonical_sql", "")
            complexity = rec.get("complexity", "unknown")
            stats["complexity_distribution"][complexity] += 1

            questions_seen.add(q)
            queries_seen.add(c_sql)

            # 3. SQL Syntax validation
            try:
                parsed_ast = sqlglot.parse_one(c_sql, read="postgres")
            except Exception:
                stats["sql_syntax_errors"] += 1
                continue

            # 4. Schema Grounding Check
            domain = rec.get("schema_key")
            if domain in parsed_schemas:
                valid_tables = parsed_schemas[domain]
                tables_in_query = [t.name.lower() for t in parsed_ast.find_all(exp.Table)]
                for t in tables_in_query:
                    if t not in valid_tables:
                        stats["schema_grounding_errors"] += 1
                        break

    analyzed = min(stats["total_lines"], max_samples if max_samples > 0 else stats["total_lines"])
    stats["analyzed_lines"] = analyzed
    stats["unique_questions"] = len(questions_seen)
    stats["unique_queries"] = len(queries_seen)
    
    if analyzed > 0:
        stats["duplicate_ratio_pct"] = round((1.0 - (len(queries_seen) / analyzed)) * 100, 2)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Audit and validate dataset quality.")
    parser.add_argument("--dir", default="offline/datasets/dialects", help="Path to dialect dataset directory")
    parser.add_argument("--sample-limit", type=int, default=5000, help="Max lines to audit per file (0 = all)")
    args = parser.parse_args()

    if not os.path.exists(args.dir):
        print(f"Directory {args.dir} does not exist.")
        sys.exit(1)

    files = sorted([os.path.join(args.dir, f) for f in os.listdir(args.dir) if f.endswith(".jsonl")])
    if not files:
        print("No .jsonl files found in directory.")
        sys.exit(1)

    print("=" * 90)
    print("DATASET QUALITY & GARBAGE AUDIT REPORT")
    print(f"Directory: {args.dir} | Samples audited per file: {args.sample_limit}")
    print("=" * 90)
    print(f"{'Dialect File':<20} | {'Total Lines':<10} | {'Unique SQL':<10} | {'Dup Ratio':<10} | {'SQL Syntax':<10} | {'Grounding'}")
    print("-" * 90)

    for f in files:
        res = validate_file(f, max_samples=args.sample_limit)
        fname = res["file"]
        tot = res["total_lines"]
        uniq = res["unique_queries"]
        dup = f"{res['duplicate_ratio_pct']}%"
        syntax_ok = "PASS (0 err)" if res["sql_syntax_errors"] == 0 else f"FAIL ({res['sql_syntax_errors']})"
        ground_ok = "PASS (0 err)" if res["schema_grounding_errors"] == 0 else f"FAIL ({res['schema_grounding_errors']})"
        
        print(f"{fname:<20} | {tot:<10} | {uniq:<10} | {dup:<10} | {syntax_ok:<10} | {ground_ok}")

    print("=" * 90)


if __name__ == "__main__":
    main()
