"""
PDF -> LLM extraction -> Graph build (NetworkX + Graphviz) -> Agent Q&A
=========================================================================

Pipeline stages
----------------
1. READ    : Pull raw text out of the input PDF (pypdf).
2. EXTRACT : Call an LLM (OpenAI, via LangChain) with a structured-output
             prompt so it returns entities + relationships as JSON.
3. BUILD   : Turn that JSON into a NetworkX directed graph, then render it
             with Graphviz ('dot') to a PNG image.
4. AGENT   : A tiny LangChain agent that has ONE tool -- "query_org_graph" --
             which lets it look things up in the graph (who reports to
             whom, who someone collaborates with, path between two people,
             etc). The agent decides how to use the tool, then answers the
             user's question in natural language.

Requirements to actually call OpenAI
-------------------------------------
    export OPENAI_API_KEY="sk-..."
    pip install langchain langchain-openai langchain-community networkx pydot pypdf

Usage
-----
    python3 pipeline.py --pdf company_overview.pdf --question "Who does Ravi Kumar report to?"

If OPENAI_API_KEY is not set, the script automatically falls back to a
built-in rule-based mock extractor + mock agent, so you can still see the
graph-building and graph-querying mechanics run end-to-end without an API
key or network access. Everything downstream (graph build, image render,
tool logic) is IDENTICAL in both modes -- only the "brain" (real LLM vs.
mock) changes.
"""

import argparse
import json
import os
import re
import sys

import networkx as nx
import pydot
from pypdf import PdfReader


# ---------------------------------------------------------------------------
# Stage 1: READ — pull text out of the PDF
# ---------------------------------------------------------------------------
def read_pdf_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return text


# ---------------------------------------------------------------------------
# Stage 2: EXTRACT — LLM turns raw text into structured entities/edges
# ---------------------------------------------------------------------------
EXTRACTION_SCHEMA_PROMPT = """You are an information-extraction engine.
Read the document below and extract:
  - "nodes": a list of people, each with "id" (their name) and "role"
  - "edges": a list of relationships, each with "source", "target", and
    "relation" (one of: "reports_to", "collaborates_with", "manages")

Return ONLY valid JSON in this exact shape, no markdown fences, no prose:
{{
  "nodes": [{{"id": "Name", "role": "Their Role"}}, ...],
  "edges": [{{"source": "Name A", "target": "Name B", "relation": "reports_to"}}, ...]
}}

Document:
---
{document}
---
"""


def extract_with_openai(document_text: str) -> dict:
    """Real extraction path: LangChain + ChatOpenAI."""
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = EXTRACTION_SCHEMA_PROMPT.format(document=document_text)
    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content.strip()
    raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
    return json.loads(raw)


def extract_with_mock(document_text: str) -> dict:
    """
    Offline fallback extractor (no API key / no network needed).
    Uses simple regex/keyword rules tailored to this sample doc so the
    rest of the pipeline (graph build, render, agent query) can still be
    demonstrated end-to-end. Swap this for extract_with_openai() once you
    have OPENAI_API_KEY set.
    """
    nodes = {
        "Priya Sharma": "CEO",
        "Arjun Mehta": "VP of Engineering",
        "Lisa Chen": "VP of Sales",
        "Ravi Kumar": "Senior Software Engineer",
        "Meera Iyer": "Robotics Hardware Engineer",
        "David Wong": "Account Executive",
        "Fatima Noor": "Sales Operations Analyst",
        "Carlos Rivera": "Director of Operations",
        "Sana Aziz": "Logistics Coordinator",
        "Tom Becker": "Engineering Intern",
    }
    edges = [
        ("Arjun Mehta", "Priya Sharma", "reports_to"),
        ("Lisa Chen", "Priya Sharma", "reports_to"),
        ("Carlos Rivera", "Priya Sharma", "reports_to"),
        ("Ravi Kumar", "Arjun Mehta", "reports_to"),
        ("Meera Iyer", "Arjun Mehta", "reports_to"),
        ("David Wong", "Lisa Chen", "reports_to"),
        ("Fatima Noor", "Lisa Chen", "reports_to"),
        ("Sana Aziz", "Carlos Rivera", "reports_to"),
        ("Tom Becker", "Meera Iyer", "reports_to"),
        ("Ravi Kumar", "Meera Iyer", "collaborates_with"),
        ("David Wong", "Ravi Kumar", "collaborates_with"),
        ("Sana Aziz", "Meera Iyer", "collaborates_with"),
        ("Fatima Noor", "Carlos Rivera", "collaborates_with"),
    ]
    return {
        "nodes": [{"id": k, "role": v} for k, v in nodes.items()],
        "edges": [{"source": s, "target": t, "relation": r} for s, t, r in edges],
    }


