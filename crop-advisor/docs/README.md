# Spec-Driven Development (SDD) with Spec Kit — Crop Advisory Agent

**Session length:** 90 minutes
**What we build:** a single AI agent that helps a farmer decide *what to spray and when*. It uses the OpenAI Agents SDK and has 3 tools.
**How we build it:** with GitHub **Spec Kit**. We write the spec first, then the plan, then the tasks, and only then the code.

> **The one idea learners should take home:**
> If you do not write a rule down, the AI will **guess** it.
> SDD means writing the decisions down *before* any code exists, so the AI follows them instead of inventing them.

---

## Table of contents

1. [What we are building](#1-what-we-are-building)
2. [Session plan (90 min)](#2-session-plan-90-min)
3. [One-time setup (PowerShell)](#3-one-time-setup-powershell)
4. [Step 0 — The "guessing" demo (vibe coding)](#4-step-0--the-guessing-demo-vibe-coding)
5. [Step 1 — Create the project (`specify init`)](#5-step-1--create-the-project-specify-init)
6. [Step 2 — Constitution](#6-step-2--constitution)
7. [Step 3 — Specify](#7-step-3--specify)
8. [Step 4 — Clarify](#8-step-4--clarify)
9. [Step 5 — Plan](#9-step-5--plan)
10. [Step 6 — Checklist (optional)](#10-step-6--checklist-optional)
11. [Step 7 — Tasks](#11-step-7--tasks)
12. [Step 8 — Analyze](#12-step-8--analyze)
13. [Step 9 — Implement](#13-step-9--implement)
14. [Step 10 — Run, test and converge](#14-step-10--run-test-and-converge)
15. [Troubleshooting](#15-troubleshooting)
16. [Key takeaways (recap slide)](#16-key-takeaways-recap-slide)
17. [Appendix A — Mock data](#appendix-a--mock-data)
18. [Appendix B — Clarify answer key](#appendix-b--clarify-answer-key)

---

## 1. What we are building

**Crop Advisor**, a command-line chat agent for farmers.

A farmer types something like:

> "Farm F001. I see brown spots with rings on my tomato leaves. Should I spray today?"

The agent:

1. Looks up the farm (crop, organic or not, days left until harvest).
2. Looks up the weather (will it rain in the next 24 hours?).
3. Looks up the treatment rules for that crop and symptom.
4. Replies with **one clear recommendation**: what to spray, the dose, and when. Or it says *don't spray, and here is why*. Or it asks a follow-up question. Or it sends the farmer to a human expert.

```
            ┌──────────────────────────────────────────┐
 Farmer ──► │          Crop Advisor Agent              │ ──► Advice
 (CLI chat) │  (OpenAI Agents SDK, single agent)       │
            └───────┬──────────────┬──────────────┬────┘
                    │              │              │
         get_field_profile  get_weather_forecast  get_treatment_rules
                    │              │              │
              farms.json     weather.json   treatment_rules.json
```

**Scope (keep it small on purpose):**

| In scope | Out of scope |
|---|---|
| 1 agent, 3 tools | Multi-agent |
| Local JSON files as mock data | Real weather / farm APIs |
| Chat history only for the current run | Database, vector store, long-term memory, RAG |
| CLI chat (`python main.py`) | Web UI |

**Why this domain?** Most learners are not farmers. They cannot fall back on "I just know how it works". The **spec is the only source of truth**, and that is exactly the point of SDD.

> ⚠️ All crop, pesticide and dose data here is **sample training data**, not real farming advice.

---

## 2. Session plan (90 min)

| Time | Step | Command | Output file |
|---|---|---|---|
| 0–10 | Why SDD + "guessing" demo | (plain chat) | — |
| 10–15 | Create the project | `specify init` | `.specify/`, `.claude/skills/` |
| 15–22 | Constitution | `/speckit-constitution` | `.specify/memory/constitution.md` |
| 22–32 | Specify | `/speckit-specify` | `specs/001-.../spec.md` |
| 32–42 | Clarify | `/speckit-clarify` | `spec.md` (updated) |
| 42–52 | Plan | `/speckit-plan` | `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` |
| 52–55 | Checklist (optional) | `/speckit-checklist` | `checklists/*.md` |
| 55–60 | Tasks | `/speckit-tasks` | `tasks.md` |
| 60–64 | Analyze | `/speckit-analyze` | report (in chat) |
| 64–80 | Implement | `/speckit-implement` | the code |
| 80–90 | Run + converge + recap | `python main.py`, `/speckit-converge` | — |

**Tip:** ask learners to finish [Section 3](#3-one-time-setup-powershell) **before** the session. Installing tools live eats the clock.

---

## 3. One-time setup (PowerShell)

### 3.1 What you need

| Tool | Version | Check with |
|---|---|---|
| Windows PowerShell | 5.1+ | `$PSVersionTable.PSVersion` |
| Python | 3.11+ | `python --version` |
| Git | any | `git --version` |
| uv | latest | `uv --version` |
| An AI coding agent | Claude Code **or** GitHub Copilot in VS Code | `claude --version` |
| OpenAI API key | — | `echo $env:OPENAI_API_KEY` |

### 3.2 Option A — run the setup script (recommended)

From this `sdd` folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup-specify.ps1
```

The script ([setup-specify.ps1](setup-specify.ps1)):

1. Checks Python and Git.
2. Allows local PowerShell scripts for your user (Spec Kit runs `.ps1` helper scripts).
3. Installs `uv`.
4. Adds `%USERPROFILE%\.local\bin` to your **user PATH**. This is where `uv` and `specify` live.
5. Installs the Spec Kit CLI (`specify`).
6. Saves `OPENAI_API_KEY` as a **user environment variable**.

Then **close and reopen** your terminal (and VS Code). New PATH values only show up in new windows.

### 3.3 Option B — the same thing, one command at a time

```powershell
# 1. Allow local scripts (Spec Kit uses .ps1 helper scripts)
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force

# 2. Install uv
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 3. Add uv's bin folder to your USER PATH (permanent) and to this window
$bin = "$env:USERPROFILE\.local\bin"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$bin*") { [Environment]::SetEnvironmentVariable("Path", "$userPath;$bin", "User") }
$env:Path = "$env:Path;$bin"

# 4. Install the Spec Kit CLI
uv tool install specify-cli
uv tool update-shell

# 5. Save your OpenAI API key (permanent, for your user only)
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-REPLACE-ME", "User")
$env:OPENAI_API_KEY = "sk-REPLACE-ME"   # also for this window
```

### 3.4 Check it works (in a NEW terminal)

```powershell
specify version
specify check
echo $env:OPENAI_API_KEY
```

`specify check` lists the tools it finds (git, claude, code, ...). A ✅ next to your AI agent is all you need.

> 🔐 Never paste your API key into a file inside the repo. The environment variable keeps it out of git.

**Upgrading later:** `uv tool upgrade specify-cli`

---

## 4. Step 0 — The "guessing" demo (vibe coding)

**Goal:** show the problem before showing the cure. (5 minutes, instructor only.)

In any AI chat, with **no spec**, type:

```
Build me a Python agent with the OpenAI Agents SDK that tells farmers
whether to spray their crops.
```

Then ask the class: *"Look at the code. Which rules did the AI decide for us?"* You will usually find answers like these:

| Question | What the AI quietly decided |
|---|---|
| What if it rains tomorrow? | Nothing, or a random threshold |
| Organic farm? | Not handled, so it may suggest a chemical spray |
| Harvest is in 3 days? | Not handled, so it may suggest an unsafe spray |
| Symptom matches 2 diseases? | Picks one at random |
| Unknown symptom? | Invents a disease and a dose ❌ |

> **Say this:** "Every empty cell is a decision the AI made *for* the business, and nobody reviewed it. SDD makes those decisions visible, written down and reviewable."

---

## 5. Step 1 — Create the project (`specify init`)

From this `sdd` folder:

```powershell
cd sdd

# Claude Code users
specify init crop-advisor --integration claude --script ps

# GitHub Copilot users (VS Code)
specify init crop-advisor --integration copilot --script ps
```

- `--integration` = which AI agent will run the slash commands.
- `--script ps` = use the PowerShell helper scripts (the default on Windows anyway).

If the CLI asks questions (for example about git), accept the defaults. This folder is already inside the course git repo.

**What you get:**

```
sdd/crop-advisor/
├── .specify/
│   ├── memory/
│   │   └── constitution.md      ← project rules (empty template for now)
│   ├── scripts/powershell/      ← helper scripts the commands call
│   └── templates/               ← templates for spec, plan, tasks
└── .claude/skills/              ← the /speckit-* commands (Copilot: .github/skills/)
```

Now open the AI agent **inside the project folder**:

```powershell
cd crop-advisor
claude            # Claude Code
# or: code .      # VS Code, then open Copilot Chat in Agent mode
```

Type `/speckit` and you should see the commands listed.

> **Command names.** In Claude Code and Copilot the commands look like `/speckit-specify`. Some older agents and tutorials show `/speckit.specify`. Same command, so use whichever form your agent shows.

---

## 6. Step 2 — Constitution

**What it is:** the project's "laws". These are rules that apply to *every* feature, not just this one. Every later step checks itself against the constitution.

**Command:** `/speckit-constitution`

**Prompt to paste:**

```
/speckit-constitution Create principles for a small, safe, teachable AI agent project:

1. Safety first: the agent must never invent a disease, chemical, or dose.
   It may only recommend treatments that exist in the treatment rules data.
   When unsure, it says so and refers the farmer to a human agri expert.
2. Business rules live in code, not only in the prompt: rules like
   "no spray before rain" and "respect the pre-harvest interval" must be
   checked by plain Python functions that can be unit-tested.
3. Simplicity: one agent, at most 3 tools, local JSON files as data,
   no database, no web UI, no extra frameworks.
4. Test-first for rules: every business rule has at least one pytest test.
5. Plain language: replies to farmers use short, simple English sentences.
6. Every recommendation explains WHY (which rule or data led to it).
7. Secrets only from environment variables (OPENAI_API_KEY). Never in code or files.
```

**Check the output:** open `.specify/memory/constitution.md`. Read it out loud with the class.

> **Teaching point:** the constitution is written *once* and reused for every future feature. It is the team's agreement, not a prompt.

---

## 7. Step 3 — Specify

**What it is:** the *what* and the *why*. **No technology.** No Python, no SDK, no JSON. Only the user, the problem and the expected behaviour.

**Command:** `/speckit-specify`

**Prompt to paste** (we leave some rules out **on purpose**, so that Clarify has something to find):

```
/speckit-specify Build a Crop Advisor assistant for small farmers.

A farmer chats with the assistant and gives their farm ID and a problem they
see on their crop (for example "brown spots with rings on tomato leaves").
The assistant decides whether the farmer should spray, what to spray, the dose,
and when to spray.

To decide, the assistant uses three sources of information:
- the farm profile (crop, organic or conventional, location, days left until harvest),
- the weather forecast for the farm's location (rain chance for the next 3 days),
- the treatment rules (which symptoms match which disease, and the allowed
  treatments for that disease with dose and pre-harvest interval).

The assistant should not recommend spraying when rain is expected soon.
Organic farms should only get organic treatments.
Treatments must respect the pre-harvest interval.
If the problem is unclear, the assistant should ask a follow-up question.
If it does not know, it must say so and refer the farmer to a human expert.

Every answer must explain why the recommendation was made.
```

**Check the output:** open `specs/001-crop-advisor/spec.md` (the folder name may be a little different). Point out these sections:

- **User stories**, written as *Given / When / Then*
- **Functional requirements** (FR-001, FR-002, ...)
- **Success criteria**
- `[NEEDS CLARIFICATION: ...]` markers ← **show these to the class!**

> **Teaching point:** every `[NEEDS CLARIFICATION]` marker is a place where vibe coding would have **guessed**. Spec Kit stops and asks instead.

---

## 8. Step 4 — Clarify

**What it is:** the AI reads the spec, finds gaps, and asks **you** up to about 5 questions, one at a time. Your answers get written back into `spec.md` under a *Clarifications* section.

**Command:**

```
/speckit-clarify
```

It will ask questions like:

- "What rain probability counts as 'rain expected soon'?"
- "How far ahead is 'soon': 24 hours or 48?"
- "What should happen when one symptom matches more than one disease?"
- "If no allowed treatment fits the pre-harvest interval, what should the assistant say?"

👉 **Answer with the rules in [Appendix B — Clarify answer key](#appendix-b--clarify-answer-key)**, so that every learner ends up with the same spec and the same demo results.

**Check the output:** open `spec.md` again and show the new `## Clarifications` section. Each answer is now a written, reviewable requirement.

> **Teaching point (the big one):** "Requirement clarity is not a meeting, it's a **file**. Tomorrow a new developer, or a new AI session, reads the same answers."

---

## 9. Step 5 — Plan

**What it is:** now, and only now, we choose the technology. The plan is checked against the constitution.

**Command:** `/speckit-plan`

**Prompt to paste:**

```
/speckit-plan Technical choices:

- Python 3.11+, OpenAI Agents SDK (pip package "openai-agents"):
  one Agent, run with Runner, tools defined with @function_tool.
- Model name read from env var OPENAI_MODEL (default "gpt-4.1-mini").
  API key from env var OPENAI_API_KEY only.
- Exactly 3 tools:
    get_field_profile(farm_id)       -> reads data/farms.json
    get_weather_forecast(location)   -> reads data/weather.json
    get_treatment_rules(crop, symptom) -> reads data/treatment_rules.json
- Business rules (rain check, organic filter, pre-harvest interval check,
  ambiguity check) are plain Python functions in rules.py, used by the tools,
  and unit-tested with pytest WITHOUT calling the LLM.
- Mock data: create the three JSON files exactly as shown in
  ../README.md, "Appendix A — Mock data".
- CLI chat loop in main.py: keep the conversation history only in memory
  for the current run (pass result.to_input_list() into the next turn).
  Type "exit" to quit. No database, no vector store, no web UI.
- Project layout: main.py, agent.py, tools.py, rules.py, data/, tests/,
  requirements.txt.
```

**Check the output** in `specs/001-crop-advisor/`:

| File | What it holds |
|---|---|
| `plan.md` | Architecture, structure and the **Constitution Check** table |
| `research.md` | Technology decisions and why |
| `data-model.md` | Farm, Forecast, TreatmentRule entities |
| `contracts/` | Tool inputs and outputs |
| `quickstart.md` | How to run and test it |

> **Teaching point:** show the *Constitution Check* in `plan.md`. The AI is reviewing its own design against the team's laws.

---

## 10. Step 6 — Checklist (optional)

**What it is:** "unit tests for the requirements". It checks that the spec is complete, clear and testable. (It does not test the code.)

```
/speckit-checklist Check the requirements for safety and clarity: no invented treatments, rain rule, organic rule, pre-harvest rule, unknown symptom handling.
```

Output: `specs/001-crop-advisor/checklists/<name>.md`. Skip this step if you are short of time.

---

## 11. Step 7 — Tasks

**What it is:** breaks the plan into small, ordered tasks. Tasks marked `[P]` can run in parallel, and the tests come before the code.

**Command:**

```
/speckit-tasks
```

**Check the output:** open `tasks.md`. Point out:

- Phases: **Setup → Tests → Core (rules, tools) → Agent → CLI → Polish**
- Each task names an exact file (for example *T005 Write tests for rain rule in tests/test_rules.py*)
- Each user story can be built and checked on its own

> **Teaching point:** small tasks = **reviewable** AI work. You can stop after any task and check it.

---

## 12. Step 8 — Analyze

**What it is:** a read-only consistency check across `constitution.md`, `spec.md`, `plan.md` and `tasks.md`. It finds requirements that no task covers, contradictions, and constitution violations. **It changes no files.**

```
/speckit-analyze
```

If it reports a **CRITICAL** issue, fix it first (re-run `/speckit-tasks`, or edit the file by hand).

> **Teaching point:** this is a code review *before* the code exists. It is the cheapest place to find a bug.

---

## 13. Step 9 — Implement

**What it is:** the AI works through `tasks.md` in order and ticks off each task (`[X]`) as it finishes it.

```
/speckit-implement
```

While it runs (about 10–15 min), narrate to the class:

- "See how it writes `tests/test_rules.py` **before** `rules.py`? That's our constitution."
- "See how `tasks.md` gets ticked? That's progress you can review."
- If it asks for permission to run `pip install` or `pytest`, allow it.

**If it stops halfway:** run `/speckit-implement` again. It continues from the first unticked task.

---

## 14. Step 10 — Run, test and converge

### 14.1 Install and run

```powershell
cd sdd/crop-advisor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

pytest                # rule tests: no LLM call, no API cost
python main.py        # chat with the agent
```

### 14.2 Live demo scenarios

Type each of these and compare the reply with the **expected behaviour**. Every row maps to a rule in [Appendix B](#appendix-b--clarify-answer-key).

| # | What to type | Expected behaviour | Rule |
|---|---|---|---|
| 1 | `Farm F001. Brown spots with rings on my tomato leaves. Should I spray today?` | **Don't spray today**: 80% rain in the next 24 h. Spray **copper oxychloride** (organic) on the first dry day. Explains why. | R1, R2 |
| 2 | `Farm F002. My chilli leaves are curling upward.` | Spray **Neem oil, 5 ml per litre**, today. Weather is dry, and the organic option is preferred and allowed (harvest in 25 days ≥ 1). | R3, R6 |
| 3 | `Farm F003. Dark wet patches on potato leaves, white mould below.` | **No spray allowed**: harvest in 4 days, but every treatment needs 7. Advises removing infected plants and contacting an expert. | R3, R5 |
| 4 | `Farm F001. Yellow spots on tomato leaves.` | **Asks a follow-up question** (rings vs. small dark-edged spots), because 2 diseases match. | R4 |
| 5 | `Farm F002. Purple stems on my chilli.` | **"I don't know"**, then refers to the local agri officer. No invented disease. | R5 |
| 6 | `What is today's tomato price?` | Politely says this is out of scope. | R7 |
| 7 | `Farm F999. Leaves are yellow.` | Says the farm ID was not found and asks the farmer to check it. | R8 |

### 14.3 Converge

```
/speckit-converge
```

This compares what was built against the spec and lists any gaps. If it finds one, the fix goes **into the spec first**, then flows down to the plan, the tasks and the code. That is the SDD loop.

> **Exercise for learners:** add a new rule: *"Do not spray if wind is above 15 km/h."* Do it the SDD way: update `spec.md` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`. Do **not** edit the code directly.

---

## 15. Troubleshooting

| Problem | Fix |
|---|---|
| `specify : The term 'specify' is not recognized` | The window has an old PATH. Refresh it: `$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")`. In VS Code, a new terminal tab is **not** enough, so quit VS Code fully and reopen it. Still failing? Run `uv tool update-shell` and check that `%USERPROFILE%\.local\bin` is in your user PATH. |
| `Set-ExecutionPolicy : ... overridden by a policy defined at a more specific scope` | Safe to ignore. The CurrentUser setting **was** saved. Only the current window keeps `Bypass`. Check with `Get-ExecutionPolicy -List`. |
| `... cannot be loaded because running scripts is disabled` | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` |
| `/speckit-...` commands don't show up | Start the agent **inside** `crop-advisor/` (where `.claude/` or `.github/` lives). Restart the agent after `specify init`. |
| `OPENAI_API_KEY` is empty | You set it after opening the window. Open a new terminal. |
| `ModuleNotFoundError: agents` | `pip install openai-agents` inside the activated `.venv`. |
| Model not found error | Set a model your key can use: `$env:OPENAI_MODEL = "gpt-4o-mini"` |
| A learner's spec differs from yours | Normal: LLM output varies. Make sure they used the **same Clarify answers** (Appendix B). |
| `/speckit-implement` stopped halfway | Run it again. It continues from the first unticked task in `tasks.md`. |

---

## 16. Key takeaways (recap slide)

1. **Unwritten rule = guessed rule.** The AI fills every gap. SDD makes the gaps visible.
2. **Clarity is a file.** Clarify answers live in `spec.md`, not in someone's head or a chat log.
3. **What before how.** The spec has no technology. The plan has no business decisions.
4. **The constitution is the team's law.** Every plan is checked against it.
5. **Small tasks = reviewable AI work.** `tasks.md` is a contract you can tick and audit.
6. **Change the spec, not the code.** New rule? Spec → Plan → Tasks → Implement.

```
 Constitution ─► Specify ─► Clarify ─► Plan ─► Tasks ─► Analyze ─► Implement ─► Converge
   (laws)        (what)    (no guess)  (how)  (steps)   (review)    (code)      (verify)
        ▲                                                                          │
        └──────────────────────── change the spec, not the code ◄──────────────────┘
```

---

## Appendix A — Mock data

The plan step asks the AI to create these files under `crop-advisor/data/`. If the generated data looks different, replace it with this, so that the demo scenarios in [14.2](#142-live-demo-scenarios) give the expected results.

> ⚠️ Sample training data only. Not real farming advice.

### `data/farms.json`

```json
[
  { "farm_id": "F001", "farmer_name": "Ravi",   "crop": "tomato", "farming_type": "organic",      "location": "Nashik", "days_to_harvest": 30 },
  { "farm_id": "F002", "farmer_name": "Lakshmi", "crop": "chilli", "farming_type": "conventional", "location": "Guntur", "days_to_harvest": 25 },
  { "farm_id": "F003", "farmer_name": "Gurpreet", "crop": "potato", "farming_type": "conventional", "location": "Jalandhar", "days_to_harvest": 4 }
]
```

### `data/weather.json`

`rain_probability` is a percent. Day 0 = the next 24 hours.

```json
{
  "Nashik":    [ { "day": 0, "rain_probability": 80 }, { "day": 1, "rain_probability": 40 }, { "day": 2, "rain_probability": 10 } ],
  "Guntur":    [ { "day": 0, "rain_probability": 10 }, { "day": 1, "rain_probability": 5  }, { "day": 2, "rain_probability": 20 } ],
  "Jalandhar": [ { "day": 0, "rain_probability": 20 }, { "day": 1, "rain_probability": 30 }, { "day": 2, "rain_probability": 70 } ]
}
```

### `data/treatment_rules.json`

```json
[
  {
    "crop": "tomato",
    "disease": "Early blight",
    "symptom_keywords": ["brown spots", "rings", "target", "yellow spots"],
    "distinguishing_sign": "Brown spots with rings, like a target",
    "treatments": [
      { "name": "Copper oxychloride", "type": "organic",  "dose": "3 g per litre of water",   "pre_harvest_interval_days": 7 },
      { "name": "Mancozeb",           "type": "chemical", "dose": "2.5 g per litre of water", "pre_harvest_interval_days": 7 }
    ]
  },
  {
    "crop": "tomato",
    "disease": "Septoria leaf spot",
    "symptom_keywords": ["small spots", "dark edges", "grey centre", "yellow spots"],
    "distinguishing_sign": "Many small spots with dark edges and grey centres",
    "treatments": [
      { "name": "Neem oil",      "type": "organic",  "dose": "5 ml per litre of water", "pre_harvest_interval_days": 1 },
      { "name": "Chlorothalonil", "type": "chemical", "dose": "2 g per litre of water",  "pre_harvest_interval_days": 7 }
    ]
  },
  {
    "crop": "chilli",
    "disease": "Leaf curl (thrips / mites)",
    "symptom_keywords": ["curl", "curling", "leaf curl"],
    "distinguishing_sign": "Leaves curl upward and look crinkled",
    "treatments": [
      { "name": "Neem oil",     "type": "organic",  "dose": "5 ml per litre of water",   "pre_harvest_interval_days": 1 },
      { "name": "Imidacloprid", "type": "chemical", "dose": "0.3 ml per litre of water", "pre_harvest_interval_days": 3 }
    ]
  },
  {
    "crop": "potato",
    "disease": "Late blight",
    "symptom_keywords": ["dark patches", "wet patches", "white mould", "white mold"],
    "distinguishing_sign": "Dark, wet-looking patches with white mould underneath",
    "treatments": [
      { "name": "Copper oxychloride",   "type": "organic",  "dose": "3 g per litre of water", "pre_harvest_interval_days": 7 },
      { "name": "Metalaxyl + Mancozeb", "type": "chemical", "dose": "2 g per litre of water", "pre_harvest_interval_days": 7 }
    ]
  }
]
```

Note: "yellow spots" matches **both** tomato diseases on purpose. This is what drives demo scenario 4 (the follow-up question).

---

## Appendix B — Clarify answer key

When `/speckit-clarify` asks a question, answer with the matching rule below. If it asks something that is not listed, answer with the closest rule, or say *"out of scope for version 1"*.

| Rule | Topic | Answer to give |
|---|---|---|
| **R1** | Rain | Do not spray if rain probability is **60% or more in the next 24 hours** (day 0). Instead, suggest the **first day in the forecast below 60%**. If no day in the 3-day forecast is below 60%, say "wait and check again in 2 days". |
| **R2** | Organic | Organic farms get **only** treatments with `type = organic`. Never show chemical options to an organic farm, not even as an "alternative". |
| **R3** | Pre-harvest interval | A treatment is allowed only if `pre_harvest_interval_days` **≤** `days_to_harvest`. Conventional farms: prefer the organic option if it is allowed, otherwise the chemical one. |
| **R4** | Ambiguous symptom | If the symptom matches **more than one disease**, ask **one** follow-up question using each disease's `distinguishing_sign`. If it is still unclear after the answer, refer to a human expert. Never pick one at random. |
| **R5** | Unknown / no safe option | If no rule matches the crop + symptom, **or** no treatment passes R2 + R3, say clearly *"I can't recommend a spray for this"*, give the reason, and refer the farmer to the **local agri officer / Krishi Vigyan Kendra**. Never invent a disease, chemical or dose. |
| **R6** | Reply format | Every recommendation has: **disease**, **treatment name**, **dose**, **when to spray**, and **why** (which data and rule led to it). Keep it to 5 short lines or fewer. |
| **R7** | Out of scope | Prices, loans, subsidies, other crops not in the data: politely say it is out of scope. |
| **R8** | Unknown farm ID | Say the farm ID was not found and ask the farmer to check it. Do not guess a crop. |
| — | Wind / temperature | **Out of scope for version 1.** (Saved for the learner exercise in 14.3.) |
| — | Language | Simple English only for version 1. |
| — | Memory | Remember the conversation only during the current run. Nothing is saved after exit. |
