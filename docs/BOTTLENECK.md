## 单一飞书 Bot 问题

### 问题

目前用户通过 `pip` 或 `uv` 安装 `immortality` 后，会在本地 HOME 目录创建 `.immortality`，其中包含 `.env` 等用户配置。  
现有实现基于单组环境变量（`LARK_APP_ID`、`LARK_APP_SECRET`、`LARK_CARD_TEMPLATE_ID`），因此 `immortality lark-service start` 每次只能启动一个 Bot 的 websocket 服务。  
当用户拥有多个飞书 Bot 且希望按需切换启动时，当前机制无法满足。

### 长期方案

将单 Bot 环境变量改为“列表化配置”，例如 `bots.yaml` / `bots.json` 或 `.immortality/bots/*.env`。  
CLI 明确支持按需选择：

- `immortality lark-service start --bot <name>`
- `immortality lark-service start --all`

# 共享数据库问题

## 问题

当前系统里，用户通过 `pip install`（或 `uv tool install`）安装 CLI 后，仍需要完成一系列前置配置（数据库创建、模型配置、飞书机器人配置等），最终才能通过 CLI 在本地/服务器启动飞书 WebSocket 服务，再通过飞书机器人与系统交互。

这个链路的心智成本非常高。  
我的目标是大量简化前期配置逻辑，让用户快速上手，从而提高整体投入意愿。

## 我尝试的切入点：共享数据库

我先从数据库入手：希望让用户的 CLI 直接连接我个人维护的 PostgreSQL 共享库，这样用户就不需要自己建库。

但一个核心安全前提是：我不能直接暴露数据库 `URI`（尤其是密码）。  
否则用户一旦拿到 URI，就可以在我的数据库上进行任意 CRUD 等高危操作。

## 已做的架构重构（当时方案）

我的思路是：`service` 层本身就是直接操作数据库的方法集合，可以再封装一层路由，通过 Web 框架暴露 HTTP 接口并上线，供用户调用。

基于这个方向，我做了如下重构：

1. 新增 `ServiceDispatcher` 模块。
    - 通过 `SERVICE_API_MAP` 将 `service` 方法与 HTTP 路由、请求方式、是否鉴权做映射。
    - 实现 `dispatchServiceCall`：根据是否启用共享数据库模式（环境变量 `USE_SHARED_DATABASE=True`），分发到本地 service（原逻辑）或远程 API。

2. 全面替换调用入口。
    - 把工程内所有消费 `service` 方法的地方，统一改为调用 `dispatchServiceCall`。
    - 覆盖范围包括 CLI、飞书服务集成、Graph。

3. 清理数据库耦合点。
    - 在改造过程中发现大量直接数据库耦合，例如 `with session() as db:`。
    - 对这些点统一处理为两类：
        - 若现有 service 可复用：直接改为 `dispatchServiceCall`。
        - 若现有 service 不可复用：下沉到新 service，同时补充路由并更新 `SERVICE_API_MAP`。
    - 最终目标是：**所有数据库操作必须在 service 层完成，其他位置不允许与数据库直接耦合。**

## 关键问题进展

在这轮重构里，我遇到过两个关键问题。现在回头看，它们都已经有了可落地的处理方式，但最终落地形态和我当时设想的不完全一样。

### 1) 登录态有效期与 Graph 稳定性冲突（已解决）

用户在 CLI 登录后，本地会保存登录态 `token`。而在安全前提下，大部分 API（包括 Graph 工作流中涉及数据库操作的 service，在 `USE_SHARED_DATABASE` 场景下即 API 调用）都需要鉴权。

问题在于：只要共享数据库模式依赖远程 API，Graph 在飞书机器人里运行时就必须持续拿到有效 token；一旦 token 过期，整条链路都会失败。

最终落地时，我没有把“仅凭飞书 `open_id` 登录”开放成远程 API，而是改成了下面这套更收敛的方案：

- 远端 `user/login` 在共享数据库模式下返回不过期 token。
- CLI 本地 session 通过 `getUserIdByAccessToken` 做有效性校验。
- 飞书机器人链路在共享数据库模式下不再尝试通过 `open_id` 自动续登；如果本地 session 不存在或失效，直接提示用户重新通过 CLI 登录。

这样做的结果是：共享数据库模式下不需要把 `userLoginByOpenId` 暴露出去，安全边界更清晰；代价是用户一旦本地 session 丢失，仍需要手动重新登录一次。

### 2) `ConversationGraph` 的 checkpointer 无法通过 API 抽象（已绕开）

`ConversationGraph` 的短期记忆原本依赖 PostgreSQL checkpointer。  
这里不是普通 service 调数据库，而是 `langgraph` 直接根据数据库 `URI` 构造 `checkpointer`。这意味着它天然没法像普通 service 一样被 `dispatchServiceCall` 分流到远程 HTTP API。

这个问题最后不是“继续抽象”，而是直接换了一条路：

- 非共享数据库模式下，`ConversationGraph` 继续使用 PostgreSQL checkpointer。
- 共享数据库模式下，`ConversationGraph` 不再尝试获取远程 checkpointer，而是直接降级为 `InMemorySaver`。

