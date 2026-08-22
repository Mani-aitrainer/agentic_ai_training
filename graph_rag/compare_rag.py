"""
compare_rag.py — Side-by-side: Basic (chunk) RAG vs Graph RAG.

Run this to see, for the SAME set of questions:
  - what each approach retrieved as context
  - what each approach answered
  - a short note on WHY one tends to do better for that question type

Usage:
    python3 compare_rag.py
    python3 compare_rag.py --pdf company_overview.pdf --k 2 --hops 2
"""

import argparse
import textwrap

from basic_rag import chunk_text, BasicRAGIndex, answer_with_basic_rag
from graph_rag import load_org_graph, GraphRAGIndex, answer_with_graph_rag
from pipeline import read_pdf_text, render_graph


# A deliberately mixed set of questions:
#  - simple lookups (both approaches should do fine)
#  - multi-hop / aggregation questions (Graph RAG should clearly win)
DEMO_QUESTIONS = [
    {
        "question": "What is Ravi Kumar's role?",
        "type": "Simple factual lookup",
        "why": "The fact sits in a single sentence, so both approaches usually get it.",
    },
    {
        "question": "Who does Ravi Kumar report to?",
        "type": "Single-hop relationship",
        "why": "Still one sentence away — basic RAG can often retrieve the right chunk.",
    },
    {
        "question": "How is Tom Becker connected to Priya Sharma?",
        "type": "Multi-hop relationship (Tom -> Meera -> Arjun -> Priya)",
        "why": ("No single sentence in the document states this chain. Basic RAG retrieves "
                "chunks that merely LOOK similar to the question and usually misses the full "
                "path. Graph RAG walks reports_to edges hop by hop and reconstructs it exactly."),
    },
    {
        "question": "List everyone who directly reports to Priya Sharma.",
        "type": "Aggregation across the whole document",
        "why": ("Arjun, Lisa and Carlos are mentioned in three different paragraphs. Basic RAG "
                "with top-k=2 chunks will likely miss one of them. Graph RAG simply reads all "
                "in-edges of Priya Sharma's node, so it can't miss any."),
    },
]


def wrap(text: str, width: int = 100, indent: str = "    ") -> str:
    return textwrap.fill(text, width=width, initial_indent=indent, subsequent_indent=indent)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", default="company_overview.pdf")
    parser.add_argument("--k", type=int, default=2, help="top-k chunks for Basic RAG")
    parser.add_argument("--hops", type=int, default=1, help="graph traversal hops for Graph RAG")
    args = parser.parse_args()

    # --- Build both indexes from the SAME source document -----------------
    print(f"Building indexes from {args.pdf} ...\n")
    text = read_pdf_text(args.pdf)
    chunks = chunk_text(text)
    basic_index = BasicRAGIndex(chunks)

    g = load_org_graph(args.pdf)
    graph_index = GraphRAGIndex(g)
    render_graph(g, "org_graph.png")

    print(f"Basic RAG chunk count : {len(chunks)}")
    print(f"Graph RAG node/edge count: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges")
    print("=" * 100)

    # --- Run every demo question through both pipelines -------------------
    for item in DEMO_QUESTIONS:
        q = item["question"]
        print(f"\nQUESTION: {q}")
        print(f"TYPE: {item['type']}")
        print("-" * 100)

        basic = answer_with_basic_rag(basic_index, q, k=args.k)
        graph = answer_with_graph_rag(graph_index, q, hops=args.hops)

        print("[BASIC RAG]  retrieved chunks (text similarity):")
        if basic["retrieved_context"]:
            for chunk, score in basic["retrieved_context"]:
                print(f"  (score={score:.3f}) {chunk[:160]}{'...' if len(chunk) > 160 else ''}")
        else:
            print("  (nothing retrieved)")
        print(f"[BASIC RAG]  answer: {basic['answer']}")

        print()
        print("[GRAPH RAG]  retrieved facts (graph traversal):")
        if graph["retrieved_context"]:
            for fact in graph["retrieved_context"]:
                print(f"  - {fact}")
        else:
            print("  (nothing retrieved)")
        print(f"[GRAPH RAG]  answer: {graph['answer']}")

        print()
        print("WHY THIS MATTERS:")
        print(wrap(item["why"]))
        print("=" * 100)


if __name__ == "__main__":
    main()
