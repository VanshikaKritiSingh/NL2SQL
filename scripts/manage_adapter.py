#!/usr/bin/env python3
"""
scripts/manage_adapter.py — Manage, Upload, Download, and Register Fine-Tuned PEFT Adapters

Commands:
  1. Upload adapter layer to Hugging Face Hub:
     python scripts/manage_adapter.py upload \
       --adapter-dir offline/checkpoints/nl2sql-qlora-1.5b \
       --repo-id <username>/nl2sql-qlora-1.5b \
       --private

  2. Download adapter layer from Hugging Face Hub:
     python scripts/manage_adapter.py download \
       --repo-id <username>/nl2sql-qlora-1.5b \
       --output-dir offline/checkpoints/nl2sql-qlora-1.5b

  3. Attach downloaded adapter to base model and run a test query:
     python scripts/manage_adapter.py test \
       --adapter-dir offline/checkpoints/nl2sql-qlora-1.5b \
       --base-model Qwen/Qwen2.5-Coder-1.5B-Instruct \
       --prompt "List all active customers from California who ordered last week"

  4. List registered adapters:
     python scripts/manage_adapter.py list
"""

import argparse
import os
import sys
import json
import re
from typing import Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)


def cmd_login(token: Optional[str] = None):
    """Logs in to Hugging Face locally without needing the external huggingface-cli."""
    from huggingface_hub import login, HfApi
    import getpass

    token = token or os.getenv("HF_TOKEN")
    if not token:
        try:
            token = getpass.getpass("Enter your Hugging Face Access Token (WRITE permission required): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(1)

    if not token:
        print("[Error] No token entered.")
        sys.exit(1)

    login(token=token, add_to_git_credential=False)
    try:
        api = HfApi(token=token)
        user = api.whoami()["name"]
        print(f"\n[Success] Successfully authenticated as '{user}' on Hugging Face Hub!")
        print(f"Token saved to local cache (~/.cache/huggingface/token).")
    except Exception as e:
        print(f"[Error] Failed to verify token: {e}")
        sys.exit(1)


def cmd_upload(adapter_dir: str, repo_id: str, private: bool, token: Optional[str] = None):
    """Uploads local fine-tuned LoRA / AdaLoRA adapter weights to Hugging Face Hub."""
    from huggingface_hub import HfApi, create_repo
    import getpass

    token = token or os.getenv("HF_TOKEN")
    if not token:
        print("[Notice] HF_TOKEN environment variable not found.")
        try:
            token = getpass.getpass("Paste your Hugging Face Access Token (input hidden): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(1)

    if not token:
        print("[Error] Hugging Face Access Token is required to upload.")
        sys.exit(1)

    adapter_path = os.path.abspath(adapter_dir)
    if not os.path.isdir(adapter_path):
        print(f"[Error] Directory not found: {adapter_path}")
        sys.exit(1)

    # Check for required adapter files
    has_config = os.path.exists(os.path.join(adapter_path, "adapter_config.json"))
    has_weights = (
        os.path.exists(os.path.join(adapter_path, "adapter_model.safetensors"))
        or os.path.exists(os.path.join(adapter_path, "adapter_model.bin"))
    )

    if not has_config or not has_weights:
        print(f"[Error] Directory {adapter_path} does not look like a valid PEFT adapter.")
        print("Expected 'adapter_config.json' and 'adapter_model.safetensors' (or 'adapter_model.bin').")
        sys.exit(1)

    # Auto-sanitize metadata so Hugging Face Hub YAML validator accepts base_model
    readme_path = os.path.join(adapter_path, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
        sanitized = re.sub(r"offline/models/qwen2\.5-coder-1\.5b-instruct", "Qwen/Qwen2.5-Coder-1.5B-Instruct", content)
        sanitized = re.sub(r"offline/models/qwen2\.5-coder-0\.5b-instruct", "Qwen/Qwen2.5-Coder-0.5B-Instruct", sanitized)
        sanitized = re.sub(r"offline/models/qwen2\.5-coder-7b-instruct", "Qwen/Qwen2.5-Coder-7B-Instruct", sanitized)
        if sanitized != content:
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(sanitized)

    cfg_path = os.path.join(adapter_path, "adapter_config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg_data = json.load(f)
            bm = cfg_data.get("base_model_name_or_path", "")
            if "offline/models" in bm:
                if "1.5b" in bm:
                    cfg_data["base_model_name_or_path"] = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
                elif "0.5b" in bm:
                    cfg_data["base_model_name_or_path"] = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
                elif "7b" in bm:
                    cfg_data["base_model_name_or_path"] = "Qwen/Qwen2.5-Coder-7B-Instruct"
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(cfg_data, f, indent=2)
        except Exception:
            pass

    api = HfApi(token=token)
    user = api.whoami()["name"]
    print(f"Authenticated as Hugging Face user: {user}")

    print(f"Creating repository '{repo_id}' (private={private})...")
    create_repo(repo_id=repo_id, token=token, private=private, exist_ok=True, repo_type="model")

    print(f"Uploading adapter files from '{adapter_path}' to '{repo_id}'...")
    api.upload_folder(
        folder_path=adapter_path,
        repo_id=repo_id,
        repo_type="model",
        commit_message="Upload NL2SQL fine-tuned PEFT adapter layer",
    )
    print(f"\n[Success] Adapter successfully uploaded to: https://huggingface.co/{repo_id}")


def cmd_download(repo_id: str, output_dir: str, token: Optional[str] = None):
    """Downloads adapter layer from Hugging Face Hub into local directory."""
    from huggingface_hub import snapshot_download

    token = token or os.getenv("HF_TOKEN")
    target_path = os.path.abspath(output_dir)
    os.makedirs(target_path, exist_ok=True)

    print(f"Downloading adapter repository '{repo_id}' to '{target_path}'...")
    snapshot_download(
        repo_id=repo_id,
        local_dir=target_path,
        local_dir_use_symlinks=False,
        token=token,
    )

    print(f"\n[Success] Download complete!")
    print(f"Files saved in: {target_path}")
    for fname in sorted(os.listdir(target_path)):
        print(f" - {fname}")


def cmd_test_inference(adapter_dir: str, base_model: str, prompt: str, schema_ddl: str = ""):
    """Loads base model, dynamically attaches adapter layer, and generates test SQL."""
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
    except ImportError:
        print("[Error] PyTorch, Transformers, or PEFT not installed.")
        print("Run: pip install torch transformers peft accelerate")
        sys.exit(1)

    adapter_path = os.path.abspath(adapter_dir)
    if not os.path.isdir(adapter_path):
        print(f"[Error] Adapter path does not exist: {adapter_path}")
        sys.exit(1)

    is_cuda = torch.cuda.is_available()
    device = "cuda" if is_cuda else "cpu"
    compute_dtype = torch.bfloat16 if (is_cuda and torch.cuda.is_bf16_supported()) else torch.float32

    print(f"[1/3] Loading Tokenizer & Base Model '{base_model}' on {device} ({compute_dtype})...")
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model_kwargs = {"trust_remote_code": True, "torch_dtype": compute_dtype}
    if is_cuda:
        model_kwargs["device_map"] = "auto"

    base = AutoModelForCausalLM.from_pretrained(base_model, **model_kwargs)

    print(f"[2/3] Attaching Adapter Layer from '{adapter_path}'...")
    model = PeftModel.from_pretrained(base, adapter_path)
    model.eval()

    print(f"[3/3] Generating SQL for Prompt:\n\"{prompt}\"\n")
    system_prompt = (
        "You are an expert database engineer. Convert natural language queries into valid SQL ending with a semicolon (;). "
        "Output ONLY the SQL query."
    )
    user_content = f"Schema:\n{schema_ddl}\n\nPrompt:\n{prompt}\nSQL:" if schema_ddl else f"Prompt:\n{prompt}\nSQL:"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    chat_input = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(chat_input, return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=150,
            temperature=0.0,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
        )

    response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    print("=" * 60)
    print("GENERATED SQL QUERY:")
    print(response)
    print("=" * 60)


def cmd_list():
    """Lists registered adapters in the software."""
    from core.connectors.peft_connector import default_peft_engine, ADAPTER_REGISTRY
    print("=" * 70)
    print("REGISTERED ADAPTER MODELS IN NL2SQL SOFTWARE:")
    print("=" * 70)
    available = default_peft_engine.list_available_models()
    avail_names = {m["name"] for m in available}

    for key, cfg in ADAPTER_REGISTRY.items():
        status = "[READY]" if key in avail_names else "[MISSING CHECKPOINT]"
        print(f"{key:10} | {status:20} | {cfg['description']}")
        for p in cfg["candidate_paths"]:
            exists = os.path.exists(p)
            print(f"           - Path: {p} (exists: {exists})")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="NL2SQL PEFT Adapter Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: login
    p_login = subparsers.add_parser("login", help="Authenticate with Hugging Face Hub (no external CLI needed)")
    p_login.add_argument("--token", default=None, help="Hugging Face API token")

    # Subcommand: upload
    p_upload = subparsers.add_parser("upload", help="Upload adapter weights to Hugging Face")
    p_upload.add_argument("--adapter-dir", required=True, help="Local directory of fine-tuned adapter")
    p_upload.add_argument("--repo-id", required=True, help="Target Hugging Face repo ID, e.g. 'username/nl2sql-qlora-1.5b'")
    p_upload.add_argument("--private", action="store_true", default=True, help="Make repository private")
    p_upload.add_argument("--token", default=None, help="Hugging Face API token")

    # Subcommand: download
    p_download = subparsers.add_parser("download", help="Download adapter weights from Hugging Face")
    p_download.add_argument("--repo-id", required=True, help="Hugging Face repo ID to download from")
    p_download.add_argument("--output-dir", required=True, help="Local directory to save adapter")
    p_download.add_argument("--token", default=None, help="Hugging Face API token (for private repos)")

    # Subcommand: test
    p_test = subparsers.add_parser("test", help="Attach adapter to base model and run test inference")
    p_test.add_argument("--adapter-dir", required=True, help="Local directory of adapter")
    p_test.add_argument("--base-model", default="Qwen/Qwen2.5-Coder-1.5B-Instruct", help="Base model ID or path")
    p_test.add_argument("--prompt", required=True, help="Natural language test prompt")
    p_test.add_argument("--schema", default="", help="Optional schema DDL")

    # Subcommand: list
    subparsers.add_parser("list", help="List registered adapters in NL2SQL")

    args = parser.parse_args()

    if args.command == "login":
        cmd_login(args.token)
    elif args.command == "upload":
        cmd_upload(args.adapter_dir, args.repo_id, args.private, args.token)
    elif args.command == "download":
        cmd_download(args.repo_id, args.output_dir, args.token)
    elif args.command == "test":
        cmd_test_inference(args.adapter_dir, args.base_model, args.prompt, args.schema)
    elif args.command == "list":
        cmd_list()


if __name__ == "__main__":
    main()
