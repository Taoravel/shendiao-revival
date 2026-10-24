# World 验证产物双轴审查

固定范围：`reviews/world-runtime-movement-acceptance-v2`，manifest SHA256 `e341f15c3c648af0f63906974afd43b96a046cd11c7fb2028ccdd37a8704981a`；2份真实 pre-edit base、10份 final、48份冻结 reference。无 Git/commit，以实际 base/final 和 changes.diff 审查；没有虚构提交。生产/shared/NPC 所属代码没有在本批修改。

方法：code-review 独立并行 Standards/Spec；AGENTS、ARCHITECTURE、DESIGN_AUTHORITY 优先于通用异味建议。diagnosing-bugs 通过实际旧版红/新版绿和准确候选绑定排除误判；research 追原生方向与shape数据流；codebase-design 保留地图权威与运行时缓存的职责差异，不通过改领域幂等语义掩盖 shared 缺陷。

## Standards

硬规范违规0项，判断性代码异味0项。审查核2份base、10份final、48份reference及8项guard观察；必要的独立命令bootstrap小重复未判为异味。两份r3绿报告各记录117个实际生产origin。独立记录 `WORLD_RUNTIME_MOVEMENT_ACCEPTANCE_STANDARDS_REVIEW_V2.md`；初审单独保留。仅静态核对，审查者未重跑长测试或操作服务/GUI。

## Spec

初审P2已关闭，新增0项可行动问题。首版仅七个名称的harness guard可漏runtime_core文件/world_collision包；实际反事实证明旧verifier执行替代模块，修正后提前拒绝。允许明确test helper、实际生产origin核验及pfs/bxml候选重绑通过复审。r1全302没有转签r3；r3子集/早到ACK单独绑定。late-finalize准确保留r3红，未声称shared已修。独立记录 `WORLD_RUNTIME_MOVEMENT_ACCEPTANCE_SPEC_REVIEW_V2.md`，初审P2记录保留。

两轴总结：Standards开放0，Spec开放0（原P2已关闭）。这是验证/研究产物的审查，**不是当前碰撞候选可发布结论**；r3旧finalize删除新runtime成员的真实反例仍红，见WORLD_LATE_FINALIZE_MEMBERSHIP_BLOCKER。

## 执行证据与未验范围

父独立：原NPC方向19例/12项输入稳定；默认shape来源10例/14项输入稳定；r2真实加密投递门槛与墙拒绝绿、typed suffix清理6例绿、1006/1404诊断绿；r3收紧origin后的加密门槛/墙拒绝绿和1006/1404诊断绿，各117生产origin；8项来源准入旧/新反事实通过。旧200906Z完整302图（3443配置NPC/294原解码批次）、1442文件和两原包稳定，作为历史准确版本记录。

旧joined前提已在反例中排除；drain与原客户端执行ACK没有混同。NPC显式方向字段和默认11206模型分支获证，但未改生产投递，完整模型/可见性/GUI未验。r3 late-finalize仍红、后续修复未在本审查范围；完整新手流程、正式战斗、多人AOI、特殊地图入口与全量真客户端目标均未完成。
