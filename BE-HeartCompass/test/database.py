def addUser():
    with session() as db:
        new_user = User(
            username="Test",
            email="test@example.com",
            password="12345",
            mbti="INTP",
            gender="MALE",
        )
        db.add(new_user)
        db.commit()


async def addMBTIKnowledgeToKnowledgeBase():
    json_path = os.path.join(os.path.dirname(__file__), "..", "mbti.json")

    print(f"Reading MBTI data from {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        mbti_list = json.load(f)
    print(f"Loaded {len(mbti_list)} MBTI items")
    print(f"mbti_list: {mbti_list}")

    # with session() as db:
    #     for item in mbti_list:
    #         mbti_type = item.get("mbti", "Unknown")
    #         print(f"Processing {mbti_type}...")

    #         # Convert dictionary to JSON string
    #         content = json.dumps(item, ensure_ascii=False)

    #         # Add to knowledge base
    #         try:
    #             result = await contextAddKnowledge(
    #                 db=db, content=content, with_embedding=True
    #             )
    #             print(f"Result for {mbti_type}: {result}")
    #         except Exception as e:
    #             print(f"Failed to add {mbti_type}: {e}")


if __name__ == "__main__":
    import asyncio
    import json
    import dotenv
    import os
    from src.database.database import session
    from src.database.models import User

    dotenv.load_dotenv()
    asyncio.run(addMBTIKnowledgeToKnowledgeBase())
