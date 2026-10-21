# Simple Support Agent

A LangGraph agent that classifies a support message and writes replies.
FastAPI serves it at `/ticket`, and `index.html` is a small web page for it.

## Layout

- `agent.py` - graph, nodes, `TicketState`
- `main.py` - FastAPI app (`/`, `/health`, `/ticket`)
- `tools.py` + `data/store.json` - fake order store for Claude tool use (see `docs/b1-tool-use.md`)
- `tests/` - pytest tests, one file per node

## Commands

```bash
pip install -r requirements.txt
cp .env.example .env             # then add your keys
uvicorn main:app --reload        # run the app
python agent.py                  # quick smoke test
pytest -q                        # run tests
```

## Rules for every change

1. **Every LLM node must work without its API key.** If the key is missing,
   return a short note like `"(skipped: set X_API_KEY to call X)"`. Never raise.
2. **Catch API errors inside the node** and return them as text. One failing
   node must not break the whole graph.
3. **Each node returns only the fields it sets.** Example: `return {"category": "billing"}`.
4. **Every field in `TicketState` has a one-line comment** saying which node sets it.
5. **New state fields must also be added to `TicketResponse` in `main.py`**,
   or the API will drop them.
6. **Keep the graph diagram current** in the `agent.py` docstring and in `README.md`.
7. **Tests must not call real APIs.** Unset the keys or use a fake client.
8. **Keys live only in `.env`** (gitignored), loaded by `load_dotenv()` in `agent.py`.
   Read them with `os.getenv`. Never write keys into code. Add new key names to `.env.example`.

## Models

- Claude: `claude-opus-5-5` (set in `CLAUDE_MODEL`)
- Gemini: `gemini-2.5-flash` (set in `GEMINI_MODEL`)

Do not change model IDs unless asked.

## Style

- Plain, simple English in comments and docs.
- Small functions with a docstring that starts with `Node N:` for graph nodes.
- No new dependencies without asking first.
