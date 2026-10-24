# 同实例重定位存储审查

2026-10-24。真实空基线→新增存储Module、验证和交接，固定于 `reviews/world-relocation-storage-20261024-r1/after`；1394项当前源码/配置复制为独立reference并逐项封存。没有Git历史，不将后续工作区共享文件当作此次来源。

## Standards

0项。DDL集中启动，位置、版本、决定CAS使用调用方连接；既有公开完整checkpoint Interface核事务/账号/租约，保持唯一持久位置和同实例进入凭据。记录解析有上界；无新全局锁、玩法队列、热I/O或隐式旧档迁移。独立核全部after/reference及主9组报告来源，详见 [standards.md](reviews/world-relocation-storage-20261024-r1/standards.md)。

## Spec

0项。独立使用同冻结依赖执行全部9组并核1394文件前后稳定，另用真实MapOwner和跨图事务进入后来完整实例，再在只读Adapter重试旧重定位commit，当前实例、坐标、版本及进入凭据保持。详见 [spec.md](reviews/world-relocation-storage-20261024-r1/spec.md)、[独立9组](reviews/world-relocation-storage-20261024-r1/spec-independent.json) 和 [后来实例](reviews/world-relocation-storage-20261024-r1/spec-later-instance.json)。

精确新Module SHA `b2ced920f1525f869b0def55041b7d5e0d343391a5f27f7e234bf188e7d3decd`，验证 SHA `f98b3a23a94b8ba260c77b5dbf62fbff3ec27f294ea4ea447d34bcb0389a2397`，依赖Owner保持 `a454134…`。后续SQL/shared变更不能转签本批绿灯。

Standards open: **0**；Spec open: **0**。只证明SQL/领域步骤，旧进程成员退休、shared发送/恢复接线、入口政策、完整native与GUI仍未完成。未部署、重启、修改正式存档或启动客户端；全量地图/场景/怪物目标仍active。
