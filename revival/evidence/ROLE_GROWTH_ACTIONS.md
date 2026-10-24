# 普通人物手动升级与潜能分配接线

2026-10-23，主策划。接线前读本文及ARCHITECTURE；原表/升级规则来源见ROLE_PROGRESSION_RESEARCH、role-progression-v1.json，普通显示见ROLE_GROWTH_UI_RESEARCH，分配原请求见ROLE_POTENTIAL_REQUEST_RESEARCH。数值策略仍按已登记设计，不把原协议证据扩大为原服完整成长算法。

## Interface 与处理顺序

1. role_growth_protocol提供两个已核验上行。CReqLevelUp=0xc32cd，body必须4字节单BE32，仍叫opaque；当前design仅0普通模式，一次升一级且10级起手动。CAddPointToAttr=0xc000c，20字节五个非负BE32增量，wire顺序体/内/力/敏/耐；decode_allocation_request转换成内部体/内/力/耐/敏。两种消息必须按kind分别解码；仅因在GROWTH_TYPES集合中不能统一当升级。
2. 所属角色已经进入世界，并通过战斗/换图门禁后，经既有有界I/O打开当前登录租约事务。小游戏已存在会话时也必须拒绝分配；当前未接小游戏的路径不能冒充已验证其活动门禁。身份、版本和请求键不来自wire，这两种原请求均没有客户端重试ID。
3. role_growth_actions的manual_level_transaction / allocation_transaction加入该事务。要求明确成长及属性基线/政策；不生成缺失档案。复用role_growth的公共请求入口，余额、点数、版本、派生及伤势在同一事务改变；固定请求键先查原凭据再处理当前版本。总和超过潜能、全0、负数、未知模式、经验不足、上限或旧租约拒绝。分配不是重置五维。
4. 返回冻结GrowthActionResult，包含当前growth/attributes及已在事务内校验的普通当前EXP与19项属性逻辑消息。历史回执仅作确认，不作为缓存或UI当前值。编码超出原范围/float32精度时回滚，提交成功后才按RoleOwner顺序publish_committed_role并由目标连接所有者发送；不借用battle初始化，不用无效SLevelUp。
5. 同一受理命令内部重试保留cmd.request_id。客户端重新发送完全相同正文仍是一条新命令，正常再次扣XP/点数或按当前不足拒绝；不能虚构原生网络去重令牌，也不能按正文合并正常连续操作。缺失完整profile的旧角色待显式迁移。

## 验证与状态

- verify_role_growth_requests：原CReqLevelUp和CAddPointToAttr的constructor、marshal、decoder执行一致；非对称1/2/3/4/5的wire转内部1/2/3/5/4；原type核对，截断/尾随/负增量拒绝。
- verify_manual_role_level：同事务L10→11→12逐次扣原门槛/发潜能，缺血缺蓝保持；旧键重试返回当前L12；伪造目标等级、不足/负模式/旧租约拒绝；外层失败全部回滚。
- verify_role_allocation：原AGI1/END2正确映射，free5扣3，防御14/躲闪24/速度11；另一次加点及以后升级后老键仍不重扣，返回当前属性；透支/零/负/bool/意图冲突/旧租约拒绝，外层失败点数、属性、凭据共同回滚。

上述均已运行，临时数据库，无GUI、真实角色、服务重启或战斗。结果各在相应evidence/*-verification.json。

共享接线后，主策划独立运行verify_manual_level_runtime.py通过实际RoleOwner→ConnectionOwner及连续RC4/原生MPPC路径：逐次L10→11→12、在线/社交等级一致，非对称敏1/耐2正确扣点；原加点type带4字节零不再被误当升级。后续加点后重试旧升级/加点键返回当前值且不重扣，重连保留HP100/max130、MP52/max112及free6。战斗/传送仅使用拒绝哨兵，没有启动系统。证据manual-level-runtime-verification.json；内存Writer与临时库，不证明真实客户端按键/画面或当前运行进程已更新。

方法：codebase-design将原生顺序/长度收在协议Adapter，外层行为复用深层成长Module的公共Interface，不复制指纹/历史结果解析或另设全服奖励队列。research从原人物按钮/预览与codec闭合增量语义；writing-for-agents按解码、资格、事务、提交、重试安排步骤。未采用完整TDD、商业容量或原版平衡验收。
