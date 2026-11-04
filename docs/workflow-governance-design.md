# Houdini MCP 工作流钳制与经验闭环：评估、设计与实施计划

> 状态：设计提案（2026-11-04）。初始盘点基于 `3fa5467`；第 1–2 节保留当时问题背景，阶段 0 的修复见实施进度。2026-11-04 根据 Hair Tangent Baker 成功经验更新 Python 判据，并补充节点输出属性观测计划。下文拟议能力不代表已经实现。
> 本文不改变 AGENTS.md 中的兼容不变量；凡涉及默认行为变化的条目都单独标注【行为变更】，需要明确同意后再落地。

---

## 0. 结论先行

1. **执行层（MCP）整体设计合理且偏稳健**：两进程架构、Typed Registry、`extra=forbid` 参数校验、SideFX DocRef、effect_scope / rollback 元数据、Undo Group、带 revision/idempotency 的 Graph Patch、事务化 HDA 创建，这些都是对的方向。
2. **Agent 偏向 Python 不是"模型不听话"，而是工具表面在结构上鼓励它**：
   - `execute_houdini_code` 是直连工具，`apply_graph_patch` / `get_network_snapshot` 却藏在三跳目录后面（可供性倒置）；
   - `allow_unsafe=true` 由模型自己填，等于没有门；
   - 一批"让结果可被美术修改"的操作（表达式/通道引用、关键帧、控制器 Spare Parm、Network Box、Sticky Note、颜色、插入节点、折叠 Subnet）**根本没有 Typed 能力**，只能走 Python；
   - Atomic Graph Patch 只能编辑"同一 Patch 内新建的节点"，不能原子地修改既有网络。
3. **经验系统（"自回归提升"）目前是开环的**：有宪章、Schema、生命周期和看板，但
   - 没有任何运行期采集（`records/experiences/` 为空），
   - 没有纠错信号来源（不知道美术事后改了什么），
   - Recipe 是散文字符串，不可执行、不可机检，
   - 知识不能从 MCP 访问（只有加载了 Skill 的客户端能读到），
   - 宪章第 10 条要求度量的指标一个都没有被测量。
   它现在是"知识库 + 晋升纪律"，还不是"提升系统"。
4. **建议**：在现有架构上增加一个 **Workflow Governor（钳制层）** 和一个 **Experience Loop（闭环层）**，两者共享一份 **执行日志（Journal）**。核心理念一句话：

   > **交付首先要好用、可调、能复现。** 原生节点无法合理覆盖所需算法时，允许将 Python 封装进 HDA、Python SOP 或显式资产命令。计算逻辑、输入、参数、版本与结果必须可追溯；普通 Cook 与烘焙/导出分别管理。约束针对不可复现的临时状态和越界副作用，不以 Python 用量替代产品质量。

---

## 1. 现状盘点

### 1.1 MCP 表面

| 层 | 内容 |
|---|---|
| Hybrid 直连（11） | `get_scene_info`, `create_node`, `execute_houdini_code`, `connect_nodes`, `set_parameters`, `get_parameter_schema`, `get_geometry_info`, `houdini_ping`, `search_tools`, `get_tool_schema`, `call_tool` |
| Catalog（43） | 场景/节点/图：create/modify/delete/connect/disconnect/flags/layout/find/info；发现：`search_node_types`, `get_node_type_schema`, `get_network_snapshot`；参数：`get_parameter_schema`, `set_parameters`（带 channel 保护）；验证：`find_error_nodes`, `cook_node`；VEX：`create_wrangle`, `set_wrangle_code`；几何：`get_geometry_info/data`；材质：`set_material`, `get_material_assignments`；USD：`get_stage_snapshot`；HIP：`get_hip_info`, `save_hip`；HDA：analyze/search/info/create/interface_patch/validate；批处理：`apply_graph_patch`；渲染 3 项；OPUS 6 项；`execute_houdini_code` |
| Legacy | 上述能力全部直连 |

### 1.2 经验层（`skills/houdini-production-workflows/`）

| 组件 | 现状 |
|---|---|
| `SKILL.md` / `routing.md` / `workflows/*.md` | 8 个工作流的路由与散文流程 |
| `constitution.md` / `experience-lifecycle.md` | 10 条原则、candidate→validated→canonical→deprecated |
| Schema | case / recipe / experience / template-manifest，严格 `additionalProperties:false` |
| Records | 5 个 case（均来自 Project Titan）、8 个 recipe，全部 `candidate`；**0 个 experience** |
| `experience_cli.py` | validate / assess / reindex / dashboard / new-experience（空壳模板） |
| `inspect_houdini_case.py` | Hython 只读摄取 HIP/HDA → candidate case |
| Dashboard | 离线知识图谱，只读展示 |

---

## 2. 合理性评估

### 2.1 做得好的（应保留）

- **分层原则正确**：宪章第 3 条"判断放 Skill、确定性操作放 MCP、可复用结构放模板、可观察真相放验证器"，与 CAPABILITY_TODO 的"MCP 承载事实/验证/边界，模型承载规划/组合"一致。
- **严格校验前置**：Pydantic `extra=forbid` 在 TCP 之前拒绝参数；节点类型与参数从 live `hou` 取，不硬编码。
- **副作用元数据完整**：risk / effect_scope / rollback_strategy / prerequisites / result_size，三态可用性。
- **Graph Patch 的骨架是对的**：dry_run、temp id（`$id`）、revision 校验、idempotency key、失败回滚新建节点。
- **晋升纪律严**：自动摄取一律 candidate，晋升要独立证据，纠错要分类（7 类）——这能防止过拟合，是闭环系统最难补的部分，已经有了。

### 2.2 问题清单（按对"钳制工作流"的影响排序）

#### P1 可供性倒置：错误路径最便宜【严重】

- Hybrid 直连里有 `execute_houdini_code`，但没有 `apply_graph_patch`、`get_network_snapshot`、`search_node_types`、`cook_node`、`find_error_nodes`。
- 一个"建 5 个节点并连线"的任务：Python 是 **1 次调用**；Typed 路径是 `search_tools → get_tool_schema → call_tool(dry_run) → call_tool(apply)` **4 次调用**，或 `create_node`×5 + `connect_nodes`×4 + `set_parameters`×N（直连 `create_node` 还不接受 `parameters`/`position`）。
- LLM 会最小化往返和不确定性，所以它"理性地"选择 Python。**提示词里的"LAST RESORT"无法对抗结构性成本差。**

#### P2 门控是自我授权【严重】

- `allow_unsafe=true` 是模型自己填的布尔值。第一次被拒后模型几乎必然带上它重试，门控只是一次额外往返。
- 没有理由字段、没有代码分类、没有策略配置、没有次数预算、没有记录。

#### P3 Python 执行本身不可追溯、不可撤销【严重】

- `houdinimcp_runtime/server.py` 的 `MUTATING_COMMANDS` 不包含 `execute_code`，**Python 修改不在 Undo Group 里**——恰恰是风险最高的操作最难 Ctrl+Z。
- 执行前后没有网络快照/diff，系统不知道这段 Python 实际改了什么。
- 没有分类：读场景、搭节点图、在图外算几何、写磁盘，四种性质完全不同的 Python 被同等对待。

