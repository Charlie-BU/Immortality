import json
import pprint
from langchain_core.messages import SystemMessage, HumanMessage
import logging
import os
from datetime import datetime

from src.agents.graphs.ConversationGraph.state import (
    ConversationGraphOutput,
    ConversationGraphState,
)
from src.agents.llm import arkAinvoke
from src.agents.prompt import getPrompt
from src.database.enums import FineGrainedFeedDimension
from src.database.index import session
from src.services.fine_grained_feed import recallFineGrainedFeeds
from src.services.figure_and_relation import buildFigurePersonaMarkdown
from src.utils.index import checkFigureAndRelationOwnership


logger = logging.getLogger(__name__)


def _formatRecalledFeeds(items: list[dict]) -> str:
    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        feed = item.get("fine_grained_feed") or {}
        content = (feed.get("content") or "").strip()
        if content == "":
            continue
        sub_dimension = feed.get("sub_dimension") or ""

        meta: list[str] = []
        confidence = feed.get("confidence") or ""
        recalled_score = item.get("score")
        if confidence:
            meta.append(f"confidence={confidence}")
        if isinstance(recalled_score, (int, float)):
            meta.append(f"recalled_score={recalled_score:.4f}")

        suffix = f" ({', '.join(meta)})" if meta else ""
        lines.append(f"{index}. {sub_dimension}\n{content}\n{suffix}")
    return "\n\n".join(lines)


async def _recallByDimension(
    state: ConversationGraphState,
    node_name: str,
    output_key: str,
    dimension: FineGrainedFeedDimension,
    top_k_env_key: str,
) -> dict:
    warnings = state.get("warnings") or []
    errors = state.get("errors") or []
    logs = state.get("logs") or []

    request = state["request"]
    user_id = request["user_id"]
    fr_id = request["fr_id"]
    messages_received = request["messages_received"]
    query = ". ".join(messages_received)

    if not isinstance(query, str) or query.strip() == "":
        warning_message = f"{node_name}: messages_received is empty"
        logger.warning(warning_message)
        warnings += [warning_message]
        logs += [
            {
                "step": node_name,
                "status": "skip",
                "detail": "Skip recall because messages_received is empty",
                "data": {
                    "fr_id": fr_id,
                    "dimension": dimension.value,
                },
            }
        ]
        logger.info(f"{node_name} executed finished\n")
        return {
            output_key: "",
            "warnings": warnings,
            "errors": errors,
            "logs": logs,
        }

    top_k = int(os.getenv(top_k_env_key, "20"))
    if top_k <= 0:
        top_k = 20
    recalled = await recallFineGrainedFeeds(
        user_id=user_id,
        fr_id=fr_id,
        query=query,
        top_k=top_k,
        scope=[dimension],
    )
    if recalled.get("status") != 200:
        error_message = (
            f"{node_name} recall failed: {recalled.get('message', 'Unknown error')}"
        )
        logger.warning(f"{node_name} recall failed: {recalled}")
        errors += [error_message]
        logs += [
            {
                "step": node_name,
                "status": "error",
                "detail": "Recall fine-grained feeds failed",
                "data": {
                    "fr_id": fr_id,
                    "dimension": dimension.value,
                    "top_k": top_k,
                    "status": recalled.get("status"),
                    "message": recalled.get("message"),
                },
            }
        ]
        logger.info(f"{node_name} executed finished\n")
        return {
            output_key: "",
            "warnings": warnings,
            "errors": errors,
            "logs": logs,
        }

    recalled_items = recalled.get("items") or []
    recalled_text = _formatRecalledFeeds(recalled_items)
    logs += [
        {
            "step": node_name,
            "status": "ok",
            "detail": "Recall fine-grained feeds success",
            "data": {
                "fr_id": fr_id,
                "dimension": dimension.value,
                "top_k": top_k,
                "recalled_count": len(recalled_items),
            },
        }
    ]
    logger.info(f"{node_name} executed finished\n")
    return {
        output_key: recalled_text,
        "warnings": warnings,
        "errors": errors,
        "logs": logs,
    }


