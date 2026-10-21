---
name: add-node
description: Add a new node to the LangGraph support agent in agent.py, including the state field, graph wiring, API response field, test, and diagram update. Use when the user asks to add a node, step, or stage to the agent, or to replace an existing node (for example "add a sentiment node" or "make classify use Claude").
argument-hint: "<what the node should do>"
---

# Add a node to the support agent

The user wants this node: **$ARGUMENTS**

Follow the project rules in CLAUDE.md. Do the steps in order.

## 1. Decide the shape (say this back to the user in 2-3 lines)

- **Name**: short snake_case, for example `sentiment`.
- **Reads** which state fields, and **writes** which new field.
- **Position**: where it goes in the graph.
  - *Before* the reply nodes (it feeds them), like `START -> classify -> sentiment -> replies`
  - *Parallel* with the reply nodes (independent), like `classify -> sentiment -> END`
  - *Replacing* a node: keep the old one as the no-key fallback.
- **Uses an LLM?** If yes, which model and which API key.

If the shape is unclear, ask one question. Otherwise continue.

## 2. Edit `agent.py`

1. Add the new field to `TicketState` with a comment: `# set by the <name> node`.
2. Write the node function:
   - Docstring starts with `Node N:`.
   - Returns only its own field.
   - For LLM nodes: copy the pattern from `claude_reply` (key check that
     returns a skip note, `try/except` that returns the error as text).
3. Wire it in `build_graph()` with `add_node` and `add_edge`.
4. Update the flow diagram in the module docstring.

## 3. Edit `main.py`

Add the new field to `TicketResponse`. Use a default (`= ""`) if the node can
be skipped.

## 4. Add a test: `tests/test_<name>.py`

- Call the node function directly with a small state dict.
- For LLM nodes: test the no-key path with `monkeypatch.delenv(...)`, and the
  happy path with a fake client. **No real API calls.**
- Add one test that runs `build_graph().invoke(...)` and checks the field exists.

## 5. Update `README.md`

Update the diagram and add one bullet that explains the node.

## 6. Check

```bash
pytest -q
python agent.py
```

Report: the files changed, the new diagram, and the test result.

## Example: LLM classifier (B2)

`/add-node make classify use Claude with structured output: category, urgency, sentiment`

Expected result:

- `classify` asks Claude for JSON `{category, urgency, sentiment}` and checks
  that `category` is one of `billing | technical | general`.
- With no `ANTHROPIC_API_KEY`, or a bad answer, it falls back to the old
  keyword logic (renamed `classify_keywords`).
- New state fields: `urgency`, `sentiment`, also added to `TicketResponse`.
- Tests: the fallback path, a fake client returning valid JSON, and a fake
  client returning junk.
