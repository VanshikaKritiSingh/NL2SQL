# Fine-Tuning Manual: NL2SQL with QLoRA / LoRA

Purpose: Learn how to fine-tune a local code-capable LLM specifically for Natural Language → SQL (and multi-paradigm: MongoDB MQL, openCypher, DuckDB, ClickHouse) so that the generation quality improves beyond the current 0.5B model that misses semicolons and misinterprets relations.

---

## 1. Which model should you use?

| Model | Size | Quant | Context | Best for |
|---|---|---|---|---|
| Qwen2.5-Coder-7B-Instruct | 7B | Q8_0 / 4-bit | 32K | SQL code generation (recommended base) |
| DeepSeek-Coder-V2-Lite | 16B (lite ~6B active) | 4-bit | 128K | Complex multi-join / CTE / multi-language |
| Qwen2.5-Coder-1.5B/3B | 1.5–3B | 4-bit | 32K | Very tight VRAM; lower accuracy |
| clef-flash (local) | 9.1B Q8_0 | Q8_0 | 262K | Currently best installed local option |

Recommendation: Start with `Qwen/Qwen2.5-Coder-7B-Instruct` (base for fine-tuning). After fine-tuning, merge LoRA and quantize to Q4_K_M (~4.3 GB) for CPU/4060 inference, or keep Q8_0 for best quality.

Why the 0.5B (`qwen2.5:0.5b`) is not sufficient: At 494M params it cannot reliably maintain table relationships, enforce semicolons, or distinguish `WHERE` from `HAVING`, which is exactly the failure mode you described.

---

## 2. Hardware profile

### Local (RTX 4060 8 GB VRAM)
- Fine-tuning a 7B with QLoRA in 4-bit fits in ~7.2 GB VRAM (confirmed in `offline/training/train_qlora.py`).
- Batch size 2 + gradient accumulation 4 + gradient checkpointing = safe on 8 GB.
- If you use 16B Lite, you need Colab A100 (40–80 GB) or you must switch to pure LoRA (not QLoRA) with very small batch.

### Google Colab A100 (recommended for faster training / larger models)
- Free tier: T4 (15 GB) — fits 7B QLoRA.
- Pro: A100 (40 GB / 80 GB) — fits 16B Lite QLoRA or larger batch on 7B.
- Use `pip install unsloth` for Unsloth optimization (2× faster, ~30% less memory).

---

## 3. Data acquisition & synthetic generation

### 3.1 Real datasets (recommended sources)
- **Spider** (~10K NL-SQL pairs, 200 DBs) — standard benchmark, download from Yale.
- **BIRD** (~13K pairs) — includes dirty values, external knowledge.
- **WikiSQL** (~80K simple SELECTs) — good for syntax/semicolon enforcement.
- **SQuAD / Spider-DK** for complex JOIN / nested queries.

### 3.2 Synthetic generation (if you have no data)
The repo already has a synthetic generator: `offline/datasets/prepare_dataset.py`. It creates 250 instruction samples across 8 schemas (ecommerce, SaaS, clinical, etc.).

To expand it:
```bash
python offline/datasets/prepare_dataset.py --sample-count 5000 --eval-ratio 0.15
```
This produces `offline/datasets/train.json` and `train.jsonl` in ChatML format.

To add multi-paradigm queries (MongoDB MQL, openCypher):
1. Edit `SCHEMAS` in `prepare_dataset.py` to include document/graph schemas.
2. Add `expected_sql` fields that use MongoDB aggregation pipeline syntax (`{"$match": ...}`) or Cypher (`MATCH ... RETURN ...`).
3. Ensure the assistant response ends with a semicolon for SQL, but for MQL the pipeline is a JSON array — adjust the format accordingly.

---

## 4. Step-by-step QLoRA fine-tuning (local, 8 GB VRAM)

### Step 4.1 — Install dependencies
```bash
pip install torch transformers peft trl datasets bitsandbytes accelerate unsloth
```
If using the repo's pre-configured environment:
```bash
cat offline/training/requirements-train.txt
pip install -r offline/training/requirements-train.txt
```

### Step 4.2 — Download base model
```bash
# Manual download (if no internet during training)
python scripts/download_model.py
```
Or via HuggingFace CLI:
```bash
huggingface-cli download Qwen/Qwen2.5-Coder-7B-Instruct --local-dir ./offline/models/qwen2.5-coder-7b-instruct
```

### Step 4.3 — Prepare dataset in ChatML format
The repo expects messages like:
```json
{"messages": [{"role":"system","content":"..."}, {"role":"user","content":"Schema: ... Request: ..."}, {"role":"assistant","content":"SELECT ...;"}]}
```
Generate or download your dataset. Example custom sample:
```json
{"schema":"CREATE TABLE users (id INT PRIMARY KEY, name TEXT); CREATE TABLE orders (id INT PRIMARY KEY, user_id INT REFERENCES users(id), amount DECIMAL);",
 "question":"Show names and amounts for all orders.",
 "sql":"SELECT users.name, orders.amount FROM users JOIN orders ON users.id = orders.user_id;"}
```

### Step 4.4 — Run fine-tuning script
The repo provides `offline/training/train_qlora.py`. Key hyperparameters:

```python
lora_r=16        # Low-rank dimension; increase to 32 or 64 if you have more data
lora_alpha=32    # Scaling factor; typically 2× r
lora_dropout=0.05
batch_size=2
learning_rate=2e-4
gradient_accumulation_steps=4
epochs=3
```

Run:
```bash
python offline/training/train_qlora.py \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --dataset offline/datasets/train.json \
  --output offline/checkpoints/qwen2.5-coder-7b-qlora \
  --epochs 3
```

