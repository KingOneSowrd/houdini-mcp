# Houdini MCP 能力扩展 TODO

本文档记录 Houdini MCP 在现有 Hybrid Tool Registry 基础上的精简扩展路线。

本文档不是重构或替换现有 MCP 的设计稿。当前直连 Tool、43 项 Catalog 能力、Shelf Server、TCP Bridge、Tool Registry 和 SideFX Docs Provider 都作为既定基础继续使用；TODO 只描述在这些能力之上补齐的缺口，以及新增能力落地时必须同步完成的小幅加固。

核心原则：**让 MCP 承载实时事实、严格验证、安全边界和不可拆分的副作用；让模型承载规划、组合、比较和领域工作流。**

MCP 不追求把每个 Houdini HOM 方法包装成一个 Tool。模型应通过少量通用原语、实时 Schema 和经过验证的工作流配方完成大多数任务。只有模型无法可靠组合、必须跨越事务边界，或能显著减少昂贵往返的操作，才升级为专用 Catalog 能力。

> 开发状态（2026-08-27）：Catalog 已包含 43 项能力。实时节点发现、Network Snapshot、Channel 保护、Graph Patch、HDA Candidate/Definition/创建/Interface 参数提升/验证、材质绑定读取和 USD Stage Snapshot 已进入代码。23 项 Bridge 单元测试以及 Houdini 21.0.440 下的基础、Catalog、HDA 扩展集成测试均通过。当前项目已经具备可靠的通用 Houdini 执行层，但异步任务、生产缓存与发布、Solaris Authoring、动画/模拟、结果验收和端到端制作案例仍是进入真实工作流前的主要缺口。

## 当前基线

- [x] 默认 Hybrid 模式：8 个高频直连工具 + 3 个目录/调度入口
- [x] 43 项内部 Catalog 能力
- [x] Typed Tool Registry、Pydantic 参数校验和高风险调用门控
- [x] Houdini 主线程 TCP Handler 和场景修改 Undo Group
- [x] 当前 Houdini 版本的 `hom.zip` / `nodes.zip` 官方文档搜索
- [x] Windows、macOS、Linux 动态 Houdini/帮助目录发现
- [x] 节点、参数、图连接、VEX、几何、基础材质、渲染和 HIP 能力

## 与现有能力的关系

### 直接复用，不重复实现

- `create_node`、`modify_node`、`delete_node`
- `connect_nodes`、`disconnect_node_input`、`set_node_flags`、`layout_network`
- `set_parameters`、`get_parameter_schema`
- `get_node_info`、`find_nodes`、`get_scene_info`
- `find_error_nodes`、`cook_node`
- `create_wrangle`、`set_wrangle_code`
- `get_geometry_info`、`get_geometry_data`
- 现有材质、渲染、HIP、OPUS 和 SideFX 文档能力

### 在现有能力上增强

- `set_parameters` 增加 Channel 保护和“全部验证后再写入”
- Registry 搜索按新增能力数量逐步增加多关键词和分页
- 修改类命令只在 Graph Patch、HDA 等需要时增加幂等或 Revision 检查
- 现有响应、路径和风险提示在相关能力被触及时顺手统一，不单独进行大规模重构

### 真正新增的能力组

- 实时节点类型发现和有界网络 Snapshot
- HDA Core
- 原子 Graph Patch 与可选 Subnetwork 折叠
- USD Stage、材质绑定等无法从普通节点图获得的只读事实

`apply_graph_patch` 应复用现有节点、连接、参数和 Flag 处理逻辑；它是减少往返并提供事务边界的批处理入口，不是第二套节点编辑实现。

## 能力边界

### MCP 应负责

- 从当前 Houdini 会话读取真实节点类型、参数模板、License、GUI 和版本能力
- 在发送 TCP 命令前使用严格 Schema 拒绝未知或错误参数
- 对场景、磁盘、外部进程和可执行脚本实施不同的风险与回滚策略
- 执行必须原子化或需要 Houdini 主线程保证的操作
- 返回有大小上限、可分页、可追踪且遵守统一 Envelope 的结果
- 为每项正式能力绑定当前 Houdini 自带的 SideFX 官方文档

### 模型应负责

- 根据目标规划节点网络、材质网络、LOP 网络和 HDA 工作流
- 组合 `search_node_types`、`get_node_type_schema`、`get_network_snapshot` 和 `apply_graph_patch`
- 比较两个有界 Snapshot，并决定需要的修复步骤
- 根据 Tool Schema、官方文档和工作流配方选择参数与节点连接
- 在调用专用能力前完成范围选择、风险判断和结果解释

### 不应直接新增 Tool 的情况