#### P4 能力缺口直接逼出 Python【高】

"可修改性"在 Houdini 里依赖的那一类操作几乎全部缺失：

| 美术可修改性需要的 | 当前 | HOM 对应 |
|---|---|---|
| 参数表达式 / 通道引用 `ch("../CTRL/seed")` | 无（`set_parameters` 只能写值，HDA 提升内部用到了 `setExpression` 但未开放） | `hou.Parm.setExpression` |
| 关键帧 | 无 | `hou.Parm.setKeyframe` |
| 控制器 Null + Spare Parm | 无 | `hou.Node.addSpareParmTuple` / `ParmTemplateGroup` |
| Wrangle `ch()` 自动生成 Spare Parm | 无 | `vexpressionmenu.createSpareParmsFromChCalls` |
| Network Box / Sticky Note / 颜色 / 注释 | 无 | `createNetworkBox`, `createStickyNote`, `setColor`, `setComment` |
| 在两节点间插入节点 | 无（需 disconnect+connect，atomic 模式禁止） | `setInput` 组合 |
| 折叠为 Subnet | 无 | `collapseIntoSubnet` |
| Multiparm 实例数 / 实例参数 | 无 | `hou.Parm.set` on multiparm count + 实例名 |
| 帧范围 / FPS / 时间 | 无 | `hou.playbar`, `hou.setFps` |
| File Cache / ROP 执行 | 无（TODO 已列） | `hou.RopNode.render` |

这些缺口导致：**即使 Agent 想走正确路径也走不通**，最终只能 Python。而且 Agent 用 Python 时往往"顺手"把能用表达式的地方写成了死值。

#### P5 Graph Patch 原子模式太窄【高】

- Atomic 拒绝 `delete` / `disconnect`，且只允许编辑同一 Patch 内新建的节点。最常见的生产编辑——"在现有链路中插一个节点、改上游参数、调整 Display Flag"——无法原子完成。
- `dry_run` 默认 `true`，每次编辑至少 2 次调用。对 Agent 来说又是成本。

#### P6 经验系统开环【高】——见 2.3

#### P7 知识不可从 MCP 访问【中】

- Recipe/Lesson 只能通过 Skill 文件读到。Claude Desktop、Cursor 等不加载 Skill 的客户端完全看不到。
- FastMCP 构造时没有设置 `instructions`，连最基本的"先建图、后 Python"的服务端级说明都没有。

#### P8 小问题

- 渲染参数默认 `render_path="C:/temp/"`（CAPABILITY_TODO 已列）。
- `search` 是子串全匹配 AND，多词或中文查询召回差；工具数增长后会更明显。
- 非 atomic Patch 失败时保留部分修改，仅依赖外层 Undo Group；响应里应提示"可 Ctrl+Z 一步撤销"。

### 2.3 经验系统专项评估

把它当作一个控制系统来看：**传感器 → 状态估计 → 控制律 → 执行器 → 度量**。

| 环节 | 需要什么 | 现状 | 评价 |
|---|---|---|---|
| 传感器（采集） | 每次调用、每次 Python、每次失败、**美术事后修改** | 无；只有离线 Hython 摄取 HIP | ❌ 缺失 |
| 状态估计（归因） | 把信号归类为：能力缺口 / 可供性缺口 / 配方错误 / 项目惯例 / 一次性 | 有 7 类分类法，但无输入 | ⚠️ 有框架无数据 |
| 控制律（提案） | 聚类重复信号 → 生成具体改进提案（新能力、Patch op、Lint 规则、Recipe 补丁、工具描述） | 无；`assess` 只数证据条数 | ❌ 缺失 |
| 执行器（回灌） | 改进如何在下一次任务中影响 Agent | 只能人工改 Markdown；运行期无注入点 | ❌ 缺失 |
| 度量（验证） | Python 回退率、可编辑性评分、首次验收率、纠错率 | 宪章写了，未测量 | ❌ 缺失 |
| 晋升纪律 | 防过拟合 | 完善 | ✅ |

另外两个结构性问题：

- **Recipe 不可执行**：`stages` 是 `"solve and clean paths"` 这样的字符串；`acceptance` 是 `"paths remain in the allowed region"` 这样的散文。系统无法自动判定一次执行是否满足 Recipe，于是"validated/canonical"永远只能靠人工判断，晋升链路实际不会转动。
- **证据单一**：8 个 recipe 全部来自同一项目，且 case 本身 `acceptance.verified=false`。`assess` 要求 ≥2 个独立 case，这条规则是对的，但没有数据入口时它只会让所有 recipe 永远停在 candidate。

**结论：现在缺的不是更多 Schema，而是"传感器"和"执行器"。**

---

## 3. Houdini 视角：什么叫"符合工作流"

钳制的对象必须先定义清楚。以下是这份设计采用的判据。

### 3.1 可修改性的七条可检测标准

以下为交付检查维度；结合产品契约验收，不以单一节点形态或语言判定合格：

1. **逻辑有归属**：程序化几何可由网络与持久化算法重新 Cook；纹理烘焙/导出可由资产显式命令及已记录输入、参数、版本重新生成。HDA 内嵌 PythonModule 是有效归属；有来源与重建路径的缓存、Stash 或外部产物不因其形态被判错。
2. **控制集中**：用户可能想调的量（数量、尺度、种子、密度、阈值）集中在一个控制节点（Controller Null / HDA 接口）上，下游通过 `ch()` 相对引用，而不是散落在各节点的死值。
3. **VEX 参数化**：Wrangle 中的魔法数字通过 `ch("name")` 暴露为 Spare Parm。
4. **输出契约明确**：每个阶段有命名的 `OUT_*` Null；Display/Render Flag 在终端节点；输出几何满足 `geometry-contracts.md` 中的属性契约。
5. **可读**：关键节点有语义名（不是 `attribwrangle7`）；按阶段用 Network Box 分组；非显然处有 Sticky Note 或 Comment。
6. **可复现**：所有随机节点暴露 seed；没有对偶然点序的依赖；路径用 `$HIP`/`$JOB`，不硬编码盘符。
7. **成本可控**：昂贵分支（Sim、Remesh、大量 Copy）前有 Cache 边界或默认 Bypass；无意外的时间依赖。

这七条中的结构条件可由 `lint_network` 辅助机检；好用程度需用户反馈，可调行为与可复现性需实际参数测试、重开及输出契约验证。不能把静态 lint 通过等同于完整验收。

### 3.2 Python 的合理位置

Python 在 Houdini 里本来就是一等公民，问题从来不是"用没用 Python"，而是"Python 住在哪里、产出是什么"：

