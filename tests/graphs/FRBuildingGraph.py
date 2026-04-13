import json
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

from src.agents.graphs.FRBuildingGraph.graph import getFRBuildingGraph


async def main():
    graph = getFRBuildingGraph()
    init_state = {
        "request": {
            "user_id": 1,
            "fr_id": 1,
            "raw_content": """
她叫林晚，是那种在人群里不会第一眼被记住的人。没有惊艳的美貌，也不刻意打扮，像一片落在城市缝隙里的叶子，安静，却顽强。
她每天坐同一班地铁，站在靠门的位置。耳机里常年循环着几首老歌，音量不大，像是给自己留一条退路。她习惯观察人——那个总是迟到、气喘吁吁的上班族，那对每天都在争吵又离不开彼此的情侣，还有那个总是穿着整洁西装、却眼神空洞的男人。
她不说话，但她记住了一切。
林晚曾经不是这样的。
大学时，她也热烈过。她会在深夜和朋友聊梦想，谈未来，觉得世界是可以被改变的。她学的是建筑设计，喜欢画线条，喜欢把一片空白变成有温度的空间。她曾经说过一句话：“房子不只是住人的，是装故事的。”
后来她进了公司，做的却是重复修改的图纸。客户要“更大气一点”，领导要“再保守一点”，她的线条被一点点磨平，像石头被水冲刷。她开始怀疑，那些所谓的“梦想”，是不是只是年轻时的错觉。
有一天，她在地铁上看见一个小女孩。女孩拿着一张歪歪扭扭的画，上面是一个奇怪的房子，屋顶是弯的，窗户像笑脸。她兴奋地对母亲说：“这是我以后要住的地方！”
林晚愣住了。
那一刻，她突然想起自己。
她曾经也画过那样的房子——不符合规范，不讲究结构，只是单纯地好看、温暖、有一点点不讲道理的浪漫。
那天晚上，她回到出租屋，没有开灯。她坐在地上，翻出尘封已久的画本。纸张已经微微发黄，但线条还在。那些曾经被她否定的、不成熟的、甚至有些幼稚的设计，在昏暗的光里重新呼吸。
她忽然笑了。
不是那种礼貌的、应付的笑，而是久违的，带点倔强的笑。
第二天，她照常去上班，依然改图，依然听领导意见。但不同的是，她在下班后开始画自己的东西。她不再给它们贴标签，不再问“有没有用”，也不急着让别人看。
她只是画。
慢慢地，她的生活没有发生翻天覆地的变化。她还是那个地铁里的普通女人，还是那个公司里不太起眼的设计师。但她心里，多了一块地方，是没人能动的。
像一间真正属于她自己的房子。
灯是她开的，窗是她画的，门也是她决定什么时候关上、什么时候敞开。
林晚没有改变世界。
但她把自己，从世界里一点点捡了回来。
            """,
            # "raw_images": [],
        },
    }
    result = await graph.ainvoke(init_state)
    return result


if __name__ == "__main__":
    import asyncio
    import time

    start_time = time.perf_counter()
    result = asyncio.run(main())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Total time: {time.perf_counter() - start_time}s")
