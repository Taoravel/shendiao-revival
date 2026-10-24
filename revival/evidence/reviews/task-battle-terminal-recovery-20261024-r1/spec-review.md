# Spec

实现错误1项；遗漏0项；扩域0项。独立Spec轴，不合并Standards。

**[P2] 按持久租约身份比较新旧epoch。** 规格 `TASK_TERMINAL_RECOVERY_DECISION.md` 要求：“只有有效的新当前租约……可调用新公开Task recovery Seam。” `source/task_battle.py:495` 仅以 `finished.login_epoch==epoch` 排除同租约；但 `valid_task_epoch` 明确同时接受int/str，`_owner`则通过SQL比较持久租约。现役 `npc-repair-20261024T023920Z/source/accounts.py:35,119` 把epoch存为TEXT、返回int，因此原event/admission为整数7、当前调用epoch及witness为字符串`'7'`时，所有者查询仍匹配同一条有效租约，而Python相等为false，恢复入口误当新租约。它不需要修改原event。应按与持久层一致的规范身份排除同一lease，或明确拒绝这种跨表示输入；补充同租约int/str别名负例。此问题是受信调用方Interface的规则漏洞，不是wire授权漏洞。

其余所读路径符合规格：“不能构造修改epoch的BattleFinished”由原event校验和直接复用结算落实；pending核active/当前角色资格，使用当前actor生成共同奖励证据。producer/source CAS、唯一consumer回执及outbox事务明确留main，witness不是自证权限。新paid/read_current要求相同已存终态并纯读当前XP/wallet/profile，不走旧奖励/链修复；普通settle仍要求事件epoch等于当前epoch，原ack保持原字节逻辑。

方法/验证：code-review Spec静态核已审dreamr4基线、405行patch、2文件/21inputs全部SHA及root acceptance对应裁定SHA；原ack/proof/cancel AST不变。只读取6组新Task契约及6组旧binding报告，未重跑、未访问DB或真人。数值Participant/terminal及SQL outbox是fixture；真实engine、producer/source CAS、完整恢复链/并行、shared与GUI仍未证明。
