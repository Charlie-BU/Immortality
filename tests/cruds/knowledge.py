import asyncio
from dotenv import load_dotenv

load_dotenv()

from src.services.knowledge import (
    addKnowledgePiece,
    deleteKnowledgePiece,
    getAllKnowledgePieces,
    getKnowledgePiece,
    recallKnowledgePieces,
)


async def testAddKnowledgePiece():
    res = await addKnowledgePiece(
        user_id=1,
        content="Test knowledge piece for recall and delete",
        weight=0.8,
    )
    return res


async def testRecallKnowledgePieces(query: str):
    res = await recallKnowledgePieces(
        user_id=1,
        query=query,
        top_k=5,
    )
    return res


def testDeleteKnowledgePiece(knowledge_id: int):
    res = deleteKnowledgePiece(
        user_id=1,
        knowledge_id=knowledge_id,
    )
    return res


def testGetKnowledgePiece(knowledge_id: int):
    res = getKnowledgePiece(
        user_id=1,
        knowledge_id=knowledge_id,
    )
    return res


def testGetAllKnowledgePieces():
    res = getAllKnowledgePieces(
        user_id=1,
    )
    return res



if __name__ == "__main__":
    print(testGetAllKnowledgePieces())
