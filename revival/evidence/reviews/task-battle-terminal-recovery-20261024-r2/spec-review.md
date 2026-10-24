# Spec

本次增量新增问题0项；r1的P2已闭合，保留原历史报告。独立Spec轴，不合并Standards。

依据root裁定“只有有效的新当前租约……可调用新公开Task recovery Seam”，唯一生产变化 `task_battle.py:495` 改为比较 `str(finished.login_epoch)==str(epoch)`，与现有SQLite TEXT租约身份一致；原整数epoch及其字符串别名现在被视为同一个租约并拒绝，不修改原event/admission，也不放宽合法新租约条件。

验证器新增负例位于 `acquire_lease` 之前，传入 `str(original_epoch)` 及相应Inventory/Witness；其余admission、终态、producer/source绑定保持有效，确实瞄准同租约别名，不能由错误owner或已换lease掩盖。冻结报告包含该负例和六组契约绿灯；修前实际红灯由本批执行方报告，本审查未重跑。

`settle_task_battle_transaction`、`_validated_terminal`、原ack及新paid/read_current函数AST均与r1相同；因此本次修复未扩大普通settle的old-epoch权限，也未改变已结算当前查询允许同租约/后续租约、拒绝pending及不重复DML的范围。r1其他结论沿用。

方法/验证：code-review Spec静态核r1/source与本批baseline精确一致、2文件两端及21inputs SHA、39行patch和报告source SHA，全匹配；AST确认只改recover生产函数。未运行DB/测试、修改源文件或接触真人。真实producer/source CAS、完整engine恢复链、并行、shared/发布/GUI仍未证明。
