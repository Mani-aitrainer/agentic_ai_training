# 📚 RAG — Retrieval Augmented Generation

> **A complete guide for AI/ML practitioners and learners**

---

## 🧠 What is RAG?

RAG stands for **Retrieval Augmented Generation** — a technique that enhances Large Language Models (LLMs) by connecting them to **external, up-to-date knowledge sources** before generating a response.

Instead of relying solely on what the model learned during training, RAG **retrieves relevant data**, **augments the prompt** with it, and then **generates a grounded, accurate response**.

![What is RAG?](rag_definition.png)

---

## ❌ The Problem: LLMs Without RAG

Without RAG, an LLM:

| Problem | Description |
|---|---|
| 🌀 Hallucination | Makes up facts with confidence — ungrounded answers |
| 📅 Stale Knowledge | Training data has a cutoff; doesn't know recent events |
| 🏦 No Domain Data | Cannot access your organisation's private documents |
| ❓ No Citations | Cannot point to where the answer came from |

---

## ✅ The Solution: LLMs With RAG

![RAG vs No RAG Comparison](rag_intro.png)

With RAG, the LLM can:

- ✅ **Ground answers** on real source data with citations
- ✅ **Stay up to date** — retrieves live or recent documents
- ✅ **Be as comprehensive as a search engine**
- ✅ **Use your private data** — internal PDFs, databases, wikis

---

## 🔤 Breaking Down R–A–G

| Letter | Term | What it Does |
|---|---|---|
| **R** | **Retrieve** | Search for relevant documents or chunks |
| **A** | **Augment** | Add the retrieved text into the prompt context |
| **G** | **Generate** | LLM produces a context-aware, accurate response |

---

## 🏗️ RAG Architecture: Full Pipeline

![RAG Pipeline — Data Preparation & Retrieval](rag_pipeline.png)

The RAG pipeline has **two phases**:

---

### Phase 1: Data Preparation (Offline / One-Time)

This phase prepares your knowledge base before any user query arrives.

```
Raw Data Sources → Information Extraction → Chunking → Embedding → Vector Database
      A                     B                  C           D
```

| Step | Component | Details |
|---|---|---|
| **A** | Raw Data Sources | PDFs, Word docs, websites, databases, CSVs |
| **B** | Information Extraction | OCR, PDF parsers, web crawlers, HTML scrapers |
| **C** | Chunking | Split large documents into small, meaningful pieces (e.g., 512 tokens) |
| **D** | Embedding | Convert each chunk into a numerical vector using an Embedding Model |
| — | Vector Database | Store all vectors for fast similarity search (e.g., FAISS, Pinecone, ChromaDB) |

---

### Phase 2: Retrieval Augmented Generation (Online / Per Query)

This phase runs every time a user asks a question.

```
Query → Embedding → Vector DB Search → Relevant Chunks → (Reranking) → LLM → Response
  1         2              3                              [Optional]      4        5
```

| Step | Action |
|---|---|
| **1** | User submits a query |
| **2** | Query is converted to a vector using the same Embedding Model |
| **3** | Vector DB performs similarity search and returns top-N chunks |
| **Reranking** | (Optional but recommended) Reranker reorders chunks by true relevance |
| **4** | Top relevant chunks are injected into the LLM prompt |
| **5** | LLM generates a grounded, cited response |

---

## 🔁 Reranking — The Missing Piece in Basic RAG

### Why Reranking?

Vector similarity search is **fast but imprecise**. It retrieves documents that are **semantically close** to the query, but the top result may not always be the **most relevant** one.

A **Reranking Model** solves this by performing a **deeper, cross-attention comparison** between the query and each retrieved chunk — reordering them by true relevance before passing to the LLM.

---

### Basic RAG vs RAG + Reranker

```
Basic RAG Pipeline:
Query → Embedding → Vector DB (Top-K) → LLM → Response

RAG + Reranker Pipeline:
Query → Embedding → Vector DB (Top-K) → Reranker (reorder) → Top-N → LLM → Response
                                           ↑
                              [More accurate relevance scoring]
```

---

### How a Reranker Works

| Stage | Description |
|---|---|
| **Input** | Query + each retrieved chunk (as a pair) |
| **Model** | Cross-encoder (e.g., `ms-marco-MiniLM`, Cohere Rerank, BGE Reranker) |
| **Output** | Relevance score for each chunk |
| **Action** | Reorder chunks by score; pass only Top-N to LLM |