- 只是现有 `create_node`、`set_parameters` 或 `connect_nodes` 的领域重命名
- 模型可用两三个通用调用可靠完成，且没有新的事务或安全边界
- 依赖硬编码的完整节点类型、参数或菜单列表
- 只能包装一次性的 HOM 调用，尚无稳定输入 Schema 和验收场景
- 仅为减少一次目录搜索而扩大长期维护面

### 专用能力晋升条件

满足下列至少一项，并有实际调用记录或失败案例支持：

- 通用原语无法保证原子性或无法安全回滚
- 操作跨越场景与磁盘，必须进行备份、哈希校验或补偿回滚
- 通用组合需要大量 TCP 往返，已经成为稳定高频工作流
- 领域上下文无法由通用节点 Schema 表达，例如 USD Stage、HDA Definition 或 GUI Pane 状态

新能力默认只进入 Catalog。只有跨领域、高频、Schema 稳定且能明显减少目录调用时，才考虑加入 Hybrid 直连表面。

## 所有新增能力的完成标准

每项能力完成前必须满足适用条目：

- [ ] 在 `houdini_mcp_bridge/catalog.py` 中使用 `extra="forbid"` 的严格 Pydantic 参数模型
- [ ] 注册名称、分类、说明、关键词、风险、可用性和至少一项有效 `DocRef`
- [ ] 明确副作用范围：`read_only`、`scene`、`session_ui`、`disk`、`external_process` 或 `external_network`
- [ ] 明确回滚方式：`none`、`undo`、`compensation`、`backup` 或 `manifest`；需要 Registry 自动门控时再扩展 `ToolSpec`
- [ ] 涉及节点类型时从实时 `hou.nodeTypeCategories()` 和父网络上下文验证
- [ ] 涉及参数时从实时 `hou.ParmTemplate`、`hou.ParmTuple` 和 `hou.Parm` 验证
- [ ] 成功返回 `{"status": "success", "result": ...}`
- [ ] 错误返回 `{"status": "error", "message": "...", "origin": "..."}`
- [ ] 大型返回统一支持 `total`、`offset`、`count`、`next_offset` 和 `truncated`
- [ ] GUI、版本、License 或连接状态不满足时返回明确原因，不伪装为可用
- [ ] 场景写入加入单次 Undo Group；跨场景与磁盘操作使用补偿或备份，不宣称由 Undo 保证
- [ ] 高风险脚本写入需要 `allow_unsafe=true`；删除和覆盖还需目标身份及 Revision 确认
- [ ] Registry 单元测试覆盖 Schema、风险、可用性和 DocRef
- [ ] 涉及 `hou` 的能力有 headless 集成测试；GUI 能力另有 GUI 会话验证
- [ ] 不改变 Shelf、长度前缀 JSON、stdio、`uv run` 和部署方式；TCP 默认端口因 Windows 保留范围冲突调整为 `127.0.0.1:9900`，并允许通过 `HOUDINI_MCP_PORT` 配置

Git commit、文档和发布要求属于能力组的交付流程，不作为每个小 Tool 的重复清单。

## 扩展实施支撑项

这些内容服务于后续能力，不作为独立的“能力拓展 P0”，也不要求先整体重构完成。只在某项新增能力实际需要时，以小步提交落地。

### 响应与副作用元数据

- [ ] 所有 Houdini 端异常补齐 `origin`
- [x] 当现有 `mutating`、`undoable` 和 `risk` 不足以描述磁盘/任务副作用时，再为 `ToolSpec` 增加 `effect_scope` 和 `rollback_strategy`
- [x] 高风险拒绝信息按 Tool 描述实际风险，不再只描述任意 Python
- [x] 区分 `available`、`unavailable` 和未连接时的 `unknown`
- [ ] 将 Houdini 版本、License、GUI、节点类别和可选模块状态作为动态能力事实缓存
- [ ] 缓存失效时安全降级，不阻止 Catalog 搜索

### Registry 搜索可扩展性

- [x] `search_tools` 支持多关键词评分，不要求整段查询连续匹配
- [x] 支持分类、效果范围、变更标记、可用性和风险过滤
- [x] 支持分页，避免 HDA 等同类能力占满前十项
- [ ] Tool Schema 返回前置条件、回滚策略、结果大小说明和经过验证的示例
- [ ] 保持 Hybrid 公开表面为 8+3，除非有实际数据证明需要晋升

### 重试与并发安全

- [x] Graph Patch 和 HDA 磁盘写入支持可选 `idempotency_key`
- [ ] Houdini 端短期缓存已完成操作结果，避免 TCP 超时重试重复写入
- [x] 需要防止陈旧写入的操作接受 `expected_revision`
- [x] 返回稳定的 `operation_id` 供日志、回滚和问题诊断使用
- [x] 串行化共享 TCP 连接上的请求/响应，避免并发 MCP 调用错配响应

### 支撑项验收

