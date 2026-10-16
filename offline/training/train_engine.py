"""
offline/training/train_engine.py — Unified PEFT Fine-Tuning Engine (QLoRA & AdaLoRA)

API targets:
  torch     2.6 + cu124
  trl       1.16+ (SFTTrainer / SFTConfig — DataCollatorForCompletionOnlyLM removed)
  peft      0.12+ (AdaLoraConfig requires `total_step`; tinit must be < total_step - tfinal)
  transformers 4.44+  (processing_class= replaces tokenizer=)

Usage examples:
  # Quick smoke-test (10 gradient steps):
  .venv312/bin/python offline/training/train_engine.py \
      --peft qlora \
      --model offline/models/qwen2.5-coder-0.5b-instruct \
      --max-steps 10 --max-samples 128 \
      --output-dir offline/checkpoints/smoke-test-qlora

  # Full QLoRA run:
  .venv312/bin/python offline/training/train_engine.py \
      --peft qlora --model offline/models/qwen2.5-coder-0.5b-instruct \
      --epochs 3 --output-dir offline/checkpoints/nl2sql-qlora-0.5b

  # Full AdaLoRA run:
  .venv312/bin/python offline/training/train_engine.py \
      --peft adalora --model offline/models/qwen2.5-coder-0.5b-instruct \
      --epochs 3 --output-dir offline/checkpoints/nl2sql-adalora-0.5b
"""

import argparse
import json
import logging
import math
import os
import sys
import time
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TrainEngine")


