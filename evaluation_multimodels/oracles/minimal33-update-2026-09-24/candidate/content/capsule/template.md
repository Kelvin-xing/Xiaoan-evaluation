---
capsule_name: 
status: draft
author: 
---

# triggers

- list
- list

# applicability

## use_when

- list
- list

## do_not_use_when

<!--
只写本胶囊不适用的条件。
不要写目标胶囊，也不要写“转向/调用/加载/切换到 N2、N5p、NC”等执行动作。
Router 会在回答模型运行前独立选择一个胶囊。
-->
- list
- list

# render_policy

<!--
只写回答模型如何选择、组织和表达本轮已提供素材。
Ground 加载由编排层独立判断，不在这里写 ground 或 ground_triggers。
不要写跨胶囊跳转、Crisis 状态、首次进入、反复命中或其他未实现的工作流。
-->
- list

# recognize

- list
- list

# act
<!-- 可以使用有序列表表示有步骤先后的行动；如果有不同选项，可以使用二级标题-->
- list
- list

## scripts
<!-- 提供1到2句话术模板 列表形式，用引号包裹的句子（optional）-->
- list
- list

# ground

<!--
严格使用 if + node + source_roles；三个字段同级，不增加字段。
source_roles 只能使用 AGENTS.md 中的六类受控词。
没有法律 Ground 时保留空的 # ground 分区。
-->
- if: 用户询问与本胶囊直接相关的法律规则
  node: node-id
  source_roles:
    - legal_basis

# related_capsules
<!--
仅供编辑者理解内容关系，不参与运行时路由。
列表形式，使用稳定的胶囊 id；不能据此要求当前胶囊调用或切换到其他胶囊。
-->
- list
- list
