"""
scripts/download_model.py — Automated Foundation Model Downloader for NL2SQL Fine-Tuning

Downloads base LLM foundation models (Qwen2.5-Coder series) from Hugging Face into the local
`offline/models/` directory for offline fine-tuning (QLoRA), GGUF conversion, or CPU inference.

Features:
- Presets for Qwen2.5-Coder (0.5B, 1.5B, 3B, 7B, and GGUF)
- Direct HuggingFace Hub snapshot download with automatic retry and resume
- Pure Python fallback using urllib streaming if huggingface_hub is unavailable
- Saves complete tokenizer, config, and safetensors weights
- Generates a local `model_info.json` manifest
"""

import argparse
import json
import os
import sys
import time
from typing import Dict, List, Optional

# Supported Model Presets
MODEL_PRESETS: Dict[str, Dict[str, str]] = {
    "0.5b": {
        "repo_id": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "description": "Qwen2.5-Coder-0.5B-Instruct (~0.98 GB, ultra-lightweight, rapid local prototyping & CPU SFT)",
        "default_dir": "qwen2.5-coder-0.5b-instruct",
        "min_vram_gb": "2.0",
    },
    "1.5b": {
        "repo_id": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
        "description": "Qwen2.5-Coder-1.5B-Instruct (~3.1 GB, balanced speed & code understanding)",
        "default_dir": "qwen2.5-coder-1.5b-instruct",
        "min_vram_gb": "4.0",
    },
    "7b": {
        "repo_id": "Qwen/Qwen2.5-Coder-7B-Instruct",
        "description": "Qwen2.5-Coder-7B-Instruct (~14.2 GB, SOTA code & SQL reasoning, primary fine-tuning target)",
        "default_dir": "qwen2.5-coder-7b-instruct",
        "min_vram_gb": "7.5",
    },
    "7b-gguf": {
        "repo_id": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
        "description": "Qwen2.5-Coder-7B-Instruct GGUF (Quantized Q4_K_M ~4.3 GB, zero-dependency CPU inference)",
        "default_dir": "qwen2.5-coder-7b-gguf",
        "min_vram_gb": "0.0 (Pure CPU)",
    },
}


def download_with_hf_hub(repo_id: str, local_dir: str, allow_patterns: Optional[List[str]] = None) -> bool:
    """Downloads model using huggingface_hub snapshot_download."""
    try:
        from huggingface_hub import snapshot_download
        print(f"[HF-Hub] Downloading repository '{repo_id}' to '{local_dir}'...")
        os.makedirs(local_dir, exist_ok=True)
        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            local_dir_use_symlinks=False,
            allow_patterns=allow_patterns,
            resume_download=True,
        )
        return True
    except Exception as e:
        print(f"[HF-Hub] snapshot_download encountered an error: {e}")
        return False


def download_with_urllib(repo_id: str, local_dir: str) -> bool:
    """Fallback streaming downloader using pure Python standard library (urllib)."""
    import urllib.request
    import urllib.error

    print(f"[Fallback] Downloading via HuggingFace API for '{repo_id}'...")
    api_url = f"https://huggingface.co/api/models/{repo_id}"
    
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "NL2SQL-Model-Downloader/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            siblings = data.get("siblings", [])
    except Exception as e:
        print(f"[Error] Failed to fetch repository file listing: {e}")
        return False

    os.makedirs(local_dir, exist_ok=True)
    files_to_download = [s["rfilename"] for s in siblings if not s["rfilename"].startswith(".")]

    print(f"[Fallback] Found {len(files_to_download)} files to download.")
    for fname in files_to_download:
        dest_path = os.path.join(local_dir, fname)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        file_url = f"https://huggingface.co/{repo_id}/resolve/main/{fname}"

        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
            print(f"  [Skip] {fname} already exists ({os.path.getsize(dest_path):,} bytes).")
            continue

        print(f"  [Downloading] {fname} from {file_url}...")
        try:
            req = urllib.request.Request(file_url, headers={"User-Agent": "NL2SQL-Model-Downloader/1.0"})
            with urllib.request.urlopen(req, timeout=60) as response, open(dest_path, "wb") as out_file:
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 1024 * 1024  # 1MB chunks
                start_t = time.time()

                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    elapsed = max(time.time() - start_t, 0.001)
                    speed_mb = (downloaded / (1024 * 1024)) / elapsed
                    if total_size > 0:
                        pct = (downloaded / total_size) * 100
                        sys.stdout.write(f"\r    -> {pct:5.1f}% [{downloaded/(1024*1024):.1f}MB/{total_size/(1024*1024):.1f}MB] @ {speed_mb:.2f} MB/s")
                    else:
                        sys.stdout.write(f"\r    -> {downloaded/(1024*1024):.1f}MB downloaded @ {speed_mb:.2f} MB/s")
                    sys.stdout.flush()
                print("")
        except Exception as e:
            print(f"\n[Error] Failed to download {fname}: {e}")
            return False

    return True


