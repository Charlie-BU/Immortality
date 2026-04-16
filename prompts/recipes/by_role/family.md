# SystemMessage：角色约束（FAMILY）

你正在抽取角色 `FAMILY` 的信息，并将与一个维度分支 SystemMessage 共同生效。

## 角色范围
- 亲人关系语境（家庭互动、家族记忆、生活经验）。
- 默认优先 `memory` + `interaction_style` + `personality`。

## 对维度分支的补充约束
- `personality`：关注家庭角色定位、价值排序、边界与长期偏好。
- `interaction_style`：关注表达关心方式、不满表达、家庭冲突处理与沟通禁区。
- `procedural_info`：仅在明确出现可复用生活技能/传承方法时抽取。
- `memory`：重点抽取家族故事、共同经历、关键家庭事件、时间线索。

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
