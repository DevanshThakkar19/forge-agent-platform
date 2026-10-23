"""Compile the planner → worker → critic graph."""

from __future__ import annotations

from collections.abc import Callable

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.config import Settings
from app.graph.nodes.critic import critique_node
from app.graph.nodes.planner import plan_node
from app.graph.nodes.worker import work_node
from app.graph.ollama import OllamaClient
from app.graph.state import GraphState
from app.mcp.client import InProcessToolClient, ToolClient
from app.rag.retrieve import Retriever, UnavailableRetriever


def build_graph(
    settings: Settings,
    client: ToolClient | None = None,
    retriever: Retriever | None = None,
    planner_complete: Callable[[str], str] | None = None,
) -> CompiledStateGraph:
    tool_client = client or InProcessToolClient(settings.sandbox_root)
    rag = retriever or UnavailableRetriever("retriever not configured")
    complete = planner_complete
    if complete is None and settings.planner == "local":
        complete = OllamaClient(
            settings.ollama_url,
            settings.ollama_model,
            settings.planner_timeout_s,
        ).complete

    def planner(state: GraphState) -> dict:
        return plan_node(state, max_steps=settings.max_graph_steps, complete=complete)

    def worker(state: GraphState) -> dict:
        return work_node(
            state,
            client=tool_client,
            retriever=rag,
            max_steps=settings.max_graph_steps,
            timeout_s=settings.tool_timeout_s,
        )

    graph = StateGraph(GraphState)
    graph.add_node("planner", planner)
    graph.add_node("worker", worker)
    graph.add_node("critic", critique_node)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "worker")
    graph.add_edge("worker", "critic")
    graph.add_edge("critic", END)
    return graph.compile(name="forge-orchestrator")
