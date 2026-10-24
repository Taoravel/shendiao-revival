## Spec

结论：漏项/部分实现 0，范围越界 0，实现错误 0；所属候选通过 Spec 审查。

方法：重读 code-review、codebase-design、tdd 及项目约束，独立核对六文件差异、当前规格和已审 Asset Interface。固定点为真实封存 E648→60820efa，新文件以空 BASE 比较；未虚构 Git 提交。manifest SHA 保持 `bc82e4eacae0b80b39f17a0c17682812fd282ad140cedc72a75c78a07710530a`。

规格“同一角色租约事务内……全部成功才提交”由显式 `equipment_messages` 在原事务提交前执行实现；严格检查冻结逻辑消息，异常沿原事务回滚。当前物品 key 交既有 Asset Adapter 决定携带1/已穿3，未重标历史帧、引入库存迁移或改变旧凭据身份。None 保持既有生产者；原 precommit 参数、资源依赖和错误文本兼容。

独立执行七项均符合预期：`native_messages`及五项 R1 回归通过，`native_red`准确得到 E648 缺少 equipment_messages 的失败。计数为六正向＋一真实RED，非七项功能绿灯。每项前后校验18本地/6112外部输入；实际 Inventory 仍与023920发布原件同 SHA。

新生产者11组公开行为全部通过：旧 Owner 真实已付凭据另进程/新租约读当前；原消息解码、fresh费用及paid只读；实际持久socket缺score编码失败回滚与同ID补来源重试；可变消息拒绝；脱装后当前carried1；错误栏目/旧租约拒绝；L21迁移资源末尾编码失败回滚、重试扣20且HP10/MP20/version保持。测试没有直接伪造付款凭据。

规格明确的新生产者共享注入、该生产者加密投递、完整GUI、非空Gem角色派生source、最终兼容policy及部署仍未完成。默认legacy生产者的Peer回归不替代这些证据；本审查不批准上线，也不完成全部NPC目标。

Spec：0项，最高严重程度：无。
