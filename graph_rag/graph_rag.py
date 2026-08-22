"""
graph_rag.py — Graph RAG.

Pipeline:
  PDF text -> LLM/mock extraction -> NetworkX graph (already built by
  pipeline.py) -> at query time, find the entities mentioned in the
  question -> walk the graph outward from those entities (ego graph /
  shortest path) -> turn the relevant edges into short "facts" (triples)
  -> stuff those FACTS (not raw text) into an LLM prompt -> LLM answers.

The key difference from basic_rag.py: retrieval unit is a structured
fact ("Tom Becker -> reports_to -> Meera Iyer") pulled by *traversing
relationships*, not a paragraph pulled by *text similarity*. This means
Graph RAG can answer multi-hop questions ("how is Tom Becker connected
to Priya Sharma?") that basic RAG typically can't, because that answer
is never stated in any single chunk of the source document — it only
exists once you connect several sentences together.
"""

import os

import networkx as nx

from pipeline import extract, build_graph, read_pdf_text  # reuse Stage 2/3 from pipeline.py


def load_org_graph(pdf_path: str) -> nx.DiGraph:
    text = read_pdf_text(pdf_path)
    data = extract(text)
    return build_graph(data)


def _find_entities(g: nx.DiGraph, question: str) -> list[str]:
    q = question.lower()
    return [n for n in g.nodes if n.lower() in q]


def _edge_to_fact(src: str, tgt: str, relation: str) -> str:
    readable = relation.replace("_", " ")
    return f"{src} {readable} {tgt}."


class GraphRAGIndex:
    def __init__(self, g: nx.DiGraph):
        self.g = g

    def retrieve(self, query: str, hops: int = 1) -> list[str]:
        """Return a list of natural-language facts pulled by traversing
        the graph outward from any entity mentioned in the query."""
        entities = _find_entities(self.g, query)
        if not entities:
            return []

        facts = set()

        # Case 1: exactly one entity mentioned -> pull its role plus its
        # local neighborhood (ego graph) out to `hops` hops. hops=1 keeps
        # this tight and focused for simple lookups; the compare script
        # asks for more hops explicitly for multi-hop questions.
        if len(entities) == 1:
            person = entities[0]
            role = self.g.nodes[person].get("role")
            if role:
                facts.add(f"{person} is a {role}.")
            undirected = self.g.to_undirected()
            ego = nx.ego_graph(undirected, person, radius=hops)
            for u, v in ego.edges():
                if self.g.has_edge(u, v):
                    facts.add(_edge_to_fact(u, v, self.g[u][v]["relation"]))
                if self.g.has_edge(v, u):
                    facts.add(_edge_to_fact(v, u, self.g[v][u]["relation"]))

        # Case 2: two (or more) entities mentioned -> pull the shortest
        # connecting path between them, edge by edge. This is the
        # multi-hop case basic chunk-retrieval struggles with.
        else:
            undirected = self.g.to_undirected()
            for i in range(len(entities) - 1):
                a, b = entities[i], entities[i + 1]
                try:
                    path = nx.shortest_path(undirected, a, b)
                    for u, v in zip(path, path[1:]):
                        if self.g.has_edge(u, v):
                            facts.add(_edge_to_fact(u, v, self.g[u][v]["relation"]))
                        if self.g.has_edge(v, u):
                            facts.add(_edge_to_fact(v, u, self.g[v][u]["relation"]))
                except nx.NetworkXNoPath:
                    continue

        return sorted(facts)


def generate_answer_openai(question: str, facts: list[str]) -> str:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage

    context = "\n".join(f"- {f}" for f in facts)
    prompt = (
        "Answer the question using ONLY the facts below, which come from "
        "an org chart graph. Chain facts together if needed to explain a "
        "multi-step relationship. If the facts don't cover the question, "
        "say so explicitly instead of guessing.\n\n"
        f"Facts:\n{context}\n\nQuestion: {question}\nAnswer:"
    )
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return llm.invoke([HumanMessage(content=prompt)]).content.strip()


def generate_answer_mock(question: str, facts: list[str]) -> str:
    """Offline stand-in: since facts are already structured triples,
    we can just present the connected chain directly — this is a large
    part of why Graph RAG mock answers tend to look more complete than
    basic RAG mock answers for relational questions."""
    if not facts:
        return "No relevant facts were retrieved from the graph."
    return " ".join(facts)


def answer_with_graph_rag(index: GraphRAGIndex, question: str, hops: int = 2) -> dict:
    facts = index.retrieve(question, hops=hops)
    if os.environ.get("OPENAI_API_KEY"):
        try:
            answer = generate_answer_openai(question, facts)
        except Exception as e:
            answer = generate_answer_mock(question, facts) + f"  [OpenAI call failed: {e}]"
    else:
        answer = generate_answer_mock(question, facts)
    return {
        "question": question,
        "retrieved_context": facts,   # list of fact strings (structured triples)
        "answer": answer,
    }