- [ ] 未连接 Houdini 时 Catalog 可搜索，但会话能力标记为 `unknown`
- [ ] 非法参数在 TCP 发送前被拒绝
- [ ] 同一 `idempotency_key` 重试不会重复创建节点
- [ ] Revision 不匹配时拒绝写入并返回最新摘要
- [ ] Bridge 单元测试与 Hybrid/Legacy 暴露测试通过

## P0：实时发现与有界场景快照

目标：让模型不猜节点类型、参数名和当前网络状态。

### 正式 Catalog 能力

- [x] `search_node_types`
  - 按父网络路径、类别、名称、标签、描述和关键词搜索
  - 只优先返回当前父网络中实际可创建的类型
  - 返回完整类型名、类别、命名空间、版本、输入输出摘要和官方文档
- [x] `get_node_type_schema`
  - 返回输入输出约束、参数模板、默认值、菜单和范围
  - 支持参数过滤与分页
  - 无法在不实例化节点的情况下获得的信息必须明确标记，不静默猜测
- [x] `get_network_snapshot`
  - 返回节点、连接、Flags、位置和可选参数摘要
  - 支持深度、节点数、参数数和结果字节上限
  - 返回 `snapshot_revision` 和会话内节点身份
  - 默认不返回全部参数值、几何数据或二进制内容

### 由模型承担

- 比较两个 Snapshot 中的新增、缺失、连接和参数差异
- 根据目标网络与当前网络生成 Graph Patch
- 解释命名空间和版本差异并选择完整节点类型名

仅当 Snapshot 比较已证明频繁消耗过多上下文时，再考虑增加服务端 `compare_network_snapshot`。

### P0 验收

- [ ] 从 `/obj` 发现 Geometry 容器，并在其内部发现 Box SOP
- [ ] 非法 SOP/OBJ/VOP/LOP 上下文返回正确类别和相近类型建议
- [ ] 大型网络严格遵守节点数和响应大小上限
- [ ] Snapshot 相同内容产生稳定 Revision；网络变化后 Revision 改变
- [ ] Houdini 本地文档不可用时仍可发现类型，并报告文档降级

## P1：HDA Core

目标：面向技术美术优先交付稳定的 HDA 创建闭环。模型负责设计资产、选择参数和组织界面；MCP 负责读取真实 HOM 状态、验证完整计划，并在一个受控事务中创建、绑定、验证和失败回滚。首版不扩展成完整资产发布平台。

HDA MVP 只依赖 P0 节点发现、现有节点/参数能力和最小 Channel 保护，不必等待完整 Graph Patch 或动画能力完成。

### P1.1 统一身份模型

明确区分 HDA Instance、`hou.NodeType`、`hou.HDADefinition` 和 Library。

- [ ] 稳定 `definition_id` 由节点类别、完整类型名和规范化 `library_ref` 组成
- [ ] 易变的文件哈希、Definition 哈希和修改时间单独作为 `revision_token`
- [ ] 返回命名空间、基础名、版本、当前/首选 Definition、Lock 和可编辑状态
- [ ] 外部与 Embedded Library 使用可移植引用；执行时才解析本机绝对路径
- [ ] License 来自当前 Houdini/HOM 实际状态，不根据扩展名猜测

### P1.2 最小正式能力

- [x] `analyze_hda_candidate`
  - 只读检查 Subnetwork 是否支持 `createDigitalAsset`
  - 检查节点类别、边界输入输出、Locked HDA、外部引用、文件依赖和不可保存状态
  - 返回当前 License、允许的 Library 类型、目标冲突、阻塞项和警告
  - 从实时参数模板生成可提升参数候选，但由模型决定最终暴露内容
- [x] `search_hda_definitions`
  - 统一覆盖已安装 Library、Definition、类型、命名空间和版本搜索
  - 支持分页和父网络可实例化过滤
- [x] `get_hda_info`
  - 接受实例路径或 Definition ID
  - 返回身份、Lock、输入输出、Sections、依赖和可分页参数界面
- [x] `create_hda_from_subnetwork`
  - 只接受已经分析并验证的 Subnetwork，首版不同时折叠任意节点
  - 接受完整类型名、Label、Description、输入范围、外部 Library 和完整 Interface/Promotion 计划
  - `dry_run=true` 返回 `plan_id`、`candidate_revision`、解析后的目标和预计修改
  - 正式执行要求 `plan_id`、`expected_revision` 和 `idempotency_key`
  - 首版只允许不存在的新外部 Library，固定 `overwrite=false`
  - 在一次 Handler 调用中完成 Definition 创建、参数界面、参数提升、更新和验证
- [x] `apply_hda_interface_patch`
  - 用 Pydantic 判别联合添加、移动、替换和删除参数或 Folder
  - 支持普通参数提升，并建立 HDA 参数到内部参数的 Channel Reference
  - 删除、重命名或解除提升前报告实例值、表达式和内部引用影响
  - 接受 `expected_revision`；危险修改默认 `dry_run=true`