def check_dependencies():
    missing = []
    for pkg in ["torch", "transformers", "peft", "trl", "datasets"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        logger.error("Missing packages: %s\nRun: .venv312/bin/pip install %s", " ".join(missing), " ".join(missing))
        sys.exit(1)


def extract_messages(item: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Standardizes dataset records into ChatML messages format.
    Accepts either pre-formatted 'messages' (our dialect format) or raw fields.
    """
    if "messages" in item and isinstance(item["messages"], list):
        return item["messages"]

    dialect = item.get("target_dialect", item.get("dialect", "POSTGRES")).upper()
    schema  = item.get("schema", "")
    question = item.get("question", "")
    sql = item.get("canonical_sql") or item.get("sql", "")
    return [
        {"role": "system",    "content": (
            "You are an expert Text-to-Universal-SQL compiler. Generate deterministic, "
            "syntactically valid Canonical ANSI/PostgreSQL queries adhering to the schema."
        )},
        {"role": "user",      "content": f"### Target Dialect: {dialect}\n\n### Database Schema:\n{schema}\n\n### User Question:\n{question}"},
        {"role": "assistant", "content": sql},
    ]


def load_dataset(dataset_path: str, max_samples: Optional[int]) -> Any:
    """Loads JSONL/JSON into conversational ChatML dataset."""
    from datasets import Dataset as HFDataset

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    records: List[Dict[str, Any]] = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        if dataset_path.endswith(".jsonl"):
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
                    if max_samples and len(records) >= max_samples:
                        break
        else:
            all_records = json.load(f)
            records = all_records[:max_samples] if max_samples else all_records

    logger.info("Loaded %d training records from %s", len(records), dataset_path)
    all_messages = [extract_messages(r) for r in records]
    return HFDataset.from_dict({"messages": all_messages})


def compute_total_steps(
    num_samples: int,
    batch_size: int,
    grad_accum: int,
    epochs: int,
    max_steps: int,
) -> int:
    """Returns the actual number of optimizer steps that will execute."""
    steps_per_epoch = math.ceil(num_samples / (batch_size * grad_accum))
    total = steps_per_epoch * epochs
    return min(total, max_steps) if max_steps > 0 else total


def build_peft_model(
    model: Any,
    peft_type: str,
    lora_r: int,
    lora_alpha: int,
    lora_dropout: float,
    ada_init_r: int,
    ada_target_r: int,
    total_optimizer_steps: int,
    is_quantized: bool,
):
    """
    Attaches LoRA / QLoRA / AdaLoRA adapters to the base model.

    AdaLoRA constraint (peft 0.12+):
        tinit must be < (total_step - tfinal)
        We use: tinit = 10% of total_steps, tfinal = 20% of total_steps.
        If total_steps is very small (<= 5 for a smoke test), we set all to 1.
    """
    from peft import LoraConfig, AdaLoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training

    if is_quantized:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]

    if peft_type in ("qlora", "lora"):
        logger.info("Configuring %s: rank=%d, alpha=%d", peft_type.upper(), lora_r, lora_alpha)
        peft_config = LoraConfig(
            r=lora_r,
            lora_alpha=lora_alpha,
            lora_dropout=lora_dropout,
            target_modules=target_modules,
            bias="none",
            task_type=TaskType.CAUSAL_LM,
        )
    elif peft_type == "adalora":
        # AdaLoRA schedule must satisfy: tinit < (total_step - tfinal)
        # Minimum viable: total_step >= tinit + tfinal + 1
        safe_total = max(total_optimizer_steps, 10)
        tinit  = max(1, int(0.10 * safe_total))
        tfinal = max(1, int(0.20 * safe_total))
        # Ensure the constraint holds
        while tinit >= (safe_total - tfinal):
            safe_total += 10
        delta_t = max(1, safe_total // 20)

        logger.info(
            "Configuring AdaLoRA: init_r=%d, target_r=%d, total_steps=%d, tinit=%d, tfinal=%d, deltaT=%d",
            ada_init_r, ada_target_r, safe_total, tinit, tfinal, delta_t,
        )
        peft_config = AdaLoraConfig(
            init_r=ada_init_r,
            target_r=ada_target_r,
            beta1=0.85,
            beta2=0.85,
            tinit=tinit,
            tfinal=tfinal,
            deltaT=delta_t,
            lora_alpha=lora_alpha,
            lora_dropout=lora_dropout,
            target_modules=target_modules,
            total_step=safe_total,
            task_type=TaskType.CAUSAL_LM,
        )
    else:
        raise ValueError(f"Unknown PEFT type: {peft_type}")

    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    return model, peft_config


def run_training(args: argparse.Namespace):
    check_dependencies()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTTrainer, SFTConfig

    is_cuda = torch.cuda.is_available()
    use_bf16 = is_cuda and torch.cuda.is_bf16_supported()
    use_fp16 = is_cuda and not use_bf16

    # Auto quantization
    if args.quantization == "auto":
        args.quantization = "4bit" if (args.peft == "qlora" and is_cuda) else "none"

    logger.info("=== NL2SQL Fine-Tuning Engine ===")
    logger.info("PEFT: %s | Quantization: %s | CUDA: %s", args.peft.upper(), args.quantization, is_cuda)
    logger.info("Base model: %s", args.model)
    logger.info("Output: %s", args.output_dir)

    # ── Tokenizer ────────────────────────────────────────────────────────────
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # ── Dataset ──────────────────────────────────────────────────────────────
    dataset = load_dataset(args.dataset, args.max_samples)
    num_samples = len(dataset)

    # ── Compute actual optimizer steps (needed by AdaLoRA before model load) ─
    effective_batch = args.batch_size * args.grad_accum
    total_steps = compute_total_steps(num_samples, args.batch_size, args.grad_accum, args.epochs, args.max_steps)
    logger.info(
        "Training schedule: %d samples, batch=%d, grad_accum=%d, total_optimizer_steps≈%d",
        num_samples, effective_batch, args.grad_accum, total_steps,
    )

    # ── Base Model ───────────────────────────────────────────────────────────
    compute_dtype = torch.bfloat16 if use_bf16 else torch.float16 if is_cuda else torch.float32

    quant_config = None
    if args.quantization == "4bit" and is_cuda:
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=compute_dtype,
        )
    elif args.quantization == "8bit" and is_cuda:
        quant_config = BitsAndBytesConfig(load_in_8bit=True)

    model_kwargs: Dict[str, Any] = {"trust_remote_code": True}
    if quant_config is not None:
        model_kwargs["quantization_config"] = quant_config
        model_kwargs["device_map"] = "auto"
    elif is_cuda:
        model_kwargs["dtype"] = compute_dtype
        model_kwargs["device_map"] = "auto"

    logger.info("Loading base model...")
    model = AutoModelForCausalLM.from_pretrained(args.model, **model_kwargs)

    # ── PEFT Adapters ────────────────────────────────────────────────────────
    model, peft_config = build_peft_model(
        model=model,
        peft_type=args.peft,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        ada_init_r=args.ada_init_r,
        ada_target_r=args.ada_target_r,
        total_optimizer_steps=total_steps,
        is_quantized=quant_config is not None,
    )

    # ── SFTConfig (TRL 1.16 API) ─────────────────────────────────────────────
    # assistant_only_loss=True: only compute cross-entropy loss on the
    # <|im_start|>assistant ... <|im_end|> tokens — gradients don't flow
    # through the system prompt or user question.
    sft_config = SFTConfig(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        max_steps=args.max_steps if args.max_steps > 0 else -1,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_steps=max(1, int(0.03 * total_steps)),
        max_length=args.max_seq_len,
        assistant_only_loss=True,          # replaces DataCollatorForCompletionOnlyLM
        optim="paged_adamw_8bit" if is_cuda else "adamw_torch",
        bf16=use_bf16,
        fp16=use_fp16,
        use_cpu=not is_cuda,
        gradient_checkpointing=is_cuda,
        logging_steps=max(1, args.logging_steps),
        save_strategy="steps" if args.max_steps > 0 else "epoch",
        save_steps=args.save_steps,
        save_total_limit=2,
        report_to="none",
        dataloader_num_workers=2 if (os.name != "nt" and is_cuda) else 0,
    )

    # ── Trainer ───────────────────────────────────────────────────────────────
    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=dataset,
        processing_class=tokenizer,         # TRL 1.16: processing_class replaces tokenizer=
    )

    # ── Train ────────────────────────────────────────────────────────────────
    start = time.time()
    logger.info("Training started...")
    result = trainer.train()
    elapsed = time.time() - start
    logger.info("Training finished in %.1fs (%.1f min)", elapsed, elapsed / 60)

    # ── Save ──────────────────────────────────────────────────────────────────
    os.makedirs(args.output_dir, exist_ok=True)
    trainer.model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    metrics = {
        "peft_type":       args.peft,
        "base_model":      args.model,
        "quantization":    args.quantization,
        "train_loss":      getattr(result, "training_loss", None),
        "train_runtime_s": elapsed,
        "epochs":          args.epochs,
        "batch_size":      args.batch_size,
        "grad_accum":      args.grad_accum,
        "lr":              args.lr,
        "total_steps":     total_steps,
        "timestamp":       time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    metrics_file = os.path.join(args.output_dir, "training_metrics.json")
    with open(metrics_file, "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info("Metrics saved to: %s", metrics_file)
    print(f"\n✅ Checkpoint saved to: {args.output_dir}")


def main():
    parser = argparse.ArgumentParser(description="NL2SQL Unified Fine-Tuning Engine (QLoRA & AdaLoRA)")

    parser.add_argument("--peft",         choices=["qlora", "adalora", "lora"],  default="qlora")
    parser.add_argument("--model",        default="offline/models/qwen2.5-coder-0.5b-instruct")
    parser.add_argument("--dataset",      default="offline/datasets/dialects/postgres.jsonl")
    parser.add_argument("--output-dir",   default="offline/checkpoints/nl2sql-qlora-adapter")
    parser.add_argument("--quantization", choices=["auto", "4bit", "8bit", "none"], default="auto")

    # LoRA / QLoRA hyperparams
    parser.add_argument("--lora-r",       type=int,   default=16)
    parser.add_argument("--lora-alpha",   type=int,   default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)

    # AdaLoRA-specific
    parser.add_argument("--ada-init-r",   type=int,   default=16,
                        help="AdaLoRA starting rank budget (pruned down to --ada-target-r)")
    parser.add_argument("--ada-target-r", type=int,   default=8,
                        help="AdaLoRA final rank after SVD pruning")

    # Training schedule
    parser.add_argument("--epochs",       type=int,   default=3)
    parser.add_argument("--max-steps",    type=int,   default=-1,
                        help="Stop after N optimizer steps. Set to 10 for a smoke test.")
    parser.add_argument("--max-samples",  type=int,   default=None,
                        help="Limit dataset size (e.g. 128 for a quick smoke test)")
    parser.add_argument("--batch-size",   type=int,   default=2)
    parser.add_argument("--grad-accum",   type=int,   default=4)
    parser.add_argument("--lr",           type=float, default=2e-4)
    parser.add_argument("--max-seq-len",  type=int,   default=2048)

    # Logging / checkpointing
    parser.add_argument("--logging-steps", type=int,  default=5)
    parser.add_argument("--save-steps",    type=int,  default=500)

    args = parser.parse_args()
    run_training(args)


if __name__ == "__main__":
    main()
