# B1: Give Claude Tools (Fake JSON Store)

## Goal

Today `claude_reply` can only *talk*. With tools it can *look things up* and
*take action*.

| | Reply for "I was charged twice for order 1001" |
|---|---|
| **Before** | "Sorry about that, our billing team will check your payment." |
| **After** | "I see order 1001 was charged twice ($49.00 each). I have opened refund R-1 for $49.00. You will see it in 3-5 days." |

This is Layer B: a Claude API feature that runs **inside the agent**.

## How tool use works

```
claude_reply node
   |
   |  1. send message + tool list
   v
 Claude ----> "call lookup_order(order_id='1001')"   (stop_reason = tool_use)
   ^                         |
   |  3. send tool result    | 2. our Python runs the tool on store.json
   +-------------------------+
   |
   |  4. repeat until Claude stops asking for tools
   v
 final text reply (stop_reason = end_turn)
```

Claude never touches the file itself. It *asks*, our code *runs*, and we send
back the result.

## Files to add

```
simple_agent/
  data/store.json   # fake orders and refunds
  tools.py          # tool schemas + Python functions
  agent.py          # claude_reply gets a tool loop
```

### 1. `data/store.json`

```json
{
  "orders": {
    "1001": {"email": "asha@example.com", "item": "Pro plan", "amount": 49.0, "charges": 2, "status": "paid"},
    "1002": {"email": "ravi@example.com", "item": "Basic plan", "amount": 19.0, "charges": 1, "status": "paid"},
    "1003": {"email": "meera@example.com", "item": "Pro plan", "amount": 49.0, "charges": 1, "status": "failed"}
  },
  "refunds": {}
}
```

### 2. `tools.py`

```python
"""Tools Claude can call. Data lives in data/store.json (a fake database)."""

import json
from pathlib import Path

STORE = Path(__file__).parent / "data" / "store.json"
MAX_REFUND = 100.0  # bigger refunds need a human (see B3 later)


def _load() -> dict:
    return json.loads(STORE.read_text())


def _save(data: dict) -> None:
    STORE.write_text(json.dumps(data, indent=2))


def lookup_order(order_id: str) -> dict:
    order = _load()["orders"].get(order_id)
    return order or {"error": f"No order {order_id}"}


def check_refund_status(order_id: str) -> dict:
    refund = _load()["refunds"].get(order_id)
    return refund or {"status": "no refund for this order"}


def issue_refund(order_id: str, amount: float, reason: str) -> dict:
    data = _load()
    order = data["orders"].get(order_id)
    if not order:
        return {"error": f"No order {order_id}"}
    if order_id in data["refunds"]:
        return {"error": "Refund already exists", **data["refunds"][order_id]}
    if amount > min(order["amount"], MAX_REFUND):
        return {"error": f"Amount too high. Max is {min(order['amount'], MAX_REFUND)}"}
    refund = {"id": f"R-{len(data['refunds']) + 1}", "amount": amount,
              "reason": reason, "status": "started"}
    data["refunds"][order_id] = refund
    _save(data)
    return refund


TOOLS = [
    {
        "name": "lookup_order",
        "description": "Get an order by its ID: item, amount, how many times it was charged, status.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "check_refund_status",
        "description": "See if a refund exists for an order and its status.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "issue_refund",
        "description": "Start a refund. Only use after lookup_order confirms the problem "
                       "(for example a double charge). Amount must not exceed the order amount.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "amount": {"type": "number"},
                "reason": {"type": "string"},
            },
            "required": ["order_id", "amount", "reason"],
        },
    },
]

FUNCTIONS = {
    "lookup_order": lookup_order,
    "check_refund_status": check_refund_status,
    "issue_refund": issue_refund,
}


def run_tool(name: str, args: dict) -> str:
    """Run one tool and return its result as a JSON string for Claude."""
    try:
        return json.dumps(FUNCTIONS[name](**args))
    except Exception as err:  # bad args, missing tool, file error
        return json.dumps({"error": str(err)})
```

### 3. Tool loop in `claude_reply`

Only the call part changes. The key check and refusal handling stay as they are.

```python
from tools import TOOLS, run_tool

MAX_TOOL_ROUNDS = 5  # safety limit so a loop can never run forever


def claude_reply(state: TicketState) -> TicketState:
    """Node 4: ask Claude to reply, letting it call order tools."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return {"claude_reply": "(skipped: set ANTHROPIC_API_KEY to call Claude)"}

    import anthropic

    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": state["message"]}]
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            response = client.beta.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT.format(category=state["category"]),
                messages=messages,
                tools=TOOLS,
                output_config={"effort": "low"},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
            if response.stop_reason != "tool_use":
                break
            # Claude asked for tools: run each one and send the results back.
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": b.id,
                 "content": run_tool(b.name, b.input)}
                for b in response.content if b.type == "tool_use"
            ]})
    except anthropic.APIError as err:
        return {"claude_reply": f"(Claude error: {err})"}

    if response.stop_reason == "refusal":
        return {"claude_reply": "(Claude declined to answer this message)"}
    text = "".join(b.text for b in response.content if b.type == "text")
    return {"claude_reply": text}
```

Also add one line to `SYSTEM_PROMPT`:

```python
"If the customer gives an order ID, use the tools to check it before replying. "
```

## Try it

```bash
curl -X POST http://127.0.0.1:8000/ticket \
  -H "Content-Type: application/json" \
  -d '{"message": "I was charged twice for order 1001, please refund"}'
```

Then open `data/store.json`. You should see a new entry under `refunds`.
Reset the file with `git checkout data/store.json` between demos.

## Teaching points

- **The tool description is the prompt.** Claude picks tools by reading the
  `description`. Try a vague description and watch it pick badly.
- **Guard rails live in Python, not in the prompt.** `MAX_REFUND` and the
  "already refunded" check are enforced by code, so Claude cannot skip them.
- **Errors go back to Claude as data.** `run_tool` never raises. Claude reads
  the error and explains it to the customer.
- **Always cap the loop** (`MAX_TOOL_ROUNDS`).

## How Layer A helps build this

| Step | Claude Code component |
|------|-----------------------|
| Writing `tools.py` follows the project rules | [CLAUDE.md](CLAUDE.md) |
| Tests for `tools.py` without real API calls | [test-writer](claude/agents/test-writer.md) |
| Tests run after every edit | [PostToolUse hook](claude/settings.json) |
| A key pasted into code by mistake is blocked | [PreToolUse hook](claude/hooks/block_key_leak.py) |
