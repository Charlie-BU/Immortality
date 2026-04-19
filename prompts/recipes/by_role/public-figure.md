# SystemMessage：角色约束（PUBLIC_FIGURE）

你正在抽取角色 `PUBLIC_FIGURE` 的信息，并将与一个维度分支 SystemMessage 共同生效。

## 角色范围

- 仅处理公开材料中的信息。
- 默认优先 `interaction_style` + `personality` + `procedural_info`，并在出现公开叙事时抽取 `memory`。

## 对维度分支的补充约束

- `personality`：仅抽取公开表达中可证据化的稳定价值观与原则。
- `interaction_style`：重点抽取公开问答、公开回应、公开表达风格。
- `procedural_info`：重点抽取公开方法论、流程、决策框架、工具实践。
- `memory`：仅抽取公开可追溯的人生事件、关键转折与时间线索。

## 输出要求（严格）

- 产出不是文件，不是 Markdown，只能输出 JSON 数组。
- 每个元素严格为：
  {
  "sub_dimension": string,
  "confidence": "verbatim|artifact|impression",
  "content": string
  }
- 每条信息必须按“同一语境（主题/阶段/对象）”聚合，避免单句级机械拆分，便于后续召回。
- 语境聚合不等于信息压缩：同一语境下的事实、条件、差异、例外要点必须在单条中保留完整，不可省略或遗漏。
- 仅在语境明显切换时才拆分（如主题切换、阶段跳变、对象变化、策略冲突）。
