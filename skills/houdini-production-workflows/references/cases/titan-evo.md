# Titan EVO — HDA 设计参考案例集

2026-11-05 收录用户指定的权威参考资料。随包 `README.md` 自述为
“Project Titan EVO / SideFX learning demo”。这里记录的是这份本地包的结构证据，
未独立核验其下载来源、完整性或再分发许可；不复制二进制资产进入经验库。

来源定位：`Titan_EVO_UE_Project_and_HDAs/otls/`，相对于用户提供的项目资料根目录。
18 个库各包含一个 SOP HDA 定义。逐资产类型名、输入数量、参数示例、Labs
依赖、节点定位和 SHA256 见 [asset inventory](titan-evo/asset-inventory.json)。
Case：`titan-evo-hda-design-reference`；Experience：
`exp-titan-evo-hda-reference-intake`。二者是同一次资料整理，不是两次独立执行。

## 环境与证据范围

- 包内 README 声明 Houdini 22、Unreal Engine 5.8、Houdini Engine 和 SideFX Labs。
  这是包的声明，不是本轮兼容性认证。
- 本轮在隔离 Hython 21.0.440、Manual 更新模式下，使用
  `scripts/inspect_houdini_case.py` 的检查函数读取定义和内部结构，并补充参数与
  VEX/字符串引用定位。未连接或改动用户当前 Houdini 场景。
- 读取到 4,469 个节点，包含 HDA 根节点及当前安装版本展开的内置/Labs 子网络。
  这个数不是原创节点量、Cook 成本或优化指标；类型计数每个资产最多保留 100 项。
- 没有显式请求 Cook、读取输出几何、模拟、缓存、导出或保存。初始化过程中仍观察到
  4 个节点各一次 Cook：`electric_pole/timeshift2`、
  `stackingTool/Data_table_example` 和建筑生成器的两个 `Model_example` Stash。
  因此不能声称绝对零 Cook。其定位保存在 inventory，未发现模拟求解器 Cook 记录。
- 全部 18 个源 HDA 的检查后 SHA256 与检查前相同。未执行安装 BAT；未写入用户
  Houdini package 配置，未安装新的依赖，未触发保存按钮或更改源资产锁定状态。
  隔离进程内为检查解锁的实例已销毁。
- 本轮没有参数响应、最终几何、性能、UE 导入或画面验收；记录保持 `candidate`。
  来源参考价值与本地运行成熟度分别判断。

## 优先复用的设计经验

| 设计问题 | 资产内的结构证据 | 后续制作时如何使用 |
|---|---|---|
| 电缆需要下垂与碰撞，但必须快速交互 | `Titan_Cable_tool.hda`：`global_gravity`、`sub_wire_gravity`、碰撞迭代与射线采样控制；作者 Sticky Note 明确碰撞是后处理 | 先评估曲线变形加后处理是否满足视觉需求，再决定是否需要 Vellum；碰撞体厚度与薄物体限制需独立测试 |
| 模块系统既要可替换，又要处理交叠 | `Titan_Scaffold.hda`：`scaffold_datatable`、`merge_inputs`、`resolve_overlap`；`column_dict`、`xform3`、`get_xform_and_iteration`、`handle_intersections`、`unreal_instance` | 分开数据表字段映射、稳定局部坐标、单元分类和实例路径解析；先验证字段、尺寸、空列表与资产路径 |
| 栏杆、轨道要保持方向与可控变体 | `Titan_Fence_Tool.hda`：`orientalongcurve`、Seed、权重和 AssetPath 参数；`Titan_Train_rails.hda`：按 `restlength` 分类再设置实例 | 在曲线清理、重采样、朝向、分类、引擎实例几个边界检查属性；长度阈值等于边界值的情况也要测试 |
| 建筑由数据与规则共同驱动 | `Tutorial_Building_Generator.hda`：Mesh/Floor DataTable、Labs pattern 节点、屋顶独立逻辑；Sticky Note 说明重复语法与排序差异 | 把数据结构、模块尺寸、模式展开和特殊屋顶分开验收；顺序是该资产/节点版本的约定，不能直接推广 |
| 植被可调性不能只靠随机种子 | `annam.ivy.1.0.hda`、`annam.shrub.1.0.hda`：生长、密度、修剪、朝向、叶片变体和多组 Seed；`vertex_color*` 节点编码材质通道 | 暴露有意义的艺术控制；`Cd` 的风、颜色和干叶语义要写进该材质的契约，避免被清理节点误删 |
| 模拟结果应能选帧并继续加工 | `Titan_Cloth_tool.hda`：Reset Simulation、Frame、Vellum、TimeShift；`Titan_StackingTool.hda`：enable sim、Frame、Bullet、DataTable 路径映射 | 分开模拟、选帧、后处理和输出。TimeShift 只代表选帧，不等于持久化缓存，也不证明跨会话能复现 |
| 管线不应绑定作者机器或场景 | 多个资产存在 `/Game/Titan/...`、Megascans、示例对象路径；Crates 暴露 Save to Disk 和 `$HIP/geo/...fbx` | 移入项目配置并检查引用；存在导出按钮不等于已授权执行导出；优先保持布局与发布动作分离 |

