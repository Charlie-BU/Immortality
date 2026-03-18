import time
import asyncio

from src.agent.graph.ContextGraph.graph import getContextGraph
from src.agent.graph.ContextGraph.state import initContextGraphState

async def main():
    state = initContextGraphState(
        {
            "user_id": 1,
            "relation_chain_id": 1,
            "type": "narrative",
            "narrative": "我和他一同去打乒乓球",
            "for_virtual_figure": False,
        }
    )
    context_graph = getContextGraph()
    result = await context_graph.ainvoke(state)
    print(result)

if __name__ == "__main__":
    start = time.perf_counter()
    asyncio.run(main())
    print(f"Time cost: {time.perf_counter() - start}")