| 用法 | 产出 | 是否符合工作流 | 处理策略 |
|---|---|---|---|
| 只读查询（遍历节点、读参数、统计） | 信息 | ✅ 但通常有 Typed 等价物 | 允许；提示等价工具；累计到"可供性缺口" |
| 用 `hou` 搭节点图（createNode/setInput/parm.set） | 一张网络 | 有记录、差异与回滚时可接受 | 有合适 Typed 能力时优先使用；缺口下允许有范围的 Python 构建并记录 diff |
| 几何算法与缓存（`hou.Geometry` 等） | 几何或中间数据 | 取决于算法归属、重建路径及副作用 | 原生算法缺口下允许持久化的 Python 实现；仅在结果依赖丢失的临时状态、没有重建路径时阻止交付 |
| Python SOP / HDA PythonModule / 参数回调 / PDG Python Processor | 参数化资产 | 可调、可复现且成本明确时符合 | 原生无合适等价算法时为合理实现；保留源码/依赖版本、参数接口和验收 |
| 读外部数据（CSV/JSON/表） | 图内数据 | ✅ 应在图内 | 优先 Table Import / Attribute from File / Python SOP |
| 文件/进程/网络副作用（写文件、进程、HIP/HDA 操作） | 磁盘/外部状态 | 取决于已授权的 effect_scope | 已授权的显式烘焙/导出可执行，记录目标与失败处理；越界或覆盖未知目标才要求补足授权。优先合适 Typed 能力 |
| 批量管线操作（批量重命名、路径重定向） | 场景元数据 | ⚠️ 合理的一次性需求 | 允许但需理由；若重复出现 → 晋升为 Catalog 能力 |

**选择顺序**：检查目标版本实际可用的原生节点/合理节点组合与 Typed 能力 → 识别算法缺口或工具封装缺口 → 选择可维护实现 → 用产品验收证明结果。不要求为降低 Python 比例把合理算法拆成难以维护的节点网络；也不把“Agent 不熟悉某节点”认定为原生缺失。

### 3.3 成功经验反馈：Hair Tangent Baker 2.11

用户于 2026-11-04 明确认可这次 HDA 交付成功，并补充：**此次接受 Python 的核心是所需算法没有合适的 Houdini 原生对应节点；评价重点是 HDA 好用、可调、能复现。** 这是该项目的选型依据，不代表已穷举所有 Houdini 版本或第三方节点。

案例：[Hair Tangent Baker](../skills/houdini-production-workflows/references/cases/hair-tangent-baker.md)；经验：`exp-hair-tangent-baker-2-11-success`；候选方法：`hda-authoring-v1`。

- 已审阅设计包含嵌入式模块、原生参数/Ramp、SOP 计算、显式烘焙、临时批次成功后发布、原输入与结果分离。
- 已有 2.11.0 报告支持默认行为、参数响应、UV/Mikk 与重开等范围内验收；本轮没有重跑资产。2.4.0 standalone 报告与历史便携报告不能直接证明最新开发包。
- 将“原生算法缺口”与“MCP 未封装已有原生能力”分开：前者支持合理 Python 算法，后者优先改善工具可供性。
- 成功经验不自动升级为跨项目通用规范。当前 Case/Experience/Recipe 属于同一证据来源，保留候选成熟度及接缝、毛流、Unreal 验收等边界。
- 后续查询相关案例时，应返回这个选型理由及产品验收条件，不能只返回“减少 Python”。

---

## 4. 设计

### 4.1 总体架构

```
                    ┌────────────────────────── Agent ──────────────────────────┐
                    │   begin_task ─► guidance(recipe, contracts, lessons)       │
                    │   snapshot ─► apply_graph_patch ─► lint/validate ─► end_task│
                    └───────────────┬────────────────────────────────▲──────────┘
                                    │ MCP stdio                      │ lessons / proposals
┌──────────────────── Bridge (外部进程) ─────────────────────────────┼──────────┐
│ A. 表面重塑   直连集合 = 快照+Patch+校验；Python 仅 Catalog           │          │
│ B. Python 网关 AST 分类 → 策略矩阵(strict/guided/permissive) → 决策   │          │
│ F. 知识服务   get_workflow_guidance / get_recipe / lessons 注入        │          │
│ D. Journal    每次调用一行 JSONL（工具/参数摘要/结果/revision/分类）  ──┼──► E.  │
└───────────────┬───────────────────────────────────────────────────────┘   经验闭环
                │ TCP（协议不变，仅新增命令）                                  ingest → mine
┌───────────────▼──────── Houdini Runtime ───────────────────────────────┐  → proposals
│ execute_code 进 Undo Group + 前后快照 diff                             │  → 评审/测试
│ 节点归属标记 userData["mcp:op"]；事件回调捕获"人工修改"                │  → 晋升/回灌
│ C. lint_network / validate_contracts（只读）                            │
│ Graph Patch v2（Undo 级原子回滚 + 可编辑性 op）                        │
└─────────────────────────────────────────────────────────────────────────┘
```

钳制分为四种力度，从软到硬：**让正确路径更便宜（A）→ 运行期即时纠偏（B、F）→ 结果机检（C）→ 闭环迭代（D、E）**。只靠最硬的"禁止"会让 Agent 卡死；只靠最软的提示词又压不住。四层叠加才稳定。

### 4.2 层 A：可供性重塑（让正确路径最便宜）

1. **调整 Hybrid 直连集合**【行为变更】
   - 移出：`execute_houdini_code`（Legacy 模式保持不变；Hybrid 下仍可经 `call_tool` 调用，受网关约束）。
   - 移入：`get_network_snapshot`、`apply_graph_patch`、`search_node_types`、`check_network`（= cook + 错误/警告 + 可选 lint 的组合只读调用）。
   - 直连 `create_node` 补上 `parameters` / `position`（Catalog 版已有，直连版缺失）。
2. **Graph Patch 单次调用模式**：保留 `dry_run=true` 默认以兼容，新增 `mode="validate_then_apply"`——内部先做静态校验，通过则直接应用并返回 revision；失败则返回校验错误且不修改。Agent 一次调用完成"计划+执行"。
3. **服务端 instructions**：在 `FastMCP(...)` 设置 `instructions`，十行以内写清：先快照、用 Graph Patch 建图、控制集中、VEX 用 `ch()`、合理 Python 算法须记录原生替代评估、资产归属与验收；临时任意代码须说明范围。这对所有 MCP 客户端生效，不依赖 Skill 加载。
4. **错误响应即教学**：Typed 能力报错时，在 `error` 信封里附带 `suggestions`（已有节点类型建议的机制可扩展）和匹配的 `lessons`（见 4.7），减少"报错一次就转 Python"。

### 4.3 层 B：Python 策略网关

**位置**：Bridge 侧（纯 Python `ast`，不依赖 `hou`，可单测），在 TCP 发送前执行；Runtime 侧补 Undo Group 与 diff。

**接口变更**（Catalog 版 `execute_houdini_code`）：

```jsonc
{
  "code": "...",
  "intent": "批量把 /obj/geo1 下所有 file SOP 的路径改为 $HIP 相对路径",
  "justification": {
    "category": "batch_metadata",        // read_only | graph_build | batch_metadata | in_graph_python | native_algorithm_gap | asset_task | other
    "typed_alternatives_considered": ["set_parameters", "apply_graph_patch"],
    "why_insufficient": "需要对 120 个节点按正则改写，Patch 单次上限 100 且需先遍历"
  },
  "allow_unsafe": true
}
```

**AST 分类器**（保守、可解释，未知即升级）：

