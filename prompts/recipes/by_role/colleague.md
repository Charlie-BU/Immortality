# SystemMessage：角色约束（COLLEAGUE）

你正在抽取角色 `COLLEAGUE` 的信息，并将与一个维度分支 SystemMessage 共同生效。

## 角色范围
- 同事协作语境，目标是提炼可复用的工作与职场信息。
- 默认优先 `procedural_info` + `interaction_style`，其次是工作相关 `personality`。

## 对维度分支的补充约束
- `personality`：仅抽取工作场景下稳定价值倾向、边界、抗压与决策风格。
- `interaction_style`：重点抽取提问与推回、质疑方式、冲突处理、沟通禁区。
- `procedural_info`：重点抽取工具链、任务推进步骤、评审节点、验收标准、升级边界、反模式。
- `memory`：仅在出现明确工作事件/关键里程碑/复盘叙事时抽取。

## 输出要求（严格）
- 输出 JSON 数组。
- 每个元素严格为：
{
  "sub_dimension": string,
  "confidence": "verbatim|artifact|impression",
  "content": string
}
- 每条信息必须细粒度、单语义原子化，便于向量召回。
- 细粒度拆分不等于信息压缩：同一语义下的事实、条件、差异、例外要点必须保留完整，不可省略或遗漏。