- [x] `validate_hda`
  - 检查身份、Library、参数界面、输入输出、Sections、依赖和权限
  - 创建或复用受控测试实例，设置测试参数、Cook、收集错误后清理
  - 返回 Definition/Library 哈希、`matchesCurrentDefinition` 和实例解析结果

### P1.3 参数界面与提升范围

首版正式支持：

- [ ] Float、Int、String、Toggle 和 Menu
- [ ] Vector、Color 和普通 Folder
- [ ] 标量与普通 Tuple Channel Reference
- [ ] 使用当前值或参数模板默认值作为 HDA 默认值
- [ ] 目标 Name、Label、Folder、范围和菜单覆盖

Ramp、Multiparm、Folder Set、Callback 和复杂条件界面留到第二阶段。遇到不支持的模板必须在 Dry Run 阶段明确拒绝，不能降级为错误类型。

### P1.4 稳定创建事务

`create_hda_from_subnetwork` 是高层事务边界，不是 `createDigitalAsset()` 的薄包装：

```text
验证 Plan 与 Candidate Revision
→ 记录 Subnetwork、连接、Flags 和目标文件状态
→ 创建新 Definition
→ 配置输入输出和正式参数界面
→ 建立参数提升与 Channel Reference
→ 更新 Definition
→ 创建/检查实例并 Cook
→ 验证 Library 和 Definition 哈希
→ 成功提交，失败执行补偿回滚
```

- [ ] 场景修改进入一个 Houdini Undo Group
- [ ] 磁盘 Library 不依赖 Undo，单独记录创建、安装和哈希状态
- [ ] 首版目标文件已存在时直接拒绝，不提供覆盖逃生参数
- [ ] 失败时撤销场景变化、卸载本次 Definition，并只删除本次新建文件
- [ ] 返回 `rolled_back`、`rollback_complete` 和 `residual_changes`
- [ ] 补偿失败时保留诊断与产物路径，不静默声称成功回滚
- [ ] 普通 HDA 创建不调用模型提供的任意 Python；只有脚本型 Section 以后才使用高风险门控

### P1.5 由模型与配方承担

- 决定资产边界、命名空间、基础名、版本和 Label
- 选择需要提升的参数、名称、Label、Folder 和默认值策略
- 根据候选分析结果修复外部引用和不适合封装的网络结构
- 比较两个 HDA 摘要并解释兼容性差异

### P1.6 后续按需晋升

以下能力保留在 Backlog，不阻塞 HDA Core 完成：

- Ramp、Multiparm、Folder Set 和复杂条件界面
- 断开参数绑定的自动修复
- Definition Diff、版本复制和实例迁移
- Python Module、Event Handler、Help、Icon 和资源 Section
- 发布 Manifest、干净会话安装验证和已有 Library 回滚
- Viewer State、Handles 和 Editable Nodes

脚本、Callback、Event Handler 和 Viewer State 写入必须 `allow_unsafe=true`。删除、覆盖和迁移还必须提供完整目标 ID、`expected_revision` 和显式确认。

### P1 验收

- [ ] 正确区分原生节点、HDA 类型、实例、Definition 和 Library
- [ ] Candidate Dry Run 能发现非法上下文、Locked 内容、外部引用、License 和目标冲突
- [ ] 将已有 `box -> transform -> normal` Subnetwork 创建为 `namespace::asset::1.0`
- [ ] 提升至少一个 Float、Vector 和 Menu 参数，并保持内部 Channel Reference
- [ ] 参数界面、输入输出、实例解析和 Cook 结果符合预期
- [ ] 已存在目标 Library 时拒绝执行且不改变场景
- [ ] 创建中途失败时恢复原 Subnetwork，并卸载/删除本次新建 Definition 和文件
- [ ] 回滚结果明确报告是否完整以及任何残留变化
- [ ] 同名、多命名空间、多版本和 Embedded Definition 不混淆
- [ ] Hybrid 公开 Tool 数量不因 HDA 能力增加

## P2：参数安全与原子图编辑

目标：用一个通用图修改能力承载大多数节点网络、材质网络和 LOP 网络构建。HDA MVP 之前先完成本节的 Channel 保护；完整 Graph Patch 可在 HDA Core 之后交付。

### P2.1 先保护 Channel

- [x] `set_parameters` 在写入前识别静态值、表达式、参数引用和关键帧
- [x] 默认拒绝覆盖已有表达式或关键帧
- [x] 增加显式 `overwrite_channel=false`，并报告会被替换的 Channel 类型
- [x] 全部参数先验证再写入；默认不再产生部分成功结果

### P2.2 `apply_graph_patch`

