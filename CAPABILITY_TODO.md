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

## P2：完整 HDA 全流程 Automation

目标：让 MCP 可以把已创建的节点网络安全地转化为可安装、可复用、可升级、
可验证、可回滚的 Houdini Digital Asset。P2 覆盖 HDA 的生产闭环，不仅是
创建 `.hda` 文件。

完整闭环：

```text
发现 HDA 与 Library
→ 分析现有网络是否适合封装
→ 折叠或使用已有 Subnetwork
→ 创建 HDA Definition
→ 配置输入输出
→ 构建参数界面并提升内部参数
→ 添加脚本、帮助、图标与资源
→ 配置命名空间和版本
→ 分析依赖并执行验证
→ 发布、安装并创建测试实例
→ 升级已有实例
→ 出错时回滚 Definition 或 Library
```

### P2.0：统一 HDA 对象模型

所有 HDA Tool 必须明确区分：

- [ ] HDA 实例：场景中的 `hou.Node`
- [ ] 节点类型：`hou.NodeType`
- [ ] Definition：`hou.HDADefinition`
- [ ] Library：外部 `.hda` / `.otl` 或 Houdini Embedded Library
- [ ] Type Name：类别、命名空间、核心名称和版本
- [ ] Current Definition、Preferred Definition 和同名冲突 Definition
- [ ] Locked、Uneditable、Editable Nodes 和 Allow Editing of Contents 状态

所有返回统一包含可获得的：

- [ ] `node_type_name`
- [ ] `category`
- [ ] `namespace`
- [ ] `base_name`
- [ ] `version`
- [ ] `definition_id`
- [ ] 可移植 `library_ref`；执行时才解析绝对路径
- [ ] `is_embedded`、`is_installed`、`is_current`、`is_preferred`
- [ ] `is_locked`、`matches_definition`、`is_editable`
- [ ] Definition 修改时间、输入输出范围和实例数量摘要

`definition_id` 必须由节点类别、完整类型名、Library 身份和 Definition 元数据
组合生成，禁止只按短类型名修改 Definition。

### P2.1：HDA 发现、检查与实例化

- [ ] `search_hda_types`
  - 按名称、标签、类别、命名空间、版本和 Library 搜索
  - 区分原生节点与 `node_type.definition() != None` 的 HDA
  - 返回当前父网络中实际可实例化的 HDA 类型
- [ ] `list_hda_libraries`
  - 返回已安装 Library、Embedded Library 和 Definition 数量
  - 默认不递归扫描整块磁盘
- [ ] `list_hda_definitions`
  - 支持 Library、类别、命名空间和版本过滤及分页
- [ ] `get_hda_definition_info`
  - 返回 Type Name 组成、Library、版本、Sections、参数、输入输出和权限摘要
- [ ] `get_hda_instance_info`
  - 返回实例路径、Definition、Lock 状态、是否匹配 Definition 和本地改动摘要
- [ ] `get_hda_parameter_schema`
  - 复用实时 `hou.ParmTemplateGroup`，返回正式 HDA 参数而非只看实例值
- [ ] `create_hda_instance`
  - 在兼容父网络中创建指定 Definition 的实例
  - 同名多版本时必须使用完整类型名或明确的 Definition ID
- [ ] `install_hda_library`
  - 默认只安装明确指定的单个 Library
  - 返回新增、替换、冲突和 Preferred Definition 变化
- [ ] `uninstall_hda_library`
  - 执行前检查当前 HIP 是否仍有实例依赖
  - 默认拒绝卸载仍被使用的 Library

### P2.2：封装候选分析与 HDA 创建

- [ ] `analyze_hda_candidate`
  - 接受 Subnetwork 或同一父网络下的一组节点
  - 检查跨边界连接、节点引用、表达式、文件依赖、Locked HDA 和不可保存状态
  - 返回建议输入输出、可提升参数、内部依赖和阻塞问题
  - 只读，不修改场景或磁盘
