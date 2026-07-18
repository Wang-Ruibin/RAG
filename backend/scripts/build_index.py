"""Build the FAISS index from all knowledge documents.

Usage:
    python build_index.py [--rebuild] [--model MODEL_NAME]

Runs the same RAG pipeline used by the server at startup,
but with explicit progress reporting and error handling.

If --rebuild is given, any existing FAISS index is deleted first.
"""

import sys
import os
import time
import shutil
from pathlib import Path

# Add parent to path so we can import from app
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Configure HF mirror for China
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"


def rebuild():
    from app.config import settings
    from app.rag_engine import rag_engine

    # FAISS C++ does not support paths with Chinese characters on Windows.
    # Use ASCII-only path for index persistence.
    persist_dir = Path(os.environ.get("TEMP", r"C:\temp")) / "hhu-rag-index"

    # Clear existing index if --rebuild
    if "--rebuild" in sys.argv:
        if persist_dir.exists():
            shutil.rmtree(persist_dir)
            print(f"[OK] Removed existing index: {persist_dir}")
    persist_dir.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Persist directory ready: {persist_dir}")

    # Check model override
    model_name = None
    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        if idx + 1 < len(sys.argv):
            model_name = sys.argv[idx + 1]

    if model_name:
        print(f"[INFO] Using embedding model: {model_name}")
        rag_engine._model_name = model_name
        rag_engine._model = None  # Force reload with new model

    # Ensure engine's persist dir matches
    rag_engine._persist_dir = persist_dir

    print(f"[INFO] Knowledge base: {settings.knowledge_base_dir}")
    print(f"[INFO] Starting document processing...")
    print(f"[INFO] This will process all .md/.txt/.pdf/.docx files.")
    print(f"[INFO] Total ~1032 .md files expected.")
    print()

    # Patch _save_cache to ensure directory exists first
    original_save_cache = rag_engine._save_cache
    def patched_save_cache():
        rag_engine._persist_dir.mkdir(parents=True, exist_ok=True)
        original_save_cache()
    rag_engine._save_cache = patched_save_cache

    start = time.time()
    total_chunks = rag_engine.load_knowledge_base(settings.knowledge_base_dir)
    elapsed = time.time() - start

    # Final persist with explicit path check
    persist_dir.mkdir(parents=True, exist_ok=True)
    rag_engine._save_cache()

    print()
    print("=" * 50)
    print(f"  Index building complete!")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Vector count: {rag_engine.vector_count}")
    print(f"  Elapsed: {elapsed:.1f}s ({elapsed/60:.1f}min)")
    print(f"  Index path: {rag_engine._cache_index_path()}")
    print(f"  Chunks path: {rag_engine._cache_chunks_path()}")
    
    # Verify files on disk
    idx_file = persist_dir / "faiss_index.bin"
    ch_file = persist_dir / "chunks.json"
    if idx_file.exists():
        print(f"  [OK] faiss_index.bin: {idx_file.stat().st_size / 1024:.1f} KB")
    else:
        print(f"  [WARN] faiss_index.bin NOT on disk!")
    if ch_file.exists():
        import json
        with open(ch_file, "r", encoding="utf-8") as f:
            saved = json.load(f)
        print(f"  [OK] chunks.json: {len(saved)} chunks, {ch_file.stat().st_size / 1024:.1f} KB")
    else:
        print(f"  [WARN] chunks.json NOT on disk!")
    
    print("=" * 50)

    if rag_engine.is_ready:
        print("\n[OK] FAISS index is ready with vectors!")
    else:
        print("\n[WARN] Index appears empty after loading.")


def main():
    parser = lambda: None  # simple CLI
    rebuild()


if __name__ == "__main__":
    main()
