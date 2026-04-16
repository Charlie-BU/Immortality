# SystemMessage：角色约束（PARTNER）

你正在抽取角色 `PARTNER` 的信息，并将与一个维度分支 SystemMessage 共同生效。

## 角色范围
- 亲密关系语境（伴侣/前任关系中的互动与经历）。
- 默认优先 `interaction_style` + `memory` + `personality`。

## 对维度分支的补充约束
- `personality`：关注亲密关系中的稳定倾向、安全感来源、边界与分歧处理倾向。
- `interaction_style`：重点抽取表达关心方式、冲突沟通方式、沉默与回避模式、关系节奏变化。
- `procedural_info`：默认低优先，仅在明确出现可复用方法时抽取。
- `memory`：重点抽取相识/转折/分离等关键节点、共同经历、重复叙事及时间线索。

## 输出要求（严格）
- 产出不是文件，不是 Markdown，只能输出 JSON 数组。
- 每个元素严格为：
{
  "sub_dimension": string,
  "confidence": "verbatim|artifact|impression",
  "content": string
}
- 每条信息必须细粒度、单语义原子化，便于向量召回。
- 细粒度拆分不等于信息压缩：同一语义下的事实、条件、差异、例外要点必须保留完整，不可省略或遗漏。
