"""
core/connectors/peft_connector.py — Native In-Process PEFT Model Engine

Provides high-speed local inference for fine-tuned adapters:
1. A2.5C0.5 — Qwen2.5-Coder-0.5B fine-tuned with AdaLoRA (Dynamic SVD rank allocation)
2. Q2.5C0.5 — Qwen2.5-Coder-0.5B fine-tuned with QLoRA (4-bit/FP16 Low-Rank Adaptation)
3. A2.5C1.5 — Qwen2.5-Coder-1.5B fine-tuned with AdaLoRA (CPU-optimized, 8-core consumer laptop)
4. Q2.5C1.5 — Qwen2.5-Coder-1.5B fine-tuned with QLoRA (CPU-optimized, 8-core consumer laptop)

Features:
- Sub-50ms token generation on GPU, zero network latency.
- Multi-threaded bfloat16/float32 CPU execution for 1.5B models (no dedicated GPU required).
- Lazy model loading & caching in memory.
- SFT ChatML alignment matching the 1GB training pipeline.
- Model-native refusal: the 1.5B model is SFT-trained to emit -- REFUSAL: [TAG] itself.
"""

import logging
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("nl2sql.connectors.peft")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
BASE_MODEL_0_5B = os.path.join(REPO_ROOT, "offline/models/qwen2.5-coder-0.5b-instruct")
BASE_MODEL_1_5B = os.path.join(REPO_ROOT, "offline/models/qwen2.5-coder-1.5b-instruct")

ADAPTER_REGISTRY = {
    "A2.5C0.5": {
        "canonical_name": "A2.5C0.5",
        "description": "Qwen2.5-Coder-0.5B (AdaLoRA Adaptive SVD)",
        "peft_type": "adalora",
        "parameter_size": "0.5B",
        "base_model": BASE_MODEL_0_5B,
        "cpu_threads": 4,
        "candidate_paths": [
            os.path.join(REPO_ROOT, "offline/checkpoints/nl2sql-adalora-0.5b"),
            os.path.join(REPO_ROOT, "offline/checkpoints/smoke-test-adalora"),
        ],
    },
    "Q2.5C0.5": {
        "canonical_name": "Q2.5C0.5",
        "description": "Qwen2.5-Coder-0.5B (QLoRA 4-bit / FP16)",
        "peft_type": "qlora",
        "parameter_size": "0.5B",
        "base_model": BASE_MODEL_0_5B,
        "cpu_threads": 4,
        "candidate_paths": [
            os.path.join(REPO_ROOT, "offline/checkpoints/nl2sql-qlora-0.5b"),
            os.path.join(REPO_ROOT, "offline/checkpoints/smoke-test-qlora"),
        ],
    },
    "A2.5C1.5": {
        "canonical_name": "A2.5C1.5",
        "description": "Qwen2.5-Coder-1.5B (AdaLoRA — Balanced Consumer CPU, SFT with refusal calibration)",
        "peft_type": "adalora",
        "parameter_size": "1.5B",
        "base_model": BASE_MODEL_1_5B,
        "cpu_threads": 8,
        "candidate_paths": [
            os.path.join(REPO_ROOT, "offline/checkpoints/nl2sql-adalora-1.5b"),
        ],
    },
    "Q2.5C1.5": {
        "canonical_name": "Q2.5C1.5",
        "description": "Qwen2.5-Coder-1.5B (QLoRA 4-bit — Consumer CPU/GPU, SFT with refusal calibration)",
        "peft_type": "qlora",
        "parameter_size": "1.5B",
        "base_model": BASE_MODEL_1_5B,
        "cpu_threads": 8,
        "candidate_paths": [
            os.path.join(REPO_ROOT, "offline/checkpoints/nl2sql-qlora-1.5b"),
        ],
    },
}


