"""
offline/training/evaluate.py — Unified Benchmark Evaluator for Base, QLoRA, and AdaLoRA

Evaluates models and PEFT adapters across 3 core benchmarks:
1. AST Exact Match (EM): Structural equality via SQLGlot normalization.
2. Execution Accuracy (EX): Real in-memory SQLite execution comparing row sets.
3. Transpilation Fidelity (TF): Passing predicted AST through DialectConverter
   to verify syntax across 7 targets: Postgres, MySQL, SQLite, DuckDB, ClickHouse,
   openCypher, and MongoDB.
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import sqlglot

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
try:
    from core.dialect_converter import DeterministicDialectConverter
    CONVERTER_AVAILABLE = True
except ImportError:
    CONVERTER_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Benchmark")


def normalize_ast(sql: str, dialect: str = "postgres") -> Optional[str]:
    """Parses and normalizes SQL into canonical syntax for structural comparison."""
    try:
        parsed = sqlglot.parse_one(sql, read=dialect)
        return parsed.sql(dialect="postgres", pretty=False)
    except Exception:
        return None


def evaluate_exact_match(pred_sql: str, gold_sql: str) -> bool:
    """Compares two SQL queries structurally via AST normalization."""
    ast_pred = normalize_ast(pred_sql)
    ast_gold = normalize_ast(gold_sql)

    if ast_pred and ast_gold:
        return ast_pred == ast_gold
    # Fallback to whitespace/case-insensitive comparison
    return " ".join(pred_sql.strip().lower().split()) == " ".join(gold_sql.strip().lower().split())


def create_in_memory_db(schema_ddl: str) -> sqlite3.Connection:
    """Initializes an in-memory SQLite DB populated with the provided DDL."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    # Clean PostgreSQL specific types for SQLite compatibility
    sqlite_ddl = (
        schema_ddl.replace("UUID", "TEXT")
        .replace("BOOLEAN", "INTEGER")
        .replace("DECIMAL(12, 2)", "REAL")
        .replace("DECIMAL(10, 2)", "REAL")
        .replace("TIMESTAMP", "TEXT")
        .replace("NOW()", "CURRENT_TIMESTAMP")
    )
    for statement in sqlite_ddl.split(";"):
        stmt = statement.strip()
        if stmt:
            try:
                cursor.execute(stmt)
            except Exception:
                pass
    conn.commit()
    return conn


def evaluate_execution(pred_sql: str, gold_sql: str, schema_ddl: str) -> Tuple[bool, str]:
    """Executes both queries on an in-memory DB and compares result sets."""
    try:
        conn = create_in_memory_db(schema_ddl)
        cursor = conn.cursor()
    except Exception as e:
        return False, f"DB Init Error: {e}"

    try:
        gold_res = cursor.execute(gold_sql).fetchall()
    except Exception as e:
        return False, f"Gold Execution Error: {e}"

    try:
        pred_res = cursor.execute(pred_sql).fetchall()
    except Exception as e:
        return False, f"Pred Execution Error: {e}"

    # Set comparison for unordered results, list comparison for ordered
    if "ORDER BY" in gold_sql.upper():
        is_match = gold_res == pred_res
    else:
        try:
            is_match = set(gold_res) == set(pred_res)
        except TypeError:
            is_match = gold_res == pred_res

    return is_match, "Success" if is_match else "Mismatch"


def evaluate_transpilation(sql: str) -> Dict[str, bool]:
    """Tests transpilation of the SQL query across all 7 supported dialects."""
    if not CONVERTER_AVAILABLE:
        return {}

    converter = DeterministicDialectConverter()
    dialects = ["postgres", "mysql", "sqlite", "duckdb", "clickhouse", "opencypher", "mongodb"]
    results = {}

    for d in dialects:
        try:
            res = converter.transpile(sql, target_dialect=d)
            results[d] = res is not None
        except Exception:
            results[d] = False

    return results


