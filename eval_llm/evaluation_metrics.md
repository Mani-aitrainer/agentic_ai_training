# Evaluation Metrics Reference — Classic NLP & RAG

This document lists common evaluation metrics used in NLP and RAG (Retrieval-Augmented Generation) systems. For each metric: **Title**, **Purpose**, and **Formula**.

---

## Part 1: Classic NLP Metrics

### BLEU (Bilingual Evaluation Understudy)
**Purpose:** Measures how much n-gram overlap exists between a machine-generated text (e.g., translation, summary) and one or more human reference texts. Rewards precision — how many of the generated n-grams actually appear in the reference. Widely used for machine translation.

**Formula:**

$$
BLEU = BP \cdot \exp\left(\sum_{n=1}^{N} w_n \log p_n\right)
$$

Where:
- $p_n$ = modified n-gram precision (count of matching n-grams clipped to max reference count, divided by total candidate n-grams)
- $w_n$ = weight for each n-gram order (typically uniform, $w_n = 1/N$, $N=4$)
- $BP$ = brevity penalty, to penalize overly short candidates:

$$
BP = \begin{cases} 1 & \text{if } c > r \\ e^{(1 - r/c)} & \text{if } c \le r \end{cases}
$$

($c$ = candidate length, $r$ = reference length)

---

### ROUGE (Recall-Oriented Understudy for Gisting Evaluation)
**Purpose:** Measures overlap between generated and reference text, but oriented toward **recall** — how much of the reference content is captured by the generated text. Commonly used for summarization. Variants: ROUGE-N (n-gram overlap), ROUGE-L (longest common subsequence), ROUGE-S (skip-bigram).

**Formula (ROUGE-N):**

$$
ROUGE\text{-}N = \frac{\sum_{S \in References} \sum_{gram_n \in S} Count_{match}(gram_n)}{\sum_{S \in References} \sum_{gram_n \in S} Count(gram_n)}
$$

**Formula (ROUGE-L, based on LCS):**

$$
R_{lcs} = \frac{LCS(X,Y)}{m}, \quad P_{lcs} = \frac{LCS(X,Y)}{n}, \quad F_{lcs} = \frac{(1+\beta^2) R_{lcs} P_{lcs}}{R_{lcs} + \beta^2 P_{lcs}}
$$

($X$ = reference of length $m$, $Y$ = candidate of length $n$, $LCS$ = longest common subsequence length)

---

### METEOR (Metric for Evaluation of Translation with Explicit ORdering)
**Purpose:** Improves on BLEU by accounting for synonyms, stemming, and word order, combining precision and recall (weighted toward recall) with a penalty for fragmented word-order matches.

**Formula:**

$$
METEOR = (1 - Pen) \cdot F_{mean}
$$

Where:

$$
F_{mean} = \frac{10 \cdot P \cdot R}{R + 9P}, \qquad Pen = 0.5 \times \left(\frac{chunks}{unigrams\_matched}\right)^3
$$

($P$ = unigram precision, $R$ = unigram recall, *chunks* = number of contiguous matched sequences)

---

### BERTScore
**Purpose:** Uses contextual embeddings (from a pretrained model like BERT) instead of exact n-gram matching, to measure semantic similarity between generated and reference text — more robust to paraphrasing than BLEU/ROUGE.

**Formula:**

$$
R_{BERT} = \frac{1}{|x|}\sum_{x_i \in x} \max_{\hat{x}_j \in \hat{x}} \, x_i^\top \hat{x}_j, \qquad P_{BERT} = \frac{1}{|\hat{x}|}\sum_{\hat{x}_j \in \hat{x}} \max_{x_i \in x} \, x_i^\top \hat{x}_j
$$

$$
F_{BERT} = \frac{2 \cdot P_{BERT} \cdot R_{BERT}}{P_{BERT} + R_{BERT}}
$$

($x$ = reference tokens, $\hat{x}$ = candidate tokens, embeddings assumed cosine-normalized so dot product = cosine similarity)

---

### Perplexity
**Purpose:** Measures how well a language model predicts a sample of text — lower perplexity means the model assigns higher probability to the actual sequence, indicating better fluency/fit.

**Formula:**

$$
PPL(W) = \exp\left(-\frac{1}{N}\sum_{i=1}^{N} \log P(w_i \mid w_1, \dots, w_{i-1})\right)
$$

---

### F1 Score (Token/Exact-Match Level, common in QA tasks like SQuAD)
**Purpose:** Balances precision and recall of overlapping tokens between predicted and ground-truth answers (used heavily in extractive QA evaluation).

**Formula:**

$$
Precision = \frac{|Predicted \cap Reference|}{|Predicted|}, \qquad Recall = \frac{|Predicted \cap Reference|}{|Reference|}
$$

$$
F1 = \frac{2 \cdot Precision \cdot Recall}{Precision + Recall}
$$

---

### Exact Match (EM)
**Purpose:** Binary metric — checks whether the predicted answer exactly matches the reference (after normalization). Strict but simple; common in QA benchmarks.