- [ ] `plan_hda_creation`
  - 生成完整创建计划和预计文件/Definition 变化
  - 支持 `embedded` 或外部 Library 目标
  - 检查类型名、命名空间、版本和目标文件冲突
- [ ] `create_hda_from_subnetwork`
  - 将已有 Subnetwork 转换为 HDA Definition
  - 可选先调用 P0 的 `collapse_nodes_to_subnetwork`
  - 支持 Operator Name、Label、Description、命名空间和版本
  - 支持最小/最大输入数量及输出数量
  - 默认 `overwrite=false`
  - 成功后返回 Definition、实例、Library 和回滚信息
- [ ] `create_hda_from_nodes`
  - 组合“折叠节点 + 创建 HDA”为一个原子工作流
  - 任一步失败时恢复原节点、位置和连接
- [ ] `set_hda_input_output_schema`
  - 设置输入数量范围、输入标签、输出标签和连接说明
  - 验证 Subnet Connector 与 Definition Schema 一致

创建 HDA 时不得根据文件扩展名猜测 License。由当前 Houdini License 和 HOM
实际能力验证 `.hda`、`.hdalc`、`.hdanc` 等目标是否允许。

### P2.3：正式参数界面与内部参数提升

Spare Parameter 与 HDA Definition 参数必须作为不同能力处理。HDA 正式界面
以 `hou.ParmTemplateGroup` 为事实来源。

- [ ] `get_hda_interface_schema`
  - 返回 Folder、Folder Set、参数顺序、类型、默认值、范围、菜单和 Tags
  - 返回 `disable_when`、`hide_when`、Join、Label、Help 和 Callback 摘要
- [ ] `validate_hda_interface_patch`
  - 在写 Definition 前检查名称冲突、无效条件、非法菜单和不兼容模板
  - `dry_run` 返回最终界面摘要
- [ ] `apply_hda_interface_patch`
  - 声明式支持添加、替换、移动和删除参数或 Folder
  - 支持 Float、Int、String、File、Toggle、Button、Menu、Ordinal Menu
  - 支持 Vector、Color、Ramp、Folder、Folder Set 和 Multiparm Block
  - 删除或重命名参数前报告现有实例值、表达式和内部引用影响
- [ ] `promote_hda_parameters`
  - 将一个或多个内部参数提升到 HDA Definition
  - 自动创建 HDA 参数到内部参数的引用
  - 支持使用当前值或原始默认值作为 HDA 默认值
  - 支持目标 Folder、Label、Name 和范围覆盖
  - 返回每个 HDA 参数到内部参数的映射
- [ ] `unpromote_hda_parameters`
  - 删除提升关系前选择保留当前求值、恢复内部默认值或取消
- [ ] `get_hda_parameter_bindings`
  - 检查 HDA 参数与内部参数、表达式和 Channel Reference 的映射
- [ ] `repair_hda_parameter_bindings`
  - 只修复明确确认且可无损恢复的断开引用
- [ ] `set_hda_parameter_callback`
  - 回调脚本属于高风险写入，必须 `allow_unsafe=true`
  - 明确 Python/HScript 语言并限制脚本大小

### P2.4：Definition 编辑、锁定与实例同步

- [ ] `update_hda_definition_from_instance`
  - 保存当前实例内容到 Definition
  - 修改前比较实例与 Definition，并返回结构化差异
  - 默认要求实例已显式进入可编辑状态
- [ ] `allow_editing_hda_contents`
  - 修改实例 Lock 状态前返回影响和当前 Definition
- [ ] `match_current_definition`
  - 丢弃实例本地改动前必须显式确认
- [ ] `revert_hda_instance`
  - 支持只恢复参数、只恢复内容或完整恢复
- [ ] `sync_hda_instances`
  - 按节点路径、Definition 或 HIP 范围同步实例
  - 默认只生成同步计划，不直接修改所有实例
- [ ] `copy_hda_definition`
  - 用于新命名空间、新版本或新 Library
  - 保留源 Definition，不默认替换