> 💡 **Key Difference:**  
> - **Bi-encoder (Embedding Model)** → encodes query and document *separately* → fast, approximate  
> - **Cross-encoder (Reranker)** → encodes query + document *together* → slower, more accurate

---

### Popular Reranking Models

| Model | Provider | Notes |
|---|---|---|
| `ms-marco-MiniLM-L-6-v2` | Hugging Face / Microsoft | Lightweight, fast |
| `bge-reranker-large` | BAAI | Strong open-source option |
| Cohere Rerank API | Cohere | API-based, production-ready |
| `cross-encoder/nli-deberta-v3-large` | Hugging Face | High accuracy |

---

### Reranking — Code Example (Python)

```python
from sentence_transformers import CrossEncoder

# Load reranking model
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# Query and retrieved chunks from vector DB
query = "What are the loan eligibility criteria for SBI home loans?"

retrieved_chunks = [
    "SBI home loans require a minimum credit score of 650.",
    "The interest rate for SBI home loans starts at 8.5% per annum.",
    "Applicants must be between 18 and 70 years of age.",
    "SBI offers pre-approved home loans for existing customers.",
]

# Create (query, chunk) pairs
pairs = [(query, chunk) for chunk in retrieved_chunks]

# Score each pair
scores = reranker.predict(pairs)

# Rank by relevance score
ranked = sorted(zip(scores, retrieved_chunks), reverse=True)

print("Reranked Results:")
for score, chunk in ranked:
    print(f"  Score: {score:.4f} → {chunk}")
```

---

## 🔄 Complete RAG + Reranker Pipeline (End to End)

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA PREPARATION (Offline)                   │
│  Raw Docs → Extract → Chunk → Embed → Store in Vector DB        │
└─────────────────────────────────────────────────────────────────┘
                              │
                     [Vector DB Ready]
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    QUERY TIME (Online)                           │
│                                                                  │
│  User Query                                                      │
│      ↓                                                           │
│  Embed Query (Bi-Encoder)                                        │
│      ↓                                                           │
│  Vector DB Similarity Search → Top-K Chunks (e.g., K=20)        │
│      ↓                                                           │
│  Reranker (Cross-Encoder) → Reorder → Top-N Chunks (e.g., N=5)  │
│      ↓                                                           │
│  Augment Prompt with Top-N Chunks                                │
│      ↓                                                           │
│  LLM Generates Response (Grounded + Cited)                       │
│      ↓                                                           │
│  Final Answer to User ✅                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏦 RAG in Indian Banking Context

| Use Case | RAG Application |
|---|---|
| **RBI Circular Q&A** | Retrieve latest circulars, answer compliance queries |
| **Loan Eligibility Bot** | Pull bank-specific product PDFs and answer customer questions |
| **KYC Document Assistant** | Extract and verify customer-submitted documents |
| **Fraud Detection Reports** | Retrieve past case summaries for pattern matching |
| **Branch Locator + Policy** | Combine structured data + policy documents |

---

## 🛠️ Key Tools & Libraries

| Category | Tool/Library |
|---|---|
| **Embedding Models** | `sentence-transformers`, OpenAI `text-embedding-ada-002`, Cohere Embed |
| **Vector Databases** | FAISS, ChromaDB, Pinecone, Weaviate, Qdrant |
| **Rerankers** | `sentence-transformers CrossEncoder`, Cohere Rerank, BGE Reranker |
| **Chunking** | LangChain `RecursiveCharacterTextSplitter`, LlamaIndex |
| **Orchestration** | LangChain, LlamaIndex, Haystack |
| **LLMs** | OpenAI GPT-4, Claude, Gemini, Mistral, LLaMA |

---

## 📌 Quick Summary

```
RAG = Retrieval + Augmentation + Generation

Without RAG  →  LLM guesses from memory
With RAG     →  LLM answers from your documents
With Reranker →  LLM answers from your MOST RELEVANT documents
```

| Feature | No RAG | RAG | RAG + Reranker |
|---|---|---|---|
| Hallucination | High ❌ | Low ✅ | Very Low ✅✅ |
| Up-to-date Info | No ❌ | Yes ✅ | Yes ✅ |
| Private Data | No ❌ | Yes ✅ | Yes ✅ |
| Answer Quality | Basic | Good | Best ✅✅ |
| Speed | Fast | Medium | Slightly slower |

---

> 📝 **Note for Learners:** Start with basic RAG using LangChain + FAISS + OpenAI. Once comfortable, add a CrossEncoder reranker to see how answer quality improves dramatically.

---

*Prepared for AI/ML Training — Indian Banking & Healthcare Context*
