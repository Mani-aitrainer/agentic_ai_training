# Claude Components for the Simple Agent

Training material showing how Claude Code components and the Claude API
help us grow the simple support agent.

Everything here is **inactive on purpose**. It lives under `docs/` so you can
read it first. To turn a piece on, copy it to where Claude Code looks for it
(see the "Activate" column).

## Order of the session

| # | Topic | File | Activate |
|---|-------|------|----------|
| 1 | Project memory | [CLAUDE.md](CLAUDE.md) | copy to `simple_agent/CLAUDE.md` |
| 2 | Tool use (B1) | [b1-tool-use.md](b1-tool-use.md) | follow the steps in the doc |
| 3 | `/add-node` skill | [claude/skills/add-node/SKILL.md](claude/skills/add-node/SKILL.md) | copy `claude/skills/` to `.claude/skills/` |
| 4 | Hooks: run tests + block key leaks | [claude/settings.json](claude/settings.json), [claude/hooks/](claude/hooks/) | copy to `.claude/settings.json` and `.claude/hooks/` |
| 5 | `test-writer` subagent | [claude/agents/test-writer.md](claude/agents/test-writer.md) | copy to `.claude/agents/` |

## Layer A vs Layer B

| Layer | Who uses it | In this folder |
|-------|-------------|----------------|
| **A. Claude Code**, your dev assistant | You, while building the agent | CLAUDE.md, skill, hooks, subagent |
| **B. Claude API**, inside the agent | The agent, while answering customers | Tool use (B1) |

Story for the session: *we use Claude Code (A) to build a better agent that
uses Claude features (B).*

## Activate everything at once

Run from the `simple_agent` folder:

```bash
cp docs/CLAUDE.md CLAUDE.md
mkdir -p .claude
cp -r docs/claude/. .claude/
```

Then restart Claude Code in `simple_agent` and check:

- `/memory` shows the project CLAUDE.md
- `/add-node` appears when you type `/`
- `/agents` lists `test-writer`
- `/hooks` lists the PreToolUse and PostToolUse hooks

## Before you activate

- The hooks and `test-writer` use **pytest**. It is not in
  `requirements.txt` yet. Add it (`pytest>=8.0`) when you activate step 4.
- Open question: should new LLM nodes keep working **without API keys**
  (skip with a note, like today)? The docs assume **yes** for now. Change the
  rule in [CLAUDE.md](CLAUDE.md) if you decide otherwise.