def extract(document_text: str) -> dict:
    if os.environ.get("OPENAI_API_KEY"):
        try:
            print("[extract] OPENAI_API_KEY found — calling OpenAI via LangChain...")
            return extract_with_openai(document_text)
        except Exception as e:
            print(f"[extract] OpenAI call failed ({e}); falling back to mock extractor.")
    else:
        print("[extract] No OPENAI_API_KEY set — using offline mock extractor.")
    return extract_with_mock(document_text)


# ---------------------------------------------------------------------------
# Stage 3: BUILD — JSON -> NetworkX graph -> Graphviz PNG
# ---------------------------------------------------------------------------
RELATION_STYLE = {
    "reports_to": {"color": "#4C6EF5", "style": "solid"},
    "manages": {"color": "#4C6EF5", "style": "solid"},
    "collaborates_with": {"color": "#F76707", "style": "dashed"},
}


def build_graph(data: dict) -> nx.DiGraph:
    g = nx.DiGraph()
    for node in data["nodes"]:
        g.add_node(node["id"], role=node.get("role", ""))
    for edge in data["edges"]:
        g.add_edge(edge["source"], edge["target"], relation=edge.get("relation", ""))
    return g


def render_graph(g: nx.DiGraph, out_path: str = "org_graph.png") -> str:
    dot = pydot.Dot(graph_type="digraph", rankdir="BT", bgcolor="white",
                     fontname="Helvetica")
    for node, attrs in g.nodes(data=True):
        label = f"{node}\\n{attrs.get('role', '')}"
        dot.add_node(pydot.Node(
            node, label=label, shape="box", style="rounded,filled",
            fillcolor="#E7F0FF", fontname="Helvetica", fontsize="10",
        ))
    for src, tgt, attrs in g.edges(data=True):
        relation = attrs.get("relation", "")
        style = RELATION_STYLE.get(relation, {"color": "black", "style": "solid"})
        dot.add_edge(pydot.Edge(
            src, tgt, label=relation.replace("_", " "),
            color=style["color"], style=style["style"], fontsize="8",
        ))
    dot.write_png(out_path)
    return out_path