这等于承认一个事实：**checkpointer 这层并不适合远程 API 化。**  
我最后选择接受共享数据库模式下的短期记忆退化，用进程内内存态替代数据库持久化，从而把“必须在本地暴露数据库 URI”这个硬限制彻底拿掉。

代价也很明确：

- 共享数据库模式下，短期记忆只在当前进程内有效。
- 飞书服务或本地进程重启后，这部分 memory 会丢失，不能像原来那样持久化在 PostgreSQL 里。

## 当前结论

到 `feature/shared-db-support` 这个分支为止，共享数据库模式的主链路已经基本打通了。更准确地说，数据库侧的接入复杂度已经被明显压下来了，但模型侧和服务归属侧还没有完全收口，所以它现在仍然是一个“内部已跑通、暂不开放给用户”的方案。也正因为如此，当前 CLI 已经把 `setup` 里的 `easy mode` 入口先隐藏掉了，不再作为默认可选项直接提供给用户。

当前实际已经落地的部分如下：

1. 模式切换已经成型。
    - 整个系统现在以 `USE_SHARED_DATABASE=True` 作为共享数据库模式开关。
    - `easy mode` 这套配置语义和底层分支逻辑已经实现过：在共享数据库模式下，不再要求用户配置本地 `DATABASE_URI` 和 `CHECKPOINT_DATABASE_URI`。
    - 但当前 CLI 已经暂时隐藏 `setup` 里的 `easy mode` 选项，不再把它作为可直接选择的公开入口。
    - CLI `doctor` 也补上了共享模式分支：本地库检查被替换为对 `HTTP_BASE_URL/ping` 的连通性检查。

2. 服务端承接了原本需要直连数据库的大部分能力。
    - 新增了独立的服务端入口和 Robyn 路由层。
    - 已经落地的 router 覆盖 `user`、`figure_and_relation`、`fine_grained_feed`、`knowledge` 这几类核心 service。
    - 路由层统一负责参数解析、鉴权、调用既有 service，并继续让数据库操作留在服务端完成。

3. 客户端侧已经形成统一 dispatcher。
    - 新增 `ServiceDispatcher` 模块和 `SERVICE_API_MAP`。
    - `dispatchServiceCall` 会根据当前模式自动选择“本地直接调 service”还是“走远端 HTTP API”。
    - 参数透传、枚举/时间等值的序列化、鉴权请求头注入，已经在 dispatcher 里做了统一处理。

4. 主要消费入口已经切到 dispatcher。
    - CLI 的鉴权、FR 管理、部分初始化与自检逻辑，已经按共享模式做了分流。
    - 飞书消息处理链路里，和用户、FR 归属校验相关的数据库访问，已经改为走 dispatcher。
    - `ConversationGraph` 和 `FRBuildingGraph` 中原本直接消费 service 的地方，也已经统一改成 `dispatchServiceCall`。

5. 共享模式下最难绕的 Graph 瓶颈已经被规避掉。
    - `ConversationGraph` 编译时会根据模式选择 checkpointer 实现。
    - 本地模式继续走 PostgreSQL checkpointer。
    - 共享数据库模式直接退化为 `InMemorySaver`，从而不再需要在用户本地暴露共享数据库 `URI`。
    - `lark-service start` 在共享模式下也不会再初始化本地数据库。

6. 登录态链路已经调整为共享模式可运行的形态。
    - 远端登录接口返回不过期 token，避免 Graph 执行期间频繁撞上 token 过期。
    - 本地 session 校验已经能够通过远端鉴权接口完成。
    - 出于安全考虑，`userLoginByOpenId` 仍然只允许留在本地内部场景使用，没有作为共享模式通用 API 暴露出去。

这套方案的核心含义其实已经比较明确了：  
**我已经把“用户必须自己建 PostgreSQL 才能跑起来”这件事拆掉了。**  
在共享数据库模式下，数据库相关 CRUD 和检索已经基本可以全部收敛到服务端，由本地 CLI / 飞书服务 / Graph 通过 dispatcher 透明消费。

但这不代表共享数据库模式已经可以对外开放。现在还剩下两类没有解决的问题：

1. 服务端 `ark_client` 依赖环境变量 `EMBEDDING_MODEL`，这部分目前无法从用户侧透传。
2. `syncFeedsToFRCore` 和 `syncAllFeedsToFRCore` 需要调用模型服务；一旦它们在服务端执行，就只能消费服务端自己的模型配置，无法消费用户侧的 `access_token` 和模型环境变量，这和我希望的“能力共享、配置仍归用户”并不一致。

所以，当前最准确的结论不是“共享数据库模式已经完全做完”，而是：

- 数据库问题本身已经基本被解决。
- 共享数据库模式的技术底座已经落地，主链路也已经跑通。
- 但 `setup` 侧的 `easy mode` 入口目前已被隐藏，现阶段不会直接引导用户走这条链路。
- 但模型依赖和服务端代执行的边界还没处理干净。
- 基于这些剩余问题，**当前共享数据库模式暂不开放给用户使用**。
