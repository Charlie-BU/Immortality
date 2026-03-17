# todo: Needs refactor
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
import asyncio
import logging

from .state import (
    AnalysisGraphInput,
    AnalysisGraphOutput,
    AnalysisGraphState,
)
from .nodes import node

logger = logging.getLogger(__name__)


# 全局单例
_analysis_graph_instance: CompiledStateGraph | None = None
_analysis_graph_lock = asyncio.Lock()


async def getAnalysisGraph() -> CompiledStateGraph:
    global _analysis_graph_instance
    if _analysis_graph_instance is not None:
        return _analysis_graph_instance
    async with _analysis_graph_lock:
        if _analysis_graph_instance is not None:
            return _analysis_graph_instance

        graph = StateGraph(
            state_schema=AnalysisGraphState,
            input_schema=AnalysisGraphInput,
            output_schema=AnalysisGraphOutput,
        )
        graph.add_node("node", node)
        graph.set_entry_point("node")
        graph.add_edge("node", END)

        _analysis_graph_instance = graph.compile()
        return _analysis_graph_instance
