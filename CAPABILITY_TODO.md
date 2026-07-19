# Houdini MCP 能力扩展 TODO

本文档记录 Houdini MCP 在现有 Hybrid Tool Registry 基础上的扩展路线。
新增能力默认进入 Catalog，通过 `search_tools`、`get_tool_schema` 和
`call_tool` 使用；除非经过实际使用证明是高频入口，否则不增加直接暴露的
MCP Tool。

## 当前基线

- [x] 默认 Hybrid 模式：8 个高频直连工具 + 3 个目录/调度入口
- [x] 31 项内部 Catalog 能力
- [x] Typed Tool Registry、Pydantic 参数校验和高风险调用门控
- [x] Houdini 主线程 TCP Handler 和场景修改 Undo Group
- [x] 当前 Houdini 版本的 `hom.zip` / `nodes.zip` 官方文档搜索
- [x] Windows、macOS、Linux 动态 Houdini/帮助目录发现
- [x] 节点、参数、图连接、VEX、几何、基础材质、渲染和 HIP 能力

## 所有新增能力的完成标准

每一项能力完成前必须满足：

- [ ] 在 `houdini_catalog.py` 中使用严格 Pydantic 参数模型
- [ ] 注册名称、分类、说明、关键词、风险、变更标记和 Undo 信息
- [ ] 至少绑定一项有效的 SideFX 官方 `DocRef`
- [ ] 节点类型来自实时 `hou.nodeTypeCategories()`，不维护完整硬编码列表
- [ ] 参数定义来自实时 `hou.ParmTemplate` / `hou.Parm` 信息
- [ ] 成功和错误返回遵守统一 Envelope
- [ ] 修改场景的命令按能力加入单次 Undo Group
- [ ] 大型返回支持摘要、过滤或分页，避免撑大模型上下文
- [ ] Houdini GUI、版本或 License 不满足时返回明确的不可用原因
- [ ] 有 Registry 单元测试；涉及 `hou` 的能力有 headless 集成测试
- [ ] 不改变 Shelf、TCP `9876`、stdio、`uv run` 和部署注册方式
- [ ] 每个主要能力组通过测试后创建独立 Git commit

## P0：通用节点发现与原子图编辑

目标：让 Agent 在不猜测节点类型和参数的情况下构建完整节点网络，并减少
多次 TCP 往返。

### 节点类型发现

- [ ] `search_node_types`
  - 按父网络路径、节点类别、名称、描述和关键词搜索
  - 返回节点类型名、标签、类别、命名空间、版本和官方文档
  - 优先当前父网络中实际可创建的节点类型
- [ ] `get_node_type_schema`
  - 返回输入/输出、参数模板、默认值、菜单、范围和节点文档
  - 支持分页及参数名称过滤
  - 区分相同节点名的命名空间和版本

### 网络快照

- [ ] `get_network_snapshot`
  - 返回节点、连接、Flags、位置和可选参数摘要
  - 支持深度、节点数量、参数数量和结果大小限制
  - 默认不返回所有参数值和大型几何数据
- [ ] `compare_network_snapshot`
  - 比较预期节点图与当前节点图
  - 返回新增、缺失、连接变化和参数差异
  - 第一版只读，不自动修复

### 原子图修改

- [ ] `apply_graph_patch`
  - 支持 `create`、`delete`、`connect`、`disconnect`、`set_parameters`
  - 支持 `collapse_to_subnetwork` 和 `extract_subnetwork`
  - 支持请求内临时节点 ID，后续操作可引用新节点
  - 支持 `dry_run=true` 进行完整预检
  - 支持 `atomic=true`，任一步失败时不留下部分修改
  - 整组操作对应一个 Houdini Undo 步骤
  - 返回每项操作的状态、真实节点路径以及失败索引
  - 限制单次操作数量和结果大小
- [ ] `collapse_nodes_to_subnetwork`
  - 将同一父网络下的一组节点折叠进 Subnetwork
  - 自动建立 Subnet Input/Output 并重连跨边界连接
  - 返回新 Subnetwork 路径、内部节点映射和边界连接映射
  - 空 Subnetwork 继续使用通用 `create_node`，不重复实现
- [ ] `extract_subnetwork`
  - 将内部节点释放回父网络并恢复外部连接
  - 默认只接受已验证的 Subnetwork 类型
  - 可选删除释放后的空 Subnetwork
- [ ] `copy_nodes`
- [ ] `move_nodes`
- [ ] `replace_node_type`
  - 尽可能保留匹配参数和连接
  - 替换前返回不能迁移的参数与连接

Subnetwork 安全约束：

- [ ] 目标节点必须属于同一个父网络
- [ ] 根据 SOP、OBJ、VOP、LOP 等实时上下文选择可用 Subnetwork 类型
- [ ] `dry_run` 返回预计的输入、输出和连接重排，不修改场景
- [ ] Locked HDA 内默认禁止折叠或释放
- [ ] 操作必须原子化，失败时不留下部分移动或断开的连接
- [ ] 保留节点名称、位置、Flags 和可迁移的网络信息
- [ ] Subnetwork、Compile Block 和 For-Each Block 保持不同语义