class LocalPEFTEngine:
    """
    In-process model server for field-testing fine-tuned LoRA and AdaLoRA models.
    Supports 0.5B (fast smoke test) and 1.5B (consumer CPU inference, no GPU required).
    """

    def __init__(self):
        # Per-model base model path and tokenizer cache
        self._tokenizers: Dict[str, Any] = {}
        self._loaded_models: Dict[str, Any] = {}

    def _resolve_adapter_path(self, model_key: str) -> Optional[str]:
        cfg = ADAPTER_REGISTRY.get(model_key)
        if not cfg:
            return None
        for p in cfg["candidate_paths"]:
            if os.path.exists(p) and (
                os.path.exists(os.path.join(p, "adapter_model.safetensors"))
                or os.path.exists(os.path.join(p, "adapter_model.bin"))
            ):
                return p
        return None

    def _get_base_model_path(self, model_key: str) -> str:
        cfg = ADAPTER_REGISTRY.get(model_key, {})
        bm = cfg.get("base_model", BASE_MODEL_0_5B)
        # Fallback to 0.5B if 1.5B not yet downloaded
        if not os.path.exists(bm):
            fallback = BASE_MODEL_0_5B
            logger.warning("Base model %s not found, falling back to %s", bm, fallback)
            return fallback
        return bm

    def list_available_models(self) -> List[Dict[str, Any]]:
        """Lists registered field-test models if their checkpoints exist."""
        available = []
        for key, info in ADAPTER_REGISTRY.items():
            path = self._resolve_adapter_path(key)
            if path:
                available.append({
                    "name": key,
                    "family": "qwen2.5-coder",
                    "parameter_size": info.get("parameter_size", "0.5B"),
                    "format": "safetensors-peft",
                    "quantization_level": "FP16 / 4-bit",
                    "supports_thinking": False,
                    "is_generative": True,
                    "peft_type": info["peft_type"],
                    "description": info["description"],
                    "adapter_path": path,
                })
        return available

    def is_supported(self, model_name: Optional[str]) -> bool:
        if not model_name:
            return False
        clean = model_name.strip().upper()
        return clean in ADAPTER_REGISTRY and self._resolve_adapter_path(clean) is not None

    def _get_tokenizer(self, model_key: str):
        if model_key not in self._tokenizers:
            from transformers import AutoTokenizer
            bm_path = self._get_base_model_path(model_key)
            logger.info("Initializing Tokenizer for %s from %s", model_key, bm_path)
            tok = AutoTokenizer.from_pretrained(bm_path, trust_remote_code=True)
            if tok.pad_token is None:
                tok.pad_token = tok.eos_token
            self._tokenizers[model_key] = tok
        return self._tokenizers[model_key]

    def _load_peft_model(self, model_key: str):
        if model_key in self._loaded_models:
            return self._loaded_models[model_key]

        import torch
        from transformers import AutoModelForCausalLM
        from peft import PeftModel

        adapter_path = self._resolve_adapter_path(model_key)
        if not adapter_path:
            raise FileNotFoundError(f"No checkpoint found for adapter {model_key}")

        cfg = ADAPTER_REGISTRY.get(model_key, {})
        n_threads = cfg.get("cpu_threads", 4)
        bm_path = self._get_base_model_path(model_key)

        is_cuda = torch.cuda.is_available()
        compute_dtype = torch.bfloat16 if (is_cuda and torch.cuda.is_bf16_supported()) else torch.float32

        # CPU optimization: leverage all logical cores for consumer laptop inference
        if not is_cuda:
            torch.set_num_threads(n_threads)
            logger.info("CPU mode: using %d threads for %s inference", n_threads, model_key)

        logger.info("Loading Base Model %s from %s...", model_key, bm_path)
        model_kwargs: Dict[str, Any] = {"trust_remote_code": True, "torch_dtype": compute_dtype}
        if is_cuda:
            model_kwargs["device_map"] = "auto"
        base_model = AutoModelForCausalLM.from_pretrained(bm_path, **model_kwargs)

        logger.info("Attaching %s Adapter from %s", model_key, adapter_path)
        peft_model = PeftModel.from_pretrained(base_model, adapter_path)
        peft_model.eval()

        self._loaded_models[model_key] = peft_model
        return peft_model

    def generate_sql(
        self,
        query: str,
        schema_ddl: str = "",
        target_dialect: str = "postgres",
        model_name: str = "A2.5C0.5",
        max_new_tokens: int = 256,
    ) -> Tuple[Optional[str], str, Optional[str]]:
        """
        Executes local generation using the selected fine-tuned adapter.
        Returns: (sql_query, model_name, reasoning_trace)
        """
        model_key = model_name.strip().upper()
        if not self.is_supported(model_key):
            return None, model_name, None

        import torch

        tokenizer = self._get_tokenizer(model_key)
        model = self._load_peft_model(model_key)
        is_cuda = torch.cuda.is_available()

        dialect_label = target_dialect.upper() if target_dialect not in ("auto", None) else "POSTGRES"

        system_prompt = (
            "You are an expert Text-to-Universal-SQL compiler. Generate deterministic, "
            f"syntactically valid Canonical ANSI/PostgreSQL AST queries adhering to the provided database schema."
        )
        user_content = f"### Target Dialect: {dialect_label}\n\n### Database Schema:\n{schema_ddl}\n\n### User Question:\n{query}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        if hasattr(tokenizer, "apply_chat_template"):
            prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        else:
            prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_content}<|im_end|>\n<|im_start|>assistant\n"

        inputs = tokenizer(prompt, return_tensors="pt")
        if is_cuda:
            inputs = {k: v.cuda() for k, v in inputs.items()}

        t0 = time.perf_counter()
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        gen_tokens = outputs[0][inputs["input_ids"].shape[1] :]
        pred_text = tokenizer.decode(gen_tokens, skip_special_tokens=True).strip()

        # Clean markdown codeblocks
        if "```" in pred_text:
            lines = pred_text.splitlines()
            pred_text = "\n".join(l for l in lines if not l.strip().startswith("```")).strip()

        # Ensure semicolon termination for SQL queries (avoid for comments/refusals)
        if pred_text and not pred_text.endswith(";") and not pred_text.startswith("--"):
            pred_text += ";"

        logger.info(
            "[%s] Generated query in %.1fms: %s",
            model_key,
            elapsed_ms,
            pred_text[:80] + "..." if len(pred_text) > 80 else pred_text,
        )

        return pred_text, model_key, f"Local PEFT Inference ({model_key}) in {elapsed_ms:.1f}ms"


# Singleton instance
default_peft_engine = LocalPEFTEngine()
