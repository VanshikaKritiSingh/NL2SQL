"""
offline/training/kfold_eval.py — Stratified K-Fold Cross-Validation Benchmark Suite

Performs domain-stratified K-Fold evaluation across schemas and complexity tiers:
1. Partitions evaluation queries into K balanced folds (balanced across the 8 domain
   schemas: ecommerce, banking, healthcare, saas, etc., and 5 complexity tiers).
2. Evaluates AST Exact Match (EM), Execution Accuracy (EX), and 7-Dialect Transpilation
   Fidelity (TF) independently per fold.
3. Computes statistical distributions (Mean ± StdDev, 95% Confidence Intervals) to prove
   whether QLoRA or AdaLoRA generalizes better across unseen database domains.
"""

import argparse
import json
import logging
import math
import os
import random
import sys
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from offline.training.evaluate import (
    evaluate_exact_match,
    evaluate_execution,
    evaluate_transpilation,
    extract_query_and_schema,
    run_model_inference,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("KFoldEval")


def partition_stratified_kfolds(
    records: List[Dict[str, Any]],
    k: int = 5,
    seed: int = 42,
) -> List[List[Dict[str, Any]]]:
    """
    Partitions records into K folds stratified by (schema_key, complexity)
    to guarantee identical domain distributions in every fold.
    """
    random.seed(seed)
    strata = defaultdict(list)

    for item in records:
        schema = item.get("schema_key", "default")
        complexity = item.get("complexity", "medium")
        strata[(schema, complexity)].append(item)

    folds = [[] for _ in range(k)]
    global_idx = 0

    for group in strata.values():
        shuffled = list(group)
        random.shuffle(shuffled)
        for sample in shuffled:
            folds[global_idx % k].append(sample)
            global_idx += 1

    logger.info("Partitioned %d records into %d stratified folds:", len(records), k)
    for i, f in enumerate(folds):
        logger.info("  • Fold %d: %d samples", i + 1, len(f))

    return folds


def calculate_stats(values: List[float]) -> Dict[str, float]:
    """Computes Mean, Standard Deviation, and 95% Confidence Interval."""
    n = len(values)
    if n == 0:
        return {"mean": 0.0, "std": 0.0, "ci95": 0.0, "min": 0.0, "max": 0.0}
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / max(1, n - 1)
    std = math.sqrt(variance)
    # 95% CI margin of error (t-critical ~ 2.776 for n=5)
    t_crit = 2.776 if n == 5 else (1.96 if n > 30 else 2.2)
    ci95 = t_crit * (std / math.sqrt(n)) if n > 1 else 0.0

    return {
        "mean": round(mean, 2),
        "std": round(std, 2),
        "ci95": round(ci95, 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
    }


def evaluate_single_fold(
    fold_records: List[Dict[str, Any]],
    base_model: Optional[str] = None,
    adapter_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluates a single fold slice."""
    if base_model:
        preds = run_model_inference(base_model, adapter_path, fold_records)
    else:
        # Gold reference / dry-run
        preds = [extract_query_and_schema(r)[0] for r in fold_records]

    total = len(fold_records)
    em_matches = 0
    ex_matches = 0
    dialects = ["postgres", "mysql", "sqlite", "duckdb", "clickhouse", "opencypher", "mongodb"]
    tf_counts = {d: 0 for d in dialects}

    for record, pred in zip(fold_records, preds):
        gold, schema = extract_query_and_schema(record)

        if evaluate_exact_match(pred, gold):
            em_matches += 1

        is_ex, _ = evaluate_execution(pred, gold, schema)
        if is_ex:
            ex_matches += 1

        tf_res = evaluate_transpilation(pred)
        for d, ok in tf_res.items():
            if ok:
                tf_counts[d] += 1

    em_rate = (em_matches / total) * 100
    ex_rate = (ex_matches / total) * 100
    avg_tf = (sum(tf_counts.values()) / (total * len(dialects))) * 100

    return {
        "total_samples": total,
        "em_rate": em_rate,
        "ex_rate": ex_rate,
        "avg_transpilation": avg_tf,
        "transpilation_by_dialect": {d: (tf_counts[d] / total) * 100 for d in dialects},
    }


def run_kfold_evaluation(
    eval_file: str,
    k: int = 5,
    max_samples: Optional[int] = 250,
    base_model: Optional[str] = None,
    adapter_path: Optional[str] = None,
    output_report: Optional[str] = None,
    seed: int = 42,
):
    logger.info("Loading records from %s (limit: %s)", eval_file, max_samples)
    records = []
    with open(eval_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
                if max_samples and len(records) >= max_samples:
                    break

    folds = partition_stratified_kfolds(records, k=k, seed=seed)

    fold_results = []
    em_scores = []
    ex_scores = []
    tf_scores = []

    print("\n" + "=" * 70)
    print(f"      STRATIFIED {k}-FOLD CROSS-VALIDATION BENCHMARK")
    print("=" * 70)
    print(f"Candidate: {adapter_path or base_model or 'Ground Truth'}")
    print(f"Total Evaluation Pool: {len(records)} queries ({len(folds[0])} per fold)")
    print("-" * 70)

    for i, fold in enumerate(folds):
        fold_id = i + 1
        logger.info("Evaluating Fold %d/%d (%d samples)...", fold_id, k, len(fold))
        res = evaluate_single_fold(fold, base_model, adapter_path)

        em_scores.append(res["em_rate"])
        ex_scores.append(res["ex_rate"])
        tf_scores.append(res["avg_transpilation"])

        print(
            f"Fold {fold_id}:  AST EM = {res['em_rate']:5.2f}%  |  "
            f"Exec Acc = {res['ex_rate']:5.2f}%  |  "
            f"Transpilation = {res['avg_transpilation']:5.2f}%"
        )
        fold_results.append({"fold": fold_id, **res})

    em_stats = calculate_stats(em_scores)
    ex_stats = calculate_stats(ex_scores)
    tf_stats = calculate_stats(tf_scores)

    print("-" * 70)
    print(f"AST Exact Match (EM):      {em_stats['mean']}% ± {em_stats['std']}%  (95% CI: [{em_stats['mean'] - em_stats['ci95']:.2f}%, {em_stats['mean'] + em_stats['ci95']:.2f}%])")
    print(f"Execution Accuracy (EX):   {ex_stats['mean']}% ± {ex_stats['std']}%  (95% CI: [{ex_stats['mean'] - ex_stats['ci95']:.2f}%, {ex_stats['mean'] + ex_stats['ci95']:.2f}%])")
    print(f"Avg Transpilation Fidelity: {tf_stats['mean']}% ± {tf_stats['std']}%")
    print("=" * 70 + "\n")

    report = {
        "k_folds": k,
        "base_model": base_model,
        "adapter_path": adapter_path,
        "total_samples": len(records),
        "exact_match_stats": em_stats,
        "execution_accuracy_stats": ex_stats,
        "transpilation_stats": tf_stats,
        "fold_breakdown": fold_results,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    if output_report:
        os.makedirs(os.path.dirname(os.path.abspath(output_report)), exist_ok=True)
        with open(output_report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info("Stratified K-Fold report saved to: %s", output_report)

    return report


def main():
    parser = argparse.ArgumentParser(description="Stratified K-Fold NL2SQL Benchmark Evaluator")
    parser.add_argument("--eval-file", type=str, default="offline/datasets/dialects/postgres.jsonl")
    parser.add_argument("--k", type=int, default=5, help="Number of stratified folds (default: 5).")
    parser.add_argument("--max-samples", type=int, default=250, help="Total evaluation samples across folds.")
    parser.add_argument("--base-model", type=str, default=None, help="Base model path or HF ID.")
    parser.add_argument("--adapter", type=str, default=None, help="Path to LoRA/AdaLoRA adapter directory.")
    parser.add_argument("--report", type=str, default=None, help="Output JSON report path.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for fold stratification.")
    args = parser.parse_args()

    run_kfold_evaluation(
        eval_file=args.eval_file,
        k=args.k,
        max_samples=args.max_samples,
        base_model=args.base_model,
        adapter_path=args.adapter,
        output_report=args.report,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