| 类别 | 判定特征（示例） |
|---|---|
| `READ` | 仅出现 `hou.node/.nodes/.parm().eval/.geometry()` 的只读方法、`print` |
| `GRAPH_BUILD` | `createNode`, `setInput`, `parm(...).set`, `setDisplayFlag`, `destroy`, `setName`, `moveToGoodPosition` |
| `GEO_COMPUTE` | `hou.Geometry()`、`createPoint/createPolygon/addAttrib/setAttribValue/setPointFloatAttribValues`、`setHardLocked`、`stash` 相关 |
| `SIDE_EFFECT` | `import os/subprocess/shutil/socket/requests`、`open(..., "w")`、`hou.hipFile.save/load/clear/merge`、`hou.hda.installFile`、`hou.RopNode.render` |
| `DYNAMIC` | `exec/eval/compile/__import__/importlib`、字符串拼接后 `getattr` —— 无法静态判定 |

AST 类别仅是操作线索。必须结合执行宿主（临时命令 / SOP / 内嵌模块 / 显式资产任务）、原生算法缺口、持久化来源、已授权 effect_scope 和重建路径决策。`hou.Geometry` 不等于违规；`exec/compile` 可能是已审阅内嵌模块加载器，需校验加载内容与版本，不能只按词命中封杀。模型自报 justification 不能代替验证；分类器也不是安全沙箱。读取 `geometry()` 可能触发 Cook，READ 不代表零成本。

**策略矩阵**（由 **人** 配置：环境变量 `HOUDINI_MCP_PYTHON_POLICY` 或项目 profile，**不是** Agent 参数）：

| 类别 | `strict` | `guided`（建议默认） | `permissive`（= 现状 + 记录） |
|---|---|---|---|
| READ | 允许 + 提示等价工具 | 允许 + 提示等价工具 | 允许 |
| GRAPH_BUILD | 拒绝，返回"改用 Graph Patch"及 op 映射表 | 需 justification；放行并做前后 diff，返回 `equivalent_patch` | 允许 + diff |
| GEO_COMPUTE | 仅允许已审阅的持久化资产实现及范围内调用 | 有原生算法缺口、持久化实现、可调接口和验收计划时允许；无重建路径的临时结果要求补齐 | 记录实现归属、理由与验收 |
| SIDE_EFFECT | 限已授权且有明确目标的资产/Typed 操作 | 已授权显式烘焙/导出等按范围执行；目标、覆盖或权限不明确时才补确认 | 同样遵守 effect_scope 和既有授权 |
| DYNAMIC | 仅允许已审阅、版本绑定的加载路径 | 可追溯内嵌模块加载器经来源校验允许；未知动态代码要求展开审查 | 记录来源与内容；未知范围不能自动获权 |

附加机制：

- **诊断预算**：重复的临时 GRAPH_BUILD 回退用于提示工具缺口，默认不以固定 Python 次数中断任务。已审阅资产内部的正常 Python 计算不计作 Agent 回退；成本预算以 Cook 时间、内存、文件写出及任务范围衡量。
- **必要确认**：仅在现有授权不足以覆盖实际副作用时请求；已授权的相同动作不因使用 Python 再次确认。若采用客户端交互机制，应先核对版本与支持情况；不支持时返回明确待授权信息，而非让模型自填 `allow_unsafe`。
- **Runtime 侧**：`execute_code` 加入 `MUTATING_COMMANDS`（进 Undo Group）；执行前后对受影响根网络取 revision 与轻量快照，返回 `scene_diff`（新建/删除节点、改动参数、改动连线）。对 GRAPH_BUILD，把 diff 规范化为 `equivalent_patch`（Graph Patch op 列表）写入 Journal——**这是把 Python 行为翻译成 Typed 语言的关键，后续用于挖掘缺口和生成 Recipe 模板**。
- **持久化实现路径**：拟新增 `create_python_sop` 及 HDA 模块更新能力，源码保存在节点或定义中；显式资产任务需输入/参数清单、版本和结果报告。Python SOP 与 VEX Wrangle 是不同宿主，不以语言开关混同。

### 4.4 层 C：程序化质量机检

新增两个只读 Catalog 能力：

**`lint_network(path, rules?, severity?)`** —— 对 3.1 七条标准的机检，返回 findings + `editability_score`：

| 规则 | 检测 | 级别 |
|---|---|---|
| `L01 untraceable_output` | 结果依赖无来源、无持久化算法或无重建路径的临时状态；缓存/静态输入/显式烘焙先检查契约，无法静态确定则报告 unknown | confirmed error / unknown |
| `L02 wrangle_magic_numbers` | VEX 中非 0/1/常见常量的数字字面量，且该 Wrangle 无对应 `ch()` | warn |
| `L03 scattered_controls` | 同一字面值在 ≥3 个节点的同类参数中重复，且无通道引用 | warn |
| `L04 missing_output_null` | 网络无 `OUT*` Null，或 Display Flag 不在终端 | warn |
| `L05 default_names` | 被下游引用 / 处于 Display 链上的节点仍为默认名 | info |
| `L06 absolute_paths` | 文件参数含盘符或用户目录，未用 `$HIP/$JOB` | error |
| `L07 unexposed_seed` | 随机类节点 seed 为字面常量且未被控制器引用 | info |
| `L08 no_organization` | 节点数 > N 且无 Network Box / Sticky Note | info |
| `L09 expensive_uncached` | Sim/Remesh/大 Copy 下游无 Cache 边界且未 Bypass | warn |
| `L10 cook_errors` | 错误/警告（复用 `find_error_nodes`） | error |
| `L11 python_in_graph_unlabeled` | Python SOP 无注释说明用途 | info |

规则阈值与豁免放在项目 profile（例如某项目允许 Hard-lock 输入资产）。

**`validate_contracts(node, contract)`** —— 对 `geometry-contracts.md` 的机检：属性 owner / 类型 / tuple size / 值域（finite、范围）/ 唯一性（如 RBD `name`）/ 多帧稳定性（VAT 点数一致）。Recipe v2 的 acceptance 直接调用它。

这两个能力让"完成"从"节点建好了"变成"lint 通过 + 契约通过"，也为闭环提供**客观度量**。

### 4.4.1 节点输出属性观测与前后差异（新增优先项，尚未实现完整差异工具）

这是 Agent 制作时对应 Geometry Spreadsheet 的观测环节：**先看输入属性 → 修改 → 看输出变化 → 核对预期契约**。网络结构 diff 说明“改了哪些节点”，几何属性 diff 才说明“结果实际变了什么”；两者都需要。

**当前实现核对（2026-11-04）：**

| 能力 | 当前范围 | 边界 |
|---|---|---|
| `get_geometry_info(path)` | 指定 SOP 输出的点/面/顶点数、包围盒、Point/Primitive/Vertex/Detail 属性名、数据类型、tuple size、点/面组名 | 几何容器会解析到 Display SOP；不是每种 Houdini 上下文、每个输出端口的通用观测器 |
| `get_geometry_data(path, element, attributes, start, limit)` | 点或面属性实际值，默认 100 条、最多 500 条/页；仓库 Hybrid 经 Catalog，Legacy 直连 | 不支持 Vertex 和 Detail 值；不提供帧、输出端口或持久快照参数 |
| `get_network_snapshot` | 节点、连接、可选参数、revision | 不包含逐元素几何属性差异 |

