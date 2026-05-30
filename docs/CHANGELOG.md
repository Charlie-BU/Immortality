## CHANGELOG - 2026-05-30 12:04 - feed 抽取补齐时间锚点约束，减少跨时间语境误召回

### 撰写时间

- 2026-05-30 12:04

### Base Commit

- 5781f8fdaee2612d5f3eaa22535b9e1d9ee543d5

### Compare Scope

- working_tree_only

### 背景与改动目标

- 这轮工作区改动很聚焦，目标不是扩 feed 结构，而是减少召回阶段的时间混淆。当前这组 `prompts/recipes` 已经会按角色和维度抽取 feed，但如果同类事件发生在不同时间点，而抽取结果里没有把时间写进 `content`，后续向量召回就容易把几段其实属于不同阶段的记忆或互动混在一起。
- 一开始最容易想到的修法，是只在 `memory` 维度里强调“保留时间线索”。但顺着 prompt 组合方式继续看，会发现运行时并不是只消费 `memory`：角色约束和维度分支是组合生效的，时间信息也不只存在于记忆叙事里，互动、人格、程序性经验里同样可能带有明确时期。因此这次没有做单点补丁，而是把“明确时间必须进入 `content`”提升成统一输出约束，再在 `memory` 维度额外加一道更强的时间锚点要求。

### 改动概览

- `prompts/recipes/by_role/colleague.md`、`family.md`、`friend.md`、`mentor.md`、`partner.md`、`public-figure.md`、`self.md`：在统一输出要求里新增两条规则。第一条要求只要原始材料明确出现时间，或可结合上下文稳定推断出明确时间/时期/阶段，就必须把时间锚点写入 `content`；第二条明确在时间无法确定时不补写、不臆造，只保留可证实的时序线索。
- `prompts/recipes/by_dimension/memory.md`：在“语境粒度要求”中补了一条更具体的约束，直接强调要避免把不同时间点的相似事件抽成无时间区分的表述。换句话说，`memory` 维度现在不只是“保留时间线索”，而是要求把可确认的时间锚点显式落到输出内容里。

### 关键链路解析（含上下游）

- 上游依赖：这次改动建立在当前 feed 抽取 prompt 的组合方式之上，也就是“角色约束 + 维度分支”共同生效。角色文件决定通用输出边界，维度文件决定各自抽取重点。因此如果只改某一个维度，很多实际抽取路径仍然可能漏掉时间要求。
- 当前改动：角色层新增统一约束，等于给所有 feed 输出都补上“有明确时间就必须带时间锚点”的底线；`memory.md` 再补一层更强说明，专门约束事件叙事不要丢掉时间区分。这样做的好处是规则覆盖面更完整，代价是 prompt 更长了一点，但当前只增加了 16 行文本，复杂度仍然可控。
- 下游影响：下游召回在拿到 `content` 做语义匹配时，更容易区分“同一关系里不同年份/阶段发生的相似事件”。这不会改变 JSON 结构，也不会要求消费方改字段协议；变化点完全落在抽取内容本身，属于低侵入的语义收口。

### 改动结果与业务影响

- 当前看，这轮收益主要在召回准确性上。只要上游材料给出了明确时间，feed 本身就会带着这层时间锚点进入向量空间，后续把不同时间点的相似经历一起召回的概率会下降。
- 这次做法也保留了一个清晰边界：只有“明确存在”或“可稳定推断”的时间才写入 `content`。这意味着系统不会为了区分度去捏造时间，能够避免另一类错误，即把模糊时序硬写成确定事实。
- 从工程角度看，这次改动没有扩字段、没有动解析协议、没有引入新的组合逻辑，只是在 prompt 层补规则，因此实现成本和回滚成本都比较低。

### 风险与待办

- 当前仍有一个边界：这次只补了规则，没有同时加入 few-shot 示例。如果模型对“明确时间”和“模糊时序线索”的区分不够稳定，实际抽取时仍可能出现漏写时间锚点的情况。
- 未验证项：当前没有针对这组 prompt 补自动化或半自动回归样例，尚未直接验证“同类事件在不同时间点的输入”能否稳定产出带时间区分的 feed。
- 后续动作：如果后面继续优化抽取稳定性，值得补两类最小示例，一类覆盖“文本中有明确年月/阶段表达”的正例，另一类覆盖“只有模糊先后关系、不能稳定定时”的反例。

### 建议 Commit Message（git-cz）

- `refactor(prompt): require explicit time anchors in extracted feeds`

## CHANGELOG - 2026-05-29 23:48 - 对话链路补齐时间语义并收口序列化时区表达

### 撰写时间

- 2026-05-29 23:48

### Base Commit

- e4fde31f422ce3f8129197e93030a03363dbdd3f

### Compare Scope

- working_tree_only

### 背景与改动目标

- 这轮工作区改动的起点是几个分散但本质相同的问题：项目里已经开始显式使用 UTC 时间，但不同链路对“时间到底是给机器算、给协议传，还是给人看”的边界还不够统一。最直观的几个表现是：`ConversationGraph` 一边给 system prompt 注入一份“当前时间”，一边消息本身又没有可靠时间语义；CLI 日志文件按本地自然日落盘，但 `logs` 默认日期的口径并不完全跟它对齐；数据库模型和通用序列化层在遇到 naive `datetime` 时，也还可能把不带 offset 的字符串直接往外透。
- 一开始最容易想到的修法，是只把 `datetime.now()` 改成 `datetime.now(timezone.utc)`。但顺着链路继续看，会发现这个问题不是“全部改 UTC”这么简单。展示型时间应该更接近本地自然日，防抖窗口更适合单调时钟，模型感知消息时间则应该跟随每条消息本身，而不是依赖 prompt 顶部一行全局时钟。因此这轮最终不是单点替换，而是按场景把时间语义重新收口。

### 改动概览

- `src/agents/graphs/ConversationGraph/nodes.py`：新增 `_buildMessageContent()`，在写入 `HumanMessage` 和本轮 `AIMessage` 时统一附加 UTC ISO8601 时间戳；`nodeCallLLM()` 不再给 `CONVERSATION_SYSTEM_PROMPT` 注入 `current_timestamp`。
- `prompts/CONVERSATION_SYSTEM_PROMPT.md`：删除 `Current time: {{current_timestamp}}`，让 prompt 本体不再承担“替消息补时间”的职责。
- `docs/TODOs.md`：把“发消息带时间戳，否则 AI 不理解什么时候的消息”标记为已完成，同时调整 TODO 排序，让这次时间语义治理在任务面板上和代码现状对齐。
- `src/cli/commands/index.py` 与 `src/main.py`：日志文件名本来就按本地日期生成，这次把 `logsCLI()` 的默认日期改成 `datetime.now().astimezone().strftime("%Y%m%d")`，让“查看当天日志”和“当天日志写到哪个文件”回到同一口径。
- `src/channels/lark/integration/index.py`：`filterDuplicatedMessage()` 从 `time.time()` 切到 `time.monotonic()`，把“30 秒内去重”从真实世界时间改成纯相对时长判断。
- `src/database/models.py` 与 `src/utils/index.py`：模型时间列统一声明为 `DateTime(timezone=True)`；`SerializableMixin.toJson()`、`jsonDefault()`、`toSerializableValue()` 统一收口到 `serializeDatetime()`，遇到 naive `datetime` 时先按 UTC 兜底，再输出带 offset 的 ISO8601 字符串。
- `src/agents/viking.py`：示例数据里的会话元数据时间戳改成 UTC 毫秒时间戳，避免本地时区和 Unix 时间混用。

### 关键链路解析（含上下游）

- 上游依赖：`ConversationGraph` 的时间语义一头连着 `CONVERSATION_SYSTEM_PROMPT`，一头连着 `nodeBuildAndTrimMessage()` / `nodeCallLLM()` 的消息拼装方式。之前 prompt 里那一行 `Current time` 更像全局旁白，模型未必能准确知道“哪条消息发生在什么时候”。这次把时间戳下沉到消息内容本身后，上游 prompt 模板反而被简化了。
- 当前改动：`nodeBuildAndTrimMessage()` 现在把用户输入包装成 `[timestamp=...]` 开头的文本再写入 `HumanMessage`；本轮模型回复在落回 state 时也走同一套包装。换句话说，时间语义不再由单独模板变量提供，而是成为消息载体的一部分。这样做的代价是上下文里会多一行时间标记，但好处是 summary、trim、后续多轮滚动都能保留这层信息。
- 下游影响：`ConversationGraph` 下游消费到的是带时间标签的真实消息，不需要额外依赖 prompt 里的“当前时刻”；`docs/TODOs.md` 与 prompt 模板同步收口后，后续再看这条需求时不会出现“代码已做、任务仍未完成”或“prompt 里还有旧口径”的漂移。CLI 侧的下游影响则更直接，`immortality logs` 默认读取的文件终于和 `src/main.py` 落盘的“今天日志”一致。
- 数据与协议链路这边，上游依赖是 SQLAlchemy 模型和所有复用 `toJson()` / `toSerializableValue()` 的调用方。当前改动把“时间列应声明带时区”和“序列化输出不该丢 offset”这两件事拆开处理：前者落在 ORM 定义，后者落在统一序列化入口。下游无论是 HTTP 透传、日志打印还是 service 返回结构，只要走到这两个入口，输出的时间字符串都会更明确。

### 改动结果与业务影响

- 当前看，这轮最大的收益不是“项目全面切到 UTC”，而是不同场景终于开始用更合适的时间表示。消息理解走 UTC 时间戳，本地日志查看走本地自然日，短时间防抖走单调时钟，数据库与 JSON 输出则尽量保证时区信息不丢。
- 对 `ConversationGraph` 来说，这次改动把“时间”从 prompt 外挂信息改成消息上下文的一部分，更接近模型真正能消费和记住的输入形态。对 CLI 和 Lark 集成来说，收益则偏稳定性和语义一致性：日志查看少踩跨午夜/跨时区边界，去重逻辑也不再受系统时钟回拨影响。
- 这轮还有一个工程层收益：`serializeDatetime()` 成为统一出口后，后续如果团队决定把“naive datetime 视为 UTC”升级成告警或直接报错，不需要再全局追着 `isoformat()` 改，可以在一个点上收紧策略。

### 风险与待办

