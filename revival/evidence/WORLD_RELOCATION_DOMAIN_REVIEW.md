# 同实例重定位Domain审查

2026-10-24。本批是原始同图门户缺口中的所属地图能力，不是运行时闭包。真实原始before为成员metadata v2的Owner `9a701d8…`；初版 `b38aacb…`、修正版 `a454134ec3d274e5c6203b66adea9364f10a42563bf7fbdc2c83ed1865a693ac` 分别冻结在 `reviews/world-relocation-20261024-r1/r2`。没有Git历史，以实际保存的before/current和新增文件空基线审查。

## Standards

独立r1/r2均0项。当前地图仍是唯一位置写者；新记录有界、按地图隔离，只保存操作证明/终态，不建立第二位置权威。退出时旧终态保留清理凭据但不再执行，每次新准备有真实独立身份，pending精确重试不重发身份。没有新增全局锁、全服队列或热路径I/O。详细结果：[r2 Standards](reviews/world-relocation-20261024-r2/standards.md)。

## Spec

初版1项P2：bare/paired的commit/cancel在同值leave→join后仍误收旧回执。独立四反例保留于r1，父任务也实际红→退出围栏绿；终态释放后同请求/位置重建另先红→新preparation_id绿。修正版独立复验全部10组及原四反例通过，P2关闭，当前0项。详细结果：[r2 Spec](reviews/world-relocation-20261024-r2/spec.md)。

父任务按准确最终Owner重新运行5项既有回归，全部exit0、源前后稳定，见 `world-relocation-existing-regressions-r2.json`。10组新验证见 `world-relocation-domain-verification.json`，Owner/verifier与r2冻结一致。成员metadata新源回归另存 `world-relocation-member-metadata-r2-verification.json`；原9a701d8已交metadata报告按其冻结reference精确保留，不将新源测试转签旧ready凭据。

Standards open: **0**；Spec open: **0**。尚缺SQL提交/重放、新租约恢复/旧冻结退休、连接真实发送屏障、共享分发及入口政策、原生流程和GUI，因此本批仍不是可部署的完整同图传送。详细调用与失败前提见 [WORLD_RELOCATION_DOMAIN_HANDOFF.md](WORLD_RELOCATION_DOMAIN_HANDOFF.md)。