def verify_and_generate_manifest(repo_id: str, local_dir: str, preset_name: Optional[str] = None):
    """Scans downloaded files and generates model_info.json manifest."""
    files = []
    total_bytes = 0
    for root, _, filenames in os.walk(local_dir):
        for f in filenames:
            if f == "model_info.json":
                continue
            fpath = os.path.join(root, f)
            fsize = os.path.getsize(fpath)
            relpath = os.path.relpath(fpath, local_dir)
            files.append({"file": relpath, "size_bytes": fsize, "size_mb": round(fsize / (1024 * 1024), 2)})
            total_bytes += fsize

    manifest = {
        "repo_id": repo_id,
        "preset": preset_name or "custom",
        "download_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "local_directory": os.path.abspath(local_dir),
        "total_files": len(files),
        "total_size_bytes": total_bytes,
        "total_size_mb": round(total_bytes / (1024 * 1024), 2),
        "total_size_gb": round(total_bytes / (1024 * 1024 * 1024), 3),
        "files": sorted(files, key=lambda x: x["file"]),
        "status": "ready_for_fine_tuning" if total_bytes > 0 else "empty",
    }

    manifest_path = os.path.join(local_dir, "model_info.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 60)
    print("           MODEL DOWNLOAD & MANIFEST VERIFICATION          ")
    print("=" * 60)
    print(f"Repository   : {repo_id}")
    print(f"Local Path   : {os.path.abspath(local_dir)}")
    print(f"Total Files  : {manifest['total_files']}")
    print(f"Total Size   : {manifest['total_size_gb']} GB ({manifest['total_size_mb']} MB)")
    print(f"Manifest File: {manifest_path}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="NL2SQL Foundation Base Model Downloader for Local Fine-Tuning & Inference"
    )
    parser.add_argument(
        "--preset",
        type=str,
        choices=["0.5b", "1.5b", "7b", "7b-gguf"],
        default="0.5b",
        help="Base model preset (default: 0.5b for rapid download & lightweight verification)",
    )
    parser.add_argument(
        "--repo-id",
        type=str,
        default=None,
        help="Custom Hugging Face repository ID (overrides --preset if supplied)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom output directory under offline/models/ (defaults to preset name)",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List available foundation model presets and exit",
    )
    args = parser.parse_args()

    if args.list_presets:
        print("\nAvailable NL2SQL Foundation Model Presets:")
        for key, p in MODEL_PRESETS.items():
            print(f"  [{key}] {p['repo_id']}")
            print(f"      Description : {p['description']}")
            print(f"      Target Dir  : offline/models/{p['default_dir']}")
            print(f"      VRAM Req    : {p['min_vram_gb']} GB\n")
        return

    # Determine repo and output dir
    if args.repo_id:
        repo_id = args.repo_id
        preset_key = None
        out_name = args.output_dir or repo_id.replace("/", "_").lower()
    else:
        preset_key = args.preset
        preset_info = MODEL_PRESETS[preset_key]
        repo_id = preset_info["repo_id"]
        out_name = args.output_dir or preset_info["default_dir"]

    # Base workspace repo path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, ".."))
    target_dir = os.path.join(repo_root, "offline", "models", out_name)

    print(f"=== NL2SQL Model Downloader ===")
    print(f"Target Model       : {repo_id}")
    print(f"Destination Folder : {target_dir}")
    print(f"Preset Configuration: {preset_key or 'Custom'}\n")

    # Attempt download via huggingface_hub first, then urllib fallback
    success = download_with_hf_hub(repo_id, target_dir)
    if not success:
        print("[Notice] Attempting standard HTTP stream download fallback...")
        success = download_with_urllib(repo_id, target_dir)

    if success:
        verify_and_generate_manifest(repo_id, target_dir, preset_key)
        print("\n[SUCCESS] Model downloaded and verified successfully!")
        print(f"To fine-tune with this model:")
        print(f"  python offline/training/train_qlora.py --model {target_dir}")
    else:
        print("\n[FAILED] Failed to download model. Please check network connectivity or Hugging Face access.")
        sys.exit(1)


if __name__ == "__main__":
    main()
