# Research & Report Writing Team (AutoGen + LangGraph)

A multi-agent system where three AutoGen agents **converse** to produce a well-structured report on any topic, and a LangGraph workflow **orchestrates** that conversation with a human-approval gate and error handling.

This is the hands-on project for **Section 8 (Building Custom Agents with AutoGen)** and **Section 9 (Combining AutoGen and LangGraph)**.

> Tested against **AutoGen 0.7.x (v0.4 AgentChat API) / LangGraph 1.x**, Python 3.10+. **15 tests, all offline, ~0.2s.** Runs with **no API key** in offline mode.

---

## The task, in plain words

You give the team a topic. Then:

1. The **Researcher** gathers facts (via a `web_search` tool when live).
2. The **Writer** turns those facts into a full report draft.
3. The **Critic** reviews the draft and either sends it back with specific feedback (`REVISE`) or signs off (`APPROVE`).
4. Steps 1–3 repeat until the Critic approves or a safety cap is hit.
5. (Section 9) A **LangGraph** wrapper then pauses for a **human** to approve publishing, and routes cleanly to a failure branch if anything went wrong.

The Researcher and Writer are **helper agents**; the Critic plays the **supervisor** that decides when the work is done. The conversation is AutoGen; the controlled workflow around it — approval gate, retries, error routing — is LangGraph. That division is the whole point of the project.

```
        AutoGen conversation                    LangGraph control
   ┌───────────────────────────┐        ┌──────────────────────────────┐
   │ researcher → writer →      │        │ run_team → quality_gate →     │
   │        critic → (loop)     │  ───▶  │   human_approval → publish    │
   │   ends on APPROVE / cap    │        │        └→ handle_failure      │
   └───────────────────────────┘        └──────────────────────────────┘
```

---

## Why both frameworks?

AutoGen is excellent at the free-flowing, role-based **conversation** (draft → critique → revise). It is weaker at the **workflow** around that conversation: a deterministic human sign-off before publishing, retor­y/error routing, and auditability. LangGraph supplies exactly that outer control. Section 9 shows the two working together: **AutoGen inside a single LangGraph node**, with the graph owning the approval gate and failure handling.

---

## Project setup

```bash
cd research_report_team
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # paste OPENAI_API_KEY (only needed for live mode)
```

Python **3.10+** is required (AutoGen v0.4 and LangGraph v1 both need it).

---

## Run it

```bash
# 1) AutoGen team only, fully OFFLINE (scripted models, no key). Streams the
#    researcher → writer → critic conversation and prints the final report:
python cli.py --topic "LangGraph vs AutoGen" --offline

# 2) The FULL Section-9 workflow offline: AutoGen team inside LangGraph, with
#    the human approval gate (auto-answered here):
python cli.py --topic "LangGraph vs AutoGen" --offline --graph --approve yes

# 3) See the human-reject path (nothing gets published):
python cli.py --topic "LangGraph vs AutoGen" --offline --graph --approve no

# 4) LIVE (needs OPENAI_API_KEY): real gpt-4.1-mini agents with live web search:
python cli.py --topic "State of AI agents in 2026"
python cli.py --topic "State of AI agents in 2026" --graph
```

**Offline vs live:** offline mode swaps the OpenAI model client for a *replay client* that returns scripted responses, and swaps live web search for a deterministic stub. Same agents, same graph, same wiring — only the model and tool backends change. That's what lets the whole room run it without keys.

---

## Test it

```bash
pytest                                   # 15 tests, all offline
pytest tests/test_agents.py              # roles, prompts, tools
pytest tests/test_team.py                # critic loop + termination
pytest tests/test_langgraph_integration.py   # Section 9 orchestration + HITL + errors
```

---

## Project layout

```
research_report_team/
├── cli.py                          # runner: --offline / --graph / --approve
├── docs/
│   ├── concept_coverage.md         # topic → file → line numbers
│   └── build_sequence.md           # step-by-step build order for teaching
├── src/research_team/
│   ├── config.py                   # model name, sentinels, round caps
│   ├── model_client.py             # OpenAI client + offline replay client
│   ├── tools.py                    # web_search (+ offline stub)
│   ├── agents.py                   # roles, prompts, communication protocol
│   ├── team.py                     # RoundRobinGroupChat + termination (supervisor)
│   ├── runner.py                   # async run + result shaping
│   ├── errors.py                   # edge-case exception types
│   └── langgraph_app.py            # Section 9: AutoGen wrapped in LangGraph
└── tests/                          # agents / team / langgraph integration
```

---

## The communication protocol (the agent contract)

- **Researcher** → hands off a bulleted factual brief.
- **Writer** → returns the *entire* updated report each round (not a diff).
- **Critic** → ends every message with exactly one sentinel: `REVISE` + actionable feedback, or `APPROVE`.

The team's termination condition watches for `APPROVE`; a `MaxMessageTermination` cap is the backstop so a never-satisfied Critic can't loop forever. This tiny protocol is what makes an open-ended conversation converge to a finished artifact.

---

## Notes for the live path

- Live web search uses DuckDuckGo via the `ddgs` package; if it's missing or the network is down, the tool returns a graceful message and the team proceeds without external sources (see `tools.py`).
- Swapping OpenAI for Azure or another provider is a one-function change in `model_client.py`.
- AutoGen's classic (v0.2) API is **deprecated**; this project uses the current **v0.4 AgentChat** API (`AssistantAgent`, `RoundRobinGroupChat`, `TextMentionTermination`). For new Microsoft-stack work, note the **Microsoft Agent Framework** is the forward path — but the concepts here transfer directly.
```