- [ ] 使用 Pydantic 判别联合定义操作：`create`、`delete`、`connect`、`disconnect`、`set_parameters`、`set_flags`、`rename` 和 `set_position`
- [ ] 支持请求内临时节点 ID，后续操作可引用新节点
- [ ] 支持 `dry_run=true`，执行完整类型、参数、连接和权限预检
- [x] 接受可选 `expected_revision` 和 `idempotency_key`
- [x] 限制单次操作数量、参数数量和响应大小
- [x] 成功 Patch 对应一个 Houdini Undo 步骤
- [x] 返回每项操作状态、真实节点路径、失败索引和最终 Snapshot Revision

### 原子性定义

`hou.undos.group()` 只负责合并撤销步骤，不等于异常自动回滚。`atomic=true` 必须采用：

```text
全量预检
→ 生成执行计划与反向操作日志
→ 执行
→ 失败时按日志反向补偿
→ 验证最终网络
→ 返回回滚是否完整及残留变化
```

- [ ] 所有操作在开始写入前完成静态预检
- [ ] `atomic=true` 下只允许有可靠反向操作的 Patch 类型
- [ ] 回滚失败返回 `rollback_complete=false` 和 `residual_changes`
- [ ] 不支持可靠补偿的操作在执行前拒绝，而不是假装原子
- [ ] `atomic=false` 必须显式传入，并返回部分结果

### 高级图变换暂不进入首版 Patch

以下操作涉及跨父网络迁移、边界连接重建或节点类型转换，先作为工作流配方和实验能力验证：

- [ ] 折叠节点为 Subnetwork
- [ ] 释放 Subnetwork
- [ ] 跨网络复制或移动节点
- [ ] 替换节点类型并迁移参数和连接

如果技术美术工作流需要把现有选择直接封装为 HDA，则优先把“折叠节点为 Subnetwork”晋升为专用原子能力；从零构建 HDA 时仍优先先创建 Subnetwork，再在内部构图。Subnetwork、Compile Block 和 For-Each Block 必须保持不同语义。

### P2 验收

- [ ] 单次 Patch 创建 `box -> transform -> normal` 并设置参数
- [ ] `dry_run` 不修改场景，同时返回真实类型和参数验证结果
- [ ] Patch 中途失败后不留下新节点或断开的连接
- [ ] 一个 `Ctrl+Z` 撤销整个成功 Patch
- [ ] 已有表达式或关键帧默认不会被静默覆盖
- [ ] Locked HDA、跨父网络连接和陈旧 Revision 返回保护性错误

## P3：MaterialX、Solaris 与 USD 检查

目标：作为 HDA 和图编辑之后的次级能力，优先复用通用节点发现与 Graph Patch，只为普通节点图无法表达的材质绑定和 USD Stage 事实增加只读能力。

### 由通用原语与配方完成

- 创建 Material Library、MaterialX 和 Karma 节点网络
- 设置 Shader 参数和连接 Shader 节点
- 创建和连接 LOP 节点
- 通过 LOP 网络配置 Reference、Sublayer、Variant、Visibility 和 Material Binding
- 配置 Karma ROP/LOP 节点参数

这些工作流使用当前 Houdini 注册类型与参数 Schema，不增加 `create_lop_node`、`set_shader_parameters`、`connect_shader_nodes` 等薄包装。

### 候选只读能力

- [x] `get_material_assignments`
  - 统一检查 OBJ/SOP/LOP 中的材质绑定摘要
- [x] `get_stage_snapshot`
  - 返回有界 Prim、Layer、Variant、Edit Target 和 Material Binding 摘要

只有在模型无法用 LOP Patch 安全表达时，才考虑直接 USD Prim 写入能力。默认持久编辑应通过 LOP 节点完成，不直接修改 Session Layer。

### P3 验收

- [ ] 模型通过发现、Schema 和 Patch 创建 MaterialX/Karma 网络
- [ ] 材质分配可跨 OBJ/SOP/LOP 检查
- [ ] Stage Snapshot 明确 Prim、Layer 和 Edit Target
- [ ] Solaris、Karma 或 License 不可用时返回明确原因

## 工作流配方

模型承担组合能力，需要稳定、可测试的配方支持，而不是继续增加 Tool。

- [ ] 为以下工作流提供版本感知的配方与最小示例：
  - SOP 基础建模网络
  - MaterialX + Karma 材质网络
  - Solaris Reference、Sublayer、Variant 和 Material Binding
  - 从已验证 Subnetwork 创建 HDA
- [ ] 配方只引用能力名和实时发现步骤，不硬编码完整节点/参数清单
- [ ] 配方包含失败分支、回滚方式和结果验证
- [ ] 配方在当前 Houdini headless 测试中定期验证

如果某个配方长期需要大量往返或频繁失败，再以真实证据提议专用 Catalog 能力。