Expected output:
```
=== Saving LoRA Adapters to: offline/checkpoints/qwen2.5-coder-7b-qlora ===
```
The adapter files (`adapter_config.json`, `adapter_model.safetensors`) are only ~20–100 MB.

### Step 4.5 — Evaluate
```bash
python offline/training/evaluate.py --eval-file offline/datasets/eval.json --db :memory:
```
Metrics printed: AST Exact Match (EM) and Execution Accuracy (EX). Aim for EX > 85% before deploying.

---

## 5. Fine-tuning with Unsloth (Colab A100, faster)

Unsloth provides a single script that is 2× faster and uses less VRAM.

```python
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit",
    max_seq_length=2048,
    load_in_4bit=True,
)
model = FastLanguageModel.get_peft_model(
    model,
    r=16, lora_alpha=32, target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
)

from trl import SFTTrainer
trainer = SFTTrainer(...)
```
Full Unsloth notebook template is available at: https://github.com/unslothai/notebooks (search for `Qwen2.5` or `Coder`).

On Colab A100:
```bash
!pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
```
Then run your dataset through the same `SFTTrainer` but with `batch_size=4` or `8`.

---

## 6. Merging LoRA and exporting to GGUF (for CPU/Ollama)

After fine-tuning, you must merge adapters into the base model before running locally via Ollama.

```bash
python offline/training/export_gguf.py \
  --base-model-path Qwen/Qwen2.5-Coder-7B-Instruct \
  --lora-path offline/checkpoints/qwen2.5-coder-7b-qlora \
  --merged-output offline/checkpoints/merged-qlora \
  --gguf-output-dir offline/checkpoints/gguf
```

Then quantize:
```bash
git clone https://github.com/ggerganov/llama.cpp.git
python llama.cpp/convert_hf_to_gguf.py offline/checkpoints/merged-qlora --outfile offline/checkpoints/gguf/model-f16.gguf
llama.cpp/llama-quantize offline/checkpoints/gguf/model-f16.gguf offline/checkpoints/gguf/model-q4_k_m.gguf Q4_K_M
```

Finally, create an Ollama Modelfile:
```bash
cat > offline/checkpoints/gguf/Modelfile <<EOF
FROM ./model-q4_k_m.gguf
PARAMETER temperature 0.1
PARAMETER stop "</s>"
PARAMETER num_ctx 32768
EOF
ollama create nl2sql-coder -f offline/checkpoints/gguf/Modelfile
```
Then switch the app to use `ollama run nl2sql-coder` or set `model_name` to `nl2sql-coder` in the GUI.

---

## 7. Improving accuracy beyond fine-tuning

1. **Schema Narrowing (RAG)** — Before calling LLM, retrieve only the relevant tables. The repo has `core/schema_linker.py`. Better linking = fewer hallucinated columns.
2. **Parameter Enforcement** — The updated `SYSTEM_PROMPT` (see `core/orchestrator.py`) now demands a trailing semicolon (`;`). The new `_enforce_sql_output()` method rejects responses that don't start with SQL keywords or omit the semicolon, and returns the exact refusal sentence `please enter a valid natural language query` for non-SQL input.
3. **Retry Gate with AST Feedback** — The validator (`validator/engine.py`) returns 6-layer errors. You can feed these errors back into a second LLM call (`RetryGate` in architecture). Example retry prompt:
   ```
   Previous SQL had error: [SCHEMA_02] Column 'foo' does not exist on table 'users'.
   Schema: ...
   Rewrite the query correctly.
   ```
4. **Deterministic Dialect Converter** — The dialect converter (`core/dialect_converter.py`) uses `sqlglot`. Ensure your fine-tuned model outputs canonical PostgreSQL-style SQL; the converter then produces MySQL, MongoDB MQL, openCypher, etc.
5. **Dataset Quality > Model Size** — A 7B model fine-tuned on 2,000 high-quality, diverse SQL pairs outperforms a 16B base model fine-tuned on 200 noisy pairs.

---

## 8. Recommended action checklist

- [ ] Read `offline/datasets/prepare_dataset.py` and expand to 1,000–5,000 synthetic pairs.
- [ ] Download `Qwen2.5-Coder-7B-Instruct` into `offline/models/`.
- [ ] Verify dataset ends with `;` for SQL queries; add refusal examples (`"Show weather" -> "please enter a valid natural language query"`).
- [ ] Run `python offline/training/train_qlora.py --model Qwen/Qwen2.5-Coder-7B-Instruct --dataset offline/datasets/train.json --epochs 3`.
- [ ] Evaluate with `offline/training/evaluate.py`.
- [ ] If EX < 80%, increase dataset size / quality; if EX >= 85%, merge and export.
- [ ] Update `core/orchestrator.py` `model` to `nl2sql-coder` (or `clef-flash:latest` until export completes).
- [ ] Confirm `SYSTEM_PROMPT` enforces semicolon and refusal sentence (done in latest edit).

---

## 9. Quick references

| File / Command | What it does |
|---|---|
| `core/orchestrator.py` | Pipeline entry; updated system prompt + enforcement gate |
| `core/dialect_converter.py` | sqlglot-based transpiler (PostgreSQL → MySQL / MongoDB / openCypher / DuckDB) |
| `validator/engine.py` | 6-layer AST validation; feeds retry context |
| `offline/training/train_qlora.py` | QLoRA fine-tuning script |
| `offline/training/export_gguf.py` | Merge LoRA + export GGUF |
| `offline/datasets/prepare_dataset.py` | Synthetic dataset generator |
| `scripts/download_model.py` | Download base model script |
| `tests/test_core_modules.py` | End-to-end tests for pipeline |