- 当前仍有一个显式边界：序列化层的兜底策略是“naive datetime 按 UTC 理解”。这能避免继续输出不带 offset 的时间字符串，但它本质上还是补救，不是从源头消除歧义。如果后续发现某些 naive 时间其实代表本地时间，这条兜底策略还需要进一步收紧。
- 已知边界：`src/database/models.py` 这次改的是 ORM 时间列定义，数据库层的真实列类型和迁移动作需要和这套定义保持一致；否则新老环境对 `timezone=True` 的感知仍然可能出现偏差。
- 未验证项：这轮没有补自动化回归去覆盖“带时间戳消息进入 Graph 后的效果”“CLI 在本地午夜边界查看日志”“序列化出口对 naive / aware datetime 的输出差异”这几类路径。当前收益主要来自代码语义收口，验证深度仍然有限。
- 另一个保留边界是 `models.py` 里的默认时间生成时机问题。本轮记录聚焦时间语义和序列化收口，这块仍保持现状，后续如果要继续做时间正确性治理，值得单独拆一轮处理。

### 建议 Commit Message（git-cz）

- `refactor(time): align timezone semantics across graph cli and serialization`

## CHANGELOG - 2026-05-21 15:18 - easy mode 入口隐藏并收口 shared mode 对外结论

### 撰写时间

- 2026-05-21 15:18

### Base Commit

- ac02f3470b8ba2c4f3a962ae96612d9e6f992b54

### Compare Scope

- working_tree_only

### 背景与改动目标

- 这次工作区改动没有继续扩 shared database 能力本身，而是在收口“现在到底该不该把它当成正式用户能力暴露出去”这个边界。前几轮已经把 `USE_SHARED_DATABASE`、`dispatchServiceCall()`、shared mode 下的 `doctor`、Graph/service 分流、Lark 启动分支都补到了可运行状态，文档里关于 bottleneck 的叙述却还停留在“方案被卡死”与“长期尝试中间态”。
- 一开始 `setupCLI()` 仍然保留了 `Easy setup (Use cloud database with encrypted data)` 这个选项，代码里也还会在选中后写入 `USE_SHARED_DATABASE=True` 和占位数据库连接串。但如果顺着 `docs/BOTTLENECK.md` 里的最新结论继续看，会发现当前真正的判断已经变成了另一件事：数据库接入问题基本被拆掉了，可对外开放的阻塞点转移到了模型配置归属、服务端代执行边界和产品化承诺。因此这轮没有再补新能力，而是先把 CLI 入口和文档结论对齐。

### 改动概览

- `src/cli/commands/index.py`：把 `setupCLI()` 里 `questionary.select()` 的 `easy` 选项注释掉，并在旁边补了一句“暂不启用，详见 `docs/BOTTLENECK.md`”。`use_shared_database = database_config_mode == "easy"`、占位连接串写入、`USE_SHARED_DATABASE` 回填和“shared mode 下跳过 `initDatabaseIfNeeded()`”这些底层分支没有被删，说明能力骨架仍然保留，只是先从公开交互入口撤下。
- `docs/BOTTLENECK.md`：新增“单一飞书 Bot 问题”作为独立议题，同时把 shared database 这一节从“仍被 checkpointer 卡死”改写成更接近当前实现状态的复盘。文档现在明确记录了六部分已落地能力，包括 router/dispatcher、Graph 在 shared mode 下退化为 `InMemorySaver`、`lark-service start` 跳过本地数据库初始化，以及当前为什么仍然不开放给用户。

### 关键链路解析（含上下游）

- 上游依赖：这轮判断建立在前几轮 shared mode 相关实现已经存在的前提上。`runDoctorCheck()` 已经会根据 `USE_SHARED_DATABASE` 分流到 `HTTP_BASE_URL/ping`；`setupCLI()` 仍保留 easy mode 对应的 `.env` 写入逻辑；`ConversationGraph`、dispatcher、Lark 启动链路也都已经按模式切分。本次改动没有新建这些能力，而是重新定义它们在产品入口层的暴露方式。
- 当前改动：CLI 层把 easy mode 从 `questionary` 选择列表里撤掉，意味着普通用户通过标准 `immortality setup` 流程不再能直接进入 shared database 模式。文档层则把“卡点是什么”说得更准确了：checkpointer 问题已经通过 shared mode 下退化到 `InMemorySaver` 被绕开，真正剩下的是服务端模型依赖 `EMBEDDING_MODEL`、`syncFeedsToFRCore` / `syncAllFeedsToFRCore` 需要消费用户侧模型配置这类边界问题。
- 下游影响：对 CLI 用户来说，`setup` 的公开可选项重新收敛到 `docker` 和 `manual` 两条路径，避免把一个内部已跑通但尚未产品化收尾的模式过早暴露出去。对维护者来说，`docs/BOTTLENECK.md` 终于和代码现状对齐，后续讨论 shared mode 时不会再同时混用“数据库仍是最终瓶颈”和“数据库问题已基本解决”这两套相互打架的表述。

### 改动结果与业务影响

- 当前看，这轮的收益主要是“能力状态表述”更一致了。shared mode 并没有被回滚，底层开关、分发层和大部分运行链路都还在；变化在于入口被主动降级成内部能力，避免用户在 `setup` 阶段看到 easy mode 后误以为这是已经准备好对外承诺的正式方案。
- 这份文档收口也把项目当前判断说清楚了：数据库问题本身已经不是最主要阻塞点，真正没有收口的是模型配置与服务端代执行的归属。这样后续如果继续推进 shared mode，重点就不会再错误地放回数据库接入，而会转向模型能力的配置透传和职责边界设计。

### 风险与待办

- 已知边界：`setupCLI()` 只是隐藏了 `easy` 选项，并没有移除底层逻辑。也就是说，shared mode 仍然是存在于代码中的一套能力，只是暂时不走公开交互入口；后续如果文档和实现再次偏移，维护者仍然可能对“是否支持”产生误读。
- 已知边界：`docs/BOTTLENECK.md` 现在明确把阻塞点收敛到了模型配置和服务端执行边界，但这些问题本身还没有解决，尤其是服务端 `EMBEDDING_MODEL` 依赖和 feed sync 相关模型调用的配置归属，当前仍然没有正式方案。
- 未验证项：这轮没有新增自动化验证去证明“隐藏 easy mode 后，setup 交互仍只保留两种合法路径”或“内部保留的 shared mode 分支仍然可用”。它更像一次入口治理和文档校准，而不是运行逻辑回归。
- 后续动作：如果后面要重新开放 easy mode，建议先把模型配置透传和服务端代执行边界做成显式设计，再决定是否恢复 `questionary` 入口；否则就继续把 shared mode 当作内部实验能力维护，并补一份更正式的 enable 条件清单。

### 建议 Commit Message（git-cz）

- `docs(shared-mode): hide easy setup and align bottleneck status`

## CHANGELOG - 2026-05-19 14:49 - shared mode 补齐 GET 参数过滤与 Lark 启动边界

### 撰写时间

- 2026-05-19 14:49

### Base Commit

- f680877971c09d52f0bc9ee66f9d0c15b7825398

### Compare Scope

- working_tree_only

### 背景与改动目标

- 这次工作区改动的起点是两个 shared mode 相关的运行时问题。第一个问题出现在 `immortality fr show --id 1`：命令没有显式传 `--query`，但 CLI 还是把 `query=None` 透传给了远端 `GET` 请求，最终在 `aiohttp` 的 `params` 编码阶段报出 `Invalid variable type`。第二个问题出现在 `immortality lark-service start`：`doctor` 已经能在 shared mode 下只检查远端 `/ping`，但真正启动时仍然无条件执行本地 `initDatabaseIfNeeded()`，于是 easy 模式写入的占位数据库地址 `shared-mode.invalid` 反过来把启动流程打断了。
- 一开始我先在命令侧做了局部兜底，但顺着调用链继续看，会发现这两个问题都不是单点 bug。前者本质上是 dispatcher 没有替 `GET` 请求兜住 `None` 参数，后者本质上是 Lark 启动链路没有尊重 `USE_SHARED_DATABASE` 的模式边界。因此这轮没有继续堆入口特判，而是把修复收口到更通用的分发层和启动层。

### 改动概览

- `src/service_dispatcher.py`：在 `_requestHTTPByConfig()` 的 `GET` 分支里新增 `query_args` 过滤，只移除值为 `None` 的 query 参数，再交给 `afetch()` 发起请求。`POST` 的 `json_data` 透传逻辑保持不变，避免误伤显式 `null` 语义。
- `src/channels/lark/websocket.py`：`startLarkService()` 现在会先读取 `isSharedDatabaseMode()`，只有在本地数据库模式下才执行 `initDatabaseIfNeeded()`；shared mode 直接进入 `startLarkWebSocketServer()`。

### 关键链路解析（含上下游）

- 上游依赖：`src/cli/commands/fr.py`、Lark integration 菜单命令和其他 CLI / channel 入口都会通过 `dispatchServiceCall()` 进入 `_requestHTTPByConfig()`。这意味着只要是远端 `GET` 请求，就共享同一套 query 参数编码路径。另一条上游是 `setup` 与 `doctor`：`src/cli/commands/index.py` 在 easy 模式下会把数据库 host 写成 `shared-mode.invalid`，同时让 `doctor` 在 shared mode 下改查 `HTTP_BASE_URL/ping`。
- 当前改动：dispatcher 现在在真正构造 `query_params` 前过滤 `None`，把“调用方允许缺省参数”和“HTTP query 不能出现 `None`”这两个语义边界隔开。Lark 启动侧则把 shared mode 当成一等公民处理，不再在启动 WebSocket 服务之前顺手做本地数据库初始化。
- 下游影响：`fr show`、Lark 菜单里的 `showFRLark()` 等所有通过 dispatcher 发起 `GET` 请求、且可能带可选参数的调用都能直接复用这次修复，不需要每个调用点再各自判断 `None`。`lark-service start` 在 shared mode 下也终于和 `doctor` 的检查语义对齐，不会再因为 easy 模式占位连接串而在启动阶段提前失败。

### 改动结果与业务影响

- 当前看，这轮主要解决的是 shared mode 下“入口看似已经切到远端，但运行时仍残留本地语义”的问题。`GET` 请求参数现在更接近 HTTP 客户端的真实约束，Lark 服务启动也更符合 easy 模式“依赖远端服务而不是本地数据库”的预期。
- 这两处改动的收益都比较直接。前者让可选 query 参数回到“省略即可”的语义，后者让 Lark Bot 在 shared mode 下至少不会被本地数据库占位地址拦住。代价也比较可控：`GET` 只过滤 `None`，不会动到空字符串、`0`、`False` 这类仍可能有业务意义的值；Lark 启动也只是跳过本地 schema 初始化，没有改动消息处理主链路。

### 风险与待办

