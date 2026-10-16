"""
offline/training/compare_models.py — Automated Benchmark Comparison & Decision Engine

Compares evaluation reports across Base Model, QLoRA, and AdaLoRA to:
1. Generate side-by-side comparison tables.
2. Calculate performance deltas across Exact Match, Execution Accuracy, and Transpilation.
3. Automatically recommend the best candidate to ship based on accuracy and efficiency.
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


def load_report(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Warning] Failed to load {path}: {e}", file=sys.stderr)
        return None


def format_percent(val: Optional[float]) -> str:
    if val is None:
        return "N/A"
    return f"{val:.2f}%"


def compare_candidates(reports: Dict[str, Dict[str, Any]]) -> str:
    """Generates a clean comparison matrix and winner recommendation."""
    lines = []
    lines.append("\n" + "=" * 78)
    lines.append("              NL2SQL CANDIDATE COMPARISON MATRIX")
    lines.append("=" * 78)

    headers = ["Metric", *reports.keys()]
    col_width = 20
    header_str = f"{headers[0].ljust(col_width)}" + "".join(h.center(col_width) for h in headers[1:])
    lines.append(header_str)
    lines.append("-" * 78)

    # Base Model / Adapter Path
    model_row = f"{'Base Model'.ljust(col_width)}"
    for name, rep in reports.items():
        base = rep.get("base_model") or "Base"
        short_base = os.path.basename(base) if "/" in base else base
        model_row += short_base[:col_width - 2].center(col_width)
    lines.append(model_row)

    adapter_row = f"{'Adapter'.ljust(col_width)}"
    for name, rep in reports.items():
        ad = rep.get("adapter_path") or "None (Zero-Shot)"
        short_ad = os.path.basename(ad) if "/" in ad else ad
        adapter_row += short_ad[:col_width - 2].center(col_width)
    lines.append(adapter_row)

    lines.append("-" * 78)

    # Core Metrics
    em_row = f"{'AST Exact Match'.ljust(col_width)}"
    ex_row = f"{'Execution Accuracy'.ljust(col_width)}"
    for name, rep in reports.items():
        em_row += format_percent(rep.get("exact_match_rate")).center(col_width)
        ex_row += format_percent(rep.get("execution_accuracy_rate")).center(col_width)
    lines.append(em_row)
    lines.append(ex_row)

    lines.append("-" * 78)
    lines.append("Transpilation Fidelity (TF):")
    dialects = ["postgres", "mysql", "sqlite", "duckdb", "clickhouse", "opencypher", "mongodb"]
    for d in dialects:
        d_row = f"  • {d.ljust(col_width - 4)}"
        for name, rep in reports.items():
            tf = rep.get("transpilation_fidelity", {}).get(d, 0.0) * 100
            d_row += format_percent(tf).center(col_width)
        lines.append(d_row)

    lines.append("=" * 78)

    # Decision Engine: Rank candidates
    ranked = []
    for name, rep in reports.items():
        em = rep.get("exact_match_rate", 0.0) or 0.0
        ex = rep.get("execution_accuracy_rate", 0.0) or 0.0
        avg_tf = sum(rep.get("transpilation_fidelity", {}).values()) / max(1, len(dialects)) * 100
        # Weighted composite score: 40% Execution, 30% Exact Match, 30% Transpilation
        score = (ex * 0.40) + (em * 0.30) + (avg_tf * 0.30)
        ranked.append((name, score, ex, em, avg_tf, rep))

    ranked.sort(key=lambda x: x[1], reverse=True)
    winner = ranked[0]

    lines.append(f"\n🏆 RECOMMENDED WINNER TO SHIP: {winner[0].upper()}")
    lines.append(f"   • Composite Score:    {winner[1]:.2f} / 100")
    lines.append(f"   • Execution Accuracy: {winner[2]:.2f}%")
    lines.append(f"   • AST Exact Match:    {winner[3]:.2f}%")
    lines.append(f"   • Avg Transpilation:  {winner[4]:.2f}%")
    lines.append("=" * 78 + "\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compare NL2SQL Benchmark Reports")
    parser.add_argument("--qlora", type=str, default=None, help="Path to QLoRA eval_report.json")
    parser.add_argument("--adalora", type=str, default=None, help="Path to AdaLoRA eval_report.json")
    parser.add_argument("--base", type=str, default=None, help="Path to Base model eval_report.json")
    parser.add_argument("--reports", nargs="*", default=[], help="Additional name=path pairs, e.g. run1=path/to/report.json")
    args = parser.parse_args()

    reports = {}
    if args.base:
        data = load_report(args.base)
        if data:
            reports["Base (Zero-Shot)"] = data
    if args.qlora:
        data = load_report(args.qlora)
        if data:
            reports["QLoRA"] = data
    if args.adalora:
        data = load_report(args.adalora)
        if data:
            reports["AdaLoRA"] = data

    for item in args.reports:
        if "=" in item:
            name, path = item.split("=", 1)
            data = load_report(path)
            if data:
                reports[name] = data

    if not reports:
        print("[Error] No valid evaluation reports provided.", file=sys.stderr)
        print("Usage: python offline/training/compare_models.py --qlora path/to/eval.json --adalora path/to/eval.json")
        sys.exit(1)

    table = compare_candidates(reports)
    print(table)


if __name__ == "__main__":
    main()