def nodeLoadFRAndPersona(state: ConversationGraphState) -> dict:
    """
    加载当前 figure_and_relation 及其人物画像
    """
    logger.info("nodeLoadFRAndPersona is called")
    request = state["request"]

    with session() as db:
        figure_and_relation = checkFigureAndRelationOwnership(
            db=db, user_id=request["user_id"], fr_id=request["fr_id"]
        )
        if figure_and_relation is None:
            logger.error("Figure and relation not found")
            raise ValueError("Figure and relation not found")

        figure_persona = buildFigurePersonaMarkdown(figure_and_relation)
        words_to_user = figure_and_relation.words_figure2user
        # 追加节点执行日志，保留上游日志链路
        logs = state.get("logs") or []
        logs += [
            {
                "step": "nodeLoadFRAndPersona",
                "status": "ok",
                "detail": "FigureAndRelation loaded",
                "data": {
                    "fr_id": request["fr_id"],
                    "figure_role": figure_and_relation.figure_role,
                },
            }
        ]
        logger.info("nodeLoadFRAndPersona executed finished\n")
        return {
            "figure_and_relation": figure_and_relation.toJson(),
            "figure_persona": figure_persona,
            "words_to_user": ", ".join(words_to_user),
            "logs": logs,
        }


async def nodeRecallPersonalitiesFromDB(state: ConversationGraphState) -> dict:
    """
    从数据库召回 personality
    """
    logger.info("nodeRecallPersonalitiesFromDB is called")
    return await _recallByDimension(
        state=state,
        node_name="nodeRecallPersonalitiesFromDB",
        output_key="recalled_personalities_from_db",
        dimension=FineGrainedFeedDimension.PERSONALITY,
        top_k_env_key="TOP_K_FEEDS_FOR_PERSONALITY_RECALL",
    )


async def nodeRecallInteractionStylesFromDB(state: ConversationGraphState) -> dict:
    """
    从数据库召回 interaction style
    """
    logger.info("nodeRecallInteractionStylesFromDB is called")
    return await _recallByDimension(
        state=state,
        node_name="nodeRecallInteractionStylesFromDB",
        output_key="recalled_interaction_styles_from_db",
        dimension=FineGrainedFeedDimension.INTERACTION_STYLE,
        top_k_env_key="TOP_K_FEEDS_FOR_INTERACTION_STYLE_RECALL",
    )


async def nodeRecallProceduralInfosFromDB(state: ConversationGraphState) -> dict:
    """
    从数据库召回 procedural info
    """
    logger.info("nodeRecallProceduralInfosFromDB is called")
    return await _recallByDimension(
        state=state,
        node_name="nodeRecallProceduralInfosFromDB",
        output_key="recalled_procedural_infos_from_db",
        dimension=FineGrainedFeedDimension.PROCEDURAL_INFO,
        top_k_env_key="TOP_K_FEEDS_FOR_PROCEDURAL_INFO_RECALL",
    )


async def nodeRecallMemoriesFromDB(state: ConversationGraphState) -> dict:
    """
    从数据库召回 memory
    """
    logger.info("nodeRecallMemoriesFromDB is called")
    return await _recallByDimension(
        state=state,
        node_name="nodeRecallMemoriesFromDB",
        output_key="recalled_memories_from_db",
        dimension=FineGrainedFeedDimension.MEMORY,
        top_k_env_key="TOP_K_FEEDS_FOR_MEMORY_RECALL",
    )


# todo：接入火山 Viking 记忆库
# async def nodeRecallFactsFromViking(state: ConversationGraphState) -> dict:
#     """
#     从 Viking 记忆库中召回记忆
#     """


async def nodeBuildMessage(state: ConversationGraphState) -> dict:
    logger.info("nodeBuildMessage is called")

    messages = state.get("messages") or []
    messages_received = state["request"]["messages_received"]
    messages_received = "\n".join(messages_received)

    messages.append(HumanMessage(content=messages_received or ""))
    logger.info(f"nodeBuildMessage executed finished\n")
    return {
        "messages": messages,
    }


