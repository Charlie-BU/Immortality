import asyncio
import os
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

_checkpointer_instance: AsyncPostgresSaver | None = None
_checkpointer_lock = asyncio.Lock()
_checkpointer_ctx = None  # 用于存储 AsyncPostgresSaver 的异步上下文管理器


def _getPostgresConnString() -> str:
    conn_string = os.getenv("DATABASE_URI") or ""
    if conn_string.startswith("postgresql+psycopg://"):
        return conn_string.replace("postgresql+psycopg://", "postgresql://", 1)
    if conn_string.startswith("postgresql+psycopg2://"):
        return conn_string.replace("postgresql+psycopg2://", "postgresql://", 1)
    return conn_string


# 全局单例 checkpointer，并在首次创建时 setup() ，后续复用同一个连接池，避免被提前关闭
async def getCheckpointer() -> AsyncPostgresSaver:
    global _checkpointer_instance, _checkpointer_ctx
    if _checkpointer_instance is not None:
        return _checkpointer_instance
    async with _checkpointer_lock:
        if _checkpointer_instance is not None:
            return _checkpointer_instance
        _checkpointer_ctx = AsyncPostgresSaver.from_conn_string(
            _getPostgresConnString()
        )  # 返回的是异步上下文管理器
        checkpointer = (
            await _checkpointer_ctx.__aenter__()
        )  # 获取真正的 checkpointer 实例
        await checkpointer.setup()
        _checkpointer_instance = checkpointer
        return _checkpointer_instance
