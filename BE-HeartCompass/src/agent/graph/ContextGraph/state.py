from typing import List, TypedDict, Literal

from src.database.models import (
    Knowledge,
    Event,
    ChatTopic,
    InteractionSignal,
    DerivedInsight,
)


class Request(TypedDict):
    user_id: int
    relation_chain_id: int
    for_virtual_figure: bool
    type: Literal["conversation", "narrative", "no_material"]
    # 情况1: conversation - 聊天记录分析
    conversation_screenshots: List[str] | None
    crush_name: str | None  # 对方在截图中出现的姓名或位置（左侧/右侧）
    additional_context: str | None
    # 情况2: narrative - 自然语言叙述分析
    narrative: str | None
    # 情况3: no_material - 无聊天记录、无自然语言叙述


class BasicContext(TypedDict):
    his_mbti: str | None  # 对方的MBTI
    his_profile: dict  # 汇总、去噪、裁剪后的对方的“可读画像摘要”
    current_stage: str | None  # 当前关系


class RecallItems(TypedDict):
    events: List[Event]
    chat_topics: List[ChatTopic]
    derived_insights: List[DerivedInsight]


class ContextGraphState(TypedDict):
    request: Request
    basic_context: BasicContext
    recall_query: str | None
    recalled_items: RecallItems | None
    mbti_knowledges: List[Knowledge] | None
    interaction_signals: List[InteractionSignal] | None
    context_block: str | None  # 组织后的关系与画像上下文
    relevant_knowledge: str | None  # 组织后的相关知识


class ContextGraphInput(TypedDict):
    request: Request


class ContextGraphOutput(TypedDict):
    context_block: str | None
    relevant_knowledge: str | None


def initContextGraphState(request: Request) -> ContextGraphInput:
    return {
        "request": request,
    }