实现依据：`houdinimcp_runtime/server.py` 的 `get_geometry_info/get_geometry_data`、`houdini_mcp_bridge/catalog.py` 的 `GeometryDataArgs`。当前读取调用 `sop.geometry()`，可能触发 Cook；不是保证无计算的缓存读取，昂贵/写出节点不能自动全图扫描。

**第一步：补齐四种 owner 的取值。** 扩展 `get_geometry_data` 支持 `vertices`、`detail`；顶点返回 vertex id、primitive number、local vertex index、point number。不能拿 Point UV 代替 Vertex UV，接缝两侧同一个点可以有不同顶点值。Detail 返回全局值；数组、字典、长字符串等需字节/元素上限和截断标记，保持 points/primitives 兼容。

**第二步：有界几何快照与差异。** 拟新增 Catalog 能力 `capture_geometry_snapshot`、`compare_geometry_snapshots`（名称为提案）：

- 两种比较：同一时间的上游/下游输出；同一节点修改前/后的不可变快照。修改前必须保存值或受控摘要，修改后重新读两次无法找回旧状态。
- 快照记录节点、实际帧/时间、输入连接、输出选择、拓扑摘要、属性 owner/name/storage/type/size、选择范围、采样策略、截断/覆盖率、Cook 策略与错误。多输出端口先验证运行时可支持范围，不能默认总是第 0 输出或把 HDA 的某个内部分支当作全部输出。
- 比较新增/删除属性、owner/类型/维度变化、元素数、包围盒、组成员以及值变化。数值提供改动数/比例、最大和均方差、非有限值；方向向量可比较夹角；字符串/类别给出变化摘要。匹配与容差需声明，不默认排序或按点号比较。
- 拓扑与顺序保证稳定时可按元素索引；有可靠唯一 `id/name` 时按键匹配并报告重复、缺失和未匹配项。顶点键需稳定 primitive 标识与局部对应；拓扑改变无法建立对应时报告“不可逐元素比较”，改用集合/统计/契约，不能把同点数当成同一批点。
- 大几何优先在 Houdini 侧聚合，返回紧凑差异和少量异常样本；抽样相等不得称为全量未改变。分页读取需固定快照，避免不同页来自不同 Cook/帧。
- 默认覆盖关键阶段边界、故障附近与用户指定节点；不把所有节点全量属性送给 Agent，也不默认自动 Cook 仿真/烘焙/导出链。

**验收与案例：** Hair Tangent Baker 的中性 Ramp 前后应验证 P/N/UV 与拓扑；UV 前处理前后应核对 Vertex UV 的变化以及 P/拓扑是否保持；“原网格”模式要求点面数、UV/权重保持而 P/N 可按预期改变；“重建”模式允许拓扑改变，采用输出契约验收。补充 owner 改变、同点数重排、拓扑改变、重复 id、空几何、数值容差、非有限值、数组/字符串、分页一致性和无 Cook 数据不可用等测试。

**接入闭环：** 阶段 1 优先补齐取值并设计有界快照，阶段 4 接入差异与契约验收；Journal/Experience 只保存快照引用、摘要和失败样本。知识层据此区分“预期造型修改”和“误伤 UV/属性”，Dashboard 后续展示关键变化，不复制完整几何数据。

### 4.5 层 D：执行日志（Journal）与人工修改捕获

**Journal**（Bridge 写，JSONL，按会话/任务分文件；位置由 `HOUDINI_MCP_JOURNAL_DIR` 指定，默认用户偏好目录，**不进仓库**）：

```jsonc
{
  "ts": "2026-11-04T10:12:03Z", "session": "s-…", "task": "t-…",
  "tool": "apply_graph_patch", "via": "direct|catalog",
  "args_summary": {"ops": 7, "op_types": {"create": 4, "connect": 3}, "node_types": ["scatter::2.0", "copytopoints::2.0"]},
  "status": "success|error", "origin": null, "duration_ms": 182,
  "revision_before": "…", "revision_after": "…",
  "python": {"classes": ["GRAPH_BUILD"], "decision": "allowed_with_diff", "justification": {...}, "equivalent_patch_ref": "…"},
  "affected": ["/obj/geo1/scatter_leaves", "…"]
}
```

只存摘要和结构化 diff，不存完整代码以外的大块数据；代码本身单独存（便于挖掘），可配置关闭。

**人工修改捕获**（Runtime，Houdini 特有、信号质量最高）：

1. Agent 创建/修改的节点写入 `userData["mcp:op"] = <operation_id>`（体积很小；可配置关闭）。
2. 对这些节点注册 `hou.Node.addEventCallback`（`ParmTupleChanged`, `InputRewired`, `NameChanged`, `FlagChanged`, `BeingDeleted`）。
3. 回调触发时若当前**不在** MCP 命令执行中，则判定为**人工修改**，记入 Runtime 环形缓冲：`{node, kind, parm, old→new, time}`。
4. Bridge 在下一次调用或 `end_task` 时拉取（新增只读命令 `get_human_edits_since`）。

"美术把 Agent 建的 `scatter` 的 `npts` 从 5000 改回 800，又把它连到 Controller 上"——这就是一条带上下文的纠错样本，比任何聊天记录都准。

### 4.6 层 E：经验闭环（"自回归"提升）

把"自回归"落实为一个可度量的迭代：**系统用自己产生的执行记录改进自己，但每一步改进都要过证据和测试。**

```
            ┌────────────── 快环（会话内，秒级）──────────────┐
            │ 网关拒绝/放行 → 返回等价 Typed 做法 + 相关 lessons │
            └─────────────────────────────────────────────────┘
            ┌────────────── 中环（任务结束，分钟级）──────────┐
 Journal ─► │ end_task: lint + 契约 + 人工修改 → 草稿 Experience │
            │ （candidate；纠错条目预分类，待人确认）           │
            └─────────────────────────────────────────────────┘
            ┌────────────── 慢环（周期，天/周级）─────────────┐
            │ experience_cli mine：跨 Experience 聚类信号        │
            │ → proposals/*.json → 人评审 → 代码/记录变更 → 测试 │
            │ → 晋升 → 回灌到 lessons/recipes/catalog           │
            └─────────────────────────────────────────────────┘
```

**信号 → 分类 → 提案类型**（在现有 7 类纠错分类上，补充两类工程归因）：

| 信号（来源） | 归因 | 提案类型 |
|---|---|---|
| 同一 Python 分类 + 相似 `equivalent_patch` 形状反复出现 | `capability_gap` / `affordance_gap` | 新 Catalog 能力、新 Patch op、调整直连集合、改工具描述/示例 |
| Typed 工具报错后 N 步内转 Python | `capability_gap` 或 `tool_defect` | 修复工具 / 扩展参数 |
| 人工修改集中在某类参数（如 seed、密度、尺度） | `project_convention` / `houdini_invariant` | Recipe `controls` 补充、Lint 规则、项目 profile |
| 人工把死值改成通道引用 / 加 OUT Null / 加 Network Box | `houdini_invariant`（可修改性） | Lint 规则加严、Recipe 模板补齐 |
| 某 Recipe 下 `validate_contracts` 反复失败于同一检查 | `recipe_error` | Recipe 补丁 |
| 只在单项目、单用户出现 | `project_convention` / `artistic_preference` / `one_off_asset` | 只进项目 profile，**不进通用知识** |

