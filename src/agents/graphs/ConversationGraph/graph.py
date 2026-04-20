from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import InMemorySaver
import logging

from src.agents.graphs.ConversationGraph.state import (
    ConversationGraphInput,
    ConversationGraphOutput,
    ConversationGraphState,
)
from src.agents.graphs.ConversationGraph.nodes import (
    nodeBuildMessage,
    nodeCallLLM,
    nodeLoadFRAndPersona,
    nodeRecallInteractionStylesFromDB,
    nodeRecallMemoriesFromDB,
    nodeRecallPersonalitiesFromDB,
    nodeRecallProceduralInfosFromDB,
)

# from src.agent.graph.checkpointer import getCheckpointer

logger = logging.getLogger(__name__)


def buildBaseConversationGraph() -> StateGraph:
    graph = StateGraph(
        state_schema=ConversationGraphState,
        input_schema=ConversationGraphInput,
        output_schema=ConversationGraphOutput,
    )

    graph.add_node("nodeLoadFRAndPersona", nodeLoadFRAndPersona)
    graph.add_node("nodeRecallPersonalitiesFromDB", nodeRecallPersonalitiesFromDB)
    graph.add_node(
        "nodeRecallInteractionStylesFromDB", nodeRecallInteractionStylesFromDB
    )
    graph.add_node("nodeRecallProceduralInfosFromDB", nodeRecallProceduralInfosFromDB)
    graph.add_node("nodeRecallMemoriesFromDB", nodeRecallMemoriesFromDB)
    graph.add_node("nodeBuildMessage", nodeBuildMessage)
    graph.add_node("nodeCallLLM", nodeCallLLM)

    graph.add_edge(START, "nodeLoadFRAndPersona")

    # 四个维度召回并行执行
    graph.add_edge("nodeLoadFRAndPersona", "nodeRecallPersonalitiesFromDB")
    graph.add_edge("nodeLoadFRAndPersona", "nodeRecallInteractionStylesFromDB")
    graph.add_edge("nodeLoadFRAndPersona", "nodeRecallProceduralInfosFromDB")
    graph.add_edge("nodeLoadFRAndPersona", "nodeRecallMemoriesFromDB")

    # 汇合到下游，确保四个召回都完成后再继续
    graph.add_edge("nodeRecallPersonalitiesFromDB", "nodeBuildMessage")
    graph.add_edge("nodeRecallInteractionStylesFromDB", "nodeBuildMessage")
    graph.add_edge("nodeRecallProceduralInfosFromDB", "nodeBuildMessage")
    graph.add_edge("nodeRecallMemoriesFromDB", "nodeBuildMessage")

    graph.add_edge("nodeBuildMessage", "nodeCallLLM")
    graph.add_edge("nodeCallLLM", END)
    # # todo: 先测试 LLM 调用前节点
    # graph.add_edge("nodeBuildMessage", END)

    return graph


def buildConversationGraph() -> CompiledStateGraph:
    graph = buildBaseConversationGraph()
    return graph.compile()


def buildConversationGraphWithMemory() -> CompiledStateGraph:
    # todo: PostgresSaver 报500，暂用 InMemorySaver
    graph = buildBaseConversationGraph()
    return graph.compile(checkpointer=InMemorySaver())
    # return graph.compile(checkpointer=getCheckpointer())


# 全局单例：在模块导入时执行一次，进程内后续都复用同一个对象
# ConversationGraph = buildConversationGraph()
ConversationGraph = buildConversationGraphWithMemory()


def getConversationGraph() -> CompiledStateGraph:
    return ConversationGraph
