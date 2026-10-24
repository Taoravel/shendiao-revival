# collision 200906 主策划固定两轴聚合

## Standards

硬违规 0，heuristic 可行动建议 0。完整独立结论见 Standards-root.md，逐 hunk 核对角色/地图/连接状态单写者和有界投递，没有新全局世界锁或全服执行器。

## Spec

缺失 0、额外 0、错误 1：[P1] 已完成开场的 paid/duplicate END 在 evidence=None 时仍重新追加正常行走 location0 声明。完整独立结论见 Spec-root.md，不与 Standards 轴重排合并。

主策划实际补验：新固定 supplemental verify_runtime_movement_terminals.py（8ecce3d31f3e2be4519499a5ac42f741cd893ed5ab3946ff2685d1f4030f5fde）对准确 200906 source 运行，在断言 `not any(kind==SET_ROLE_LOCATION for kind,_ in duplicate)` 准确失败；此前 stale callback/new lease/实际intro新提交等路径完成。测试独立于原候选 harness，明确为 supplemental，不伪称已在原40项之内。1442 source/415 harness/1199 workspace/runner 前后全 SHA 不变，actual imports 全部固定 source/harness。报告 evidence/root-world-collision-20261024/world-collision-20261023T200906Z/supplemental-duplicate-red/root-red-verification.json。

另两项准确冻结 lifecycle/wall probe 已 exit0，原始墙格 STOP 被拒且不落库；初始 lifecycle 仍有旧 joined 门槛限制。302 图脚本 stdout绿后 checker 因 workspace worker import 未绑定而 exit1、result 缺失，发布条件未闭合。

结论：200906 不予发布，保留原错误与报告；main 已修 paid 分支并将强化 early ACK、错包绑定与close失效，必须新冻 r2、差异复审及原反例转绿后再验收。Standards 0；Spec 1，最高 P1。未操作正式 DB/服务/GUI或正式剧情战斗，商业容量未验证。
