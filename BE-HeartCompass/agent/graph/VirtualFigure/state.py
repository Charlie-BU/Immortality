from typing import List, TypedDict, Annotated
from langgraph.graph import add_messages


from database.models import (
    User,
    Crush,
    RelationChain,
    ChainStageHistory,
    Knowledge,
    Event,
    ChatTopic,
    InteractionSignal,
    DerivedInsight,
)


class Request(TypedDict):
    user_id: int
    relation_chain_id: int
    messages: List[str]  # 本轮收到的消息


class Memory(TypedDict):
    short_term_memory: Annotated[list, add_messages]    # 最近的消息
    long_term_hits: dict


class ContextBlock(TypedDict):
    context_block: str  # Context


class LLMOutput(TypedDict):
    messages_to_send: List[str]  # 本轮要发送的消息


class VirtualFigureGraphState(TypedDict):
    pass
