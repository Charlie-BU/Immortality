import json
import logging
import os
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.graphs.FRBuildingGraph.state import FRBuildingGraphState
from src.agents.llm import prepareLLM
from src.agents.prompt import getPrompt
from src.database.enums import (
    FigureRole,
    FineGrainedFeedConfidence,
    FineGrainedFeedDimension,
    OriginalSourceType,
    parseEnum,
)
from src.database.index import session
from src.services.fine_grained_feed import addOriginalSource
from src.utils.index import checkFigureAndRelationOwnership

logger = logging.getLogger(__name__)


def nodeLoadFR(state: FRBuildingGraphState) -> dict:
    """
    加载当前 figure_and_relation 和 figure_role
    """
    request = state["request"]
    with session() as db:
        figure_and_relation = checkFigureAndRelationOwnership(
            db=db, user_id=request["user_id"], fr_id=request["fr_id"]
        )
        if figure_and_relation is None:
            logger.error("Figure and relation not found")
            raise ValueError("Figure and relation not found")
        # 追加节点执行日志，保留上游日志链路
        logs = state.get("logs") or []
        logs += [
            {
                "step": "nodeLoadFR",
                "status": "ok",
                "detail": "FigureAndRelation loaded",
                "data": {
                    "fr_id": request["fr_id"],
                    "figure_role": figure_and_relation.figure_role,
                },
            }
        ]
        return {
            "figure_and_relation": figure_and_relation.toJson(),
            "figure_role": parseEnum(FigureRole, figure_and_relation.figure_role),
            "logs": logs,
        }


async def nodePreprocessInput(state: FRBuildingGraphState) -> dict:
    """
    预处理 raw_content 和 raw_images（如有）
    """
    request = state["request"]
    raw_content = (request.get("raw_content") or "").strip()
    raw_images = request.get("raw_images") or []
    # warnings / logs 统一通过 state 透传，保证可观测性
    warnings = state.get("warnings") or []
    logs = state.get("logs") or []

    # 空判定
    if raw_content == "" and len(raw_images) == 0:
        logger.error("raw_content and raw_images cannot be both empty")
        raise ValueError("raw_content and raw_images cannot be both empty")
    # 内容过短
    if raw_content and len(raw_content) < 10:
        warning = "raw_content is too short, it may not contain enough information"
        logger.warning(warning)
        # 保留为 warning，中断流程
        warnings = warnings + [warning]
        raise ValueError(warning)

    # LLM 预处理
    llm = prepareLLM(
        "DOUBAO_2_0_MINI", options={"temperature": 0, "reasoning_effort": "low"}
    )
    FR_BUILDING_PREPROCESS_SYSTEM_PROMPT = await getPrompt(
        os.getenv("FR_BUILDING_PREPROCESS_SYSTEM_PROMPT")
    )
    FR_BUILDING_PREPROCESS_INPUT = await getPrompt(
        os.getenv("FR_BUILDING_PREPROCESS_INPUT"),
        {"figure_role": state["figure_role"].value, "raw_content": raw_content},
    )
    user_prompt = FR_BUILDING_PREPROCESS_INPUT
    if raw_images:
        user_prompt = [{"type": "text", "text": FR_BUILDING_PREPROCESS_INPUT}] + [
            {"type": "image_url", "image_url": {"url": url}} for url in raw_images
        ]

    messages = [
        SystemMessage(content=FR_BUILDING_PREPROCESS_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]
    response = await llm.ainvoke(messages)
    try:
        parsed_res = json.loads(response.content)
    except json.JSONDecodeError:
        logger.error("LLM response is not valid JSON")
        raise ValueError("LLM response is not valid JSON")

    # logger.info(json.dumps(parsed_res, ensure_ascii=False, indent=2))
    cleaned_content = parsed_res.get("cleaned_content", "")
    metadata = parsed_res.get("metadata", {})

    # 格式兜底
    if cleaned_content.strip() == "":
        warning = "cleaned_content is empty after preprocessing"
        logger.warning(warning)
        warnings = warnings + [warning]
    if not metadata.get("included_dimensions"):
        warning = "included_dimensions is empty, fallback to [other]"
        logger.warning(warning)
        warnings = warnings + [warning]
    if not metadata.get("approx_date"):
        warning = "approx_date is missing"
        logger.warning(warning)
        warnings = warnings + [warning]

    original_source_draft = {
        "content": cleaned_content,
        "type": parseEnum(OriginalSourceType, metadata.get("original_source_type")),
        "confidence": parseEnum(
            FineGrainedFeedConfidence, metadata.get("confidence", "")
        ),
        "included_dimensions": [
            parseEnum(FineGrainedFeedDimension, dim)
            for dim in metadata.get("included_dimensions", [])
        ]
        # 维度缺失时兜底，避免 addOriginalSource 参数校验失败
        or [FineGrainedFeedDimension.OTHER],
        "approx_date": metadata.get("approx_date"),
    }

    # 追加当前节点日志，用于后续返回给消费方
    logs += [
        {
            "step": "nodePreprocessInput",
            "status": "ok",
            "detail": "Input preprocessed and original source draft prepared",
            "data": {
                "type": original_source_draft["type"].value,
                "confidence": original_source_draft["confidence"].value,
                "included_dimensions": [
                    dim.value for dim in original_source_draft["included_dimensions"]
                ],
                "has_raw_images": len(raw_images) > 0,
                "raw_content_length": len(raw_content),
                "cleaned_content_length": len(cleaned_content),
            },
        }
    ]

    return {
        "original_source_draft": original_source_draft,
        "warnings": warnings,
        "logs": logs,
    }


def nodePersistOriginalSource(state: FRBuildingGraphState) -> dict:
    """
    original_source 落库
    """
    original_source_draft = state["original_source_draft"]
    res = addOriginalSource(
        user_id=state["request"]["user_id"],
        fr_id=state["request"]["fr_id"],
        **original_source_draft,
    )
    if res["status"] != 200:
        logger.error(res.get("message", "Add original source failed"))
        raise ValueError("Add original source failed")

    logs = state.get("logs") or []
    warnings = state.get("warnings") or []
    original_source_id = res.get("original_source_id")

    # 持久化完成后记录服务返回，方便排查链路问题
    logs += [
        {
            "step": "nodePersistOriginalSource",
            "status": "ok",
            "detail": "Original source persisted",
            "data": {
                "service_status": res.get("status"),
                "service_message": res.get("message"),
                "original_source_id": original_source_id,
            },
        }
    ]

    return {
        "original_source_id": original_source_id,
        "warnings": warnings,
        "logs": logs,
    }
