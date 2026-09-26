# 场景胶囊编写约束

修改本目录前，必须先阅读根目录的 [`内容撰写指南.md`](../内容撰写指南.md)。

## 当前运行时模型

当前小安 chatflow 不是可自主调用工具的 Agent。每轮严格按以下顺序执行：

```text
Safety Scan -> Router 选择恰好一个胶囊 -> 回答模型生成回复
```

- Safety Scan 在普通胶囊路由之前处理明确的即时危险。
- Router 在回答模型运行之前，从全部候选中选择一个胶囊。
- 回答模型只收到已经选中的胶囊内容，不会看到胶囊目录或其他胶囊。
- 回答模型没有加载、调用、切换或跳转到其他胶囊的工具。
- 胶囊文案不能创建状态机、计时器、主动追发、外部联络或人工转接能力。

## 编辑后测试指定胶囊

编辑某个胶囊后，应使用本地隔离测试 CLI 查看它实际生成的回复。从仓库根目录运行：

```bash
.venv/bin/python tech/chatflow/poc/capsule_test.py --capsule n5p
```

将 `n5p` 换成当前胶囊 id。该工具每轮重新读取文件并强制使用指定胶囊，但会跳过
Safety Classifier 和 Router。只能输入合成案例；不能用隔离测试证明正式 Router 会选中
该胶囊。安装、单条测试、模型配置、输出说明和完整限制见
[`test/README.md`](../../test/README.md)。

## 字段职责

- `triggers`：供 Router 召回候选胶囊。
- `use_when`：供 Router 判断本胶囊何时适用。
- `do_not_use_when`：只描述本胶囊不适用的条件。不得写目标胶囊或“转向、调用、加载、切换”等执行动作。
- `render_policy`：只约束回答模型如何组织和表达当前已提供的素材，不控制 `ground` 加载。
- `recognize`、`act`、`scripts`、`ground`：是已选中胶囊提供给回答模型的本轮内容素材。
- `related_capsules`：仅供编辑者理解内容关系，不参与运行时路由。

## 胶囊引用 Wiki 时的 `source_roles`

`source_roles` 是 Wiki 节点用来说明“某个来源在本节点中承担什么作用”的受控词表。
权威定义和效力规则见 [`content/knowledge/AGENTS.md`](../knowledge/AGENTS.md)；
如两处说明不一致，以该文件为准。

| `source_role` | 中文含义 | 胶囊中适合引用的内容 | 能否单独支撑当前法律结论 |
| --- | --- | --- | --- |
| `legal_basis` | 法源／请求权基础 | 现行权利、义务、构成要件、程序、救济及法律后果 | **可以；这是唯一承重角色** |
| `doctrinal_foundation` | 法理／学理渊源 | 概念形成、理论解释或立法历史背景 | 不可以 |
| `authoritative_commentary` | 权威解读 | 权威主体对法条含义、立法目的或适用边界的说明 | 不可以 |
| `institutional_implementation` | 机关实施 | 机关内部如何落实规则的流程、分工或操作做法 | 不可以 |
| `case_application` | 案例适用 | 规则在具体案件中的认定、证据评价和裁判结果 | 不可以，也不能据此保证个案结果 |
| `empirical_findings` | 实证观察 | 调研、统计或监测发现及其时间、样本和方法边界 | 不可以，也不能直接外推为普遍规则 |

新版 Wiki 节点不再使用旧的 `legal_basis`／`practice_basis` 二分法：
`legal_basis` 是上述六类角色之一，`practice_basis` 不是节点的 `source_role`。
不要把旧二分法写成新版 Wiki 的来源分类。

### 胶囊 `ground` 格式

当前 runtime 按本轮用户情况执行 `if + node + source_roles`。同一个胶囊可以在不同条件下，
从同一 node 或不同 node 展开不同角色：

```markdown
# ground

- if: 用户询问哪些行为在现行法上构成家庭暴力
  node: domestic-violence-scope
  source_roles:
    - legal_basis

- if: 用户询问为什么控制、隐蔽和反复性是识别家暴的重要特征
  node: domestic-violence-scope
  source_roles:
    - legal_basis
    - authoritative_commentary
    - doctrinal_foundation

- if: 用户询问法院在类似案件中如何认定家庭暴力
  node: domestic-violence-scope
  source_roles:
    - legal_basis
    - case_application

- if: 用户询问妇联接案后通常如何进行风险评估和转介
  node: local-intake-risk-assessment-and-referral
  source_roles:
    - legal_basis
    - institutional_implementation
```

- `if` 描述本轮用户问题必须满足的语义条件；不能写成要求回答模型自行跳转胶囊或调用工具。
- 地方规则的 `if` 必须明确写出法域；只有当前或既往用户消息已经确认该法域时，
  运行时才允许命中该分支。
- `node` 使用 `content/knowledge/wiki/nodes/` 下的 node id。
- `source_roles` 只能从上表六类中选择；不要为了凑齐六类而全部填写。
- 每个分支必须严格使用上例的同级 `if`、`node`、`source_roles`；不得写成嵌套的
  `- node`／`- source_roles`，loader 会将格式错误作为失败。
- runtime 只展开命中分支中，该 node 在指定 `source_roles` 下列出的 `source_refs`；
  不展开未指定角色的来源片段。
- 多个分支同时命中时，合并并去重它们的 node、role 和 `source_refs`；条件应尽量互斥，
  避免无意加载过多上下文。没有分支命中时，不展开 source 片段。
- 在线运行时由与 Router 同级的结构化 LLM 选择器判断分支，离线测试使用确定性轻量匹配；
  两种模式最多选择3个分支。解析后的完整条文按项装入最多8000字符的 Ground 预算，超出
  预算的完整条目会被省略并写入 debug warning，不会截断法条；预算顺序优先保留命中
  node、`legal_basis` 和直接案例，再装入实施、解读、学理与实证背景。
- 条件分支本身不发送给回答模型；回答模型只收到命中分支解析出的 node 正文和来源片段。
- 只要胶囊要表达当前法律规则、权利、义务、程序、要件或救济，对应 node 就必须选择
  `legal_basis`；其他五类不能替代它。
- 案例、实施做法和实证材料按实际需要选择，并保留其非承重边界。
- 本目标格式只使用 `if`、`node`、`source_roles`；不要再新增 `when`、`load`、
  `role_filter` 等同义字段。

## 禁止写入胶囊的能力

不要写：

- “转向 N2”“调用 N5p”“跳出本胶囊进入 NC”
- “进入或退出 Crisis 状态”
- “首次进入时”“连续两轮后”“反复命中时”
- “稍后主动跟进”“转接真人”
- 任何当前运行时代码尚未实现的工具、状态或工作流

如果内容需求确实依赖上述能力，应将其记录为运行时需求，明确负责组件、状态字段和测试；在代码实现前，不得把它描述成胶囊已经能够执行的行为。

## 提交前检查

- 每条规则是否只依赖当前选中的一个胶囊？
- `do_not_use_when` 是否只有排除条件，没有去向？
- `render_policy` 是否只包含 `ground` 加载策略？
- 即时危险是否交给 Safety Scan，而不是普通胶囊自行切换 Crisis？
- 文案是否暗示了不存在的工具、记忆或外部行动能力？