**晋升门槛**（沿用宪章，补充可计算条件）：

- **Lesson**：同一签名在 ≥2 个独立任务中出现，且应用该 lesson 后同类信号下降 → `validated`。
- **Recipe**：≥2 个独立 case + ≥1 个 `validate_contracts` 全通过的 experience → `validated`；跨 ≥2 个项目 + 回放测试通过 → `canonical`。
- **Catalog 能力**：满足 CAPABILITY_TODO 的"专用能力晋升条件"，且 Journal 中有 ≥K 次相关 Python 回退或失败记录作为证据（K 可配置，建议 3）。

**防止自我强化偏差**：
- 提案只生成，不自动合并；状态晋升仍然是"带证据的仓库变更"（沿用 AGENTS.md 规则）。
- 每个提案必须引用 Journal / Experience id；没有证据引用的提案被 `mine` 丢弃。
- 晋升后监测：若同类信号未下降或上升，自动生成 `deprecate` 候选提案。

### 4.7 层 F：运行期知识回灌（让经验真的影响下一次）

新增 Bridge 本地能力（不需要 Houdini 连接，类似现有 OPUS 本地 handler）：

- **`begin_task(goal, target_path?, workflow?)`**：开启 Journal 任务边界；按 routing 选工作流；返回 **紧凑** guidance：
  - 选中的 Recipe（状态、阶段、控制项、契约、禁止模式）；
  - Top-N 相关 lessons；
  - 当前策略模式与 Python 预算；
  - 推荐的第一步调用（通常是 `get_network_snapshot`）。
- **`end_task(acceptance_notes?)`**：运行 lint + 契约 + 拉取人工修改 → 写草稿 Experience → 返回评分与未通过项。
- **`get_recipe(id)` / `search_knowledge(query)`**：按需展开，保持渐进披露。

**Lessons 存储**（`references/records/lessons/*.json`，新 Schema）：小而原子的"触发器 → 正确做法 → 反模式 → 证据"：

```jsonc
{
  "record_type": "lesson", "id": "lesson-wrangle-ch-params", "status": "validated",
  "trigger": {"tools": ["create_wrangle", "set_wrangle_code"], "python_classes": [], "keywords": ["wrangle", "vex"]},
  "do": "VEX 中可调数值用 ch(\"name\")，并调用 create_spare_parms_from_ch 生成参数",
  "dont": "在 VEX 里写死 0.35、1200 等数值",
  "why": "美术无法在参数面板调节；与控制器无法联动",
  "evidence": {"experience_ids": ["exp-…", "exp-…"], "signal": "human_edit:vex_literal_to_ch", "count": 5}
}
```

Lessons 在三个时机注入：`begin_task` 返回、Typed 工具报错时附带、Python 网关拒绝/放行时附带。注入有条数上限，避免上下文膨胀。

### 4.8 Recipe v2：从散文到可执行契约

在 recipe schema 上增加 v2（v1 继续有效，迁移渐进）：

```jsonc
{
  "schema_version": 2, "record_type": "recipe", "id": "curve-instancing-v2",
  "controls": [  // 必须暴露在控制器/HDA 接口上的量
    {"name": "spacing", "type": "float", "default": 0.5, "range": [0.01, 10]},
    {"name": "seed", "type": "int", "default": 0}
  ],
  "stages": [
    {
      "id": "resample", "box": "01_PREP",
      "patch_template": [   // Graph Patch op，${…} 为槽位，$CTRL 为控制器
        {"op": "create", "id": "rs", "parent_path": "${parent}", "node_type": "resample", "name": "resample_curve"},
        {"op": "set_expression", "path": "$rs", "parm": "length", "expr": "ch(\"../CTRL/spacing\")"},
        {"op": "connect", "from_path": "${input}", "to_path": "$rs"}
      ],
      "alternatives": ["existing project HDA: ${profile.curve_resample_hda}"]
    }
  ],
  "outputs": [{"null": "OUT_INSTANCES", "contract": "instance-points"}],
  "checks": [   // 每条是一次 validate_contracts / lint 调用
    {"kind": "contract", "node": "OUT_INSTANCES", "contract": "instance-points"},
    {"kind": "lint", "path": "${parent}", "max_severity": "warn"}
  ],
  "forbidden": ["untraceable_output", "unauthorized_side_effect"]
}
```

要点：
- `patch_template` 是**骨架**而非唯一解（宪章第 4 条"契约优先于图形状"）；Agent 可以偏离，但 `checks` 必须通过。
- 当某 Recipe 有经验证的模板 HIP/HDA 时，`stages` 直接是"实例化 HDA + 设置控制参数"，这是最强的钳制：**最好的工作流约束是一个已经做好的 HDA**。
- `checks` 可机检，晋升就能由数据驱动而不只是人工判断。

### 4.9 度量体系

在 Dashboard 上增加"运行指标"视图（仍然只读、离线，由 Journal 聚合生成）：

| 指标 | 定义 | 目标（建议） |
|---|---|---|
| 临时 Python 回退率 | 有合理 Typed 等价物仍使用临时代码的调用占比；内嵌算法和原生能力缺口单列 | 诊断工具缺口，不设统一语言比例门槛 |
| 不可复现输出率 | 缺输入/参数/版本/持久化实现或无法重建的交付比例 | 0；不把合法内嵌算法、缓存和显式产物计为失败 |
| 原生能力缺口交付质量 | Python 补足缺失算法后的参数行为、重开复现、任务验收与用户认可 | 好用、可调、可复现；按版本留证 |
| 可编辑性评分 | `lint_network` 加权分（终态） | 持续上升 |
| 首次验收率 | `end_task` 时 checks 全通过的比例 | 持续上升 |
| 重复纠错率 | 经归因确认的同类缺陷修正次数；艺术探索、偏好调整单列 | 持续下降，不以压低正常调参次数为目标 |
| 到达有效交付的成本 | 调用数、耗时和计算/人工成本 | 在质量与复现成立时下降，不惩罚合理 Python |
| Lesson 效果 | 注入前后同签名信号频次 | 下降，否则进入 deprecate 候选 |

---

## 5. 修改方案（按文件）