### P0 验收场景

- [ ] 从 `/obj` 开始发现 Geometry 容器，在其内部发现并创建 Box SOP
- [ ] 单次 Patch 创建 `box -> transform -> normal` 并设置参数
- [ ] `dry_run` 不修改场景，同时返回真实类型和参数验证结果
- [ ] Patch 中途失败时不留下新节点
- [ ] 一个 `Ctrl+Z` 撤销整个成功 Patch
- [ ] 非法 SOP/OBJ/LOP 上下文返回可用类别和相近类型建议
- [ ] 折叠带有外部输入输出的节点链后，边界连接保持一致
- [ ] 释放 Subnetwork 后恢复原节点链，并可单步 Undo
- [ ] Locked HDA、跨父网络节点和不兼容上下文返回保护性错误

建议提交：

```text
feat: add live Houdini node type discovery
feat: add bounded network snapshots
feat: add atomic graph patch operations
feat: add guarded subnetwork collapse and extraction
test: cover node discovery snapshots graph patches and subnetworks
```

## P1：表达式、通道与关键帧

目标：正式支持动画，同时避免静态参数写入意外破坏已有 Channel。

- [ ] `get_channel_info`
  - 区分静态值、表达式、参数引用和关键帧
- [ ] `set_parameter_expression`
  - 明确表达式语言：HScript 或 Python
  - 默认禁止覆盖已有关键帧，除非显式允许
- [ ] `clear_parameter_expression`
- [ ] `get_keyframes`
  - 支持帧范围和分页
- [ ] `set_keyframes`
  - 支持 float/string keyframe、值、斜率和加速度
  - 多个关键帧作为一个 Undo 步骤
- [ ] `delete_keyframes`
  - 必须指定参数和帧范围，不提供无界全场景删除
- [ ] `set_keyframe_interpolation`
- [ ] `get_playbar_info`
- [ ] `set_frame_range`
- [ ] `set_current_frame`

官方依据至少覆盖：

- [ ] `hou.Parm`
- [ ] `hou.Keyframe`
- [ ] `hou.StringKeyframe`
- [ ] `hou.playbar`
- [ ] Houdini Expression Language 文档

### P1 验收场景

- [ ] 读取已有静态值、表达式和关键帧时能正确分类
- [ ] 默认操作不会静默覆盖现有动画
- [ ] 为 Transform 的 `tx` 写入三个关键帧并正确读取
- [ ] 删除限定范围关键帧后可单步 Undo
- [ ] headless 模式与 GUI 模式的时间轴行为一致

建议提交：

```text
feat: add channel expression inspection and editing
feat: add typed Houdini keyframe capabilities
test: cover expression and keyframe safety
```

## P2：HDA 数字资产

目标：覆盖 HDA 查询、安装、创建和安全版本管理。

- [ ] `list_hda_definitions`
- [ ] `get_hda_definition_info`
- [ ] `install_hda_library`
- [ ] `uninstall_hda_library`
- [ ] `create_hda`
- [ ] `update_hda_definition`
- [ ] `match_current_definition`
- [ ] `get_spare_parameter_schema`
- [ ] `add_spare_parameters`
- [ ] `sync_node_version`

安全要求：

- [ ] 默认禁止覆盖现有 Definition 或 HDA 文件
- [ ] 区分 Embedded Definition 与外部 `.hda` / `.otl`
- [ ] 修改前返回 Library 路径、节点类型和版本信息
- [ ] 文件路径在运行时解析，不存储机器绝对路径
- [ ] 写 Definition 前支持预检和备份策略

建议提交：

```text
feat: add HDA definition discovery
feat: add guarded HDA library and definition editing
test: cover HDA overwrite and version safety
```

## P3：MaterialX、材质网络与 Karma

目标：从基础材质分配扩展到可检查、可编辑的现代 Houdini 渲染工作流。

- [ ] `get_material_info`
- [ ] `find_material_assignments`
- [ ] `create_material_network`
- [ ] `create_mtlx_material`
- [ ] `set_shader_parameters`
- [ ] `connect_shader_nodes`
- [ ] `assign_material`
- [ ] `configure_karma_rop`
- [ ] `configure_karma_lop`
- [ ] `render_to_disk`
- [ ] `get_render_status`
- [ ] `cancel_render`

约束：

- [ ] Shader、VOP、LOP 类型从当前 Houdini 注册类型中选择
- [ ] 优先 MaterialX/Karma，传统 SHOP/VOP 保留兼容路径
- [ ] 输出文件默认禁止覆盖
- [ ] 长时间渲染不阻塞一次 MCP 请求，使用任务状态查询

## P4：Solaris、LOP 与 USD

目标：提供版本感知且明确 Edit Target 的 USD 操作。