- 已验证项：`uv run immortality fr show --id 1` 已经可以正常返回画像内容，不再出现 `Invalid variable type`。`uv run immortality lark-service start` 也已经越过了 `shared-mode.invalid` 的数据库报错，说明启动链路里的本地初始化问题被绕开了。
- 当前暴露出的新边界是日志权限：Lark 服务继续启动时，失败点转移到了 `src/main.py` 里的 `logging.FileHandler`，报错为 `Operation not permitted: '/Users/bytedance/.immortality/logs/app-20260519.log'`。这说明数据库问题已经不再是首个阻塞点，但日志写入仍有环境兼容性风险。
- 未验证项：这轮没有补自动化回归，尤其是“shared mode 下远端 `GET` 统一过滤 `None`”和“Lark 服务在不同模式下启动分支”这两类行为，目前主要依赖手工验证。
- 后续动作：先决定是否给 `preconfig()` 加日志文件不可写时的 fallback，再补一组最小回归验证，覆盖 shared mode 下 `dispatchServiceCall()` 的 `GET` 参数过滤和 `startLarkService()` 的模式分支。

### 建议 Commit Message（git-cz）

- `fix(shared-mode): align get dispatch and lark startup`

## CHANGELOG - 2026-05-18 15:43 - 收紧文档写作约束并修正 CLI 的 Robyn 导入副作用

### 撰写时间

- 2026-05-18 15:43

### Base Commit

- f502a338922d152a9cbba074b110815d33e42459

### Compare Scope

- working_tree_only

### 背景与改动目标

- 这次工作区改动有两条线，但它们都在处理“入口不要带副作用”这件事。一条是文档侧：`doc-generator` 和 `doc-optimizer` 之前更强调结构化，当前补上的约束开始明确要求少空话、少模板腔、少机械收束，让产出的文档更接近真实工程复盘。另一条是 CLI 侧：`immortality auth -h` 会在真正进入命令树之前被 `robyn` 抢走参数解析，根因是 `src/services/user.py` 顶层导入了只用于类型标注的 `Request`。
- 一开始最直接的修法只是把报错压下去，但顺着链路看，问题本质不是某个 help 命令异常，而是“被 CLI 预加载的模块不该顺手把 Web 框架带进来”。因此这轮改动除了修类型导入，还顺手把这次经验写成 `docs/DEV_CASES.md`，并清掉一份已经不再保留的总览文档。

### 改动概览

- `.trae/skills/doc-generator/SKILL.md`：新增“表达约束”与禁止事项，明确要求少套固定模板、少同义反复、少 AI 腔，同时把部分 YAML 引号和列表缩进统一为更稳定的写法。
- `.trae/skills/doc-optimizer/SKILL.md`：补充“能收短就收短”“只删冗余、不重复原意”等约束，继续强调不要把原文压成更整齐但更空的总结稿。
- `src/services/user.py` 与 `src/server/auth.py`：都切到 `from __future__ import annotations` + `TYPE_CHECKING`，把 `Request` 从运行时导入改成仅类型检查时导入，避免 CLI 预加载 `robyn`。
- `docs/DEV_CASES.md`：新增一条开发案例，直接记录这次 `robyn` 导入副作用的触发路径、修法和最小经验。
- `docs/BRIEF_INTRO.md`：整份删除，当前工作区没有看到对应的替代链接收口动作。

### 关键链路解析（含上下游）

- 上游依赖：`src/cli/commands/auth.py` 在注册子命令阶段就会导入 `src.services.user`，而 `src.services.user` 又会被 `src.service_dispatcher`、`src.cli.utils`、server 鉴权等多条链路复用。这意味着它一旦在模块顶层带入 `robyn`，CLI 和 Server 两侧都会被影响。
- 当前改动：`Request` 现在只存在于注解语义里，不再参与运行时导入。实测 `uv run immortality auth -h` 已经回到项目自己的帮助输出，说明“CLI 帮助被 Robyn 抢参”这条链路被修正了。文档 skill 侧则通过增加显式表达约束，把“结构化”从模板化写作里剥离出来。
- 下游影响：所有会被 CLI 预加载的用户相关命令都会共享这次导入修复收益；`docs/DEV_CASES.md` 也把这个坑沉淀成了后续可复用的排查经验。另一方面，`docs/BRIEF_INTRO.md` 被删之后，仓库里至少还有 `.trae/deepwiki/项目概览.md` 保留着指向它的链接，如果不继续收口，文档导航会留下死链。

### 改动结果与业务影响

- 当前看，CLI 侧的实际收益是明确的：帮助命令恢复正常，`src/services/user.py` 这类会被 CLI 和 Server 共用的模块也更接近“无副作用模块”的目标。
- 文档侧的收益更偏长期治理。`doc-generator` 和 `doc-optimizer` 现在把“不要为了完整而写空话”写成了显式规则，后续产出的 `docs/` 文档在语气和密度上会更可控。
- 这轮改动也带来了一个边界：`docs/BRIEF_INTRO.md` 被删掉后，仓库里原来依赖它做导航的说明文档还没有同步更新。换句话说，文档资产在收口，但索引还没完全跟上。

### 风险与待办

- 已验证项：`uv run immortality auth -h` 现在输出的是项目 CLI 自己的帮助，不再出现 `robyn` 抢先解析参数的现象。
- 已知风险：`.trae/deepwiki/项目概览.md` 仍然引用 `docs/BRIEF_INTRO.md`。如果这次删除是有意为之，至少需要把链接改到新的承载文档；如果不是有意删除，这份总览文档需要恢复或迁移。
- 未验证项：当前只修了 `src/services/user.py` 和 `src/server/auth.py` 这两处类型导入，没有系统验证其他“会被 CLI 预加载但又可能引用 Web 框架类型”的模块是否也存在同类副作用。
- 后续动作：先补文档索引收口，再做一次面向 CLI 入口的全局排查，重点看顶层导入是否还会带入 `robyn`、网络客户端或参数解析副作用。

### 建议 Commit Message（git-cz）

- `fix(cli): avoid robyn import side effects in auth flow`

## CHANGELOG - 2026-05-18 14:27 - Graph 节点统一经由 dispatcher 分发 service 调用

### 撰写时间

- 2026-05-18 14:27

### Base Commit

- 82d59839d4bc241eb7eb274efc8715f3fa9cdbeb

### Compare Scope

- working_tree_only

### 背景与改动目标

- 这次改动的起点不是扩功能，而是把 shared database 这条链路继续往里收口。前几轮 dispatcher 已经接进了 CLI 和部分 channel，但两个 Graph 节点内部仍然残留着不少直接调用本地 service 的路径。这样一来，本地模式和共享数据库模式在 Graph 层会出现两套行为：前者直接触库，后者理论上应该走 HTTP 分发，但实际又没有完全接上。
- 一开始最直接的做法是只补几个明显的读操作，例如 `getFigureAndRelation()` 或 `recallFineGrainedFeeds()`。但顺着 `FRBuildingGraph` 往下看，很快会发现它真正的问题不是“某一个漏网调用”，而是整条 Graph 执行链路里夹杂了多种调用方式。最终这轮选择把相关 service 调用尽量统一改成 `dispatchServiceCall()`，并把缺失的 router 契约和序列化能力一并补齐。

### 改动概览

- `src/agents/graphs/ConversationGraph/nodes.py`：`getUserById`、`getFigureAndRelation`、`recallFineGrainedFeeds` 全部改成通过 `dispatchServiceCall()` 获取数据。这样 `ConversationGraph` 在 shared mode 下不再偷偷回落到本地 service。
- `src/agents/graphs/FRBuildingGraph/nodes.py`：把 `addOriginalSource`、`updateFigureAndRelation`、`recallFineGrainedFeeds`、`addFineGrainedFeed`、`updateFineGrainedFeed`、`addFineGrainedFeedConflict`、`getFROverallUpdateLogsThisRound`、`addFRBuildingGraphReport` 等调用统一收口到 dispatcher。`nodeGenerateFRBuildingReport()` 还补了一个降级分支：如果本轮更新日志拉取失败，会记 warning 和 logs，然后按 skip 继续，不阻塞整份报告生成。
- `src/server/routers/figure_and_relation.py`、`src/services/figure_and_relation.py` 与 `src/service_dispatcher.py`：补出 `/fr/getFROverallUpdateLogsThisRound` 这条 HTTP API，并把原本只返回列表的 `getFROverallUpdateLogsThisRound()` 改成统一返回 `status/message/logs` 结构，同时增加 `user_id` ownership 校验。
- `src/utils/index.py` 与 `src/service_dispatcher.py`：新增 `toSerializableValue()`，在 dispatcher 发起 HTTP 请求前统一把 `Enum`、`datetime`、嵌套 `dict/list/tuple` 转成可安全透传的基础类型，避免 Graph 节点把枚举和时间对象直接塞进 query 或 JSON 时出现序列化不一致。
- `src/server/routers/graph.py` 被删除，`src/server/routers/index.py` 不再注册 `graph_router`；同时 `src/service_dispatcher.py` 里未被使用的 `GRAPH_API_MAP` 也一并清理。按当前约束，这两个 Graph API 已经不再作为外部依赖入口保留。

### 关键链路解析（含上下游）

- 上游依赖：这轮改动建立在 `dispatchServiceCall()` 已经能区分本地模式和 shared mode 的前提上。dispatcher 上游依赖 `SERVICE_API_MAP` 提供 service 到 HTTP 路径的映射，也依赖 CLI 本地 session 提供鉴权头。
- 当前改动：`ConversationGraph` 和 `FRBuildingGraph` 现在都把“取用户、取 FR、召回 feed、写 original source、写冲突、写报告、拉本轮 update logs”这些 service 访问收口到同一种 dispatch 方式。换句话说，Graph 节点本身不再关心底层到底是本地直调还是远端 HTTP，它只消费统一的 service 返回结构。
- 下游影响：shared mode 下，Graph 执行链路终于能完整复用 service router 契约，不会再因为某个节点偷偷直连本地数据库而绕开 dispatcher。与此同时，`getFROverallUpdateLogsThisRound` 从“本地 helper”升级成正式 API 之后，后续如果还有别的入口需要复用这份日志，也可以直接走同一条 HTTP 契约。

### 改动结果与业务影响

