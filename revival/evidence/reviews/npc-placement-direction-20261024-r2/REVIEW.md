## Standards

结论：文档规范违例 0；可行动的 Fowler smell 0。

固定点为真实字节对比，非 Git 提交：`world_npcs.py` 177f55→995834，`npc_lifecycle.py` 已审域 8a0cd→ab2b90，新验证脚本以空文件为基线；审阅 `changes.diff` 的全部三个文件。未把线上 f5e077 的 Lifecycle 当成本片基线。

采用 code-review Standards 方法，逐项对照冻结的 `current/AGENTS.md`、`ARCHITECTURE.md`、`DESIGN_AUTHORITY.md` 及十二项 Fowler 启发式；仓库未发现 CODING_STANDARDS/CONTRIBUTING。NPC 状态仍属地图；构造时精确整数范围校验和现有两个编码入口赋值没有引入热路径 I/O、共享可变状态、全局串行器或跨所有者网络发送。没有改共享入口。两个现有生成入口各补一个字段不构成值得抽象的重复逻辑。

独立实际执行六项冻结检查，均通过：`verify_npc_placement_direction.py`、`verify_world_npcs.py`、`verify_npc_lifecycle.py`、`verify_npc_motion.py`、`verify_npc_lifecycle_rules.py`、`verify_npc_cell_interaction.py`。每项执行前后均校验 1607 个输入，实际导入均来自冻结目录，结果保存在 `verification/standards/`。方向检查覆盖 304 个地图记录、3443 处摆放、13 个零回退值及动态重放；R1 缺旧测试配置的失败保留，R2 补齐配置后通过。

范围限制：仅审三个所属文件的增量及其冻结回归。静态文件接入、Lifecycle 严格启动与真实 MapOwner 激活须按各自基线独立集成审验；未操作服务、真实角色、运行数据库或 GUI，本结论不构成发布或完整 NPC 验收。

Standards：0 项，最严重问题：无。

## Spec

结论：0 项缺失/部分实现、0 项越界、0 项实现错误；本片 NPC 方向领域候选通过。

方法：按 code-review 独立 Spec 轴逐项核对 `changes.diff` 与冻结的 `NPC_PLACEMENT_DIRECTION_INTEGRATION.md`、两份 World 原生研究、`NPC_ORIENTATION_NATIVE_RESEARCH.md`、World 接线队列及 ARCHITECTURE/DESIGN_AUTHORITY。没有 Git；比较使用 manifest 中的真实 Scene177f55、已审但未激活的 Life8a0cd 和新测试空基线，未虚构提交。

规范要求“将每一实际placement.direction原样填写现有NpcBasic.field_48”，Scene 与 Lifecycle 唯一消息生成入口均实现该传递，后者被 bootstrap、当前 snapshot、动态生成及重试共用。“0保留原回退哨兵”通过原始 13 个零值及动态零值保留；没有把 0 转为其他方向，也没有新增朝向控制。NpcPlacement 公共入口严格拒绝 bool、浮点、字符串及越界整数，符合“有效数据为精确int0..7”。

实际独立运行六个 manifest 声明的固定输入检查，全部通过：方向、world_npcs、Lifecycle、motion、Lifecycle rules、cell interaction。每次运行前后校验 1607 个固定输入，使用 `verification/spec/` 独立报告。方向检查经原 SAddUserScreen decoder 覆盖真实重复实例7/1、304地图/3443摆放、13个零、七类非法输入及动态生成/重试/当前快照；其余五项回归保持权限、原子性、移动及启动约束。

R1 缺少历史 v1 测试配置的失败保留；R2 仅补验证资源，三个范围文件不变。未将 Life8a 合入线上 f5，也未开启成员绑定、鉴定、动态生命周期或其他服务。原服历史线包、完整模型构造/最终朝向、共享运行时投递、GUI 与部署仍未验证；这些边界与规范一致。

Spec：0 项，最高严重程度：无。

总计：Standards 0（最严重：无）；Spec 0（最严重：无）。