async def nodeCallLLM(state: ConversationGraphState) -> ConversationGraphOutput:
    """
    调用 LLM 生成回复
    """
    logger.info("nodeCallLLM is called")
    warnings = state.get("warnings") or []
    errors = state.get("errors") or []
    logs = state.get("logs") or []
    llm_output = state.get("llm_output") or {
        "messages_to_send": [],
        "reasoning_content": "",
    }
    messages = state.get("messages") or []

    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    CONVERSATION_SYSTEM_PROMPT = await getPrompt(
        os.getenv("CONVERSATION_SYSTEM_PROMPT"),
        {
            "words_to_user": state["words_to_user"],
            "current_timestamp": current_timestamp,
        },
    )
    if not CONVERSATION_SYSTEM_PROMPT:
        error_message = "nodeCallLLM failed: CONVERSATION_SYSTEM_PROMPT is empty"
        logger.error(error_message)
        errors += [error_message]
        logs += [
            {
                "step": "nodeCallLLM",
                "status": "error",
                "detail": "System prompt is empty",
                "data": {},
            }
        ]
        logger.info("nodeCallLLM executed finished\n")
        llm_output["messages_to_send"] = []
        llm_output["reasoning_content"] = ""
        return {
            "llm_output": llm_output,
            "warnings": warnings,
            "errors": errors,
            "logs": logs,
        }

    messages_to_send = [
        # 1. 系统提示词
        SystemMessage(content=CONVERSATION_SYSTEM_PROMPT),
        # 2. 关系与画像上下文
        SystemMessage(content=f"关系与人物画像：\n{state['figure_persona']}"),
        # # 3. DB召回的长期记忆（真实）
        # SystemMessage(
        #     content=f"可能参考的召回的长期记忆：\n{state['recalled_facts_from_db']}"
        # ),
        # # 4. Viking召回的长期记忆（不可信）
        # SystemMessage(
        #     content=f"可能参考的召回的长期记忆：\n{json.dumps(state['recalled_facts_from_viking'], ensure_ascii=False)}"
        # ),
    ] + messages

    # 使用 Ark SDK 替换 LangChain ainvoke 拿reasoning_content
    # llm: ChatOpenAI = prepareLLM(model="DOUBAO_2_0_LITE", options={
    #     "temperature": 0.3,
    #     "reasoning_effort": "low",
    # })
    # response = await llm.ainvoke(messages_to_send)
    # response_content = response.content if hasattr(response, "content") else response

    resp = await arkAinvoke(
        model="DOUBAO_2_0_LITE",
        messages=messages_to_send,
        model_options={
            "temperature": 0.3,
            "reasoning_effort": "low",
        },
    )
    output = resp["output"]
    reasoning_content = resp["reasoning_content"]
    ai_message = resp["ai_message"]

    try:
        parsed_output = json.loads(output)
    except json.JSONDecodeError:
        warning_message = "nodeCallLLM: failed to parse JSON output from LLM"
        logger.warning(f"{warning_message}: {output}")
        warnings += [warning_message]
        logs += [
            {
                "step": "nodeCallLLM",
                "status": "error",
                "detail": "LLM output is not valid JSON",
                "data": {"raw_output": output},
            }
        ]
        llm_output["messages_to_send"] = []
        llm_output["reasoning_content"] = reasoning_content or ""
        logger.info("nodeCallLLM executed finished\n")
        return {
            "llm_output": llm_output,
            "warnings": warnings,
            "errors": errors,
            "logs": logs,
        }

    if not isinstance(parsed_output, dict):
        warning_message = "nodeCallLLM: parsed output is not a dict"
        logger.warning(f"{warning_message}: {output}")
        warnings += [warning_message]
        logs += [
            {
                "step": "nodeCallLLM",
                "status": "error",
                "detail": "LLM output JSON is not an object",
                "data": {"parsed_output_type": str(type(parsed_output))},
            }
        ]
        llm_output["messages_to_send"] = []
        llm_output["reasoning_content"] = reasoning_content or ""
        logger.info("nodeCallLLM executed finished\n")
        return {
            "llm_output": llm_output,
            "warnings": warnings,
            "errors": errors,
            "logs": logs,
        }

    llm_output["messages_to_send"] = parsed_output.get("messages_to_send", [])
    llm_output["reasoning_content"] = reasoning_content or ""

    # parse成功写入short-term memory
    next_messages = messages + [ai_message]
    logs += [
        {
            "step": "nodeCallLLM",
            "status": "ok",
            "detail": "LLM response generated",
            "data": {
                "messages_to_send_count": len(llm_output["messages_to_send"]),
            },
        }
    ]

    logger.info("nodeCallLLM executed finished\n")

    # todo: 测试，上线删
    print("\n")
    pprint.pprint(state, indent=2)
    logger.info(f"\nllm_output: {llm_output}\n")
    logger.info(f"next_messages: {next_messages}\n")
    
    return {
        "llm_output": llm_output,
        "messages": next_messages,
        "warnings": warnings,
        "errors": errors,
        "logs": logs,
    }