- 当前看，这轮改动解决的是 Graph 层调用语义不一致的问题。之前 dispatcher 已经存在，但 Graph 还是保留了不少直接 service 调用；现在这两层终于连上，shared database 模式的边界更清楚了。
- `FRBuildingGraph` 的报告链路也更稳了一点。日志查询现在有显式的 API 和 ownership 校验，失败时会留下 warning 和执行日志，而不是直接让整个报告节点崩掉。这个选择偏保守，它优先保证“报告尽量产出”，代价是某些失败场景下报告可能缺少本轮 update logs。
- 还有一个工程收益是序列化边界被固定下来了。Graph 里本来就会传 `FineGrainedFeedDimension`、`ConflictStatus`、`datetime` 这类对象；把它们在 dispatcher 入口统一归一化，比散落在各个 router 或调用点手写转换要稳定得多。

### 风险与待办

- 这轮已经解决的风险是“Graph 节点里还留着游离的直接 service 调用”。至少在当前 diff 覆盖到的 `ConversationGraph` 和 `FRBuildingGraph` 主链路上，这部分已经被 dispatcher 收口。
- 仍然保留的边界是 `nodeGenerateFRBuildingReport()` 对 update logs 查询失败采用了 skip 策略。这个选择符合当前“不要阻塞报告”的目标，但也意味着当日志服务或远端调用异常时，最终报告可能不完整。当前更像是显式降级，不是彻底修复。
- 未验证项主要有两类：一类是 shared mode 下 Graph 节点实际发起 HTTP 调用时，`toSerializableValue()` 是否已经覆盖了所有参数形态；另一类是 `getFROverallUpdateLogsThisRound` 新增 ownership 校验后，历史调用方是否都已经补齐 `user_id`。

### 建议 Commit Message（git-cz）

- `refactor(graph): route service calls through dispatcher`

## CHANGELOG - 2026-05-14 18:36 - 共享数据库模式补齐登录校验与环境诊断闭环

### 撰写时间

- 2026-05-14 18:36

### Base Commit

- 3eb9bed4c285606da39494afcea7ba1374f01cd2

### Compare Scope

- working_tree_only

### 背景与改动目标

- 这次改动延续的还是 shared database 这条主线，但目标已经从“让 dispatcher 能跑起来”收敛成“把用户真正会碰到的几个缺口补平”。上一轮把 CLI 和 Lark 入口接进 `dispatchServiceCall()` 之后，工作区里暴露出几个新问题：`doctor` 还不会区分本地数据库和远端服务，CLI 里的登录态校验仍然默认走本地 helper，同步链路缺一个可复用的 HTTP 封装，另外登录成功后本地 session 还要额外再解析一次 token 才能拿到 `user_id`。
- 一开始最直接的修法是继续在各个入口各补一段兼容逻辑，但这样会把 shared mode 的边界散落在 CLI、router、request utils 和数据库检查里。最终这轮还是选择把这些问题收口到几条主链路：环境变量检查、健康检查、登录态校验，以及 dispatcher 所依赖的同步请求能力。

### 改动概览

- `src/cli/commands/index.py`：`runDoctorCheck()` 新增 `USE_SHARED_DATABASE` 与 `HTTP_BASE_URL` 检查，并按模式分流健康检查。shared mode 下改为探测 `HTTP_BASE_URL/ping`，本地模式下则通过 `checkDatabaseConnection()` 校验数据库连通性。`setupCLI()` 同时新增 `easy` 模式，会写入 `USE_SHARED_DATABASE=True`，并跳过本地数据库初始化。
- `src/database/index.py`：抽出 `checkDatabaseConnection()`，把原来散落在 CLI 里的 `SELECT 1` 检查收回数据库模块，避免 `index.py` 继续直接依赖 SQL 细节。
- `src/server/routers/user.py`、`src/service_dispatcher.py` 与 `src/cli/utils.py`：新增 `getUserIdByAccessToken` 的远端路由和 dispatcher 映射，CLI 校验本地 session 时不再直接调本地 helper，而是通过 `dispatchServiceCall()` 去校验 token，并在返回 `None` 时主动清理失效 session。
- `src/services/user.py` 与 `src/cli/commands/auth.py`：`userLogin()` 现在直接返回 `user_id`，CLI 登录成功后不需要再本地二次解析 token，就可以把 `access_token` 和 `user_id` 一起写入 session。
- `src/utils/index.py` 与 `src/utils/request.py`：把同步运行 awaitable 的能力抽成 `runAwaitableSync()`，同时新增同步版 `fetch()`，让 `doctor` 这种同步 CLI 路径也能复用同一套 HTTP 请求基础设施。
- `docs/BOTTLENECK.md`：当前结论改写为“数据库访问已经收敛到 service 层并通过 dispatcher 分流消费”，和这轮代码状态保持一致。

### 关键链路解析（含上下游）

- 上游依赖：这轮改动建立在前一轮 dispatcher 已经存在的前提上。`dispatchServiceCall()` 负责判断 `USE_SHARED_DATABASE`，`SERVICE_API_MAP` 负责把 service 名映射到 Robyn 路由，`src/server/routers/index.py` 的 `/ping` 则成为 shared mode 下 `doctor` 的最小健康探针。
- 当前改动：CLI 的三条关键链路被补成闭环。第一条是 `setup -> .env`，`easy` 模式会显式写入 `USE_SHARED_DATABASE=True`；第二条是 `doctor`，它现在会先解析 `.env`，再按模式选择检查数据库或远端 `/ping`；第三条是 `auth/session`，登录后通过 `userLogin()` 直接拿到 `user_id`，后续 `getCurrentUserFromLocalSession()` 再通过远端 `getUserIdByAccessToken` 校验 token 是否仍然可用。
- 下游影响：`whoami`、`modify-password`、`bind-lark`、`fr` 这类依赖 `getCurrentUserFromLocalSession()` 的 CLI 命令，在 shared mode 下终于不再偷偷回落到本地 JWT 解析逻辑。换句话说，session 是否有效现在由当前运行模式对应的链路来判断，而不是默认假设本地校验一定可用。
- 还有一个配套动作是把 `runAwaitableSync()` 从 `service_dispatcher.py` 挪到 `src/utils/index.py`。这样 dispatcher、本地 async service 收口、同步版 `fetch()` 都复用同一个同步桥接实现，后续如果还要在别的同步 CLI 命令里发异步 HTTP，请求层不会再重复造轮子。

### 改动结果与业务影响

- 当前看，这轮改动把 shared database 模式下最容易踩坑的几个入口补齐了。用户如果走 `easy setup`，`.env` 会明确带上模式标记；`doctor` 也会按模式给出更贴近真实链路的诊断，而不是一律检查本地 PostgreSQL。
- 登录链路也更顺了。CLI 登录成功后不再额外本地解 token 拿 `user_id`，session 校验时则统一经过 dispatcher 对应的链路，这让 shared mode 下的行为和本地模式保持了同样的入口形态，只是底层分发目标不同。
- 这次还有一个工程收益：同步 CLI 场景和异步 HTTP 工具之间终于有了明确桥接层。`fetch()` 和 `afetch()` 共用一套底层请求语义，`runAwaitableSync()` 则把“同步入口消费异步能力”的边界固定在工具层，而不是继续散落在业务文件里。

### 风险与待办

- 已补齐的风险：`doctor` 之前会把 `HTTP_BASE_URL` 当成所有模式的硬依赖，现在已经按 shared mode / local mode 分开检查；CLI 登录态校验也不再依赖本地直调 `getUserIdByAccessToken()`。
- 已补齐的风险：`access_token` 不再经由 query string 传输，而是改成 `POST` JSON 请求体，至少避免了最显眼的 URL 泄露面。
- 仍然保留的边界：`userLogin(from_remote=True)` 现在依旧生成无 `exp` 的 token。这个选择能让 shared mode 下的远端登录持续可用，但也意味着 token 轮换、撤销和失效治理还没有设计完，这一点不能包装成“已经彻底解决”。
- 未验证项：当前工作区没有看到围绕 `easy setup -> doctor -> auth whoami` 这条 shared mode 主链路的自动化回归。接下来至少值得补两类验证，一类是远端 `/ping` 与 `getUserIdByAccessToken` 的 happy path / failure path，另一类是本地模式下 `doctor` 仍然能正确只检查数据库。

### 建议 Commit Message（git-cz）

- `feat(shared-mode): close setup doctor and auth validation loop`

## CHANGELOG - 2026-05-14 11:57 - dispatcher 接入 CLI/Lark 并补齐共享数据库登录边界

### 撰写时间

- 2026-05-14 11:57

### Base Commit

- e45914187ec72a110abd9567b0eba062ddc40cef

### Compare Scope

- working_tree_only

### 背景与改动目标

- 这次改动延续了上一轮 shared database 分发层的主线，但重点已经从“预埋 dispatcher 骨架”转向“把真实入口接过去”。如果 `dispatchServiceCall()` 只存在于基础设施层，CLI 和 Lark 入口继续直连本地 service，那么共享数据库模式的价值还是落不到实际链路里。
- 一开始最容易出问题的地方有两类：一类是 CLI 和飞书集成里还残留着直调 service 的路径；另一类是登录链路在 shared mode 下有特殊约束，`userLoginByOpenId` 不能暴露成远端能力，但又必须保证消息入口不会误走本地 fallback。最终这轮改动的目标很明确，就是把能远程分发的 service 调用统一收口，同时把例外分支写成显式边界。

### 改动概览

- `src/cli/commands/auth.py`：`userLogin`、`userRegister`、`getUserById`、`userModifyPassword`、`userBindLark` 统一改走 `dispatchServiceCall()`，CLI 登录、注册、查当前用户、改密和绑定飞书都开始消费分发层。
- `src/cli/commands/fr.py`：`addFigureAndRelation`、`getAllFigureAndRelations`、`getFRAllContext`、`syncFeedsToFRCore`、`syncAllFeedsToFRCore` 全部接到 dispatcher，原先直接 `asyncio.run(...)` 执行异步 service 的路径被移除。
- `src/channels/lark/integration/index.py` 与 `src/channels/lark/integration/menu.py`：`getUserIdByOpenId`、`ifFRBelongsToUser`、`getFigureAndRelation`、`getAllFigureAndRelations`、`getFRAllContext` 统一改为通过 `dispatchServiceCall()` 获取数据。
- `src/server/routers/user.py` 与 `src/service_dispatcher.py`：新增 `/user/getUserIdByOpenId` 及对应 `SERVICE_API_MAP` 映射，补齐 Lark 入口切到远端 service 所需的 API 契约。
- `src/services/user.py`：`userLogin()` 新增 `from_remote` 参数；远端登录不再构造超大过期时间，而是通过 `expires_delta=None` 生成“无 `exp`” token，避免时间溢出。
- `src/service_dispatcher.py` 与 `src/channels/lark/integration/index.py`：把共享数据库环境判断函数暴露为 `isSharedDatabaseMode()`，Lark 登录入口据此在 shared mode 下直接拒绝 `userLoginByOpenId` fallback，并提示用户通过 CLI 重新登录。

