# PDF → Graph → Agent: Basic RAG vs Graph RAG (Teaching Demo)

A small, self-contained demo built for training sessions. It takes one
PDF document, and shows learners **three** things side by side:

1. A full pipeline: **PDF → LLM extraction → NetworkX/Graphviz graph → agent Q&A**
2. **Basic RAG**: the "naive" chunk-and-embed retrieval every RAG tutorial starts with
3. **Graph RAG**: retrieval by walking relationships in a knowledge graph instead

The goal is to let learners *see* the difference in retrieved context and
answer quality, not just be told about it.

---

## 1. The story / dataset

`company_overview.pdf` is a generated, domain-neutral document describing
a fictional company, **Northwind Robotics** — its people, roles, reporting
lines, and who collaborates with whom. It's intentionally small (10
people, ~13 relationships) so learners can read the whole source document
in under a minute and then verify the graph/answers against it by eye.

Swap this PDF for a domain-specific one (insurance claims, fraud cases,
loan approvals, etc.) and the same pipeline still works — see
[Adapting this to your own domain](#adapting-this-to-your-own-domain).

---

## 2. Files in this folder

| File | Purpose |
|---|---|
| `make_sample_pdf.py` | Generates `company_overview.pdf` (the source document) |
| `company_overview.pdf` | The sample input document |
| `pipeline.py` | Stage-by-stage pipeline: read PDF → LLM-extract entities/relationships → build graph → render with Graphviz → agent answers a question using the graph as a tool |
| `basic_rag.py` | Basic RAG: chunk the PDF text, retrieve top-k chunks by TF-IDF similarity, answer from those chunks |
| `graph_rag.py` | Graph RAG: reuse the graph from `pipeline.py`, retrieve *facts* by traversing relationships (ego graph / shortest path), answer from those facts |
| `compare_rag.py` | Runs the same set of questions through **both** RAG approaches and prints retrieved context + answers side by side, with a short "why this matters" note per question |
| `notebook.ipynb` | The same walkthrough as an interactive Jupyter notebook, with explanations in markdown cells — best format to actually present to learners |
| `org_graph.png` | Rendered graph image (generated when you run `pipeline.py` or `compare_rag.py`) |
| `requirements.txt` | Python dependencies |

---

## 3. Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

You also need the Graphviz **system binary** (`dot`) installed — it's not
a Python package:

```bash
# Ubuntu/Debian
sudo apt-get install graphviz

# macOS
brew install graphviz
```

### Optional: real OpenAI calls

Everything in this demo runs **fully offline** by default, using a
rule-based mock extractor/agent so learners with no API key can still see
every stage execute end to end. To use real LLM calls instead:

```bash
export OPENAI_API_KEY="sk-..."
```

Every script auto-detects the key and switches from mock mode to real
`ChatOpenAI` (via LangChain) automatically — no code changes needed. Look
for the `[extract] ...` / `[agent] ...` log lines each script prints to
see which mode it's running in.

---

## 4. How to run each piece

### 4.1 Regenerate the sample PDF (optional — already included)
```bash
python3 make_sample_pdf.py
```

### 4.2 Full pipeline demo (PDF → graph → agent)
```bash
python3 pipeline.py --question "Who does Ravi Kumar report to?"
```
This prints each of the 4 stages as it runs and saves `org_graph.png`.

### 4.3 Basic RAG vs Graph RAG comparison (the main teaching artifact)
```bash
python3 compare_rag.py
```
This runs 4 pre-picked questions — ranging from simple lookups to
multi-hop and aggregation questions — through both approaches and prints,
for each one:
- what **Basic RAG** retrieved (raw text chunks + similarity scores) and its answer
- what **Graph RAG** retrieved (structured facts/triples from graph traversal) and its answer
- a short note on *why* one approach tends to do better for that question shape

Flags:
```bash
python3 compare_rag.py --k 3 --hops 2   # retrieve more chunks / hop further in the graph
```

### 4.4 Notebook (recommended for live teaching)
```bash
jupyter notebook notebook.ipynb
```
Walks through the same material interactively, one concept per cell, so
you can pause and discuss with learners at each stage.

---

## 5. Basic RAG vs Graph RAG — what to point out to learners

| | **Basic RAG** (`basic_rag.py`) | **Graph RAG** (`graph_rag.py`) |
|---|---|---|
| Retrieval unit | A chunk of raw text (fixed-size sentence windows) | A fact/triple (`A —relation→ B`) pulled by traversing edges |
| Retrieval method | Text similarity (TF-IDF here; cosine similarity over embeddings in production systems) | Graph traversal (ego graph / shortest path) anchored on entities named in the question |
| Good at | Questions whose answer sits inside **one** chunk of text | Questions whose answer requires **connecting multiple facts**, possibly stated in different sentences or even different documents |
| Struggles with | **Multi-hop** questions ("how is A connected to B through several relationships?") and **aggregation** questions ("list all X that relate to Y") — the answer may be split across chunks that don't all score high enough to be retrieved together | Free-text nuance that was never modeled as an entity/relationship in the first place (e.g. sentiment, opinions, unstructured narrative) |
| Fails silently as | A chunk that merely *sounds* similar to the question, but doesn't contain the actual answer, gets retrieved instead of the correct one | A relationship that was missed during entity/relationship extraction — if it's not in the graph, it can't be traversed |

### The 4 demo questions in `compare_rag.py`, and why they're chosen

1. **"What is Ravi Kumar's role?"** — simple, single-fact lookup. Both
   approaches usually do fine. Baseline to show they're not *always*
   different.
2. **"Who does Ravi Kumar report to?"** — still a single-hop fact, but
   now relational. Shows both can still work when the fact is local.
3. **"How is Tom Becker connected to Priya Sharma?"** — a **3-hop**
   relationship (Tom → Meera → Arjun → Priya) that is **never stated in
   any single sentence** of the source document. This is the clearest
   "aha" moment: Graph RAG reconstructs the full chain exactly, because
   it's just walking edges. Basic RAG retrieves whichever chunk sounds
   textually closest to the question and usually gets it wrong or
   incomplete.
4. **"List everyone who directly reports to Priya Sharma."** — an
   **aggregation** question. The three direct reports (Arjun, Lisa,
   Carlos) are mentioned in three different paragraphs. Basic RAG with a
   small top-k will typically miss at least one, because it's ranking
   chunks by similarity to the *question text*, not by whether they
   contain a complete list. Graph RAG just reads every in-edge of one
   node — it structurally cannot miss one.

**The core lesson for learners:** Basic RAG treats retrieval as *"find
text that looks like the question."* Graph RAG treats retrieval as
*"find facts that are structurally connected to what the question is
about."* The second framing generalizes much better to multi-hop and
aggregation questions — which is exactly the kind of question real
fraud-graph / claims-relationship use cases are full of.

---

## 6. Architecture diagram (conceptual)

```
                    ┌─────────────┐
                    │  Input PDF  │
                    └──────┬──────┘
                           │  pypdf text extraction
                           ▼
                 ┌───────────────────┐
                 │   Raw document     │
                 │       text         │
                 └──────┬─────┬───────┘
                        │     │
        ┌───────────────┘     └────────────────┐
        ▼                                       ▼
┌───────────────────┐               ┌────────────────────────┐
│   BASIC RAG PATH    │               │     GRAPH RAG PATH       │
│ ------------------  │               │ ------------------------ │
│ chunk_text()         │               │ LLM/mock extraction       │
│  -> fixed windows     │               │  -> {nodes, edges} JSON    │
│ TF-IDF vectorize       │              │ build_graph()               │
│  -> similarity search   │             │  -> NetworkX DiGraph          │
│ top-k chunks             │            │ GraphRAGIndex.retrieve()        │
└──────────┬────────────────┘           │  -> ego graph / shortest path      │
           │                            │  -> facts as triples                 │
           ▼                            └───────────────┬───────────────────────┘
   generate_answer()                                     ▼
   (LLM or mock, given                             generate_answer()
    raw chunks as context)                    (LLM or mock, given facts as context)
           │                                                    │
           └───────────────────────┬────────────────────────────┘
                                    ▼
                     compare_rag.py prints both,
                     side by side, per question
```

---

## 7. Adapting this to your own domain

To reuse this for the healthtech/insurance capstone (or any other
domain):

1. Replace `make_sample_pdf.py`'s content with real (or synthetic)
   domain text — claims, providers, patients, policies, etc.
2. Update the extraction prompt in `pipeline.py`
   (`EXTRACTION_SCHEMA_PROMPT`) and the mock extractor's node/edge
   schema to match your entities (e.g. `Claim`, `Provider`, `Patient`)
   and relationship types (e.g. `filed_by`, `treated_by`, `flagged_for`).
3. `basic_rag.py` needs no domain changes — chunking and TF-IDF are
   domain-agnostic.
4. `graph_rag.py` needs no domain changes either, as long as
   `pipeline.extract()` and `pipeline.build_graph()` still return a
   NetworkX graph with `role`/`relation` attributes in the same shape.
5. Pick 3-4 new demo questions the same way this README does: one
   simple lookup, one single-hop relation, one multi-hop relation, one
   aggregation — that mix is what makes the Basic-vs-Graph contrast
   visible to learners.
