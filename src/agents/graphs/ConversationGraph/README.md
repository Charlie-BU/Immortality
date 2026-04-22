# 第一版 ConversationGraph 性能分析

- 这条 `ConversationGraph` 的功能链路很短，但当前这一轮对话下的性能表现我会评为 `中等偏慢，且会随对话轮数明显恶化`。
- 真正的瓶颈不在图结构本身，而在 `每轮重复注入的大体积上下文`、`无裁剪的短期记忆`、以及 `额外远程 I/O`。
- 以你贴出的这一轮为例，输入已经是明显的 `万级 token` 量级候选，延迟和成本都会偏高，后续多轮对话会继续线性甚至接近超线性变差。

**主要问题**

- `提示词重复严重`：`figure_persona` 已经包含 `core_personality/core_interaction_style/core_procedural_info/core_memory`，但在 `nodeCallLLM` 里又把四类 recalled feeds 再完整拼进去一次，见 [nodes.py:L289-L304](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L289-L304) 和 [figure_and_relation.py:L521-L566](file:///Users/bytedance/Desktop/work/Immortality/src/services/figure_and_relation.py#L521-L566)。你给的样例里，“黄色网站”“基金回本”“PPT 很 AI”“调侃风格”等内容明显重复出现，属于最伤性能的一类冗余。
- `每轮都可能拉太多 recall`：四个维度默认都是 `top_k=20`，合计最多 80 条，见 [nodes.py:L123-L151](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L123-L151)。而 `_recalledFeeds2Markdown()` 基本是原样展开文本，见 [nodes.py:L23-L42](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L23-L42)。这会直接把召回结果膨胀成大段 system message。
- `短期记忆不做 trim/summarize`：代码里已经有 `todo`，但当前没有真正裁剪，见 [nodes.py:L232-L237](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L232-L237)。同时 `nodeCallLLM` 会把新的 `ai_message` 继续写回 `messages`，见 [nodes.py:L378-L404](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L378-L404)。这意味着轮数越多，历史越长，LLM 输入持续变大。
- `每轮远程取 prompt`：`getPrompt()` 每次都 `fetch` 远程 HTML，再解析 prompt，见 [prompt.py:L73-L80](file:///Users/bytedance/Desktop/work/Immortality/src/agents/prompt.py#L73-L80)。这是额外的网络 I/O，而且在高 QPS 或网络抖动时会直接放大尾延迟。
- `关键路径完全串行`：图是 `Load FR -> Recall -> Build Message -> Call LLM`，见 [graph.py:L24-L41](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/graph.py#L24-L41)。其中 FR 查询、recall、prompt fetch、LLM 调用都堆在同一条关键路径上，没有做前置并发。
- `日志本身也很重`：`logger.info(f"\nmessages_to_send:\n{messages_to_send}\n\n")` 会把整包 prompt 和历史消息直接打日志，见 [nodes.py:L314-L314](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L314-L314)。在你这种长上下文场景里，这会增加 CPU、I/O 和日志存储成本。

**这轮样例的具体评价**

- 这轮输入最贵的不是最后那句 `垃圾`，而是模型在处理它之前被塞进去的那一大坨背景：
    - 基础系统 prompt
    - 整个人物画像
    - 四类召回结果
    - 累积的历史 Human/AI message
- 从你贴出的实际内容看，`人物画像` 和 `召回记忆` 存在高重叠，信息增益很低，但 token 成本很高。
- 对“闲聊回复”这个任务来说，模型真正需要的上下文其实很少：最近几轮语气、对方人设摘要、1 到 3 条相关记忆，通常就够了。现在是典型的 `为一个很短的输出，支付了过大的输入成本`。
- 这类任务的输出只有一个 JSON，且通常 1 到 3 句短消息；所以当前系统的 `input/output token 比` 很不经济。

**性能分解**

- `图调度成本`：低。图只有 4 个节点，本身不是问题，见 [graph.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/graph.py)。
- `数据库/召回成本`：中到高。尤其是 recall 的结果体积大时，后续拼 prompt 的成本更高。
- `网络成本`：中。每轮 `getPrompt()` 都是一次额外远程请求。
- `LLM 推理成本`：高，而且是主瓶颈。不是因为输出难，而是因为输入太长。
- `长期可扩展性`：偏差。对话越长、FR 越丰富、feed 越多，延迟和成本都会继续上升。

**我会优先做的优化**

- `先砍重复`：`figure_persona` 只保留稳定摘要；四类 recall 改成“仅注入和当前 query 最相关的少量增量信息”。这是收益最大的优化点。
- `降低 top_k`：对闲聊场景，`personality/interactions` 可以保留少量，`procedural/memory` 更应该压低，先从 `3/3/2/2` 这种量级试。
- `做短期记忆裁剪`：保留最近 `N` 轮显式消息，再附一个 conversation summary；不要无上限累积 `messages`。
- `缓存系统 prompt`：`getPrompt()` 结果至少做进程内缓存，按 prompt key + variables 模板控制。
- `删大日志`：不要打印整包 `messages_to_send`，改成只打 token 估算、条数、字符数。
- `并发非依赖项`：FR 加载完成后，prompt fetch 和 recall 理论上可以并行准备，减少关键路径时长。

**综合评分**

- `单轮性能`: 6/10
- `多轮稳定性`: 4/10
- `成本效率`: 3/10
- `可优化空间`: 很大

**一句话判断**

- 现在这条图 `能跑、也能产出像样结果`，但对这种短回复闲聊任务来说，`上下文注入明显过重`，已经属于“效果可能不错，但性能和成本都不划算”的实现。

如果你愿意，我下一步可以直接基于这三个文件给你做一版 `性能优化方案 + diff 预览`，优先只动最值钱的两处：`recall 压缩` 和 `short-term memory trim`。

# 性能优化

## 去除重复注入

我基于现有 `ConversationGraph` 的拼装方式，先给你一个“只改注入策略、不改图结构”的去重方案，尽量把改动收敛在 `nodes.py` 和少量辅助函数里。**任务描述**

- 基于当前 `ConversationGraph` 架构，设计一套“先砍重复内容”的优化方案。
- 目标是 `最小改动`、`不重构图`、`优先减少 prompt 冗余`。

**任务结果**

- 可行，而且可以只通过调整 [nodes.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py) 的上下文组装逻辑实现。
- 核心思路不是“减少信息种类”，而是把当前的两份重叠上下文拆成 `稳定底座` 和 `本轮增量`。

**方案总览**

- 保留 `figure_persona`，但把它从“全量画像”收缩成“稳定画像摘要”。
- 保留 recall，但只注入 `figure_persona` 里没有表达过的“本轮增量信息”。
- 图结构不变，仍然是 `Load FR -> Recall -> Build Message -> Call LLM`，只调整节点产物的内容和 `nodeCallLLM()` 的拼装方式。

**为什么当前会重复**

- `figure_persona` 由 `buildFigurePersonaMarkdown()` 生成，里面已经包含：
    - `core_personality`
    - `core_interaction_style`
    - `core_procedural_info`
    - `core_memory`
      见 [figure_and_relation.py:L521-L566](file:///Users/bytedance/Desktop/work/Immortality/src/services/figure_and_relation.py#L521-L566)
- `nodeCallLLM()` 又把四类 recalled feeds 再完整拼成两段 system message：
    - `low_context_depended_feeds`
    - `high_context_depended_feeds`
      见 [nodes.py:L289-L304](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L289-L304)
- 所以现在属于：
    - `稳定信息` 在 persona 里出现一次
    - `相同主题的细节和例子` 又在 recall 里出现一次

**最小改动方案**

- 第一层：保留 `figure_persona`，但注入时改成“轻量版 persona”
- 第二层：保留 recall，但只传“增量 recall”
- 第三层：如果某一类 recall 和 persona 高度重复，则整类跳过

**具体设计**

- `Compact Persona` 只保留稳定、低频变化、跨轮都重要的信息：
    - 基本身份：姓名、角色、关系、职业、学校、常住地、家乡
    - 风格摘要：`core_personality`、`core_interaction_style`
    - 可选边界：`core_procedural_info` 里真正稳定的规则
- `Compact Persona` 不再直接放这些高重复字段：
    - `words_figure2user`
    - `words_user2figure`
    - `core_procedural_info`
    - `core_memory`
- 理由：
    - `words_figure2user` 已经大量出现在 system prompt 模板变量里，见 [nodes.py:L259-L266](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L259-L266)
    - `core_memory` 和 recall memory 高度重叠
    - likes/dislikes 对很多短聊轮次帮助不大，且 token 占比高

**增量 recall 的规则**

- 回忆不是全贴，而是按“是否补充 persona 中没有的内容”决定是否注入。
- 可先用一个非常朴素的规则，**不需要语义模型**，不引入额外依赖：
    - 如果某类 recall 为空，跳过
    - 如果某类 recall 的标题对应摘要字段在 persona 中已有，就只保留该类 recall 的前 `1~3` 条
    - 如果 recall 文本和 persona 文本出现明显重叠关键词，就只保留分数最高的 `1` 条
    - 如果完全没有新增价值，就整类不注入

**最小实现版本**

- 不做复杂文本去重，只做“按字段职责切分”
- 直接规定：
    - `figure_persona` 只负责“稳定画像”
    - recall 只负责“本轮相关例子”
- 这样已经能砍掉很大一部分重复

**字段切分**

- `figure_persona` 保留：
    - `figure_name`
    - `figure_role`
    - `figure_mbti`
    - `figure_occupation`
    - `figure_education`
    - `figure_residence`
    - `figure_hometown`
    - `figure_likes`
    - `figure_dislikes`
    - `exact_relation`
    - `core_personality`
    - `core_interaction_style`
- `figure_persona` 移除：
    - `words_figure2user`
    - `words_user2figure`
    - `core_memory`
    - `core_procedural_info`
- recall 保留：
    - `recalled_procedural_infos_from_db`
    - `recalled_memories_from_db`
    - `recalled_personalities_from_db` 和 `recalled_interaction_styles_from_db` 只保留少量高分条目，或直接先不注入

**推荐的注入结构**

- `SystemMessage 1`: 基础对话规则
- `SystemMessage 2`: 精简人物画像
- `SystemMessage 3`: 本轮相关补充信息，仅包含少量 recall
- `HumanMessage`: 本轮收到的消息

**可以直接删掉的重复点**

- `关系与人物画像` 中的 `core_memory`
- `关系与人物画像` 中的大段“常说的话”
- recall 中的 `personality` 和 `interaction_style` 全量展开
- 这几项删掉后，效果一般不会明显变差，但 token 会明显下降

**一版更具体的执行顺序**

- 第一步：在 `nodeCallLLM()` 内不再直接注入 `state['figure_persona']`
- 第二步：新增一个 conversation-specific 的 compact persona 构造函数
- 第三步：限制 recall 注入量，只保留每类前几条
- 第四步：观察回复质量是否下降
- 第五步：如果质量没掉，再考虑进一步从 recall 侧减 `top_k`

**我认为最适合你的最小版本**

- 只做这两件事：
    - `figure_persona` 改为精简版
    - recall 每类只注入前 `1~2` 条，先保留 `memory/procedural`，弱化 `personality/interaction`
- 这已经能解决当前 70% 以上的重复问题，而且代码改动很小。

**风险与注意点**

- 如果把 persona 砍得太狠，模型会更依赖 recall，可能导致“人设稳定性”下降。
- 如果把 `interaction_style` recall 全删掉，模型可能短期内更像“通用会聊天的人”，不像具体角色。
- 所以第一版不要一步到位，建议：
    - persona 保留摘要
    - interaction recall 留 1 条
    - memory recall 留 2 条

# FAQs

1. 每轮 message 中（指HumanMessage 和 AIMessage）除了 content 外，还有如下内容：
   additional_kwargs={}, response_metadata={}, id='ff407a75-7706-4b29-920b-fce587dc50da'
   这些内容的存在会占用token吗？会影响模型输入体积吗？

**结论**

- 在你这个项目当前的实现里，`additional_kwargs`、`response_metadata`、`id` **不会进入模型输入 token**。
- 真正发给 Ark/模型的，只有 `role` 和 `content`，见 [adapter.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/adapter.py#L233-L240)。
- 所以从“模型看到的上下文体积”角度，这些字段 **不计入 token**。

**依据**

- `nodeCallLLM()` 调用的是 `arkAinvoke(messages=messages_to_send)`，见 [nodes.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L326-L333)。
- `arkAinvoke()` 在真正请求前，会把 LangChain message 转成 Ark/OpenAI chat message，见 [llm.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/llm.py#L92-L97)。
- 转换函数 `langchain2OpenAIChatMessages()` 明确只取：
    - `role`
    - `content`
      见 [adapter.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/adapter.py#L233-L240)

也就是说，像下面这些：

```python
additional_kwargs={}
response_metadata={}
id="xxx"
```

是 `LangChain/BaseMessage` 对象在 Python 侧的元数据，不是最终发给模型的 prompt 内容。

**但有两个“会影响体积”的例外**

- `日志体积`：你现在有一行
  [nodes.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L324-L324)
  会直接打印 `messages_to_send`。这里打印出来的对象字符串里，通常会带上 `additional_kwargs`、`response_metadata`、`id`。这 **不影响模型 token**，但会增加日志 I/O 和日志存储。
- `checkpoint / 内存存储体积`：你把 `AIMessage` 原对象放回了 `messages`，见 [nodes.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L388-L414)。这些元数据会跟着消息对象一起被短期记忆/checkpointer 保存，所以会影响：
    - Python 内存占用
    - checkpoint 持久化体积
    - 序列化/反序列化成本
      但仍然 **不直接增加模型输入 token**。

**对你当前优化的实际含义**

- 你做短期记忆 trim 时，最该关注的还是 `message.content` 的长度。
- `id`、`response_metadata` 不是 token 问题，但如果你追求极致性能，也可以考虑在写回短期记忆前，把 AIMessage 压成更轻的形式，只保留必要字段。
- 不过这一步不属于第一阶段必须做的事，优先级低于：
    - 裁剪 `messages` 数量
    - 控制 `content` 总长度
    - 删除大段重复 system context

**一句话**

- 对模型 token：`不会占`
- 对程序内存/日志/checkpoint：`会有一点影响`