| 文件 | 修改 |
|---|---|
| `houdini_mcp_bridge/bridge.py` | `FastMCP(..., instructions=...)`；调整 hybrid 直连集合【行为变更】；直连 `create_node` 加 `parameters/position`；新增 `begin_task/end_task/get_recipe/search_knowledge` 本地 handler；所有调用经 Journal 中间层 |
| `houdini_mcp_bridge/python_policy.py`（新） | AST 分类器、策略矩阵、预算、justification 校验；纯函数，无 `hou` 依赖 |
| `houdini_mcp_bridge/journal.py`（新） | JSONL 写入、任务边界、摘要器（参数摘要、节点类型统计）；路径来自环境变量，可关闭 |
| `houdini_mcp_bridge/knowledge.py`（新） | 读取 skill records（recipes/lessons/routing），按触发器检索，渐进披露 |
| `houdini_mcp_bridge/catalog.py` | `CodeArgs` 增加 `intent/justification`；`GeometryDataArgs` 增加 Vertex/Detail；拟新增有界几何快照/差异 ToolSpec（4.4.1）；新 ToolSpec：`lint_network`, `validate_contracts`, `check_network`, `create_python_sop`, `get_human_edits_since`；`GraphOperation` 扩展 op；`RenderArgs` 去掉 `C:/temp/` 默认值 |
| `houdini_mcp_bridge/registry.py` | `invoke` 前后挂 Journal 钩子；错误信封附带 `lessons`/`suggestions`；`search` 改为分词打分（任一词命中即候选，按命中数排序） |
| `houdinimcp_runtime/server.py` | `execute_code` 进 `MUTATING_COMMANDS`，并返回 `scene_diff`；四类属性取值与有界几何快照/差异（4.4.1）；Graph Patch v2（见下）；节点 `userData` 归属标记与事件回调；`lint_network`、`validate_contracts`、`get_human_edits_since` handler |
| `houdinimcp_runtime/lint.py`（新） | Lint 规则实现（只读，不 Cook 昂贵分支；L10 复用已有错误收集） |
| `skills/.../schemas/` | 新增 `lesson.schema.json`、`proposal.schema.json`；`recipe.schema.json` 支持 v2；`experience.schema.json` 增加 `python_events`、`human_edits`、`lint`、`journal_ref` |
| `skills/.../scripts/experience_cli.py` | 新子命令：`ingest-journal`（草稿 Experience）、`mine`（聚类出 proposals）、`metrics`（指标聚合） |
| `skills/.../scripts/build_dashboard.py` | 增加指标与提案视图（只读） |
| `skills/.../references/mcp-usage.md`、`SKILL.md` | 更新为 begin/end task 流程、Python 分级规则、可修改性七条 |
| `tests/` | 见第 6 节各阶段 |

**Graph Patch v2 细节**：

- **原子性升级**：当 `hou.undos.areEnabled()` 时，handler 自管一个 Undo Group，失败时退出 group 后 `hou.undos.performUndo()` 回滚——从而允许在 atomic 模式下编辑既有节点、delete、disconnect。Undo 不可用时（部分 hython 场景）回退到"预先捕获状态 + 补偿"或维持现有限制并在响应中说明。需要在 GUI 与 hython 下分别验证。
- **新增 op**：`set_expression`（hscript/python，含 `ch()` 引用）、`set_keyframes`、`insert_between`、`add_spare_parms`（含从 Wrangle `ch()` 自动生成）、`create_controller`（Null + Spare Parm 组）、`create_network_box`、`create_sticky_note`、`set_color`、`set_comment`、`collapse_to_subnet`、`set_multiparm`。
- **既有节点绑定**：`{"op": "bind", "id": "src", "path": "/obj/geo1/OUT"}`，让模板可以把 `$src` 指向既有节点。
- `mode="validate_then_apply"` 单次调用。

**兼容性**：TCP 协议与已有命令名不变，仅新增命令；`uv run` / stdio / Shelf / 端口 / 包注册不变；Legacy 模式行为不变（仅增加 Journal）；唯一行为变更是 Hybrid 直连集合与 Python 网关默认模式，均可通过环境变量回退（`HOUDINI_MCP_PYTHON_POLICY=permissive`、`HOUDINI_MCP_DIRECT_TOOLS=v1`）。

---

## 6. 实施计划

每个阶段都可以独立交付、独立回退，并且都先产生数据——**先装传感器，再加控制律**。

### 阶段 0：止血（约 1–2 天）

| 项 | 内容 |
|---|---|
| 修改 | `execute_code` 进 Undo Group；FastMCP `instructions`；直连 `create_node` 加参数；渲染默认路径改为 `$HIP/render` 或必填 |
| 测试 | `test_tools.py` 增加"Python 修改可一步 Undo"；`test_hybrid_surface.py` 校验 instructions 存在 |
| 验收 | 现有全部测试通过；行为无破坏性变化 |

### 阶段 1：传感器（约 1 周）

| 项 | 内容 |
|---|---|
| 修改 | 补齐 Vertex/Detail 属性取值并设计有界快照（4.4.1）；`journal.py`；Registry/直连工具挂 Journal；`execute_code` 返回 `scene_diff` 与 `equivalent_patch`；节点归属 userData 与人工修改事件捕获；`get_human_edits_since` |
| 测试 | Journal 单测（摘要、关闭开关、无绝对路径泄露进仓库）；hython 集成：脚本修改后 diff 正确、事件回调区分 MCP 内/外修改 |
| 验收 | 跑 3 个真实小任务，Journal 能完整还原调用序列、Python 行为与人工修改 |
| 价值 | **此阶段完成后即可开始统计现状 Python 回退率，作为后续所有改动的基线** |

### 阶段 2：网关与表面（约 1 周）

| 项 | 内容 |
|---|---|
| 修改 | `python_policy.py`（分类器 + 矩阵 + 预算）；`CodeArgs` 增加 justification；默认 `guided`；Hybrid 直连集合调整【行为变更，需确认】；Graph Patch `validate_then_apply` |
| 测试 | 分类器表驱动单测（每类 ≥10 个样例，含混合与 DYNAMIC）；策略矩阵单测；`test_hybrid_surface.py` 更新直连集合并保留 v1 回退 |
| 验收 | 用阶段 1 的基线任务重跑：有 Typed 等价物的无理由回退减少；不可复现输出为 0；原生算法缺口任务与 Hair Tangent Baker 类内嵌实现可完成；任务完成率和可调性不下降 |

### 阶段 3：补能力缺口（约 1–2 周）

| 项 | 内容 |
|---|---|
| 修改 | Graph Patch v2（Undo 级原子、新 op、bind）；`create_python_sop`；`check_network` |
| 优先级 | 以阶段 1–2 Journal 中 `equivalent_patch` 的高频形状为准排序；预期 `set_expression`、`insert_between`、`create_controller`、`create_network_box` 排在前面 |
| 测试 | hython 集成：每个新 op 的成功/失败/回滚；GUI 下 Undo 一步回滚；hython Undo 不可用时的降级路径 |
| 验收 | 阶段 2 中被拒绝或需 justification 的 Python 场景，常见图操作优先由 Typed 路径完成；原生算法缺口按持久化 Python 的产品验收评价，不要求为凑覆盖率改写算法 |

### 阶段 4：机检与可执行 Recipe（约 1–2 周）

| 项 | 内容 |
|---|---|
| 修改 | 有界几何快照/差异（4.4.1）、`lint_network`（L01–L11）、`validate_contracts`；recipe schema v2；先迁移 `curve-instancing` 与 `surface-growth` 两个 recipe；`begin_task` / `end_task` / `get_recipe` / `search_knowledge` |
| 测试 | Lint 每条规则正反例（hython 构造网络）；契约校验覆盖 owner/type/size/值域/多帧；`test_experience_system.py` 覆盖 v1/v2 共存 |
| 验收 | 两个 recipe 各完成 1 次端到端执行，`end_task` 产出通过 schema 校验的 Experience，`checks` 全部机检 |

