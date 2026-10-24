# Spec review: same-instance relocation storage

2026-10-24。按 `code-review` 的 Spec 轴，读取 AGENTS、项目架构约束和 `after/WORLD_RELOCATION_STORAGE_HANDOFF.md`，对父任务记录的真实空基线→新增Module/验证/交接进行审查；无Git提交历史。核新增Module SHA `b2ced920…`、验证 SHA `f98b3a23…`，使用本批1394项冻结 reference，不混后续工作区共享代码。

## Findings

**Open findings: 0。**

调用方事务与有效角色租约由现有完整实例Interface验证，typed/canonical准备证明绑定Owner代次、preparation_id、旧租约与源/目标拓扑。begin核源完整地址、进入凭据和位置版本；commit将目标位置/版本及决定写入同一caller事务，保留同实例原entry_version/transfer_id。精确终态重试只核当前权威，不重写旧位置；新租约不能拿历史证明再提交，committed不能cancel。

新租约恢复分别处理prepared、committed及freeze后未写journal三窗口，补录窗口要求可信精确旧proof及当前已知完整源。prepared恢复保留严格更晚checkpoint；普通无历史None分支未隐式绑定未知实例，也明确没有授权清理原进程旧冻结成员。晚期SQL故障继续由caller整事务回滚，不在helper偷偷提交、连接或建表。

## Independent verification

已按指定引导保留原客户端ROOT、将OUT及生产导入切到reference，并重绑其PFS/BXML。独立运行冻结验证全部9组，exit0；`spec-independent.json` 为完整范围、输入稳定。执行前后逐项核reference1394文件与after清单，实际accounts/runtime_storage/world_owner/transfer/新Module/PFS/BXML均来自reference。

另以同冻结依赖及真实MapOwner/跨图事务，在重定位提交后进入另一个已知完整实例1007/(1099511627875,4)、版本7，再用只读Adapter重试旧目标版本4的commit：返回False，当前完整实例、位置、版本和非空进入凭据均保持。独立结果为 `spec-later-instance.json`，reference仍稳定；没有直接改表伪造另一实例。

以上只证明本批SQL/领域步骤。旧进程成员退休、恢复后的共享接线、真实发送屏障、具体入口/住宅政策、native全流程与GUI仍未完成，本批不构成同图运行时闭包或发布验收。只新增本轴报告和独立证据，没有修改after/reference/主源、正式存档或服务。

Spec findings: **0**。
