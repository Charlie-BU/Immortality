import asyncio
import json
import time
from src.database.enums import FigureRole, Gender, MBTI
from src.services.figure_and_relation import (
    addFigureAndRelation,
    deleteFigureAndRelation,
    getAllFigureAndRelations,
    getFRAllContext,
    getFigureAndRelation,
    updateFigureAndRelation,
)


def testAddFigureAndRelation():
    res = addFigureAndRelation(
        user_id=1,
        figure_name="卜天（Charlie. BU）",
        figure_gender=Gender.MALE,
        figure_role=FigureRole.SELF,
        figure_mbti=MBTI.ENTJ,
    )
    return res


def testgetAllFigureAndRelations():
    res = getAllFigureAndRelations(
        user_id=1,
    )
    return res


def testGetFigureAndRelation(fr_id: int):
    res = getFigureAndRelation(
        user_id=1,
        fr_id=fr_id,
    )
    return res


def testUpdateFigureAndRelation(fr_id: int):
    res = updateFigureAndRelation(
        user_id=1,
        fr_id=fr_id,
        fr_body={
            "figure_appearance": "short hair, with glasses",
            "exact_relation": "Best friend from university",
            "figure_likes": ["music", "travel"],
            "core_personality": "Warm and creative",
            "core_interaction_style": "Open and expressive",
            "core_procedural_info": "Prefers planning weekly",
            "core_memory": "Shared graduation trip",
            "words_figure2user": ["You can do this"],
            "words_user2figure": ["Thanks for always supporting me"],
            "figure_dislikes": ["dishonesty"],
        },
    )
    return res


def testDeleteFigureAndRelation(fr_id: int):
    res = deleteFigureAndRelation(
        user_id=1,
        fr_id=fr_id,
    )
    return res


async def testGetFRAllContext(query: str | None = None):
    res = await getFRAllContext(user_id=1, fr_id=3, query=query)
    return res


if __name__ == "__main__":
    start = time.perf_counter()
    # print("testAddFigureAndRelation:", testAddFigureAndRelation())
    print("testGetFRAllContext:", json.dumps(asyncio.run(testGetFRAllContext("全部")), ensure_ascii=False, indent=2))
    # print(f"testGetFRAllContext cost: {time.perf_counter() - start:.4f} s")