### 关键链路解析（含上下游）

- 上游依赖：这轮改动直接建立在上一轮的 Robyn router 基础上。`dispatchServiceCall()` 只有在 `/user/*`、`/fr/*` 这些 API 已存在时才有意义；因此新增 `getUserIdByOpenId` router 和 dispatcher 映射，是 Lark 链路真正切到远端调用的前提。
- 当前改动：CLI 和 Lark 入口不再自己判断“本地 service 是同步还是异步”，统一把这个问题交给 `dispatchServiceCall()`。本地模式继续直调 service，并通过 `_runAwaitableSync()` 收口异步返回；共享数据库模式则按 `SERVICE_API_MAP` 发起 HTTP 请求，调用方只消费统一的 `dict` 协议。
- 下游影响：`auth`、`fr` 两组 CLI 命令，以及飞书消息入口、菜单查询、FR 展示链路，现在已经具备 shared mode 下切远端 service 的能力。下游最直接的收益是调用面更一致，后续继续接入更多入口时不需要重复处理 async/sync 差异。
- 特殊边界：`userLoginByOpenId` 没有被纳入 dispatcher，也没有对外暴露远端登录接口。这不是遗漏，而是显式约束。因为 shared database 场景下不允许通过 `open_id` 从远端补登，所以 `loginIfNeeded()` 在 shared mode 下只做失效提示，不再偷偷走本地 fallback。

### 改动结果与业务影响

- 当前看，这轮改动真正把 shared database 分发从“基础设施预埋”推进到了“入口开始消费”。尤其是 CLI 和 Lark 两条最容易感知的链路，已经不再依赖各自维护一套本地 service 调用方式。
- 另一个关键收益是登录边界更清楚了。此前如果远端登录为了“永不过期”去伪造一个极大的过期时间，链路本身会先在 `datetime` 上溢出；现在改成 `expires_delta=None` 之后，远端 token 生成逻辑更直接，也更符合这条特殊约束的真实语义。
- 代价是远端登录 token 当前没有 `exp` 字段，这能满足 shared mode 的续航要求，但也意味着后续如果要引入更细粒度的过期治理，需要单独设计这类 token 的撤销或轮换策略。

### 风险与待办

- 已解决的运行风险：`userLogin(from_remote=True)` 不再通过超大 `timedelta` 规避过期，时间溢出问题已经被消掉。
- 已解决的链路风险：Lark 入口里此前那类“共享数据库模式仍可能直调本地 `userLoginByOpenId`”的路径已经显式拦住；另外，无效 FR 清理分支也恢复为按 `open_id` 正常清理，不再向 `pop()` 传不可哈希对象。
- 仍需关注的边界：本次覆盖的是当前 diff 触达的 CLI/Lark 入口，不代表仓库内所有 service 消费点都已经全面切到 dispatcher。像本地 JWT 解析这类 helper 仍然直接调用本地函数，这类调用不属于 shared service 分发范畴，但后续做全量收口时需要继续区分“业务 service”与“本地工具函数”。
- 未验证项：当前没有看到围绕 shared mode 的自动化回归，建议至少补三类检查，分别是 CLI 在 shared mode 下的登录/查询链路、Lark `open_id -> user_id` 查询失败分支，以及远端 `userLogin` 生成无 `exp` token 的兼容性验证。

### 建议 Commit Message（git-cz）

- `refactor(dispatcher): route cli and lark service calls via dispatcher`

## CHANGELOG - 2026-05-13 16:03 - Shared Database 分发层预埋与 Graph API 返回收口

### 撰写时间

- 2026-05-13 16:03

### Base Commit

- b4b0d783b9a16a957ca2a23d2a10c6ccfeeaf594

### Compare Scope

- working_tree_only

### 背景与改动目标

- 这次改动的起点很明确：前一轮 Robyn router 和 Graph HTTP API 已经补齐了，但 CLI / service 调用面还停留在“默认直连本地 service”的模式。只要后续要支持 shared database、多环境或者 remote service，调用方迟早需要一个统一的分发层。
- 一开始工作区里看到的内容有两部分。一部分是运行链路本身：`src/service_dispatcher.py`、`.env.example`、`src/server/routers/graph.py`、`src/utils/request.py`、`src/agents/prompt.py` 这些文件，明显是在为“本地 service / 远程 HTTP”双模式做预埋。另一部分是 `.trae/deepwiki/` 下的一批未跟踪文档资产，它们不直接改变运行行为，但在当前工作区里确实构成了新的知识沉淀。
- 因此这条 changelog 采用当前最新工作区口径来写：既记录 shared database 分发主线，也把 Graph API 返回结构的收口、TODO 优先级调整和 DeepWiki 文档资产一起纳入说明。

### 改动概览

- `src/service_dispatcher.py`：新增 service 分发层。核心能力是根据 `USE_SHARED_DATABASE` 判断走本地 service 还是远程 HTTP；本地模式直接调用 `service(**args)`，异步 service 会通过 `_runAwaitableSync()` 同步收口；共享模式则基于 `SERVICE_API_MAP` 和 `HTTP_BASE_URL` 发起请求。
- `src/utils/request.py` 与 `src/agents/prompt.py`：把通用请求函数从 `fetch` 重命名为 `afetch`，同时 `getPrompt()` 切到新名字，语义上更清楚地表达“这是异步请求工具”，也为 dispatcher 侧复用打通了入口。
- `src/cli/assets/.env.example`：新增 `USE_SHARED_DATABASE=False` 与 `HTTP_BASE_URL=http://124.223.93.75:1314`，把 shared mode 所需的两个关键环境变量显式写进模板。
- `src/server/routers/graph.py`：`/graph/conversation` 不再整包返回 graph state，而是只返回 `llm_output`；`/graph/frBuilding` 增加图片 form 的 TODO 注释，并把 graph 执行结果包在 `res` 字段里返回。
- `docs/TODOs.md`：新增“发消息带时间戳，否则 AI 不理解什么时候的消息（P00）”，同时把 `multi-env, multi-service 支持` 从 `P00` 下调到 `P1`，说明当前工作区虽然已经开始预埋，但优先级判断更谨慎了。
- `.trae/deepwiki/`：新增一组项目知识文档，包括“项目概览、核心概念与架构、数据模型与存储、代理图设计与工作流、飞书集成与交互、部署与运维、开发与贡献指南”等内容，属于文档资产沉淀。

### 关键链路解析（含上下游）

- 上游依赖：`service_dispatcher.py` 直接依赖上一轮已落地的 Robyn router 契约，也就是 `/user/*`、`/fr/*`、`/feed/*`、`/knowledge/*` 这些 API 已经存在，dispatcher 才能通过 `SERVICE_API_MAP` 把 service 名映射到 HTTP 路径。它还依赖 `src.cli.utils.getCurrentUserFromLocalSession()` 提供 `access_token`，用来给远程请求补鉴权头。
- 当前改动：shared mode 的核心不是替换业务逻辑，而是在调用入口增加一层 `dispatch`。本地模式继续保留原有 service 调用语义，减少侵入；远程模式则把参数按 GET query 或 POST JSON 发给 Robyn API。与之配套，`afetch()` 成为统一的异步 HTTP 基础设施，`getPrompt()` 这类本来就跑在 async 链路里的逻辑也顺势切到同一个工具名。
- 下游影响：如果后续 CLI、channel 或 graph 节点开始接入 `dispatchServiceCall()`，它们就不需要再关心“当前到底连的是本地数据库还是远程服务”。另一方面，`/graph/conversation` 的返回被裁剪到 `llm_output` 后，下游调用方不再拿到整份 graph state，接口语义更聚焦，但如果有旧调用方依赖原来的 `result` 整包结构，就需要同步适配。`/graph/frBuilding` 目前仍保留顶层 `status/message` 包装，并把内部 graph 输出放在 `res` 里，说明这条 API 还没有完全和 graph 原始输出做一体化收口。
- 文档链路这边的影响更偏长期。`.trae/deepwiki/` 这批未跟踪资产不会进入运行时，但它们把项目概览、Graph 工作流、提示词工程、飞书集成等信息整理成了可检索文档，后续无论是人读还是 agent 消费，都会比只看源码更容易建立全局上下文。

### 改动结果与业务影响

- 当前看，这轮工作的真正收益是把“shared database / multi-service”从一个 TODO 议题推进成了可落地的代码骨架。虽然调用入口还没有在全链路切过去，但环境变量、API 映射、鉴权头构造、同步包 async 结果这些基础件已经放好了。
- Graph API 的返回结构也开始做取舍。`conversation` 只暴露 `llm_output`，说明接口开始从“调试友好”转向“协议清晰”；`frBuilding` 仍保留 `res` 包装，则说明这块还处于过渡状态。
- 文档侧的收益是知识资产更完整。DeepWiki 目录里的内容覆盖项目介绍、数据模型、Graph 设计、部署与飞书交互，这些信息对后续协作和自动化分析都有帮助。

### 风险与待办

- 已知风险：`src/service_dispatcher.py` 目前还是未跟踪文件，而且从当前代码看还没有被业务入口正式接入。换句话说，shared mode 的分发层已经成形，但还没有走到“被真实链路消费”的阶段。
- 已知风险：`.env.example` 直接写入 `HTTP_BASE_URL=http://124.223.93.75:1314`，虽然便于快速试用，但把真实服务地址放进模板会增加环境耦合，也会让后续部署迁移更麻烦。
- 已知风险：`GRAPH_API_MAP` 已经在 dispatcher 里预留，但当前 `dispatchServiceCall()` 只消费 `SERVICE_API_MAP`。这意味着 graph 远程调用还停留在规划态，没有真正打通。
- 未验证项：当前工作区没有看到围绕 dispatcher 的自动化验证，例如“共享模式下 GET/POST 参数是否正确透传”“本地模式调用 async service 是否稳定收口”“token 缺失时 auth header 构造失败如何回显”。
- 后续动作：先决定哪些 CLI / 集成入口要优先接入 `dispatchServiceCall()`，再补最小回归验证。与此同时，建议把 `HTTP_BASE_URL` 改成占位符或显式注释配置，并确认 `.trae/deepwiki/` 是否作为正式文档资产纳入版本控制。

### 建议 Commit Message（git-cz）

- `feat(dispatcher): scaffold shared database service routing`

