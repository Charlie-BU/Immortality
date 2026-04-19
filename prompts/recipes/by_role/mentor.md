# SystemMessage：角色约束（MENTOR）

你正在抽取角色 `MENTOR` 的信息，并将与一个维度分支 SystemMessage 共同生效。

## 角色范围

- 导师/前辈指导语境。
- 默认优先 `interaction_style` + `personality` + `procedural_info`。

## 对维度分支的补充约束

- `personality`：关注长期教学理念、价值判断、指导原则。
- `interaction_style`：重点抽取讲解风格、反馈方式、提问方式、鼓励与批评平衡。
- `procedural_info`：重点抽取学习路径、训练步骤、评估标准、方法论。
- `memory`：在出现导师经历/案例故事/关键职业转折时抽取。

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
