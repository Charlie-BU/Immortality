from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
import asyncio
import logging

from .state import ContextGraphState, ContextGraphInput, ContextGraphOutput
from .nodes import (
    nodeGenBasicContext,
    nodeBuildRecallQueryFromScreenshots,
    nodeBuildRecallQueriesFromNarrative,
    nodeRecallFromDB,
    nodeRecallBranchDone,
    nodeGetMBTIKnowledge,
    nodeGetInteractionSignal,
    nodeOrganizeContext,
)

logger = logging.getLogger(__name__)


# 全局单例
_context_graph_instance: CompiledStateGraph | None = None
_context_graph_lock = asyncio.Lock()


async def getContextGraph() -> CompiledStateGraph:
    global _context_graph_instance
    if _context_graph_instance is not None:
        return _context_graph_instance
    async with _context_graph_lock:
        if _context_graph_instance is not None:
            return _context_graph_instance

        graph = StateGraph(
            state_schema=ContextGraphState,
            input_schema=ContextGraphInput,
            output_schema=ContextGraphOutput,
        )
        graph.add_node("nodeGenBasicContext", nodeGenBasicContext)
        graph.add_node(
            "nodeBuildRecallQueryFromScreenshots", nodeBuildRecallQueryFromScreenshots
        )
        graph.add_node(
            "nodeBuildRecallQueriesFromNarrative", nodeBuildRecallQueriesFromNarrative
        )
        graph.add_node("nodeRecallFromDB", nodeRecallFromDB)
        graph.add_node("nodeRecallBranchDone", nodeRecallBranchDone)
        graph.add_node("nodeGetMBTIKnowledge", nodeGetMBTIKnowledge)
        graph.add_node("nodeGetInteractionSignal", nodeGetInteractionSignal)
        graph.add_node("nodeOrganizeContext", nodeOrganizeContext)

        # 三链路并行
        # BasicContext → MBTIKnowledge
        graph.add_edge(START, "nodeGenBasicContext")
        graph.add_edge("nodeGenBasicContext", "nodeGetMBTIKnowledge")

        # 路由到不同的召回节点
        def routerByType(state: ContextGraphState) -> str:
            req_type = state["request"].get("type")
            match req_type:
                case "conversation":
                    return "nodeBuildRecallQueryFromScreenshots"
                case "narrative":
                    return "nodeBuildRecallQueriesFromNarrative"
                case "no_material":
                    return "nodeRecallBranchDone"
                case _:
                    return "nodeRecallBranchDone"

        graph.add_conditional_edges(
            START,
            routerByType,
            [
                "nodeBuildRecallQueryFromScreenshots",
                "nodeBuildRecallQueriesFromNarrative",
                "nodeRecallBranchDone",
            ],
        )
        graph.add_edge("nodeBuildRecallQueryFromScreenshots", "nodeRecallFromDB")
        graph.add_edge("nodeBuildRecallQueriesFromNarrative", "nodeRecallFromDB")
        graph.add_edge("nodeRecallFromDB", "nodeRecallBranchDone")

        # InteractionSignal
        graph.add_edge(START, "nodeGetInteractionSignal")

        # 三链路汇聚到上下文组织节点，nodeOrganizeContext 只在三条链路都完成后触发
        graph.add_edge(
            [
                "nodeGetMBTIKnowledge",
                "nodeRecallBranchDone",
                "nodeGetInteractionSignal",
            ],
            "nodeOrganizeContext",
        )

        # 结束
        graph.add_edge("nodeOrganizeContext", END)

        # ContextGraph无需短期记忆
        _context_graph_instance = graph.compile()
        return _context_graph_instance