**Formula:**

$$
EM = \frac{1}{N}\sum_{i=1}^{N} \mathbb{1}[\text{prediction}_i = \text{reference}_i]
$$

---

## Part 2: RAG (Retrieval-Augmented Generation) Metrics — RAGAS Framework

### Answer Relevancy
**Purpose:** Measures how well the generated answer addresses the actual question asked — penalizes answers that are incomplete, redundant, or contain irrelevant information. Computed by generating synthetic questions from the answer and comparing their embedding similarity to the original question.

**Formula:**

$$
Answer\ Relevancy = \frac{1}{N}\sum_{i=1}^{N} \cos(E_{g_i}, E_o)
$$

Where:
- $E_{g_i}$ = embedding of the $i$-th question generated (by an LLM) from the answer
- $E_o$ = embedding of the original question
- $N$ = number of generated questions (typically sampled, e.g., 3–5)

---

### Faithfulness (a.k.a. Groundedness)
**Purpose:** Measures whether the claims made in the generated answer can be inferred/supported from the retrieved context — i.e., checks for hallucination. Higher score means the answer sticks to the retrieved facts.

**Formula:**

$$
Faithfulness = \frac{|\text{Claims in answer supported by context}|}{|\text{Total claims in answer}|}
$$

(Claims are extracted from the answer via an LLM, then each is verified against the retrieved context as entailed/not entailed.)

---

### Context Precision
**Purpose:** Measures whether the retrieved context chunks that are actually relevant to answering the question are ranked highly (near the top) — evaluates the retriever's ranking quality.

**Formula:**

$$
Context\ Precision@K = \frac{\sum_{k=1}^{K} \left(Precision@k \times v_k\right)}{\text{Total number of relevant items in top } K}
$$

Where:
- $v_k \in \{0,1\}$ = relevance indicator of the chunk at rank $k$
- $Precision@k = \frac{\text{relevant chunks in top } k}{k}$

---

### Context Recall
**Purpose:** Measures how much of the information needed to answer the question (as present in the ground-truth answer) is actually captured within the retrieved context — evaluates whether the retriever fetched enough of the right information.

**Formula:**

$$
Context\ Recall = \frac{|\text{Ground-truth claims attributable to retrieved context}|}{|\text{Total claims in ground-truth answer}|}
$$

---

### Context Entity Recall
**Purpose:** A variant of context recall focused specifically on named entities — measures how many entities present in the ground-truth answer are also present in the retrieved context. Useful for fact-heavy or entity-dense domains.

**Formula:**

$$
Context\ Entity\ Recall = \frac{|E_{gt} \cap E_{ctx}|}{|E_{gt}|}
$$

($E_{gt}$ = set of entities in ground-truth answer, $E_{ctx}$ = set of entities in retrieved context)

---

### Answer Correctness
**Purpose:** Combines semantic similarity and factual overlap between the generated answer and the ground-truth answer — captures both meaning and factual accuracy, unlike pure semantic similarity which can miss factual errors.

**Formula:**

$$
Answer\ Correctness = w_1 \cdot F1_{factual} + w_2 \cdot Sim_{semantic}
$$

Where:

$$
F1_{factual} = \frac{2 \cdot TP}{2 \cdot TP + FP + FN}
$$

(TP = claims correctly present in both answer & ground truth, FP = claims in answer not in ground truth, FN = claims in ground truth missing from answer; $Sim_{semantic}$ = embedding cosine similarity between answer and ground truth; $w_1, w_2$ are weighting factors, commonly $w_1=w_2=0.5$)

---

### Answer Semantic Similarity
**Purpose:** Measures the semantic closeness between the generated answer and the ground-truth answer using embeddings — independent of exact wording.

**Formula:**

$$
Answer\ Semantic\ Similarity = \cos(E_{answer}, E_{ground\_truth}) = \frac{E_{answer} \cdot E_{ground\_truth}}{\|E_{answer}\| \, \|E_{ground\_truth}\|}
$$

---

## Summary Table

| Metric | Category | What it Checks |
|---|---|---|
| BLEU | Classic NLP | N-gram precision vs reference |
| ROUGE | Classic NLP | N-gram / LCS recall vs reference |
| METEOR | Classic NLP | Precision + recall with synonym/order awareness |
| BERTScore | Classic NLP | Semantic similarity via embeddings |
| Perplexity | Classic NLP | Language model fluency/fit |
| F1 (QA) | Classic NLP | Token-level precision/recall of answers |
| Exact Match | Classic NLP | Strict answer match |
| Answer Relevancy | RAG | Is the answer relevant to the question |
| Faithfulness | RAG | Is the answer grounded in retrieved context (no hallucination) |
| Context Precision | RAG | Are relevant chunks ranked high in retrieval |
| Context Recall | RAG | Did retrieval fetch all needed information |
| Context Entity Recall | RAG | Are needed entities present in retrieved context |
| Answer Correctness | RAG | Factual + semantic accuracy vs ground truth |
| Answer Semantic Similarity | RAG | Embedding-level closeness to ground truth |
