# 同实例恢复：旧进程成员退休审查

2026-10-24。最终固定副本为 `reviews/world-relocation-recovery-20261024-r2`，manifest SHA256 `6a536ada07f956ca1b2f7f6fb0b0ac5c97b55f3a93dd59d9c4b5606429fc4cae`。真实原始实现基线仍保留于r1/before，r2/before是第一轮已审实现；无Git提交历史，按实际before/after差异审查。r1的缺口和原红结果不覆盖。

## Standards

**0项。** 地图仍是唯一位置写者，真实成员关系ID仅表示关系身份；投影使用真实生命周期代次，即使已空也不可替换。最终修正在空幂等分支之前比较该代次，没有新增共享锁、SQL、网络或跨所有者等待。独立核对3项before、11项after、1419项reference、原映像/原包及7份主报告的准确来源；本轴为静态和证据链核验，未重跑玩法。见 [standards.md](reviews/world-relocation-recovery-20261024-r2/standards.md)。

## Spec

**原P2关闭，0项新发现。** 第一轮正确清理后的空重试误收None/foreign view；新增公开projection反例先红，最终Owner先核投影代次后绿。Spec独立重放原反例：原view空重试仍幂等，None/foreign空view拒绝且无状态变化；再独立执行冻结reference全部11组，逐项核依赖与原映像/map/config资产前后稳定。见 [spec.md](reviews/world-relocation-recovery-20261024-r2/spec.md)、[独立11组](reviews/world-relocation-recovery-20261024-r2/spec-independent.json)、[原反例修复](reviews/world-relocation-recovery-20261024-r2/spec-empty-projection-r2.json)。

父任务最终源的新11组、SQL9组、原Domain10组及既有5项回归均通过，且来源稳定；既有5项包含metadata14组。Owner为 `d748e058d17c757062a4f70afd467ecb84e516e3117d9e7e325f663d2c8cbb05`，RoleScene为 `5bf03c3e1ff3869a808b8fa2f871d6a9064e9c7074632036f190a9e0c47dfba4`，最终verifier为 `bcbb7fa2767e9c33d0a883d145fcf4ba29c08efa622b16a2c460cc31afb6c7d9`。真实临时SQLite七个故障窗口与同一个旧MapOwner清理、再加入和继续行走已覆盖；不冒称真人自然触发。

Standards open: **0**；Spec open: **0**。该Module可以交共享集成采用，仍需真实旧写者围栏、SQL提交、缓存/连接流程重核、新许可与精确发送屏障接线；同图入口/住宅政策和原生GUI仍独立验收。没有部署、重启、改正式存档或启动客户端，全量地图/场景/怪物目标仍active。