## 生产级能力缺口（新增 Backlog）

当前 43 项能力足以完成节点发现、普通网络构建、参数修改、基础诊断、HDA 创建和只读 USD 检查，但“能够创建节点”不等于“能够独立交付镜头或资产”。以下缺口按真实制作阻塞程度排序。

### P0：异步任务与生命周期

目标：让模拟、缓存、渲染和导出不再受单次同步 TCP 调用及固定超时限制。

- [ ] 增加会话内 `JobRegistry`，为长任务返回稳定 `job_id`、类型、创建时间和当前状态
- [ ] 增加 `get_job_status`、`cancel_job` 和有界 `list_jobs`
- [ ] 状态至少区分 queued、running、succeeded、failed、cancelled 和 unknown
- [ ] 返回进度、当前帧、输出摘要、警告、错误和可安全重试标记
- [ ] Houdini/Shelf Server 重启后明确报告任务状态丢失，不把失联任务标记为成功
- [ ] 明确哪些 Houdini 操作可安全取消，不能取消的操作只提供停止后续帧或进程的补偿策略
- [ ] 长任务不占用共享请求/响应通道；普通只读查询仍可响应
- [ ] 同一幂等键重试不会重复提交缓存、导出或渲染任务

验收：提交 20 帧测试缓存或渲染，能够轮询进度、取消、识别部分产物，并在连接超时或服务器重启后返回真实状态。

### P0：生产文件、缓存、导入导出与发布

目标：形成“构建网络 → 生成产物 → 验证产物 → 发布”的磁盘交付闭环。

- [ ] 增加 File Cache/ROP 输出计划读取和执行能力，默认 Dry Run
- [ ] 支持受控的 BGEO、USD、Alembic 和 FBX 导入/导出；格式支持由当前 Houdini 节点与 License 动态判断
- [ ] 统一帧范围、步长、文件序列、`$HIP`/`$JOB`/环境变量展开和跨平台路径规范化
- [ ] 默认禁止覆盖已有缓存、HIP、HDA、USD 和渲染产物
- [ ] 输出前验证目标目录、真实解析路径、写权限、预计覆盖范围和可用空间
- [ ] 输出后验证文件存在、大小、帧完整性、时间戳和可选 SHA-256
- [ ] 返回发布 Manifest，记录 HIP Revision、输出节点、参数摘要、帧范围、产物和失败帧
- [ ] 支持缺帧、零字节文件、损坏文件和陈旧缓存检测
- [ ] 明确临时文件、部分输出和失败清理策略；不得依赖 Houdini Undo 回滚磁盘写入

验收：将 SOP 几何缓存为帧序列并发布 USD，在人为制造缺帧和已有目标时能够正确拒绝或报告，不产生未声明覆盖。

### P1：正式渲染链路

目标：从当前的视口/相机图像能力扩展到可跟踪、可验证的正式渲染交付。

- [ ] 发现当前会话可用的 Karma、Mantra 和第三方 ROP/LOP Render 节点
- [ ] 读取并验证相机、分辨率、帧范围、AOV、输出路径、采样和颜色管理摘要
- [ ] 通过异步任务提交单帧和帧序列渲染，并支持进度、取消和失败帧重试
- [ ] 验证输出图像存在、尺寸、通道/AOV、帧完整性和基础像素统计
- [ ] 检测全黑、全透明、NaN/Inf、明显过曝等基础失败模式
- [ ] 区分“渲染命令成功”和“图像通过验收”，不得只以进程退出码判定交付完成

验收：模板场景完成 Karma Turntable，输出序列和 AOV 完整；删除一帧或制造黑帧后验收必须失败并给出定位信息。

### P1：Solaris / USD Authoring

目标：在保留 LOP 节点优先原则的前提下，安全完成可持久化 USD 场景装配。

- [ ] 用节点发现、Schema 和 Graph Patch 验证 Reference、Sublayer、Payload、Variant、Collection 和 Configure Primitive 配方
- [ ] 验证 Material Library、Assign Material、Light、Camera、Render Settings 和 Karma 节点配方
- [ ] 增加 USD Layer 保存/导出计划、目标层身份、Edit Target 和覆盖保护
- [ ] 增加 Reference/Payload 资产路径和缺失依赖检查
- [ ] `get_stage_snapshot` 补齐 Variant Set/Selection、实例、Payload 加载状态和分页层栈摘要
- [ ] 只有 LOP 无法安全表达且有真实案例时，才增加直接 USD Prim 写入；默认禁止持久修改 Session Layer

验收：从空模板装配一个外部资产，创建 Variant、材质绑定、灯光和 Karma 设置，保存 USD 后在干净会话重新打开并通过 Stage Snapshot 验证。

### P1：动画、时间与 Channel

