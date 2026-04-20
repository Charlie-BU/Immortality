import logging
import pprint
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

from src.agents.graphs.ConversationGraph.graph import getConversationGraph


messages_samples = [
    "最近压力有点大，事情很多，感觉每天都在救火。",
    "不过我还是想保持高效和积极，也希望沟通更直接一点。",
]


async def main():
    fr_id = 2
    graph = getConversationGraph()
    init_state = {
        "request": {
            "user_id": 1,
            "fr_id": fr_id,
            "messages_received": messages_samples,
        },
    }
    short_term_memory_config = {"configurable": {"thread_id": str(fr_id)}}
    result = await graph.ainvoke(init_state, config=short_term_memory_config)
    return result


if __name__ == "__main__":
    import asyncio
    import time

    start_time = time.perf_counter()
    result = asyncio.run(main())
    pprint.pprint(result, indent=2)
    print(f"Total time: {time.perf_counter() - start_time}s")
