# 忠诚恢复按已知血脉当前值报价

2026-10-24主策划裁定，新费用片唯一规则为design/npc-pet-loyalty-v2.json。修改kind3/4忠诚价或重放旧NPC恢复凭据前读取。原整段1136290、原Pet字段刷新和80例原消费见NPC_LOYALTY_QUOTE_NATIVE_RESEARCH；当前旧公开plan/settle在power9/1139仍收900、原报1260的差例已保留。

已知普通PetBlood.power按每宠(45+2×power个位)×本宠缺忠诚求和。字段为1140当前power，不是血脉等级或颜色；颜色只查原maxloy。当前血脉上限截断1139也是有效非0个位，不能假设所有设计新宠永远个位0。原客户端报价client_verified；采用为服务器价格为designed。等级≤20的原-3映射免费0，不产生负扣款；无宠/全满保持原拒绝。

未知旧blood但已有合法care的既有支持实例，明确沿用旧设计个位0单价45，并在新凭据记legacy_unknown来源；不生成或保存blood0，也不把畸形/已存在但不支持的数据当未知回退。这样保留旧功能边界，而已知状态不再与原报价不符。原kind4资源费用、inn、NPC资格、现金npc_shop用途与其它状态规则均不变。

旧paid凭据必须先查，保留原npc.1和共同/恢复fingerprint契约；不因后来known power或新价格补扣/退差/重算旧费用，不回放历史忠诚或资源。新命令在同一角色事务冻结当前role/pet/care/blood及fee recipe来源，费用、恢复、唯一source、凭据与最终native编码一并提交，晚期异常全回滚。同ID重试只读当前，新ID才受新价格准入；新政策不追改历史数据或改存档版本。

完成条件：原0..9个位/边界/多宠异色/免费门槛，当前BloodRules可达1139差例，同输入原消费与领域总价一致；未知旧fallback、畸形known拒绝、kind4合价、旧paid跨recipe和后来power变化仍SQL只读、同事务扣款/恢复/source/编码故障回滚均有反馈，固定两轴后再交main单片。创建时原80及旧领域红成立，新实现/共享/部署/GUI未验；当前private整批保留BASE恢复模块，避免夹带本费用变更。

方法：research沿真实scalar→属性→余数→累加追源；diagnosing-bugs以900对1260最小差例反馈；codebase-design把新报价冻结于既有角色结算Interface；writing-for-agents共置原值、兼容与完成条件。完整原服异常存档行为及商业容量未验证。
