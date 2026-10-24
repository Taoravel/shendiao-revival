# 生命周期固定审查与修正

2026-10-23。code-review两轴并行。基线是本批前world_owner准确副本、目录初版868853…及三个新增空文件；无Git，不编造commit。v1/v2固定diff、源码和正式标准/政策分别位于 `reviews/world-story-lifecycle-v1`、`reviews/world-story-lifecycle-v2`。最终以v2的5交付文件/4依据为准。

## Standards

v1及v2代理 `/root/story_directory_standards` 各0项硬规范违规，0项需要报告的代码异味。v2核pool `3fdedb54…a5c2bd9b`、目录 `f8a817fb…b8b6268`：元数据所有者顺序维护取消中状态，精确执行终止/清理确认后释放槽；未知等待结果保持围栏。pin、池空闲与地图空闲分别由本所有者维护，用不可变ticket/receipt组合；没有跨所有者锁或锁内I/O。64/64从启动单一政策严格读取，拒绝超过上限。交单保留shared hooks、动态持久化和GUI未验，未扩大完成范围。

## Spec

v1代理 `/root/story_directory_spec` 发现P2一项：cancel_load在观察超时后直接释放仍执行加载的名额，允许实际超过128。父任务加128槽取消后仍须128的公共断言，实际exit1；修为ProjectionLoadCancellation与取消中保留槽位，真实loader终止/清理后finish_load_cancel才移除。重复取消幂等，取消中的acquire/late finish_load拒绝，交单同步撤去超时即释放的操作。

v2复审原P2关闭，新增0项：取消状态和真实确认覆盖原触发路径；最后pin后重新计时，卸载须满足池侧完整60000ms及地图退休独立idle/generation/时序；正式64/64严格校验冻结，构造及实际操作数分别受限。父任务另将“刚释放pin便开始卸载”实红→绿，避免用地图旧idle时间掩盖外部排队工作。

两轴只读静态审查，未将部分快照或可能经OUT指向工作区的程序称为固定完整运行时实跑。执行证据独立为最终18组、32次线程竞态两分支、自然目录空投影循环，以及预算增补后的目录12组。原MapOwner/邮箱与view/传送与view/恢复与view、实例持久12、302图/212跨图回归亦已实跑，范围由交单逐项限定。

最终Standards 0项；Spec原1项P2已修正关闭，未解决发现0项。完整共享私有入场、动态冷快照、GUI与全量世界仍未证明。


2026-10-23后续文档顺序补正：当前HANDOFF第5步已改为retire后保留unloading槽，先等实际Adapter/邮箱/资源终止，再finish_unload确认释放。该补正不改变v2领域源码/参数；v2固定旧交单保留历史。current-interface明确区分当前交单hash与原v2快照，不以18组宣称共享关闭/清理已经验证。具体Seam见WORLD_STORY_SHARED_HOOK_AUDIT。
