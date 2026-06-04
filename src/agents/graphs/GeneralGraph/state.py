from typing import Annotated, Any, Literal, TypedDict
from langgraph.graph.message import MessagesState


def _mergeUniqueList(left: list[Any], right: list[Any]) -> list[Any]:
    """
    合并并去重列表，兼容并行分支同时写同一 channel 的场景
    """
    merged = []
    for item in (left or []) + (right or []):
        if item in merged:
            continue
        merged.append(item)
    return merged


INTENT_ARGUMENTS_MAP = {
    "reject": [],
    "clarify": [],
    "conversation_graph": ["FigureAndRelation"],
    "fr_building_graph": ["FigureAndRelation", "narrative"],
    "auth_whoami": [],
    "fr_add": [
        "figure_name",
        "figure_gender",
        "figure_role",
        "figure_mbti",
        "figure_birthday",
        "figure_occupation",
        "figure_education",
        "figure_residence",
        "figure_hometown",
        "exact_relation",
    ],
    "fr_list": [],
    "fr_show": ["FigureAndRelation"],
    "fr_sync_feeds": ["FigureAndRelation"],
    "fr_feed_recall": ["FigureAndRelation", "query"],
    "fr_conflict_list": ["FigureAndRelation"],
    # "fr_conflict_resolve": [],    # todo: 后续加
    # todo: 加删除 FR 和 feed 支持
}


class Request(TypedDict, total=False):
    user_id: int
    original_text: str  # 原始用户输入


class Clarification(TypedDict, total=False):
    question: str
    content: str | None


class FigureAndRelation(TypedDict, total=False):
    id: int
    figure_name: str
    figure_gender: str
    figure_role: str


class GeneralGraphState(
    MessagesState
):  # 继承自MessagesState，自动包含messages: Annotated[list[AnyMessage], add_messages]字段
    round_uuid: str  # 本轮次唯一标识 uuid
    request: Request  # 用户首次输入

    intent: Literal[
        "reject",  # 拒绝
        "clarify",  # 需进一步澄清意图（仅意图不明确时触发）
        "conversation_graph",  # 进入对话
        "fr_building_graph",  # 完善 FR
        "auth_whoami",  # 查看个人信息
        "fr_add",  # 添加 FR
        "fr_list",  # 查看 FR 列表
        "fr_show",  # 查看 FR 详情
        "fr_sync_feeds_one",  # 同步单个 FR 细粒度信息
        "fr_feed_recall",  # 回忆 FR 内容
        "fr_conflict_list",  # 查看全部 pending 状态冲突
        # "fr_conflict_resolve",  # 解决 pending 状态冲突    # todo: 后续加
    ]
    coordinator_reason: str  # Coordinator reason 内容

    clarification: Clarification | None  # 澄清：问题-回答
    clarification_rounds: int = 0  # 澄清轮次
    is_clarification_complete: bool = False  # 是否澄清完成

    required_slots: list[str]  # 本 intent 必须字段槽位
    missing_slots: list[str]  # 当前缺失字段槽位

    figure_and_relation: FigureAndRelation | None

    execution_result: dict[str, Any] | None
    execution_reason: str | None  # 执行结果 reason 内容
    final_output: str | None
    warnings: Annotated[list[str], _mergeUniqueList]
    errors: Annotated[list[str], _mergeUniqueList]
    status: Literal["running", "failed", "completed", "human_in_the_loop"]


class GeneralGraphInput(TypedDict, total=False):
    request: Request
