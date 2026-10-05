#!/usr/bin/env python3
"""
scripts/pipeline_stepper.py — Interactive Terminal User Interface (TUI) Stepper
Demonstrating:
  CLEF Intent Classifier -> Schema Linker -> Qwen2.5-Coder + LoRA Adapter ->
  Deterministic Dialect Converter (Multiple Query Languages) -> 6-Layer Validator -> Cost Gate Router.
"""

import os
import sys
import json
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.pipeline_trace import execute_pipeline_trace

BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[0;36m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
MAGENTA = "\033[0;35m"
RED = "\033[0;31m"
NC = "\033[0m"


def box_print(title: str, content: str, color: str = CYAN):
    lines = content.strip().split("\n")
    max_len = max(len(l) for l in [title] + lines)
    width = min(max(max_len + 4, 60), 100)
    print(f"\n{color}┌{'─' * (width - 2)}┐{NC}")
    print(f"{color}│ {BOLD}{title.ljust(width - 4)}{NC}{color} │{NC}")
    print(f"{color}├{'─' * (width - 2)}┤{NC}")
    for l in lines:
        print(f"{color}│ {NC}{l.ljust(width - 4)}{color} │{NC}")
    print(f"{color}└{'─' * (width - 2)}┘{NC}")


def render_step(step: dict, step_idx: int, total_steps: int):
    name = step["step_name"]
    duration = step["duration_ms"]
    print(f"\n{MAGENTA}{BOLD}▶ [Step {step_idx}/{total_steps}] {name}{NC} {DIM}({duration} ms){NC}")
    print(f"{DIM}{'─' * 70}{NC}")

    if step_idx == 1:
        out = step["output"]
        print(f"  {CYAN}Paradigm Detected   :{NC} {BOLD}{out['paradigm']}{NC}")
        print(f"  {CYAN}Confidence Score    :{NC} {GREEN}{out['confidence']*100:.1f}%{NC}")
        print(f"  {CYAN}Recommended Engines :{NC} {', '.join(out['recommended_engines'])}")
        print(f"  {CYAN}CLEF Reasoning      :{NC} {DIM}{out['reasoning']}{NC}")

    elif step_idx == 2:
        out = step["output"]
        print(f"  {CYAN}Selected Tables     :{NC} {', '.join(out['selected_tables'])}")
        print(f"  {CYAN}Grounded Trie Values:{NC} {out['grounded_values']}")
        print(f"  {CYAN}FK Relational Bridge:{NC} {', '.join(out['foreign_key_bridges']) or 'None (Single table)'}")

    elif step_idx == 3:
        inp = step["input"]
        out = step["output"]
        print(f"  {CYAN}Instruction Prompt  :{NC} ChatML SFT template with DDL context")
        print(f"  {CYAN}Active LoRA Adapter :{NC} {YELLOW}{inp['lora_adapter']}{NC}")
        print(f"  {CYAN}Canonical SQL (AST) :{NC}\n  {GREEN}{BOLD}{out['canonical_sql']}{NC}")

    elif step_idx == 4:
        out = step["output"]
        queries = out["transpiled_queries"]
        print(f"  {CYAN}Simultaneous Multi-Dialect Transpilation:{NC}")
        for d, info in queries.items():
            q_val = info["query"]
            if isinstance(q_val, dict):
                preview = json.dumps(q_val.get("pipeline", q_val), indent=2)
            else:
                preview = str(q_val)
            print(f"\n    {YELLOW}{BOLD}[{d.upper()}]{NC} ({info['execution_time_ms']} ms):")
            for line in preview.split("\n"):
                print(f"      {line}")

    elif step_idx == 5:
        out = step["output"]
        status_color = GREEN if out["status"] == "valid" else YELLOW
        print(f"  {CYAN}AST Validation Status:{NC} {status_color}{BOLD}{out['status'].upper()}{NC}")
        print(f"  {CYAN}Statement Type       :{NC} {out['statement_type']}")
        if out["issues"]:
            print(f"  {CYAN}Validation Findings  :{NC}")
            for iss in out["issues"]:
                print(f"    - [{iss['code']}] {iss['severity'].upper()}: {iss['message']}")
        else:
            print(f"  {GREEN}✓ All 6 layers (Parse, Policy, Schema, Semantic, Query AP, Schema AP) passed clean.{NC}")

    elif step_idx == 6:
        out = step["output"]
        route_color = GREEN if out["execution_route"] == "SANDBOX_REPLICA" else YELLOW
        print(f"  {CYAN}Cost Engine Decision :{NC} {BOLD}{out['decision']}{NC}")
        print(f"  {CYAN}Estimated Scanned Rows:{NC} {out['estimated_rows_scanned']}")
        print(f"  {CYAN}Execution Gate Route :{NC} {route_color}{BOLD}{out['execution_route']}{NC}")
        print(f"  {CYAN}Human Approval Gate  :{NC} {'YES (Required)' if out['requires_human_approval'] else 'NO (Direct read execution)'}")


def main():
    print(f"\n{CYAN}{BOLD}========================================================================={NC}")
    print(f"{CYAN}{BOLD}  NL2SQL Full-Pipeline Interactive Stepper (CLEF + Qwen LoRA + AST)      {NC}")
    print(f"{CYAN}{BOLD}========================================================================={NC}")

    demo_queries = [
        "Find all completed orders placed by customers in Germany with total amount > $100",
        "Show 3 hops and connection paths between user Alice and Bob",
        "Increase all product prices in the Electronics category by 10%",
        "Add a discount_code column to the orders table",
        "Fetch document where customer.profile.address is nested in MongoDB format",
    ]

    print(f"\n{BOLD}Select a sample query to trace through all 6 stages:{NC}")
    for idx, q in enumerate(demo_queries, start=1):
        print(f"  [{idx}] {q}")
    print(f"  [C] Enter custom natural language query\n")

    choice = input(f"{YELLOW}Enter selection (1-{len(demo_queries)} or C, default=1): {NC}").strip().lower()
    if choice == "c":
        query = input(f"{YELLOW}Enter your Natural Language Query: {NC}").strip()
        if not query:
            query = demo_queries[0]
    elif choice in [str(i) for i in range(1, len(demo_queries) + 1)]:
        query = demo_queries[int(choice) - 1]
    else:
        query = demo_queries[0]

    print(f"\n{GREEN}{BOLD}Tracing Pipeline for:{NC} \"{query}\"")
    print(f"{DIM}Running step-by-step pipeline execution...{NC}")

    trace_result = execute_pipeline_trace(query)
    steps = trace_result["steps"]

    for idx, step in enumerate(steps, start=1):
        render_step(step, idx, len(steps))
        time.sleep(0.3)

    summary = trace_result["final_summary"]
    box_print(
        "PIPELINE EXECUTION SUMMARY",
        f"Query               : {query}\n"
        f"Total End-to-End    : {trace_result['total_duration_ms']} ms\n"
        f"Paradigm            : {summary['paradigm']}\n"
        f"Canonical AST Query : {summary['canonical_sql']}\n"
        f"Execution Route     : {summary['target_route']}\n"
        f"Status              : {summary['validation_status'].upper()}",
        color=GREEN if summary['target_route'] != "BLOCKED" else RED
    )


if __name__ == "__main__":
    main()
