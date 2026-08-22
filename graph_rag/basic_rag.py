"""
basic_rag.py — "Vanilla" chunk-based RAG.

Pipeline:
  PDF text -> split into paragraph chunks -> TF-IDF vectorize chunks
  -> at query time, vectorize the question -> cosine similarity ->
  top-k most similar chunks -> stuff those chunks into an LLM prompt
  -> LLM answers using ONLY those chunks as context.

This is deliberately the "naive" baseline every RAG tutorial starts
with. It has no notion of entities or relationships — it only knows
which blocks of text look textually similar to the question.

No network/API key needed for retrieval (TF-IDF runs locally).
An OpenAI key is only used for the final answer-generation step;
without one, a simple extractive mock answer is returned instead.
"""

import os
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def chunk_text(text: str, sentences_per_chunk: int = 2) -> list[str]:
    """Fixed-size sentence-window chunking — the 'naive chunking' every
    basic RAG tutorial starts with: no overlap, no semantic awareness,
    no notion that a fact might span across a chunk boundary."""
    flat = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", flat)
    chunks = []
    for i in range(0, len(sentences), sentences_per_chunk):
        window = " ".join(sentences[i:i + sentences_per_chunk]).strip()
        if window:
            chunks.append(window)
    return chunks


class BasicRAGIndex:
    """A minimal in-memory vector index using TF-IDF instead of dense
    embeddings, so the whole demo runs offline. Swap `TfidfVectorizer`
    for `OpenAIEmbeddings` + a real vector store (FAISS/Pinecone) and
    the rest of this class's logic is the same idea real RAG systems use."""

    def __init__(self, chunks: list[str]):
        self.chunks = chunks
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.matrix = self.vectorizer.fit_transform(chunks)

    def retrieve(self, query: str, k: int = 2) -> list[tuple[str, float]]:
        q_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self.matrix)[0]
        ranked = sorted(zip(self.chunks, scores), key=lambda x: x[1], reverse=True)
        return ranked[:k]


def generate_answer_openai(question: str, chunks: list[str]) -> str:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage

    context = "\n\n".join(f"- {c}" for c in chunks)
    prompt = (
        "Answer the question using ONLY the context below. "
        "If the answer isn't fully contained in the context, say so explicitly "
        "instead of guessing.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"
    )
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return llm.invoke([HumanMessage(content=prompt)]).content.strip()


def generate_answer_mock(question: str, chunks: list[str]) -> str:
    """Offline stand-in: just surfaces the single most relevant sentence
    from the retrieved chunks, the way an under-powered RAG answer often
    reads — correct only if the whole answer happens to live in one
    sentence of one retrieved chunk."""
    if not chunks:
        return "No relevant context was retrieved."
    best_chunk = chunks[0]
    sentences = re.split(r"(?<=[.!?])\s+", best_chunk)
    q_words = set(re.findall(r"[A-Za-z]+", question.lower()))
    best_sentence = max(
        sentences,
        key=lambda s: len(q_words & set(re.findall(r"[A-Za-z]+", s.lower()))),
        default=best_chunk,
    )
    return best_sentence.strip()


def answer_with_basic_rag(index: BasicRAGIndex, question: str, k: int = 2) -> dict:
    retrieved = index.retrieve(question, k=k)
    chunks = [c for c, _ in retrieved]
    if os.environ.get("OPENAI_API_KEY"):
        try:
            answer = generate_answer_openai(question, chunks)
        except Exception as e:
            answer = generate_answer_mock(question, chunks) + f"  [OpenAI call failed: {e}]"
    else:
        answer = generate_answer_mock(question, chunks)
    return {
        "question": question,
        "retrieved_context": retrieved,   # list of (chunk_text, similarity_score)
        "answer": answer,
    }