- [ ] `rename_hda_definition`
  - 通过安全复制、验证和可选迁移实现，不原地猜测重命名
- [ ] `delete_hda_definition`
  - 高风险操作；检查实例、嵌套依赖和 Preferred Definition
  - 必须 `allow_unsafe=true` 且显式传入 Definition ID
- [ ] `set_preferred_hda_definition`
  - 同名多 Definition 时显式控制解析优先级
- [ ] `get_hda_definition_diff`
  - 比较内部节点、连接、参数界面、Sections、版本和输入输出 Schema

### P2.5：命名空间、版本与迁移

- [ ] `parse_hda_type_name`
  - 返回类别、命名空间、核心名称和版本，不自行切割字符串猜测
- [ ] `plan_hda_version_upgrade`
  - 比较源/目标 Definition 和参数 Schema
  - 返回参数迁移、重命名、删除、默认值变化和实例影响
- [ ] `create_hda_version`
  - 从现有 Definition 复制为新版本
  - 默认保留旧版本并安装新版本
- [ ] `set_hda_version_metadata`
  - 写入版本、变更摘要和可选兼容范围
- [ ] `migrate_hda_instances`
  - 将明确范围内的实例迁移到目标完整类型名
  - 保存可映射参数、输入连接、输出连接、位置、名称和 Flags
  - 不可迁移数据必须先报告，默认不丢弃
- [ ] `rollback_hda_instances`
  - 使用迁移前 Manifest 将实例恢复到旧 Definition

版本操作必须优先采用“创建新 Definition → 验证 → 迁移实例”，避免直接覆盖
正在生产使用的旧 Definition。

### P2.6：Sections、脚本、帮助、图标与内嵌资源

- [ ] `list_hda_sections`
- [ ] `get_hda_section`
  - 文本 Section 返回大小受限摘要或分页内容
  - 二进制 Section 默认只返回元数据和哈希
- [ ] `set_hda_section`
  - 覆盖前返回原 Section 哈希并创建回滚记录
  - 脚本和可执行 Section 必须 `allow_unsafe=true`
- [ ] `delete_hda_section`
  - 高风险；默认禁止删除 Houdini 必需 Section
- [ ] `set_hda_python_module`
- [ ] `set_hda_event_handler`
  - 覆盖 OnCreated、OnLoaded、OnUpdated、OnDeleted 等事件
  - 明确事件名、语言、大小限制和风险
- [ ] `set_hda_help`
  - 支持 Help 文本与 SideFX 文档引用
- [ ] `set_hda_icon`
  - 支持图标名称或受控资源，不把任意大文件塞进 Definition
- [ ] `embed_hda_resource`
  - 嵌入配置、模板和小型资源
  - 限制类型、单文件大小和 Definition 总大小
- [ ] `extract_hda_resource`
  - 默认禁止覆盖磁盘目标
- [ ] `get_hda_resource_manifest`
  - 返回 Section 名称、类型、大小和 SHA-256，不直接返回全部二进制

### P2.7：Viewer State、Handles 与高级交互

- [ ] `get_hda_interaction_schema`
  - 返回 Handle、Viewer State、State Script 和绑定参数摘要
- [ ] `set_hda_handles`
  - 配置参数 Handle 与参数绑定
- [ ] `set_hda_viewer_state`
  - Viewer State 脚本属于高风险写入，必须 `allow_unsafe=true`
- [ ] `validate_hda_viewer_state`
  - 静态检查注册信息和脚本；GUI 会话中可执行交互验证
- [ ] `set_hda_editable_nodes`
  - 明确 Editable Nodes 列表及资产锁定后的行为

这些能力可以写入 Definition，但实际交互验收要求 `hou.isUIAvailable()`；在
`hython` 中应可发现、可静态检查，并标记动态验证不可用。

### P2.8：依赖分析与可移植性