- [ ] 增加关键帧和表达式的分页读取能力
- [ ] 增加带 Dry Run、时间范围、Channel 覆盖保护和 Undo 的关键帧写入能力
- [ ] 支持插值、外推、关键帧删除和 Channel Revision 检查
- [ ] 增加全局帧范围、FPS、当前时间和播放范围读取/设置
- [ ] 保持表达式、参数引用和关键帧类型，不允许静默烘焙或覆盖

验收：创建并修改一条动画曲线，Revision 冲突和已有表达式时拒绝写入，一个 Undo 恢复整次修改。

### P2：模拟与领域工作流

优先通过通用节点能力和版本感知配方构建网络；只为任务生命周期、缓存边界和稳定高频事务增加专用能力。

- [ ] Vellum：约束、Solver、缓存和基础结果检查配方
- [ ] Pyro：Source、Sparse Solver、缓存、体积字段和渲染检查配方
- [ ] FLIP：Source、Solver、Meshing、缓存和粒子/表面检查配方
- [ ] RBD：分块、约束、Solver、缓存和断裂结果检查配方
- [ ] TOP/PDG：Graph Cook、Work Item 状态、失败重试和输出收集
- [ ] KineFX/APEX 只在有明确角色工作流案例后进入范围

验收不以“节点成功创建”为准，必须包含小规模模拟运行、缓存完整性、错误收集和可重复结果检查。

### P2：事务、恢复与可观测性

- [ ] Houdini 端缓存近期 `operation_id`/`idempotency_key` 结果，覆盖 TCP 超时后的安全重试
- [ ] Graph Patch 完成反向操作日志与失败补偿，不再仅依赖 Undo Group
- [ ] 为高风险场景修改增加可选 HIP Checkpoint/Save Copy，并明确恢复点
- [ ] 所有响应携带可关联的 `operation_id`；Bridge 与 Houdini 日志可按该 ID 检索
- [ ] 增加结构化耗时、Cook 时间、请求大小、返回大小和截断信息
- [ ] 区分调用失败、Cook 失败、任务失败、验收失败和回滚失败
- [ ] 本地 TCP 继续只绑定 loopback；若未来允许远程连接，必须先增加认证、授权和传输保护

### P2：结果语义验收

- [ ] 几何规则：边界、点面数量、属性、组、退化面、非流形和尺寸容差
- [ ] USD 规则：Prim 路径、类型、Layer、Variant、Binding、Payload 和依赖完整性
- [ ] 缓存规则：帧范围、缺帧、大小异常、拓扑变化策略和时间采样
- [ ] 图像规则：尺寸、通道、黑帧、透明帧、NaN/Inf 和曝光范围
- [ ] HDA 规则：接口兼容性、默认值、内部引用、干净会话安装和测试实例 Cook
- [ ] 验收规则使用严格 Schema，可保存到项目但不得执行任意模型生成代码

## 真实案例、Skill 与模板 HIP

Skill 和模板 HIP 是生产工作流层，不替代 MCP 底层能力：

- **MCP** 提供实时事实、原子操作、安全边界、任务生命周期和结果验证。
- **Skill** 描述任务规划、能力调用顺序、失败分支、恢复策略和验收标准。
- **模板 HIP** 提供稳定的网络上下文、输出目录、颜色管理、灯光、相机、渲染设置和命名约定。

### 首批端到端案例

- [ ] **程序化道具 → HDA → Turntable**
  - 从需求构建 SOP 网络并封装版本化 HDA
  - 提升参数、创建 MaterialX、生成 Turntable 和 Karma 输出
  - 在干净会话安装 HDA、Cook、渲染并验证产物
- [ ] **SOP 地形/散布 → 缓存 → USD 发布**
  - 构建地形和实例散布网络
  - 生成可恢复缓存、装配 LOP、发布 USD 和 Manifest
  - 验证 Prim、Payload/Reference、材质绑定和缺失依赖
- [ ] **Solaris 场景装配 → 灯光 → Karma 序列**
  - 从模板装配资产、Variant、材质、相机和灯光
  - 异步渲染帧序列和 AOV
  - 检查缺帧、黑帧、分辨率、通道和交付目录

### 每个案例的交付物

- [ ] 一个版本化、可重复执行的工作流 Skill
- [ ] 一个尽量精简且不包含项目私有绝对路径的模板 HIP
- [ ] 一份机器可读验收规则和期望产物 Manifest
- [ ] 一组 Houdini 21.0.440 headless/GUI 集成测试
- [ ] 一份失败注入记录：陈旧 Revision、已有目标、缺失资产、Cook 失败、任务取消和输出不完整

只有上述三个案例至少完整通过一个，才能把项目定义为“已介入真实生产工作流”；仅通过节点创建和技术单元测试仍定义为“通用执行层完成”。

## 路径与磁盘写入统一规则

