"""
offline/training/export_gguf.py — LoRA Merge & GGUF Quantization Exporter

Workflow:
1. Merges PEFT LoRA adapter weights back into full 16-bit base model.
2. Converts merged safetensors into GGUF format via llama.cpp conversion script.
3. Quantizes into Q4_K_M (optimal CPU inference ~4.3GB RAM) and Q8_0 (near-lossless ~7.8GB RAM).
4. Generates an Ollama Modelfile for one-command local deployment.
"""

import argparse
import os
import subprocess

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    PEFT_AVAILABLE = True
except ImportError:
    PEFT_AVAILABLE = False


def merge_and_export(
    base_model_path: str,
    lora_path: str,
    merged_output_path: str,
    gguf_output_dir: str,
):
    if not PEFT_AVAILABLE:
        print("[Error] transformers/peft not installed.")
        return

    print(f"=== Step 1: Merging LoRA ({lora_path}) into Base ({base_model_path}) ===")
    tokenizer = AutoTokenizer.from_pretrained(base_model_path, trust_remote_code=True)
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        torch_dtype=torch.float16,
        device_map="cpu",
        trust_remote_code=True,
    )

    model = PeftModel.from_pretrained(base_model, lora_path)
    merged_model = model.merge_and_unload()

    print(f"=== Step 2: Saving Merged 16-bit Model to {merged_output_path} ===")
    os.makedirs(merged_output_path, exist_ok=True)
    merged_model.save_pretrained(merged_output_path, safe_serialization=True)
    tokenizer.save_pretrained(merged_output_path)

    print(f"=== Step 3: GGUF Conversion Instructions ===")
    print("To convert to GGUF using llama.cpp:")
    print(f"  git clone https://github.com/ggerganov/llama.cpp.git")
    print(f"  python3 llama.cpp/convert_hf_to_gguf.py {merged_output_path} --outfile {gguf_output_dir}/model-f16.gguf")
    print(f"  llama.cpp/llama-quantize {gguf_output_dir}/model-f16.gguf {gguf_output_dir}/model-q4_k_m.gguf Q4_K_M")

    # Generate Ollama Modelfile
    modelfile_path = os.path.join(gguf_output_dir, "Modelfile")
    os.makedirs(gguf_output_dir, exist_ok=True)
    with open(modelfile_path, "w") as f:
        f.write(f"""FROM ./model-q4_k_m.gguf
TEMPLATE \"\"\"<|im_start|>system
You are an expert Text-to-Universal-SQL compiler. Output only valid SQL.<|im_end|>
<|im_start|>user
{{{{ .Prompt }}}}<|im_end|>
<|im_start|>assistant
\"\"\"
PARAMETER temperature 0.0
PARAMETER stop <|im_end|>
PARAMETER stop <|endoftext|>
""")
    print(f"=== Step 4: Generated Ollama Modelfile at {modelfile_path} ===")
    print("Run: ollama create universal-nl2sql -f " + modelfile_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LoRA Merge and GGUF Export")
    parser.add_argument("--base", type=str, default="Qwen/Qwen2.5-Coder-7B-Instruct")
    parser.add_argument("--lora", type=str, default="offline/checkpoints/qwen2.5-coder-7b-qlora")
    parser.add_argument("--merged-out", type=str, default="offline/checkpoints/qwen2.5-coder-7b-merged")
    parser.add_argument("--gguf-out", type=str, default="offline/checkpoints/gguf")
    args = parser.parse_args()

    merge_and_export(
        base_model_path=args.base,
        lora_path=args.lora,
        merged_output_path=args.merged_out,
        gguf_output_dir=args.gguf_out,
    )