## CHANGELOG - 2026-05-11 17:33 - Robyn 服务化入口补齐并暴露 Graph HTTP API

### 撰写时间

- 2026-05-11 17:33

### Base Commit

- 9b3f8a72ad0fecf0975abf674e3094244e8e2742

### Compare Scope

- working_tree_only

### 背景与改动目标

- 这轮改动的主线是把“已有 service / graph 能力”收敛到统一的 HTTP 入口，而不是继续扩展业务逻辑。前一个阶段我们已经把核心能力沉淀在 `src/services/*` 和 `src/agents/graphs/*`，但服务端对外调用面还是缺口状态，调用方很难直接通过 API 对接。
- 因此这次目标有三层：一是引入并启动 Robyn 服务入口；二是把 `figure_and_relation`、`fine_grained_feed`、`knowledge` 的 service 方法按既有风格封装成 router；三是把 `ConversationGraph` 与 `FRBuildingGraph` 暴露为可鉴权调用的 HTTP 接口，形成完整链路。

### 改动概览

- 依赖层：`pyproject.toml` 增加 `robyn>=0.84.0`，`uv.lock` 同步更新。
- 服务入口层：新增 `src/server/app.py`、`src/server/auth.py`、`src/server/routers/index.py`，并在 `index.py` 统一注册 `user/fr/feed/knowledge/graph` 五组子路由。
- router 封装层：新增 `src/server/routers/figure_and_relation.py`、`src/server/routers/fine_grained_feed.py`、`src/server/routers/knowledge.py`、`src/server/routers/user.py`，补齐 query/body 取参、鉴权、枚举解析与参数校验。
- Graph API 层：新增 `src/server/routers/graph.py`，提供 `/graph/conversation` 与 `/graph/frBuilding` 两个入口，对接 `getConversationGraph()` 和 `getFRBuildingGraph()`。
- 通用工具层：`src/utils/index.py` 新增 `parseInt()`、`parseFloat()`；相关 router 改为复用 util，不再重复定义局部解析函数。
- 用户与 CLI 衔接：`src/services/user.py` 的 `getUserIdByAccessToken` 支持直接接收 `request`；`getUserById` 返回完整 `user.toJson()`；`src/cli/commands/auth.py` 的 `whoami` 增加 `user_raw is None` 防御分支，避免空指针。
- Harness 资产：新增 `.trae/skills/service-router-api-wrapper/SKILL.md`，把 router 封装约束写成可复用规则（取参、鉴权、错误结构、util 复用）。

### 关键链路解析（含上下游）

- 上游依赖：Graph 路由依赖 `ConversationGraph` / `FRBuildingGraph` 的 `ainvoke` 调用语义；鉴权链依赖 `AuthHandler` 与 `getUserIdByAccessToken(request=request)`；service 路由依赖枚举解析 `parseEnum` 与各模块 service 返回协议。
- 当前改动：HTTP 请求先在 Robyn router 做参数校验和身份提取，再把 `user_id` 注入 `request` state 后调用 service 或 graph。换句话说，router 现在承担“协议入口层”，业务逻辑仍留在 service / graph 本体。
- 下游影响：调用方可以直接通过 API 触发人物关系 CRUD、细粒度 feed 管理、知识检索与两类 Graph 执行；CLI 与 service 的用户信息字段保持兼容，不再因为 `whoami` 空用户分支导致崩溃。

### 改动结果与业务影响

- 当前收益是服务化入口成型：项目从“内部函数可用”变成“可鉴权 API 可用”，后续前端或外部系统联调有了统一接入面。
- 这次也顺带完成了参数解析能力的收敛，`parseInt()/parseFloat()` 统一放到 util 后，router 代码重复度下降，后续扩接口时更容易保持一致风格。
- 代价是接口面迅速扩大，运行稳定性更依赖参数边界处理与统一错误语义；在这个边界下，后续需要更系统的接口级回归来兜底。

### 风险与待办

- 已知风险：`/graph/frBuilding` 当前仍要求 `raw_content` 非空，和 `FRBuildingGraph` 节点“文本与图片二选一即可”的语义存在偏差，纯图片输入会被提前拒绝。
- 已知风险：Graph 路由顶层固定返回 `status=200`，而 graph 内部输出可能是失败状态；若调用方只看顶层 `status`，会产生成功误判。
- 已知风险：`figure_and_relation` 中 `getFROverallUpdateLogsThisRound` 路由已注释下线，相关 service 仍保留；后续若重新开放，需要补 ownership 校验后再暴露。
- 建议补充验证：至少覆盖五类路径，分别是 router 参数非法分支、token 缺失分支、`ConversationGraph` 正常调用、`FRBuildingGraph` busy 分支、以及 Graph 内部失败时的状态透传行为。

### 建议 Commit Message（git-cz）

- `feat(server): add robyn routers and expose graph http apis`

## CHANGELOG - 2026-05-11 11:14 - Graph 用户名展示统一为 username(nickname)

### 撰写时间

- 2026-05-11 11:14

### Base Commit

- 2cd2d5c18e4210bcd98d74e44c538ed1acd8f8d0

### Compare Scope

- working_tree_only

### 背景与改动目标

- 这次改动的出发点是“对话上下文里的用户称呼不够稳定”。之前 `ConversationGraph` 与 `FRBuildingGraph` 都直接把 `username` 写入 `user_name`，当昵称和账号名存在差异时，提示词和报告上下文会丢失一部分身份信息。
- 目标是让两个 Graph 在构建 `user_name` 时保持同一规则，并让下游提示词消费到更完整的用户标识；同时顺手清理一处无实际作用的调试注释，减少链路噪音。

### 改动概览

- `src/agents/graphs/ConversationGraph/nodes.py`：`nodeLoadFRAndPersona` 新增 `username`/`nickname` 变量，`user_name` 统一改为 `username(nickname)`（两者相同则保留单值）。
- `src/agents/graphs/FRBuildingGraph/nodes.py`：`nodeLoadFR` 按同样规则构建 `user_name`，保持两个 Graph 的状态语义一致。
- `src/channels/lark/integration/menu.py`：删除 `buildPersonaLark` 内一行注释掉的调试输出（`# print(res)`），不改变流程行为。

### 关键链路解析（含上下游）

- 上游依赖：两处改动都依赖 `getUserById(user_id)` 返回的 `user` 字典字段（`username`、`nickname`）；规则变化发生在 Graph 的加载节点，而不是提示词模板本身。
- 当前改动：在 `nodeLoadFRAndPersona` 与 `nodeLoadFR` 入口统一把 `user_name` 做格式化，之后继续透传到 Graph state，不改变原有执行路径与错误分支。
- 下游影响：`ConversationGraph.nodeCallLLM` 仍通过 `state["user_name"]` 注入 `CONVERSATION_SYSTEM_PROMPT`；`FRBuildingGraph` 内多处报告和约束提示也消费该字段，因此下游会看到更明确的人名标识。`menu.py` 的注释清理只影响可读性，不影响飞书任务执行。

### 改动结果与业务影响

- 当前收益主要是“称呼一致性”提升：两个 Graph 对 `user_name` 的构造口径对齐，避免一处显示账号名、另一处显示昵称的语义偏差。
- 在昵称与账号名不同的场景下，提示词中的指代信息更完整，理论上有助于减少模型把“我/说话人”映射错对象的概率。
- 这轮变更没有引入新的服务调用或状态字段，整体属于低侵入改动。

### 风险与待办

- 未验证项：本次未看到围绕“昵称缺失/昵称等于账号名/昵称不同于账号名”的自动化回归，建议补最小单测覆盖格式化分支。

### 建议 Commit Message（git-cz）

- `fix(graph): unify user_name format with username and nickname`

## CHANGELOG - 2026-05-11 09:22 - Docker 模式 PostgreSQL 就绪检查收敛并统一 checkpoints 库名

### 撰写时间

- 2026-05-11 09:22

### Base Commit

- 82f7d2ad627e2d4e82351a779359146bffe70978

### Compare Scope

- working_tree_only

### 背景与改动目标

- 这次改动的起点是 `immortality setup` 在 Docker 模式下存在误判：前置检查显示 PostgreSQL 已就绪，但后续执行 `psql` 仍可能因为默认 Unix socket 不存在而失败。
- 目标是让“就绪检查”和“实际数据库操作”使用同一连接语义，减少“看起来 ready、实际失败”的体验割裂，并同步文档与模板里的 checkpoint 数据库命名。

### 改动概览

- `src/cli/commands/index.py`：将 checkpoint 数据库初始化函数重命名为 `_setupCheckpointsDBIfNeeded`，并把数据库名统一为 `immortality_checkpoints`。
- `src/cli/commands/index.py`：两处 `docker exec ... psql` 增加 `-h 127.0.0.1`，强制走 TCP，不再依赖容器内默认 socket。
- `src/cli/commands/index.py`：Docker 启动后就绪判断从主机 `socket.create_connection` 改为容器内 `pg_isready` 探活，语义与后续执行链路保持一致。
- `src/cli/assets/init-db.sh`、`src/cli/assets/.env.example`、`README.md`：数据库名从 `immortality_checkpoint` 同步为 `immortality_checkpoints`，确保脚本、配置模板和说明口径一致。

### 关键链路解析（含上下游）

- 上游依赖：`docker compose up` 负责拉起 `immortality-postgres`；资源模板由 `src/cli/assets/init-db.sh` 与 `src/cli/assets/.env.example` 提供。
- 当前改动：`dockerDBSteup()` 先以 `pg_isready` 判断容器内 PostgreSQL 可用，再进入 `_setupCheckpointsDBIfNeeded()` 执行数据库存在性检查和创建。
- 下游影响：`setupCLI()` 继续写入 `.env`，但 `CHECKPOINT_DATABASE_URI` 默认指向 `immortality_checkpoints`；文档和自动初始化脚本不再出现单复数混用。

### 改动结果与业务影响

- 当前收益是失败模式更可预测：如果数据库未真正就绪，会在 `pg_isready` 阶段尽早失败；如果进入 `psql`，连接方式与探活方式一致。
- 对用户侧来说，这次优化能显著降低“容器已启动但 `psql` 报 socket 文件不存在”的概率，排障路径也更清晰。
- 这轮改动同时完成了配置与文档的口径收口，后续新环境初始化时不易因数据库命名不一致产生偏差。

### 风险与待办