补充资产的可借鉴范围：`electric_cable_tool_v1` 与 `electric_pole` 提供电力设施组合，
`sop_tut_pipe_greeble` 展示局部坐标到原位的变换，`Titan_Pipes_Curves`、
`Titan_Constructions`、`Titan_Platforms` 展示曲线/轮廓模块组合，
`Billboard_Generator`、`titatn_simple_crates::1.0` 和 `Titan_SkyTrain` 展示较小的参数化
产品。`titatn_simple_crates` 是源定义的实际拼写；SkyTrain 本次未取得动画交付证据。

这里提取的是设计原则，不要求复刻节点图，也不根据 Python、VEX 或原生节点的比例
评判 HDA。Scaffold 内有作者给出的局部性能比较注释，但本轮未复跑，不将其数值
作为实测结论或“VEX 总是更快”的依据。

## 属性观察如何接入后续制作

上述属性来自参数、代码或注释引用，**不是本轮读取到的 Cook 后属性值**；owner、类型、
尺寸和最终保留情况仍需运行时确认。需要复用资产时，先选一个小输入，检查关键边界：

1. 曲线清理/Resample 后：点数、方向、分组和锚点是否按预期变化。
2. 朝向/模块选择后：`orient`、`scale`/`pscale`、模块键与实例路径是否完整。
3. Merge/Attribute Delete 后：下游需要的属性是否保留，是否有同名不同 owner。
4. 引擎输出前：`unreal_instance`、`unreal_material`、UV 或材质使用的 `Cd` 是否符合
   当前 Houdini Engine 与项目约定。`instancepath` 与 `unreal_instance` 不能直接等同。

使用 MCP 几何快照和对比能力获取实际证据；拓扑变化后使用真正唯一且稳定的键，
没有对应关系时只比较 schema/数量，不强行按索引匹配。先批准小规模 Cook，再决定
是否运行昂贵分支，最后单独完成引擎验收。

## 与旧 Titan 资料的关系

[旧 Titan 摘要](project-titan.md) 来自 `TiTan Project/`，本次不会覆盖其历史观察。
本轮对旧目录 12 个 HDA 库与这批 18 个库做 SHA256 比较，未发现完全相同的二进制；
但名称、功能与内部注释存在延续关系，**不能由哈希不同推导为独立案例**。
18 个工具也不算 18 个独立生产成功；它们组成一份参考案例集。未据此提升旧 Recipe
的成熟度或声称它们已经执行了 `hda-authoring-v1`。

## 来源快照与复查

Inventory 的 `source_files` 保存 18 个 HDA、README、安装 BAT 的相对路径和 SHA256。
集合指纹为该路径到 SHA256 映射经 `json.dumps(..., sort_keys=True,
ensure_ascii=False, separators=(",", ":"))` 序列化后的 UTF-8 SHA256。
资产哈希绑定的是检查时文件，不证明上游官方发布身份。

复查结构可在隔离 Hython 下对单个资产执行：

```text
hython skills/houdini-production-workflows/scripts/inspect_houdini_case.py <source.hda> --source-root <project-collection> --output <temporary-record.json>
```

先审阅脚本段与依赖，避免在生产会话批量实例化；Manual 模式不是零 Cook 保证。
完整功能复现需要目标版本、Labs、数据表和对应 UE 内容。原包未随经验库再分发。