- [ ] 使用 `pathlib`、Houdini 环境展开和规范化绝对路径进行执行时验证
- [ ] 不在 Schema 中使用 `C:/temp/` 等平台特定默认路径
- [ ] 默认禁止覆盖 HIP、HDA 和 USD 等磁盘产物
- [ ] 检查目标是否位于允许范围、父目录是否存在/可写以及符号链接后的真实目标
- [ ] 外部文件修改优先写临时文件，验证后再替换
- [ ] 返回产物大小、SHA-256、是否覆盖和备份/Manifest 引用
- [ ] License 决策来自当前 Houdini/HOM 能力，不根据扩展名猜测

## 测试矩阵

### Bridge 单元测试

- [ ] 参数校验、未知字段拒绝和判别联合错误
- [ ] Hybrid/Legacy 暴露、Catalog 搜索分页和多关键词评分
- [ ] 高风险、覆盖、Revision 和幂等门控
- [ ] DocRef、便携帮助发现和文档降级
- [ ] 动态 Availability 的 `available/unavailable/unknown`

### Houdini headless 集成测试

- [ ] 实时类型与参数发现
- [ ] Snapshot 限制、Revision 和 Graph Patch 原子补偿
- [ ] Channel 保护不覆盖已有表达式或关键帧
- [ ] HDA 创建、身份、参数界面、License 和覆盖保护
- [ ] MaterialX、LOP 和 USD 的可用能力按当前安装条件运行或跳过

### 故障注入

- [ ] TCP 超时后使用同一幂等键重试
- [ ] Patch 和 HDA 创建中途失败的补偿回滚
- [ ] 只读目录、磁盘不足、已有目标和失效路径
- [ ] Houdini 退出或 Shelf Server 重启时的明确错误

## 近期里程碑

### Milestone A：HDA 就绪基础

- [ ] 在现有 `find_nodes`、`get_parameter_schema` 和 SideFX Docs 基础上完成节点类型发现、Schema 和有界 Snapshot
- [ ] 完成 `set_parameters` Channel 保护和“全部验证后再写入”
- [ ] 只实现上述能力实际需要的响应、Availability 和分页增强
- [ ] 保持现有 8+3 Hybrid 表面和 31 项 Catalog 能力兼容
- [ ] Bridge 单元测试与新增发现能力的 headless 测试通过

### Milestone B：稳定 HDA MVP

- [ ] 完成 HDA Candidate 分析、Definition 搜索和统一身份读取
- [ ] 完成带 Dry Run、Plan、Revision 和幂等的 `create_hda_from_subnetwork`
- [ ] 完成常用参数界面、参数提升和内部 Channel Reference
- [ ] 完成实例 Cook、Library 哈希、覆盖保护和失败补偿验证
- [ ] 通过 `box -> transform -> normal` Subnetwork 创建版本化 HDA 的真实验收

### Milestone C：高效图编辑与次级领域

- [ ] 完成首版原子 `apply_graph_patch`，复用现有节点、参数、连接和 Flag Handler
- [ ] 根据实际 HDA 工作流决定是否晋升原子 Subnetwork 折叠能力
- [ ] 用通用原语与配方完成 MaterialX/Solaris 网络
- [ ] 只在确有需求时增加材质绑定和 Stage Snapshot 只读能力

## 暂不优先

- HDA Viewer State、Handles 和高级交互资产
- 完整 HDA 发布平台、跨项目依赖打包和自动市场发布
- Houdini UI 选择、Pane、Desktop 布局和高级视口交互控制
- CHOP 专用工作流、Takes 和 Bundles
- Python Panel 创建与编辑
- 第三方渲染器专用 Tool
- 第三方资产平台的更多直接集成

异步任务、正式 Render/USD Export、File Cache、动画和模拟验收已经提升到“生产级能力缺口”Backlog。它们仍应以真实案例驱动，避免为每个节点或领域建立重复的薄包装 Tool。

实验性需求仍可通过高风险 `execute_houdini_code` 处理，但该逃生口不替代稳定能力。只有调用模式稳定、Schema 严格、安全边界明确且能绑定官方文档后，才晋升为正式 Catalog 能力。

## 建议提交顺序

```text
feat: extend the existing catalog with live node discovery
feat: add bounded network snapshots on the current TCP bridge
fix: protect parameter channels from implicit overwrite
feat: add HDA candidate discovery and stable identity
feat: add transactional HDA creation from subnetworks
feat: add guarded HDA interface editing and parameter promotion
test: cover HDA license overwrite validation and rollback
feat: batch existing graph handlers into validated atomic patches
docs: add model-composed Houdini workflow recipes
test: cover retries graph rollback and production workflows
```

每个提交前运行相关单元测试；涉及 `hou` 的主要能力组还需通过 headless 集成测试。除非用户明确要求，不合并、不推送、不改变远程仓库。