- 已知风险：本次未包含“旧库名 `immortality_checkpoint` 自动迁移到 `immortality_checkpoints`”逻辑，历史环境是否保留旧数据可见性取决于用户现有库状态。
- 未验证项：尚未补充自动化测试覆盖 `pg_isready` 超时分支与 checkpoints 数据库创建分支。
- 后续动作：建议增加最小回归验证，覆盖 Docker 首次初始化、重复执行 setup、以及容器未就绪错误提示文案。

### 建议 Commit Message（git-cz）

- `fix(cli): align docker postgres readiness and checkpoints db setup`

## CHANGELOG - 2026-05-10 00:34 - Python 最低版本统一提升至 3.12 并同步发布链路

### 撰写时间

- 2026-05-10 00:34

### Base Commit

- 751bd2da74d98a7681e6c4b28ce5fd523583fc0e

### Compare Scope

- working_tree_only

### 背景与改动目标

- 这次改动的核心目标很直接：把项目里“Python 最低版本”从 `3.11` 统一提升到 `3.12`，避免文档、运行时校验、打包元数据和 CI 配置出现口径不一致。
- 一开始我们只看到包元数据里的 `requires-python`，但如果只改这一处，CLI 的 `doctor` 提示和 README 仍会继续引导用户使用 `3.11`，最终会造成“规范已变更、入口提示未同步”的体验割裂。因此这轮改动按链路做了同步收口。

### 改动概览

- 包与锁文件：`pyproject.toml`、`uv.lock` 的 `requires-python` 均从 `>=3.11` 调整为 `>=3.12`。
- 运行时校验：`src/cli/commands/index.py` 的 `min_py` 从 `(3, 11)` 提升到 `(3, 12)`，并同步更新失败提示文案。
- 文档口径：`README.md` 中“环境准备”和 `doctor` 检查项的版本描述同步改为 `3.12`；`docs/HEARTCOMPASS.md` 的 `langgraph.json` 示例 `python_version` 改为 `"3.12"`。
- 发布链路：`.github/workflows/publish.yml` 的 `actions/setup-python` 从 `3.11` 调整为 `3.12`，保证打包与发布作业不再基于旧版本。
- 资产补充：`.trae/skills/commit-update-writer/SKILL.md` 触发词补充了 `changelog`，让“生成本次 changelog”可以被更稳定地路由到该 skill。

### 关键链路解析（含上下游）

- 上游依赖：安装与解析入口依赖 `pyproject.toml`/`uv.lock` 的 `requires-python` 约束；开发与发布入口依赖 GitHub Actions 的 Python 解释器版本。
- 当前改动：在元数据、CLI 校验、用户文档、CI 四个层面同时把最低版本切到 `3.12`，并保持提示文案与实际校验逻辑一致。
- 下游影响：本地安装、`immortality doctor`、以及发布流水线现在都以 `3.12` 为基准；仍使用 `3.11` 的环境会更早在安装或健康检查阶段暴露不满足约束，而不是在运行时隐式失败。

### 改动结果与业务影响

- 当前收益是“版本约束单一事实源”更清晰：用户看到的文档、CLI 报错、构建元数据和 CI 行为已经对齐到同一最低版本。
- 对维护侧的好处是减少排障分歧。后续遇到环境问题时，团队不再需要先确认“到底以 README、doctor 还是 CI 为准”，因为三者口径一致。
- 代价是兼容边界收窄：仍在 `Python 3.11` 的开发机/执行环境需要升级到 `3.12` 才能继续走标准流程。

### 风险与待办

- 已知风险：本次是配置与文案对齐，没有覆盖完整运行回归；若某些依赖在 `3.12` 下存在边缘兼容问题，需要在真实安装链路中进一步验证。
- 未验证项：未执行完整的“新环境从零安装 + `uv sync` + `immortality doctor` + 发布作业”端到端校验。
- 后续动作：建议在 CI 中新增一条最小健康检查（安装并运行 `immortality doctor` 关键分支），把版本升级后的行为验证前置到流水线。

### 建议 Commit Message（git-cz）

- `build(python): raise minimum supported version to 3.12`

## CHANGELOG - 2026-05-08 18:51 - 会话校验扩展为当前用户信息并补齐飞书自动续登链路

### 撰写时间

- 2026-05-08 18:51

### Base Commit

- 498d8172ffa9bd45a471fdee89c0eca5a9031a7b

### Compare Scope

- working_tree_only

### 背景与改动目标

- 这次改动的起点是登录态校验语义不足。原实现 `getUserIdFromLocalSession()` 只返回 `user_id`，调用方如果还需要 token，需要重复读取本地会话，链路上存在重复与分散。
- 同时，飞书消息处理链路在 token 过期时没有自动恢复能力。用户在飞书里发消息时，若本地会话失效，服务侧会直接进入失败分支，交互连续性不稳定。
- 因此这次目标有两点：一是把本地会话读取能力从“只拿 user_id”扩展成“返回当前用户信息”；二是在 Lark 集成入口补上基于 `open_id` 的自动登录与会话落盘，降低 token 过期带来的中断。

### 改动概览

- `src/cli/utils.py`：将 `getUserIdFromLocalSession` 重命名为 `getCurrentUserFromLocalSession`，并把返回值改为包含 `user_id` 与 `access_token` 的 dict，同时更新返回类型注解。
- `src/cli/commands/auth.py`、`src/cli/commands/fr.py`、`src/cli/commands/lark_service.py`：统一切换到新接口，通过 `.get("user_id")` 读取身份信息，保持命令行为一致。
- `src/services/user.py`：新增 `userLoginByOpenId(open_id)`，用于飞书链路在已绑定账号场景下补发 access token。
- `src/channels/lark/integration/index.py`：新增 `loginIfNeeded(open_id)`，在 `messageHandler()` 前置执行。流程是先校验本地会话，失效时走 `userLoginByOpenId`，成功后 `saveLocalSession`。
- `docs/BOTTLENECK.md` 与 `src/main.py`：分别做文档小标题表述收口与函数签名类型补充（`-> None`），不改变主功能行为。

### 关键链路解析（含上下游）

- 上游依赖：`getCurrentUserFromLocalSession()` 依赖 `loadLocalSession()` 与 `getUserIdByAccessToken()` 做本地 token 校验；`userLoginByOpenId()` 依赖 `User.lark_open_id` 查询与 `createAccessToken()` 发 token。
- 当前改动：CLI 侧从“取单一 user_id”迁移到“取当前用户上下文”；Lark 侧在消息入口新增“先校验，后补登”的恢复逻辑，并将成功 token 写回本地 `session.json`。
- 下游影响：`whoami`、`fr`、`lark-service start` 这些命令仍沿用原有 user_id 语义，但现在可以复用同一份会话上下文；飞书消息主链路在会话过期时具备自动续登能力，减少因 token 失效导致的对话中断。

### 改动结果与业务影响

- 当前看，主要收益是“登录态能力聚合”和“消息入口稳定性”提升。调用方不再各自拼接会话信息，Lark 服务也不需要完全依赖人工重新登录才能继续处理消息。
- 这次还补了异常兜底：`loginIfNeeded()` 在自动登录或写本地会话异常时会记录日志并返回错误卡片，不会把异常直接抛到上层中断整条消息处理函数。
- 边界上仍然存在一类语义问题：`open_id` 未绑定账号时，当前反馈文案仍是“请稍后重试”，可读性不如“请先绑定账号”直观。

### 风险与待办

- 已知风险：`loginIfNeeded()` 里把“未绑定账号”和“系统异常”都收敛成同一提示文案，排障信息粒度不够。
- 已知风险：Lark 自动登录会覆盖本地 `session.json`，单机多账号轮流触发消息时会出现“最后一次登录覆盖前一次会话”的行为，需要后续按账号隔离会话文件。
- 未验证项：当前未看到新增自动化测试覆盖“token 过期自动续登成功”“open_id 未绑定失败文案”“会话写盘失败兜底”三条关键分支。
- 后续动作：补最小回归测试，并细分 `userLoginByOpenId` 的失败码与用户提示，降低误导性反馈。

### 建议 Commit Message（git-cz）

- `feat(auth): add lark open_id relogin and unify current session access`

## CHANGELOG - 2026-05-07 19:06 - 文档体系补全与 Harness 约束沉淀

### 撰写时间

- 2026-05-07 19:06

### Base Commit

- 0e1926cdce2b9fff9caf373706f5d9773dccf3c5

### 背景与改动目标

- 这次改动的主体是文档收口，不是代码逻辑变更。目标是把项目现状、Harness 方法论和后续规划写成可复用的文档资产，减少协作时的信息断层。
- 本次记录按用户确认口径，忽略 `.env.example` 删除，仅聚焦文档相关改动。

### 改动概览

- `docs/HARNESS.md`：从单行标题扩展为完整落地方案，补齐 skill 定位、生产流程、消费方式、闭环示例与边界说明。
- `docs/BOTTLENECK.md`：在“共享数据库问题”之外，新增“单一飞书 Bot 问题”背景与长期方案，明确多 Bot 配置方向。
- `docs/BRIEF_INTRO.md`：新增项目简要介绍文档，覆盖 Why/What/How、核心链路、数据对象、CLI 与飞书集成、Harness 角色等全局信息。
- `docs/TODOs.md`：将“同一时间只允许一个 FRBuildingGraph 运行，限制并发”标记为已完成，状态与当前实现对齐。
- `.trae/rules/language-style.md`：新增表达风格规则，约束文档与回复语言，减少模板化表达。

### 关键链路解析（含上下游）

- 上游依赖：现有实现与既有 skill（`commit-quality-reviewer`、`commit-update-writer`、`doc-generator`、`doc-optimizer`）是文档内容的事实来源，文档更新需要与这些能力契约保持一致。
- 当前改动：通过 `HARNESS` 主文档 + `BRIEF_INTRO` 总览 + `BOTTLENECK` 议题沉淀 + `TODOs` 状态同步 + `language-style` 规则约束，形成“背景、方法、执行、约束、路线图”一体化文档链路。
- 下游影响：后续协作在“项目介绍、任务对齐、文档写作、收尾沉淀”场景下可直接复用这些资产，减少口头传递和重复解释成本。

### 改动结果与业务影响

- 当前收益主要在工程协作层：项目介绍、瓶颈分析、Harness 方法和待办状态都获得了统一的书面基线。
- 新成员和跨会话协作者可以更快理解系统结构与工作方式，降低“只看代码难以把握全貌”的成本。
- 文档规则被显式化后，后续更新记录与说明文档在表达风格上更一致，可读性更稳定。

### 风险与待办

