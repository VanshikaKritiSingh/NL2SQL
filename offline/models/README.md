<div align="center">

# Offline Foundation Model Registry

### Local Base Model Storage, Checkpoint Management, and GGUF Exports

[![Model Registry](https://img.shields.io/badge/Model%20Registry-Active-brightgreen?style=flat-square)](https://github.com/VanshikaKritiSingh/NL2SQL)
[![Base Model](https://img.shields.io/badge/Foundation-Qwen2.5--Coder-blueviolet?style=flat-square&logo=huggingface&logoColor=white)](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct)
[![Quantization](https://img.shields.io/badge/Quantization-GGUF%20Q4__K__M-00bcd4?style=flat-square)](https://github.com/ggerganov/llama.cpp)
[![Volume Protection](https://img.shields.io/badge/Git%20Status-Excluded%20%28.gitignore%29-blue?style=flat-square)](../../.gitignore)

<br />

[Root Overview](../../README.md) &bull; [Visual Blueprint](../../diagrams/SVG_DIAGRAM.svg) &bull; [Interactive Spec](../../html/nl2sql.html) &bull; [Core AI/ML Engine](../../core/README.md) &bull; [Studio GUI](../../GUI/README.md) &bull; [Scripts & Automation](../../scripts/README.md)

</div>

<br />

---

## Overview

This directory holds local foundation LLM model checkpoints downloaded from Hugging Face for local fine-tuning (4-bit NF4 QLoRA), GGUF compilation, and offline CPU/GPU inference.

All large weight binaries (`*.safetensors`, `*.bin`, `*.pt`, `*.gguf`) in this directory are strictly ignored by `.gitignore` to preserve repository clone volume (< 15MB).

---

## Foundation Model Presets & Footprints

| Preset Name | Base Hugging Face Repo | Disk Size | Target Hardware | Primary Use Case |
| :--- | :--- | :--- | :--- | :--- |
| `0.5b` | `Qwen/Qwen2.5-Coder-0.5B-Instruct` | ~0.93 GB | CPU / Edge Laptop | Instant verification, automated tests, CPU fine-tuning |
| `1.5b` | `Qwen/Qwen2.5-Coder-1.5B-Instruct` | ~3.10 GB | 4GB-6GB VRAM / CPU | Balanced local development and smoke tests |
| `7b` | `Qwen/Qwen2.5-Coder-7B-Instruct` | ~14.2 GB | 8GB-12GB GPU (RTX 4060) | Flagship 4-bit NF4 QLoRA target for SOTA accuracy |
| `7b-gguf` | `Qwen2.5-Coder-7B-Instruct-GGUF` | ~4.30 GB | 8GB System RAM (CPU) | Zero-GPU production inference via Ollama / llama.cpp |

---

## Local Checkpoint Catalog

- **`offline/models/qwen2.5-coder-0.5b-instruct/`**:
  - Base Model: `Qwen/Qwen2.5-Coder-0.5B-Instruct`
  - Status: Downloaded & ready for offline execution
  - Artifacts: `model.safetensors`, `config.json`, `generation_config.json`, `tokenizer.json`, `vocab.json`, `merges.txt`, `model_info.json`

---

## Downloading Foundation Models

Use the provided cross-platform scripts in `scripts/`:

```bash
# Linux / macOS
./scripts/download_model.sh --preset 7b          # Flagship SOTA Qwen2.5-Coder-7B
./scripts/download_model.sh --preset 1.5b        # Balanced 1.5B model
./scripts/download_model.sh --preset 7b-gguf     # Quantized GGUF Q4_K_M for CPU
./scripts/download_model.sh --list               # List all available presets

# Windows PowerShell
.\scripts\download_model.ps1 -Preset 7b

# Windows CMD
scripts\download_model.bat --preset 7b
```

---

## Related Subsystem Documentation & Specifications

- **Root Pipeline Overview:** [`../../README.md`](../../README.md)
- **Interactive Architecture Specification:** [`../../html/nl2sql.html`](../../html/nl2sql.html)
- **High-Resolution Master Blueprint:** [`../../diagrams/SVG_DIAGRAM.svg`](../../diagrams/SVG_DIAGRAM.svg)
- **Core AI/ML Engine & QLoRA Suite:** [`../../core/README.md`](../../core/README.md)
- **Cross-Platform Script Automation:** [`../../scripts/README.md`](../../scripts/README.md)

---

<div align="center">

*NL2SQL Offline Model Registry: Technical Reference*

</div>