- [ ] `analyze_hda_dependencies`
  - 分析嵌套 HDA、节点类型、外部文件参数、Python Module 和资源引用
  - 区分 Houdini 内置依赖、项目依赖和机器绝对路径
- [ ] `find_missing_hda_dependencies`
- [ ] `find_external_hda_paths`
  - 检测用户名、盘符、临时目录和版本目录硬编码
- [ ] `remap_hda_paths`
  - 只按明确规则改写 `$HIP`、`$JOB` 或项目变量
  - 默认 `dry_run=true`
- [ ] `get_hda_dependency_manifest`
  - 输出可移植 Manifest，不复制 SideFX 自带文件
- [ ] `validate_hda_portability`
  - 在不安装额外依赖的干净会话中检查类型和文件引用

### P2.9：验证、发布、安装与回滚闭环

- [ ] `validate_hda_definition`
  - 检查 Type Name、Library、参数界面、输入输出、Sections、依赖和权限
- [ ] `test_hda_instance`
  - 在临时网络创建实例、设置测试参数、Cook、检查错误后清理
  - 测试修改在单独 Undo/临时 HIP 范围内完成
- [ ] `create_hda_release_manifest`
  - 记录完整类型名、版本、Library 哈希、依赖、测试结果和 Houdini 版本
- [ ] `publish_hda_library`
  - 发布前强制执行验证和实例 Smoke Test
  - 默认发布到新文件，不覆盖已有 Release
  - 返回产物路径、SHA-256 和 Manifest
- [ ] `install_and_verify_hda_release`
  - 安装发布产物并创建新实例验证解析到正确 Definition
- [ ] `backup_hda_library`
  - 修改外部 Library 前创建显式备份或版本化副本
- [ ] `rollback_hda_library`
  - 根据备份和 Manifest 恢复，并重新验证已安装 Definition
- [ ] `unpublish_hda_release`
  - 不直接删除；优先移出搜索路径或标记弃用
  - 仍被 HIP/HDA 依赖时拒绝执行

发布结果必须能在另一个 Houdini 会话中完成：

```text
安装 Library
→ 找到指定完整类型名和版本
→ 创建实例
→ 参数 Schema 与 Manifest 一致
→ Cook 无错误
→ 输入输出连接有效
→ 卸载或回滚后环境恢复
```

### P2.10：安全、事务与权限规则

- [ ] 所有写操作先支持 `dry_run` 或独立 Plan Tool
- [ ] 默认禁止覆盖 HDA 文件、Definition、Section 和 Release
- [ ] Definition 写入前记录文件哈希、Definition ID 和修改时间，防止并发覆盖
- [ ] 外部文件修改采用临时文件验证后再原子替换
- [ ] Embedded Definition 修改前要求 HIP 有可恢复保存点
- [ ] 修改 Definition 时报告受影响实例数量和路径摘要
- [ ] 修改正在使用的 Definition 默认创建新版本，不原地覆盖
- [ ] 写 Python/HScript、Callbacks、Event Handlers、Viewer State 必须
  `allow_unsafe=true`
- [ ] 删除 Definition、Library、Section 或不可逆迁移必须高风险门控
- [ ] 不将 HDA 二进制内容、密钥或大型资源放入 MCP 返回上下文
- [ ] 遵守当前 Houdini License，不尝试绕过 Commercial/Indie/Apprentice 限制
- [ ] 所有路径使用 `pathlib`、环境展开和平台适配，不写死盘符或用户名
- [ ] 场景内修改支持 Undo；磁盘 Library 修改使用备份/Manifest 回滚

### P2.11：SideFX 官方文档绑定

HDA Registry Tool 至少绑定下列实际相关文档之一，并由测试验证对应 DocRef 在
当前 Houdini 官方帮助中存在：

- [ ] `hou.HDADefinition`
- [ ] `hou.HDASection`
- [ ] `hou.NodeType`
- [ ] `hou.NodeTypeCategory`
- [ ] `hou.Node`
- [ ] `hou.hda`
- [ ] `hou.ParmTemplateGroup`
- [ ] `hou.ParmTemplate` 及具体参数模板类型
- [ ] `hou.ViewerStateTemplate`
- [ ] Houdini Digital Assets 用户文档
- [ ] Operator Type Properties、Namespacing、Versioning 和 Safeguarding 文档