- [ ] `get_stage_info`
- [ ] `find_prims`
- [ ] `get_prim_info`
- [ ] `create_lop_node`
- [ ] `set_prim_attribute`
- [ ] `set_prim_variant`
- [ ] `set_prim_visibility`
- [ ] `create_sublayer`
- [ ] `configure_reference`
- [ ] `configure_material_binding`
- [ ] `export_usd`

约束：

- [ ] 默认通过 LOP 节点进行持久编辑
- [ ] 明确区分 Session Layer、Root Layer 和 LOP 网络
- [ ] 所有写入返回 Prim Path、Layer 和 Edit Target
- [ ] USD 导出默认禁止覆盖文件
- [ ] Solaris/USD 不可用时仍允许搜索并返回不可用原因

## P5：异步任务基础设施

目标：为渲染、模拟、缓存和 PDG 提供不阻塞 Bridge 的统一任务模型。

- [ ] 内部 `JobRegistry`
- [ ] `get_job_status`
- [ ] `cancel_job`
- [ ] 任务 ID、类型、状态、进度、开始/结束时间和简短日志
- [ ] 任务结果有大小上限，较大产物只返回路径和摘要
- [ ] Houdini 退出或 Shelf Server 重启后返回明确的任务失效状态
- [ ] 限制并发任务数
- [ ] 不允许后台线程直接调用非线程安全的 `hou` UI API

只有实际证明高频后，才考虑将通用任务查询提升为直接 MCP Tool。

## P6：模拟与缓存

- [ ] `get_simulation_info`
- [ ] `configure_simulation_range`
- [ ] `reset_simulation`
- [ ] `start_simulation_job`
- [ ] `get_dop_object_info`
- [ ] `get_cache_status`
- [ ] `configure_file_cache`
- [ ] `start_file_cache_job`
- [ ] `validate_cache_path`

安全要求：

- [ ] 帧范围、Cook 时长和磁盘写入有明确上限
- [ ] 缓存覆盖必须显式允许
- [ ] 启动前检查目录、剩余空间和节点错误
- [ ] 支持取消与失败后的清晰诊断

## P7：TOP/PDG

- [ ] `get_pdg_graph_info`
- [ ] `generate_work_items`
- [ ] `start_pdg_cook`
- [ ] `get_work_item_status`
- [ ] `get_work_item_result`
- [ ] `cancel_pdg_cook`
- [ ] `dirty_pdg_node`

PDG Cook 必须使用 P5 的异步任务模型，不在一次 MCP 请求中同步等待整个图完成。

## P8：Houdini UI 与视口

目标：只在 Houdini GUI 会话中提供可选的交互辅助能力。

- [ ] `get_ui_context`
- [ ] `get_current_network`
- [ ] `get_selected_nodes`
- [ ] `select_nodes`
- [ ] `frame_nodes`
- [ ] `set_network_editor_path`
- [ ] `get_viewport_state`
- [ ] `set_viewport_camera`

约束：

- [ ] 使用 `hou.isUIAvailable()` 进行可用性判断
- [ ] `hython` 中可搜索但标记为不可用
- [ ] UI Tool 不成为场景自动化能力的依赖
- [ ] 选择和视口操作与场景持久修改分开标记

## 暂不优先

- [ ] CHOP 专用工作流
- [ ] Takes 和 Bundles
- [ ] Python Panel 创建与编辑
- [ ] Desktop/Pane 布局持久化
- [ ] 第三方渲染器专用 Tool
- [ ] 第三方资产平台的更多直接集成

这些领域继续可通过 `execute_houdini_code` 处理实验性需求。只有调用模式稳定、
能定义严格 Schema、能绑定官方文档并有明确安全边界后，再升级为正式 Catalog
能力。

## 近期建议里程碑

### Milestone A：可靠构图

- [ ] 完成 `search_node_types`
- [ ] 完成 `get_node_type_schema`
- [ ] 完成 `get_network_snapshot`
- [ ] 完成 `apply_graph_patch`
- [ ] 完成 `collapse_nodes_to_subnetwork`
- [ ] 完成 `extract_subnetwork`
- [ ] 通过单元测试和 Houdini headless 集成测试

### Milestone B：参数不会破坏动画

- [ ] `set_parameters` 检测已有表达式/关键帧并返回保护性错误
- [ ] 完成表达式查询和设置
- [ ] 完成关键帧查询、写入和删除
- [ ] 验证单步 Undo

### Milestone C：生产资产与渲染

- [ ] 完成 HDA 发现与只读检查
- [ ] 完成 MaterialX 材质网络基础能力
- [ ] 建立异步 Job 基础设施
- [ ] 完成 Karma 渲染任务状态查询

## 公开 MCP Tool 数量策略

- [ ] 默认 Hybrid 公开面保持紧凑
- [ ] 新能力默认只进入 Catalog
- [ ] 只有跨领域、高频、参数稳定且能显著减少目录调用的能力才考虑直连
- [ ] 任何新增直连 Tool 都要增加 Hybrid/Legacy 暴露测试
- [ ] `execute_houdini_code` 保留高风险逃生口，但不代替正式能力实现
