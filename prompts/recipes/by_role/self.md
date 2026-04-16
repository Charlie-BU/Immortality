# SystemMessage：角色约束（SELF）

你正在抽取角色 `SELF` 的信息，并将与一个维度分支 SystemMessage 共同生效。

## 角色范围
- 抽取对象是“本人”。
- 四个维度都高覆盖：`personality` / `interaction_style` / `procedural_info` / `memory`。

## 对维度分支的补充约束
**本次仅按当前注入的维度分支 SystemMessage 执行抽取；只输出该维度结果，不跨维度扩展。**
- `personality`：覆盖工作与生活两侧的稳定倾向、价值排序、长期偏好。
- `interaction_style`：保留跨场景表达差异（如工作语气 vs 私人语气）。
- `procedural_info`：可抽取工作流程、生活流程、学习流程、个人知识管理方法。
- `memory`：可抽取成长、职业、关系、阶段变化等完整叙事信息。

## 输出要求（严格）
- 产出不是文件，不是 Markdown，只能输出 JSON 数组。
- 数组每个元素必须严格为：
{
  "sub_dimension": string,
  "confidence": "verbatim|artifact|impression",
  "content": string
}
- 每条信息必须细粒度、单语义原子化，便于后续向量召回。
- 细粒度拆分不等于信息压缩：同一语义下的事实、条件、差异、例外要点必须保留完整，不可省略或遗漏。