文档不可用时 HDA Tool 继续执行，但返回 `docs_status: degraded`；不得联网抓取
文档作为运行时前置条件。

### P2.12：HDA 测试矩阵与验收场景

只读与发现：

- [ ] 正确区分原生节点与 HDA 节点类型
- [ ] 多 Library、同名、多命名空间和多版本结果不混淆
- [ ] Embedded 与外部 Definition 返回正确身份

创建与参数：

- [ ] 将 P0 创建的 `box -> transform -> normal` 网络折叠并打包为 HDA
- [ ] 自动暴露 Size、Translate、Seed 等内部参数并保持 Channel Reference
- [ ] 创建 Folder、Menu、Ramp 和 Multiparm 后 Schema 可完整读取
- [ ] 输入输出连接在创建 HDA 前后保持一致
- [ ] 创建失败时恢复原 Subnetwork、连接和磁盘状态

Definition 与版本：

- [ ] 修改一个实例后生成 Definition Diff
- [ ] 从 `namespace::asset::1.0` 创建 `namespace::asset::2.0`
- [ ] 迁移实例时保留参数、连接、名称、位置和 Flags
- [ ] 不兼容参数在迁移前被报告，不静默丢失
- [ ] 能使用 Manifest 将实例和 Library 回滚到旧版本

资源与脚本：

- [ ] Help、Icon、小型资源和 Python Module 可写入并重新读取
- [ ] 未传 `allow_unsafe=true` 时拒绝可执行脚本写入
- [ ] 大型/非法二进制资源被大小和类型门控拒绝

依赖与发布：

- [ ] 检测嵌套 HDA 和缺失节点类型
- [ ] 检测硬编码用户名、盘符和临时路径
- [ ] Release Manifest 包含版本、哈希、依赖和测试结果
- [ ] 在新的 headless Houdini 会话安装、实例化、Cook、卸载成功
- [ ] 无 HDA 文件、只读目录、License 不匹配时安全降级且不留下残留文件

### P2 建议实现阶段与提交

```text
feat: add typed HDA library definition and instance discovery
test: cover HDA identity namespaces versions and embedded libraries

feat: add planned HDA creation from subnetworks
feat: add HDA input output schema automation
test: cover atomic HDA creation and connection preservation

feat: add declarative HDA parameter interface editing
feat: add guarded internal parameter promotion and binding inspection
test: cover HDA folders ramps multiparms and parameter bindings

feat: add HDA definition diff locking and instance synchronization
feat: add versioned HDA definition and instance migration workflows
test: cover HDA migration compatibility and rollback

feat: add guarded HDA sections scripts help icons and resources
feat: add optional HDA viewer state and handle metadata automation
test: cover HDA resource limits unsafe gates and UI availability

feat: add HDA dependency and portability analysis
feat: add validated HDA release publishing and installation
test: cover clean-session HDA release verification and rollback

docs: document end-to-end HDA automation workflows
```

### P2 完成定义

P2 只有在下面的真实闭环通过后才算完成：

- [ ] Agent 从普通节点网络创建带版本的 HDA
- [ ] 自动生成正式参数界面并将参数绑定到内部节点
- [ ] HDA 带有正确输入输出、帮助、图标和依赖 Manifest
- [ ] 发布到新 Library，并在全新 Houdini 会话安装
- [ ] 新实例参数、连接、Cook 和输出符合预期
- [ ] 从旧版本升级到新版本且不丢失可迁移数据
- [ ] 一次失败发布不会破坏原 Definition 或现有实例
- [ ] 能使用备份和 Release Manifest 完整回滚
- [ ] Hybrid MCP 公开 Tool 数量不因 HDA 子能力数量显著增长

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