def run_model_inference(
    base_model_path: str,
    adapter_path: Optional[str],
    test_samples: List[Dict[str, Any]],
    max_new_tokens: int = 256,
) -> List[str]:
    """Runs generation inference using base model + optional PEFT adapter."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    is_cuda = torch.cuda.is_available()
    compute_dtype = torch.bfloat16 if (is_cuda and torch.cuda.is_bf16_supported()) else torch.float16

    logger.info("Loading Tokenizer for: %s", base_model_path)
    tokenizer = AutoTokenizer.from_pretrained(base_model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    logger.info("Loading Base Model: %s", base_model_path)
    model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        dtype=compute_dtype if is_cuda else torch.float32,
        device_map="auto" if is_cuda else None,
        trust_remote_code=True,
    )

    if adapter_path and os.path.exists(adapter_path):
        logger.info("Attaching PEFT Adapter from: %s", adapter_path)
        model = PeftModel.from_pretrained(model, adapter_path)

    model.eval()
    predictions = []

    logger.info("Running inference on %d test samples...", len(test_samples))
    for i, sample in enumerate(test_samples):
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert Text-to-Universal-SQL compiler. Generate deterministic, "
                    "syntactically valid Canonical ANSI/PostgreSQL AST queries adhering to the provided database schema."
                ),
            },
            {
                "role": "user",
                "content": f"### Database Schema:\n{sample.get('schema', '')}\n\n### User Question:\n{sample.get('question', '')}",
            },
        ]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt")
        if is_cuda:
            inputs = {k: v.cuda() for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )

        gen_tokens = outputs[0][inputs["input_ids"].shape[1] :]
        pred_text = tokenizer.decode(gen_tokens, skip_special_tokens=True).strip()

        # Clean markdown codeblocks if model returned ```sql ... ```
        if "```" in pred_text:
            lines = pred_text.splitlines()
            pred_text = "\n".join(l for l in lines if not l.strip().startswith("```")).strip()

        predictions.append(pred_text)
        if (i + 1) % 10 == 0 or (i + 1) == len(test_samples):
            logger.info("Evaluated %d/%d samples...", i + 1, len(test_samples))

    return predictions


def extract_query_and_schema(item: Dict[str, Any]) -> Tuple[str, str]:
    """Robustly extracts SQL query and schema DDL from various dataset formats."""
    sql = item.get("canonical_sql") or item.get("sql") or ""
    schema = item.get("schema", "")

    if "messages" in item and isinstance(item["messages"], list):
        for msg in item["messages"]:
            if msg.get("role") == "assistant" and not sql:
                sql = msg.get("content", "").strip()
            elif msg.get("role") == "user" and not schema:
                content = msg.get("content", "")
                if "### Database Schema:" in content:
                    parts = content.split("### Database Schema:\n")
                    if len(parts) > 1:
                        schema = parts[1].split("\n\n### User Question:")[0].strip()

    return sql, schema


def run_benchmark(
    base_model: Optional[str] = None,
    adapter_path: Optional[str] = None,
    eval_file: str = "offline/datasets/dialects/postgres.jsonl",
    max_samples: int = 100,
    output_report: Optional[str] = None,
):
    """Executes the full evaluation pipeline and compiles metric reports."""
    # 1. Load Evaluation Samples
    records = []
    with open(eval_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                item = json.loads(line)
                records.append(item)
                if len(records) >= max_samples:
                    break

    logger.info("Loaded %d benchmark evaluation samples from %s", len(records), eval_file)

    # 2. Obtain Predictions
    if base_model:
        preds = run_model_inference(base_model, adapter_path, records)
    else:
        # Dry-run or pre-computed predictions
        preds = [extract_query_and_schema(r)[0] for r in records]

    # 3. Calculate Benchmark Metrics
    total = len(records)
    em_matches = 0
    ex_matches = 0
    tf_dialects = {"postgres": 0, "mysql": 0, "sqlite": 0, "duckdb": 0, "clickhouse": 0, "opencypher": 0, "mongodb": 0}

    for i, (record, pred) in enumerate(zip(records, preds)):
        gold, schema = extract_query_and_schema(record)

        # Exact Match
        if evaluate_exact_match(pred, gold):
            em_matches += 1

        # Execution Accuracy
        is_ex, _ = evaluate_execution(pred, gold, schema)
        if is_ex:
            ex_matches += 1

        # Transpilation Fidelity
        tf_res = evaluate_transpilation(pred)
        for d, ok in tf_res.items():
            if ok:
                tf_dialects[d] += 1

    em_rate = (em_matches / total) * 100
    ex_rate = (ex_matches / total) * 100

    print("\n" + "=" * 65)
    print("           NL2SQL BENCHMARK EVALUATION RESULTS")
    print("=" * 65)
    print(f"Base Model:             {base_model or 'Ground Truth (Sanity)'}")
    print(f"PEFT Adapter:           {adapter_path or 'None (Base Zero-Shot)'}")
    print(f"Benchmark Test Size:    {total} queries")
    print("-" * 65)
    print(f"AST Exact Match (EM):   {em_matches}/{total} ({em_rate:.2f}%)")
    print(f"Execution Accuracy (EX): {ex_matches}/{total} ({ex_rate:.2f}%)")
    print("-" * 65)
    print("7-Dialect Transpilation Fidelity (TF):")
    for d, count in tf_dialects.items():
        print(f"  • {d.ljust(12)}: {count}/{total} ({(count/total)*100:.1f}%)")
    print("=" * 65 + "\n")

    report = {
        "base_model": base_model,
        "adapter_path": adapter_path,
        "test_samples": total,
        "exact_match_rate": em_rate,
        "execution_accuracy_rate": ex_rate,
        "transpilation_fidelity": {d: count / total for d, count in tf_dialects.items()},
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    if output_report:
        with open(output_report, "w") as f:
            json.dump(report, f, indent=2)
        logger.info("Report saved to: %s", output_report)


def main():
    parser = argparse.ArgumentParser(description="NL2SQL Benchmark Evaluator")
    parser.add_argument("--base-model", type=str, default=None, help="Base model path or HF ID.")
    parser.add_argument("--adapter", type=str, default=None, help="Path to LoRA/AdaLoRA adapter directory.")
    parser.add_argument("--eval-file", type=str, default="offline/datasets/dialects/postgres.jsonl")
    parser.add_argument("--max-samples", type=int, default=100, help="Number of benchmark samples to test.")
    parser.add_argument("--report", type=str, default=None, help="Output JSON benchmark report path.")
    args = parser.parse_args()

    run_benchmark(
        base_model=args.base_model,
        adapter_path=args.adapter,
        eval_file=args.eval_file,
        max_samples=args.max_samples,
        output_report=args.report,
    )


if __name__ == "__main__":
    main()