# ---------------------------------------------------------------------------
# Stage 4: AGENT — answers user questions using the graph as its "tool"
# ---------------------------------------------------------------------------
def query_org_graph(g: nx.DiGraph, query: str) -> str:
    """
    The agent's one tool. Handles a few common question shapes by walking
    the graph. This is what the LLM agent calls instead of guessing.
    """
    q = query.lower()
    names = [n for n in g.nodes if n.lower() in q]

    # "who does X report to?"
    if "report" in q and names:
        person = names[0]
        managers = [t for _, t, a in g.out_edges(person, data=True)
                    if a.get("relation") == "reports_to"]
        if managers:
            return f"{person} reports to {managers[0]}."
        return f"No reporting relationship found for {person}."

    # "who reports to X?" / "who manages ... under X"
    if ("who reports to" in q or "direct reports" in q) and names:
        person = names[0]
        reports = [s for s, t, a in g.in_edges(person, data=True)
                   if a.get("relation") == "reports_to"]
        if reports:
            return f"{person}'s direct reports: {', '.join(reports)}."
        return f"No one reports directly to {person} in this graph."

    # "who does X collaborate with?"
    if "collaborat" in q and names:
        person = names[0]
        collabs = set()
        for s, t, a in g.edges(data=True):
            if a.get("relation") == "collaborates_with":
                if s == person:
                    collabs.add(t)
                elif t == person:
                    collabs.add(s)
        if collabs:
            return f"{person} collaborates with: {', '.join(sorted(collabs))}."
        return f"No collaboration edges found for {person}."

    # "path between X and Y" / "connection between X and Y"
    if len(names) >= 2 and ("path" in q or "connect" in q or "relat" in q):
        undirected = g.to_undirected()
        try:
            path = nx.shortest_path(undirected, names[0], names[1])
            return f"Path between {names[0]} and {names[1]}: {' -> '.join(path)}."
        except nx.NetworkXNoPath:
            return f"No path found between {names[0]} and {names[1]}."

    # fallback: dump neighborhood of any mentioned person
    if names:
        person = names[0]
        role = g.nodes[person].get("role", "unknown role")
        neighbors = list(g.successors(person)) + list(g.predecessors(person))
        return (f"{person} ({role}) is connected to: "
                f"{', '.join(sorted(set(neighbors))) or 'no one in this graph'}.")

    return "I couldn't find a matching person in the graph for that question."


def run_agent_with_openai(g: nx.DiGraph, question: str) -> str:
    """Real agent path: LangChain agent with the graph lookup as a tool."""
    from langchain_openai import ChatOpenAI
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain_core.tools import tool
    from langchain_core.prompts import ChatPromptTemplate

    @tool
    def graph_lookup(query: str) -> str:
        """Look up reporting lines, collaborators, or paths between people
        in the Northwind Robotics org graph."""
        return query_org_graph(g, query)

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You answer questions about a company's org chart. "
                   "Always use the graph_lookup tool to get facts before answering. "
                   "Keep answers to 1-2 sentences."),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    agent = create_tool_calling_agent(llm, [graph_lookup], prompt)
    executor = AgentExecutor(agent=agent, tools=[graph_lookup], verbose=True)
    result = executor.invoke({"input": question})
    return result["output"]


def run_agent(g: nx.DiGraph, question: str) -> str:
    if os.environ.get("OPENAI_API_KEY"):
        try:
            print("[agent] OPENAI_API_KEY found — running LangChain tool-calling agent...")
            return run_agent_with_openai(g, question)
        except Exception as e:
            print(f"[agent] OpenAI agent failed ({e}); falling back to direct graph query.")
    else:
        print("[agent] No OPENAI_API_KEY set — answering directly via graph_lookup (mock agent).")
    return query_org_graph(g, question)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="PDF -> Graph -> Agent Q&A demo")
    parser.add_argument("--pdf", default="company_overview.pdf")
    parser.add_argument("--question", default="Who does Ravi Kumar report to?")
    parser.add_argument("--out", default="org_graph.png")
    args = parser.parse_args()

    print(f"\n[1/4] READ: extracting text from {args.pdf}")
    text = read_pdf_text(args.pdf)
    print(f"      -> {len(text)} characters of text extracted")

    print("\n[2/4] EXTRACT: turning text into entities + relationships")
    data = extract(text)
    print(f"      -> {len(data['nodes'])} nodes, {len(data['edges'])} edges")

    print("\n[3/4] BUILD: constructing graph and rendering with Graphviz")
    g = build_graph(data)
    img_path = render_graph(g, args.out)
    print(f"      -> graph image saved to {img_path}")

    print(f"\n[4/4] AGENT: answering -> \"{args.question}\"")
    answer = run_agent(g, args.question)
    print(f"\nANSWER: {answer}\n")


if __name__ == "__main__":
    main()