### 阶段 5：闭环（持续）

| 项 | 内容 |
|---|---|
| 修改 | lesson schema 与注入；`experience_cli ingest-journal / mine / metrics`；proposal schema；Dashboard 指标视图 |
| 测试 | `mine` 对合成 Journal 的聚类结果确定性；无证据引用的提案被丢弃；lesson 注入条数上限 |
| 验收 | 第一批由 Journal 自动生成、经人工评审合并的提案（至少 1 个 Patch op 或 Catalog 能力、1 个 lesson、1 个 recipe 补丁）；对应信号在后续任务中下降 |

### 阶段 6：回放与评测（与阶段 5 并行）

- **确定性回放**：Experience 中的 `equivalent_patch` / patch 序列可在 hython 中回放，作为 Recipe 在新 Houdini 版本下的回归测试。
- **任务评测集**：10–20 个代表性任务（每个工作流 1–2 个 + 若干"诱导 Python"的任务，例如"按 CSV 摆放物体"、"把所有 file 路径改成相对路径"、"做一个可调密度的散布"），每个带 checks；定期用真实 Agent 跑，记录第 4.9 节指标。**没有评测集，"提升"就无法被证明。**

---

## 7. 风险与权衡

| 风险 | 缓解 |
|---|---|
| 网关过严导致 Agent 卡死或绕路 | 默认 `guided` 而非 `strict`；拒绝时必须给出可执行替代；Python 次数仅作缺口信号，实际成本或副作用超出现有授权时再处理；阶段 2 验收要求完成率不下降 |
| AST 分类被绕过（DYNAMIC、间接调用） | 未知即升级；分类器不是安全边界，effect_scope 与人工确认才是；Runtime diff 作为事后核对 |
| userData 标记写入 HIP | 体积极小、命名空间化；可通过环境变量关闭；`end_task` 可选清理 |
| 事件回调影响交互性能 | 只挂在 Agent 触达的节点上，回调只入环形缓冲；数量上限 |
| Journal 泄露路径/机密 | 默认存仓库外；摘要化；不记录 OPUS key 等；提供关闭开关 |
| 闭环过拟合单一项目/用户 | 沿用宪章分类；`project_convention` 只进 profile；晋升要求跨任务/跨项目证据 |
| Lesson/guidance 注入撑大上下文 | 条数和字节上限；渐进披露（摘要 → `get_recipe` 展开） |
| Undo 在 hython 下行为不同 | 阶段 3 明确双环境测试，失败则降级并在响应中声明 |

---

## 8. 决策记录

已确认（2026-11-04）：

1. **默认 Python 策略为 `guided`**；Hybrid 下 `execute_houdini_code` 移出直连（阶段 2 落地，Legacy 不变）。
2. **允许节点归属标记**：Agent 触达的节点写入 `userData["mcp:op"]`，用于人工修改捕获（阶段 1 落地，可通过环境变量关闭）。
3. **首批 Recipe v2 迁移对象**：`curve-instancing` 与 `surface-growth`（阶段 4）。
4. **Python 判据修订（本次用户确认）**：Hair Tangent Baker 的原生算法缺口支持 Python 选型；以 HDA 好用、可调、可复现为核心，按执行归属和实际副作用分类，不设统一 Python 比例或 GEO_COMPUTE 清零目标。
5. **节点输出观测**：已核对当前只能完整读取点/面属性值；Vertex/Detail 与几何快照差异纳入后续开发，当前未实现。

待定：

6. **Journal 存放位置与保留期**：暂按建议默认 `$HOUDINI_USER_PREF_DIR/houdinimcp/journal/`，保留 30 天，可关闭。
7. **评测集**：是否有可用于评测的真实任务/HIP（去除私有路径）可以纳入？

### 实施进度

- **成功经验已入库**：Hair Tangent Baker 的 Case/Experience/候选 Recipe 与 HDA authoring 路由，提交 `8728d84`。本次反馈修订设计判据与属性观测计划，不代表网关、Vertex/Detail 或快照差异能力已经上线。

- **阶段 0（已完成）**：`execute_code` 进入 Undo Group（GUI 与 hython 均验证为一步撤销，只读代码不留 Undo 记录）；FastMCP `instructions`；直连 `create_node` 支持 `position/parameters`；渲染路径去除 `C:/temp/` 默认值。
  - 顺带修复一个既有缺陷：`create_node` 过去会**静默忽略**元组参数（如 box `size`）和拼错的参数名，Graph Patch 的 `create` op 同样受影响。现在复用 `set_parameters` 的校验路径，失败时报错并销毁半成品节点。
  - 已验证前提：hython 21.0.440 下 `hou.undos` 可用，阶段 3"基于 Undo 的原子回滚"可行。

---

## 附录 A：直连集合建议（Hybrid v2）

| 保留 | 新增 | 移出到 Catalog |
|---|---|---|
| `get_scene_info`, `create_node`（加参数）, `connect_nodes`, `set_parameters`, `get_parameter_schema`, `get_geometry_info`, `houdini_ping`, `search_tools`, `get_tool_schema`, `call_tool` | `get_network_snapshot`, `apply_graph_patch`, `search_node_types`, `check_network`, `begin_task`, `end_task` | `execute_houdini_code` |

直连数量从 11 增至 16。若需控制在原规模，可把 `connect_nodes` / `create_node` 降为 Catalog（其功能被 Graph Patch 覆盖），保持 ~14 个。

## 附录 B：网关拒绝响应示例

```jsonc
{
  "status": "error",
  "origin": "python_policy",
  "message": "本次交付仅保留临时几何，缺少可持久化算法和重建入口；请补齐后交付。",
  "execution_context": {"host": "temporary_command", "persistent_implementation": false, "rebuild_entry": null},
  "classification": {"classes": ["GEO_COMPUTE"], "evidence": ["hou.Geometry.createPoint @ line 4", "setAttribValue @ line 7"]},
  "alternatives": [
    {"tool": "create_wrangle", "hint": "逐点计算用 Point Wrangle，数值用 ch() 暴露"},
    {"tool": "create_python_sop", "hint": "确需 Python（如解析外部数据）时，把代码放进 Python SOP，使其留在网络中"}
  ],
  "lessons": ["lesson-reproducible-asset", "lesson-exposed-controls"],
  "policy_mode": "guided"
}
```

## 附录 C：`end_task` 返回示例

```jsonc
{
  "task": "t-…", "workflow": "curve-instancing", "recipe": "curve-instancing-v2",
  "calls": 14, "python": {"count": 1, "classes": {"READ": 1}},
  "lint": {"editability_score": 0.86, "findings": [{"rule": "L05", "node": "/obj/geo1/attribwrangle3"}]},
  "checks": {"passed": 3, "failed": 0, "skipped": 1},
  "human_edits": 0,
  "experience_draft": "experiences/exp-20261104-101203-curve-instancing.json"
}
```
