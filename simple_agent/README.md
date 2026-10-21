# Simple Support Agent (LangGraph + FastAPI)

A tiny agent. After `classify`, three reply nodes run in parallel:

```
                  +-> respond      -+
START -> classify +-> gemini_reply -+-> END
                  +-> claude_reply -+
```

- **classify**: looks for keywords and picks `billing`, `technical`, or `general`.
- **respond**: writes a fixed reply for that category.
- **gemini_reply**: asks Google Gemini (`gemini-2.5-flash`) to write a reply.
- **claude_reply**: asks Anthropic Claude (`claude-opus-5-5`) to write a reply.

The LLM nodes need API keys. Without a key, the node is skipped and returns a short note.

Put your keys in `simple_agent/.env` (it is gitignored). `agent.py` loads it with `load_dotenv()`:

```bash
cp .env.example .env   # then fill in the values
```

```
GEMINI_API_KEY=...      # from https://aistudio.google.com/apikey
ANTHROPIC_API_KEY=...   # from https://console.anthropic.com
```

## Run

```bash
cd simple_agent
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000 for a simple web page ([index.html](index.html)),
or http://127.0.0.1:8000/docs for the API docs.

## Example

```bash
curl -X POST http://127.0.0.1:8000/ticket \
  -H "Content-Type: application/json" \
  -d '{"message": "I was charged twice, please refund"}'
```

Response:

```json
{
  "message": "I was charged twice, please refund",
  "category": "billing",
  "reply": "Thanks! Our billing team will check your payment within 24 hours.",
  "gemini_reply": "...",
  "claude_reply": "..."
}
```
