# Spec

结论：0 项缺失/部分实现、0 项越界、0 项实现错误；本片 NPC 方向领域候选通过。

方法：按 code-review 独立 Spec 轴逐项核对 `changes.diff` 与冻结的 `NPC_PLACEMENT_DIRECTION_INTEGRATION.md`、两份 World 原生研究、`NPC_ORIENTATION_NATIVE_RESEARCH.md`、World 接线队列及 ARCHITECTURE/DESIGN_AUTHORITY。没有 Git；比较使用 manifest 中的真实 Scene177f55、已审但未激活的 Life8a0cd 和新测试空基线，未虚构提交。

规范要求“将每一实际placement.direction原样填写现有NpcBasic.field_48”，Scene 与 Lifecycle 唯一消息生成入口均实现该传递，后者被 bootstrap、当前 snapshot、动态生成及重试共用。“0保留原回退哨兵”通过原始 13 个零值及动态零值保留；没有把 0 转为其他方向，也没有新增朝向控制。NpcPlacement 公共入口严格拒绝 bool、浮点、字符串及越界整数，符合“有效数据为精确int0..7”。

实际独立运行六个 manifest 声明的固定输入检查，全部通过：方向、world_npcs、Lifecycle、motion、Lifecycle rules、cell interaction。每次运行前后校验 1607 个固定输入，使用 `verification/spec/` 独立报告。方向检查经原 SAddUserScreen decoder 覆盖真实重复实例7/1、304地图/3443摆放、13个零、七类非法输入及动态生成/重试/当前快照；其余五项回归保持权限、原子性、移动及启动约束。

R1 缺少历史 v1 测试配置的失败保留；R2 仅补验证资源，三个范围文件不变。未将 Life8a 合入线上 f5，也未开启成员绑定、鉴定、动态生命周期或其他服务。原服历史线包、完整模型构造/最终朝向、共享运行时投递、GUI 与部署仍未验证；这些边界与规范一致。

Spec：0 项，最高严重程度：无。
