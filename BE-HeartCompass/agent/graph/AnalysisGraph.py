from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import HumanMessage
import json
import asyncio
import logging
import os

from .state import (
    AnalysisGraphInput,
    AnalysisGraphOutput,
    AnalysisGraphState,
)
from ..llm import prepareLLM
from ..prompt import getPrompt
from .checkpointer import getCheckpointer

logger = logging.getLogger(__name__)


# 全局单例
_analysis_graph_instance: CompiledStateGraph | None = None
_analysis_graph_lock = asyncio.Lock()


async def nodeFetchPromptFromScreenshots(state: AnalysisGraphState) -> dict:
    prompt_bundle = state["prompt_bundle"]

    request = state["request"]
    additional_context = request.get("additional_context") or ""
    context_block = prompt_bundle.get("context_block") or ""
    final_prompt = await getPrompt(
        os.getenv("CONVERSATION_ANALYSIS"),
        {
            "additional_context": additional_context,
            "context_block": context_block,
        },
    )
    prompt_bundle["final_prompt"] = final_prompt

    return {
        "prompt_bundle": prompt_bundle,
    }


async def nodeFetchPromptFromNarrative(state: AnalysisGraphState) -> dict:
    prompt_bundle = state["prompt_bundle"]

    context_block = prompt_bundle.get("context_block") or ""
    final_prompt = await getPrompt(
        os.getenv("NARRATIVE_ANALYSIS"),
        {
            "narrative": state["request"].get("narrative") or "",
            "context_block": context_block,
        },
    )
    prompt_bundle["final_prompt"] = final_prompt

    return {
        "prompt_bundle": prompt_bundle,
    }


async def nodeCallLLM(state: AnalysisGraphState) -> dict:
    llm: ChatOpenAI = prepareLLM()
    prompt_bundle = state["prompt_bundle"]
    final_prompt = prompt_bundle.get("final_prompt") or ""

    # todo: 删调试
    logger.info(f"final_prompt: \n{final_prompt}")

    msg = [{"type": "text", "text": final_prompt}]
    # 聊天记录分析才会有图片
    screenshot_urls = state["request"].get("conversation_screenshots")
    if screenshot_urls:
        for url in screenshot_urls:
            if not url:
                continue
            msg.append({"type": "image_url", "image_url": {"url": url}})

    messages = [HumanMessage(content=msg)]
    response = await llm.ainvoke(messages)
    response_content = response.content if hasattr(response, "content") else response
    parsed = None
    if isinstance(response_content, dict):
        parsed = response_content
    elif isinstance(response_content, str):
        try:
            parsed = json.loads(response_content)
        except json.JSONDecodeError:
            logger.warning(f"Error parsing LLM response: {response_content}")

    llm_output = state.get("llm_output") or {
        "message_candidates": [],
        "risks": [],
        "suggestions": [],
    }
    if isinstance(parsed, dict):
        if parsed.get("status") == 200:
            data = parsed.get("data") or {}
            llm_output["message_candidates"] = data.get("message_candidates", []) or []
            llm_output["risks"] = data.get("risks", []) or []
            llm_output["suggestions"] = data.get("suggestions", []) or []
        else:
            llm_output["message"] = parsed.get("message") or ""

    return {
        "llm_output": llm_output,
    }


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
        graph.add_node("nodeFetchPromptFromNarrative", nodeFetchPromptFromNarrative)
        graph.add_node("nodeFetchPromptFromScreenshots", nodeFetchPromptFromScreenshots)
        graph.add_node("nodeCallLLM", nodeCallLLM)

        # 通过_routeAnalysisPrompt按narrative分流
        def _routeAnalysisPrompt(state: AnalysisGraphState) -> str:
            narrative = state["request"].get("narrative")
            if isinstance(narrative, str) and narrative.strip():
                return "nodeFetchPromptFromNarrative"
            return "nodeFetchPromptFromScreenshots"

        graph.add_conditional_edges(
            START,
            _routeAnalysisPrompt,
        )
        graph.add_edge("nodeFetchPromptFromNarrative", "nodeCallLLM")
        graph.add_edge("nodeFetchPromptFromScreenshots", "nodeCallLLM")
        graph.add_edge("nodeCallLLM", END)

        # PostgresSaver实现短期记忆
        # todo：trim
        checkpointer = await getCheckpointer()
        _analysis_graph_instance = graph.compile(checkpointer=checkpointer)
        return _analysis_graph_instance
