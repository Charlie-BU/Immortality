from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
import asyncio
import os
from threading import Lock
from typing import Any
from src.database.enums import (
    FigureRole,
    Gender,
    MBTI,
    FineGrainedFeedDimension,
    FineGrainedFeedConfidence,
    ConflictStatus,
)

_sync_checkpointer_instance: PostgresSaver | None = None
_sync_checkpointer_lock = Lock()
_sync_checkpointer_ctx: Any = None

_async_checkpointer_instance: AsyncPostgresSaver | None = None
_async_checkpointer_lock = asyncio.Lock()
_async_checkpointer_ctx: Any = None
_checkpoint_serde = JsonPlusSerializer(
    allowed_msgpack_modules=[
        FigureRole,
        Gender,
        MBTI,
        FineGrainedFeedDimension,
        FineGrainedFeedConfidence,
        ConflictStatus,
    ]
)


def _requireCheckpointerURI() -> str:
    uri = (os.getenv("CHECKPOINT_DATABASE_URI") or "").strip()
    if uri == "":
        raise RuntimeError("CHECKPOINT_DATABASE_URI is empty")
    return uri


def getCheckpointer() -> PostgresSaver:
    global _sync_checkpointer_instance, _sync_checkpointer_ctx
    if _sync_checkpointer_instance is not None:
        return _sync_checkpointer_instance
    with _sync_checkpointer_lock:
        if _sync_checkpointer_instance is not None:
            return _sync_checkpointer_instance
        _sync_checkpointer_ctx = PostgresSaver.from_conn_string(
            _requireCheckpointerURI()
        )
        checkpointer = _sync_checkpointer_ctx.__enter__()
        # checkpointer.setup()  # 仅首次需要 setup()
        _sync_checkpointer_instance = checkpointer
        return _sync_checkpointer_instance


# 全局单例 checkpointer，并在首次创建时 setup() ，后续复用同一个连接池，避免被提前关闭
async def agetCheckpointer() -> AsyncPostgresSaver:
    global _async_checkpointer_instance, _async_checkpointer_ctx
    if _async_checkpointer_instance is not None:
        return _async_checkpointer_instance
    async with _async_checkpointer_lock:
        if _async_checkpointer_instance is not None:
            return _async_checkpointer_instance
        _async_checkpointer_ctx = AsyncPostgresSaver.from_conn_string(
            _requireCheckpointerURI(),
            serde=_checkpoint_serde,
        )
        checkpointer = await _async_checkpointer_ctx.__aenter__()
        # await checkpointer.setup()  # 仅首次需要 setup()
        _async_checkpointer_instance = checkpointer
        return _async_checkpointer_instance


def closeCheckpointer() -> None:
    """
    关闭同步 checkpointer（可在应用退出时调用）
    """
    global _sync_checkpointer_instance, _sync_checkpointer_ctx
    with _sync_checkpointer_lock:
        if _sync_checkpointer_ctx is not None:
            _sync_checkpointer_ctx.__exit__(None, None, None)
        _sync_checkpointer_instance = None
        _sync_checkpointer_ctx = None


async def acloseCheckpointer() -> None:
    """
    关闭异步 checkpointer（可在应用退出时调用）
    """
    global _async_checkpointer_instance, _async_checkpointer_ctx
    async with _async_checkpointer_lock:
        if _async_checkpointer_ctx is not None:
            await _async_checkpointer_ctx.__aexit__(None, None, None)
        _async_checkpointer_instance = None
        _async_checkpointer_ctx = None