- 已知风险：文档体量快速增长后，若缺少周期性校对，容易与代码实现再次漂移。
- 未验证项：`docs/BRIEF_INTRO.md` 中的流程和参数说明尚未做系统化一致性检查（仅基于当前认知整理）。
- 后续动作：在后续迭代建立“文档一致性复查”节奏，重点核对 Graph 行为、CLI 命令和 skill 清单是否保持同步。

### 建议 Commit Message（git-cz）

- `docs(harness): enrich project docs and align writing rules`

## CHANGELOG - 2026-05-05 15:14 - FRBuildingGraph 并发收口与提交质检文档补强

### 撰写时间

- 2026-05-05 15:14

### Base Commit

- ae067db5a89f989ed37cbda1d9fa1e04da057868

### 背景与改动目标

- 这次改动的起点有两条线，但本质上都在处理“约束要不要落成显式规则”。一条在线上链路：`FRBuildingGraph` 作为进程内单例被复用时，如果同时有多个画像完善任务进入，运行语义其实是不稳定的。另一条在 Harness 侧：我们已经开始依赖 `commit-quality-reviewer` 和 `commit-update-writer` 做提交流程约束，因此这些 skill 的触发边界和写作规则也需要写得更清楚。
- 一开始的目标不是扩展功能，而是把原本隐含的使用约束收紧成代码和文档里的显式行为。换句话说，这轮改动更像一次“收口”，而不是新增能力。

### 改动概览

- Graph 侧：`src/agents/graphs/FRBuildingGraph/graph.py` 把 `getFRBuildingGraph()` 从直接返回全局 graph，改成异步上下文管理器；内部新增 `asyncio.Semaphore(1)`，把“同一时刻只允许一个画像完善任务执行”变成显式约束。
- Lark 集成侧：`src/channels/lark/integration/menu.py` 的 `buildPersonaLark()` 同步切到 `async with getFRBuildingGraph()`；当 graph 处于运行中时，菜单命令不再静默失败，而是给用户回一张“请稍后再试”的黄色提示卡片。
- 测试/脚本侧：`tests/graphs/FRBuildingGraph.py` 的调用方式同步更新，避免继续以旧接口直接拿 graph。
- Harness 文档侧：`.trae/skills/commit-quality-reviewer/SKILL.md` 补充了“审查本次改动 / 检查代码变更 / review 代码 / 代码质检”等触发描述；`.trae/skills/commit-update-writer/reference/language-style.md` 删掉了重复的“追加记录建议骨架”，把重点重新收敛到文风和表达约束。

### 关键链路解析（含上下游）

- 上游依赖：`buildPersonaLark()` 并不是在当前线程里直接 `await` graph，而是通过 `_submitBackgroundCoroutine()` 把协程扔到 `src/channels/lark/integration/index.py` 里那条全局后台事件循环执行。因此这次并发控制的落点不是 HTTP 层或消息队列层，而是 `FRBuildingGraph` 入口本身。
- 当前改动：`getFRBuildingGraph()` 现在负责两件事。第一件事是用 `Semaphore(1)` 拒绝并发进入；第二件事是用 `async with` 保证异常路径也能释放占用。对应地，`buildPersonaLark()` 不再先拿 graph 再调用，而是在上下文里执行 `graph.ainvoke(init_state)`，并在 busy 分支回显更明确的用户提示。
- 下游影响：对人物画像完善主链路来说，输入 state、graph 节点拓扑和返回结果都没有变化，真正变化的是“什么时候允许执行”。也就是说，下游的报告发送、成功卡片、失败卡片逻辑基本保持原样；但从现在开始，同一进程内第二个并发画像任务会在入口被拒绝，而不是和第一个任务同时跑。
- 文档链路侧的影响更偏流程治理。`commit-quality-reviewer` 的触发面写清楚后，后续让 agent 执行“审查本次改动”这类自然语言请求时，路由更稳定；`commit-update-writer` 的风格参考去掉模板重复段落后，更新记录的唯一模板来源重新回到 skill 主文档，避免两份模板漂移。

### 改动结果与业务影响

- 当前看，最直接的收益是 `FRBuildingGraph` 的单实例使用语义更明确了。以前这件事更多依赖调用方自觉，现在变成 graph 入口自己兜底。对于 Lark 菜单命令来说，这能减少同一时刻重复触发画像完善时的状态错乱风险。
- 另一个收益是用户反馈更可解释。之前如果后台任务冲突，调用方很难知道为什么失败；现在至少会明确告诉用户“当前存在运行中任务，请等待完成后再试”。
- Harness 侧的收益则更偏长期。skill 触发词和文风规则补强后，提交流程里的自动质检、更新记录沉淀更容易走到一致路径，减少“能做但触发不到”或“同类文档写法反复漂移”的问题。

### 风险与待办

- 已知风险：这次把并发限制落在 graph 入口，主链路行为是清晰了，但没有配套自动化测试去验证“第二个请求被拒绝”“异常退出后信号量会释放”这两个边界。它不一定马上影响当前功能，但后续重构时缺少回归保护。
- 未验证项：当前没有看到基于真实 Lark 后台 loop 的并发回归，也没有看到针对 busy 提示卡片的自动化检查。现阶段只能认为语义上合理、实现上可读，但验证深度还不够。
- 后续动作：先把 busy 分支改成专用异常，再补一组最小异步测试，直接围绕 `getFRBuildingGraph()` 的占用与释放语义做校验；这样这轮“并发收口”才算真正闭环。

### 建议 Commit Message（git-cz）

- `feat(graph): guard FR building graph against concurrent runs`

## CHANGELOG - 2026-05-05 01:19 - Service 解耦收口与 Graph/Lark 链路对齐

### 撰写时间

- 2026-05-05 01:19

### Base Commit

- 922eb20468224b03c719a4bce1f193d3e4b8b91b

### 背景与改动目标

- 这轮改动的主线不是新增功能，而是把“非 service 解耦数据库操作”继续收口，目标是让 Graph、Lark 集成与 CLI 的数据访问统一走 service，减少 `with session() as db` 在非 service 层的散落。
- 同时我们在做 Harness 化沉淀：补齐 skill 能力（文档生成、文档优化、Graph 文档重写、commit 质检与更新记录写作）和对应文档资产，降低后续重复工作成本。

### 改动概览

- Graph 节点侧：`ConversationGraph` 与 `FRBuildingGraph` 的加载节点从 ORM 实体访问改为 service 返回 dict 访问，去掉对 `checkFigureAndRelationOwnership`/`session` 的直接依赖。
- Service 层：`user` 新增 `getUserIdByOpenId`；`figure_and_relation` 新增 `ifFRBelongsToUser`，并扩充 `getAllFigureAndRelations` 返回字段，补齐上游调用改造所需数据。
- Lark 集成侧：`index.py`、`menu.py` 从 `integration/utils.py` 中移除 DB 查询逻辑，统一改走 `src/services/user.py` 与 `src/services/figure_and_relation.py`。
- CLI 侧：`fr list` 输出前统一 `figure_role` 的字符串格式（`stringifyValue(...).upper()`），`doctor` 将 `session` import 下沉到检查分支，减少模块加载时耦合。
- 文档与工程资产：重写/更新 `ConversationGraph`、`FRBuildingGraph` README 以及 `docs/BOTTLENECK.md`、`docs/REFACTOR.md`、`docs/TODOs.md`，并新增多份 `.trae/skills/*` 能力说明。

### 关键链路解析（含上下游）

- 上游依赖：
- `src/services/user.py` 的 `getUserById`、新加 `getUserIdByOpenId`，以及 `src/services/figure_and_relation.py` 的 `getFigureAndRelation`/`getAllFigureAndRelations`/新加 `ifFRBelongsToUser` 成为统一数据入口。
- `buildFigurePersonaMarkdown` 的入参从 ORM 实例改为 dict，这直接要求上游调用方在 Graph 节点里不再传 ORM 对象。

- 当前改动：
- `ConversationGraph.nodeLoadFRAndPersona` 与 `FRBuildingGraph.nodeLoadFR` 先拿 `user` 再拿 `fr`，失败即抛错，成功后把 `figure_role`、`figure_name`、`words_figure2user` 等字段从 dict 读取并回写 state/log。
- `integration/utils.py` 删除 `getUserIdByOpenId` 与 `frBelongsToUser` 两个带 DB 访问的方法；`index.py`、`menu.py` 对应替换为 service 返回结构（`res.get(...)`）。
- `buildFigurePersonaMarkdown` 内部统一用 `fr.get(...)` 取字段，并在 `figure_name` 为空时降级标题为“人物画像”，避免空标题。

- 下游影响：
- Lark 消息处理链路（批量发送、菜单切换、消息入口鉴权）现在依赖 service 响应结构，减少 channel 层绕过 service 的概率，便于后续切到 dispatcher/远程 service。
- Graph 输出仍保持原状态字段形状（`figure_and_relation`、`user_name`、`logs` 等），因此下游节点消费面基本不变；但因为加载逻辑从 ORM 切到 dict，后续新增字段要同步 service 返回 include 列表。
- 文档消费侧（README、架构文档）与当前实现更对齐，能直接作为后续改造和 review 的事实基线。

### 改动结果与业务影响

- 当前看，核心收益是“链路一致性”提升：Graph / Lark / CLI 的身份与 FR 查询入口向 service 收敛，减少重复实现和跨层 DB 访问。
- 这也给后续能力（共享数据库模式、dispatcher 分流、权限治理）打了地基，因为调用方已经逐步从“拿 ORM 实体直接操作”迁移到“消费 service 返回协议”。
- 代价是返回值语义更依赖约定（大量 `.get(...)`），如果 service 返回字段不完整，调用侧会静默拿到 `None`，需要更多契约验证与回归测试兜底。

### 风险与待办

- 已知风险：`buildFigurePersonaMarkdown` 入参类型切换后，若仍有旧调用传 ORM 对象，会在运行时出现字段读取偏差；当前 diff 中已覆盖主要调用点，但仍建议做一次全局检索回归。
- 已知风险：Lark 集成链路改为 `dict` 协议后，错误码与空值分支主要靠调用侧判断，建议补一层统一错误处理工具，避免各处 `res.get(...)` 分散。
- 未验证项：本次没有看到针对 Graph/Lark/CLI 的自动化回归新增，建议至少补三类验证：`open_id -> user_id` 查找失败分支、`fr` 归属校验分支、Graph 节点加载失败分支。
- 后续动作：继续把剩余“非 service 层 DB 访问”做清点；并基于新加的 skill 资产在每次提交前固定执行“diff 质检 + 更新记录追加”。

### 建议 Commit Message（git-cz）

- `refactor(service): align graph and lark flows with service-only data access`
