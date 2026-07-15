# CLI RAG — Learnings

## Created
- `ai_service/cli.py` — standalone CLI RAG script

## Key Design Decisions

1. **Path setup**: `sys.path.insert(0, os.path.dirname(__file__))` makes `engine.pipeline` importable without modifying PYTHONPATH.

2. **Imports**: Uses `from engine.pipeline import RAGPipeline` directly — no FastAPI or backend dependencies.

3. **CLI modes**:
   - `--ask "问题"` — single question
   - `--test` — 10 pre-defined test questions with keyword-based PASS/FAIL
   - `--rebuild` — delete index + rebuild
   - `--index` — build index only
   - No flags → interactive mode (loop with `quit`/`rebuild` commands)

4. **Parameters**: `--chunk-size` (500), `--overlap` (50), `--top-k` (5)

5. **Index auto-detection**: Checks `data/faiss.index` + `data/metadata.json` existence. Auto-builds if missing when entering ask/test/interactive modes.

6. **Test questions**: Hardcoded from instructor spec (10 questions with keyword lists). The current knowledge base doesn't contain these facts, so tests show 0/10 — that's a data issue, not a CLI issue.
