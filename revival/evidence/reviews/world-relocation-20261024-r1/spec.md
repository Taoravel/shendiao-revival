# Spec review: same-instance relocation domain

2026-10-24。读取 `code-review`、AGENTS、架构约束与本批 `after/WORLD_RELOCATION_DOMAIN_HANDOFF.md`。以保存的真实 before/current 作 `git diff --no-index`，新增验证按空基线审查。核验 before `9a701d8…`、after `b38aacb…`、验证脚本 `a8c4065…`；没有仓库提交历史。

## Findings

- **[P2] 同值重新入图后，旧重定位回执仍被当成当前成员的幂等结果。** 规格明确要求：“后续移动或新成员后的旧重试拒绝”。`after/world_owner.py:774` 的 `commit_relocation` 终态分支仅以 `current in (previous.location, ready)` 判断；`:811` 的 `cancel_relocation` 同样只比较当前 `Location` 与取消后的旧值。`Location` 不含一次地图成员关系的代次。已完成重定位后公开 `leave(active)` 再 `join(active)`，地址、租约、版本和坐标可以完全相同，但已形成新成员关系，旧 proof 仍返回成功终态回执。paired 路径也只核当前 projection 的 Location，没有把旧 proof 围栏到原成员代次。建议在当前成员生命周期结束时撤销回执的可执行资格，或给重定位证明加实际成员代次围栏；终态记录仍保留给显式退休/持久重放，不应靠删除记录绕过预算与回收规则。

## Verification and limits

准确 after SHA 下使用原1627资源与本批公开 fixture，独立执行 commit→ready→leave→join→旧commit，以及 cancel→leave→join→旧cancel，分别覆盖 bare/paired 四例。四例均错误接受旧终态回执；paired成员 revision 分别5→7、3→6。结构化反例在 `spec-member-rejoin-counterexample.json`；执行前后生产源 SHA 未变。此次反例没有观察到坐标倒退，发现的缺口是旧成员回执跨越新成员关系仍被认可，不扩大为已发生存档损坏。

其余所审范围与领域能力规格一致：唯一冻结源、目标loading、metadata许可围栏、容量失败不发布、终态计闲置及显式退休、原普通reserve与跨图路径保留。没有独立重跑全部8组或5项旧回归；原SQL/故障恢复/真实发送/shared/GUI均继续未验，本批不构成可发布闭包。仅写本报告与反例，没有改源、冻结文件或服务。

Spec findings: **1 P2 open**。
