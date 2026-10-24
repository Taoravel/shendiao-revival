# 原生家族快照：已核对字段

2026-10-24。FamilyData原序列化器0xed7340，SUpdateFamilyData(0xc55f3)的wrapper序列化器0xed7cf0在+8内嵌该bean，正文无额外前缀。FamilyView已通过FAMILY_MANAGEMENT_RUNTIME所述读模型接运行面板；原GUI未验收。第六批补证+68/+6c为人气当前/上限，+70/+74为建设当前/目标；第十八批确认尾Q为客户端家族场景标识，实际绑定由main另接，见FAMILY_DONATION_NATIVE_HANDOFF。

| bean偏移 | 原布局 | 已有消费证据 |
|---|---|---|
| +4 | i32 | 家族ID，14a2950写管理器+d0；FamilyID控件显示 |
| +8 | 字符串 | 创始人姓名；管理器+e0，14c9265给FamilyCreater，family.layout明确“创始人” |
| +24 | 字符串 | 家族名称；管理器+fc，14c8a6b/14c8aae给FamilyName |
| +40 | 字符串 | 家族宗旨；管理器+118，14c9452/14c9490给FamilyPurpose |
| +5c | i32 | 家族等级；管理器+140，14c8b53/14c8bb0给FamilyLevel |
| +60 | u64 | 家族资金；管理器+148，14c8b15/14c8b2a给FamilyMoney；独立于族长cash |
| +68/+6c | 两个i32 | 人气当前/上限，经管理器+150/+154到FamilyPopular控件；14c9692/14c96aa/14c975b |
| +70/+74 | 两个i32 | 建设当前/目标，经管理器+158/+15c到BuliderProgress；14c94bb起计算进度与显示数字对 |
| +78 | u64 | 客户端家族场景标识；14a2950写manager+d8/+dc，148c1f0与当前world+30/+34完整比较 |
| +80 | course向量 | 元素跨度0x18，尚待恢复，当前空向量 |

UI创建14cb1f0起将FamilyName/FamilyMoney/FamilyLevel/FamilyCreater/FamilyManager/FamilyPurpose绑定到独立控件；更新14c8a20追踪上述管理器字段。现任族长姓名另由1496ec0从成员缓存选职位标志2的人，再写FamilyManager，故第一姓名字符串不能拿当前族长姓名替代。FAMILY_POSITION已按原任命函数绑定0/1/2及退位规则。

verify_faction_native.py现共29项，包括非空UTF16、资金2^40+7及四个人气/建设数字逐字节比对；未知资金None拒绝。family-view-disasm及family-panel-runtime-disasm保存原生链。FamilyView要求明确资金，未知旧余额不填0；新家族初始规则按ORGANIZATION_FUNDS，面板/名单/重登按FAMILY_MANAGEMENT_RUNTIME。尾Q原消费已证，组织驻地真实绑定、历程与完整库存等扩展仍待补齐。

原包family.layout提供建设/维护线索：捐献银箱提升建设、人气按小时变化、低于1000维护费增加50%。后续已实现的领域维护与银箱升级及来源/设计分界，分别查FAMILY_MAINTENANCE_RUNTIME及FAMILY_DONATION_RUNTIME；这些实现尚不代表真实NPC与GUI完成。

方法：codebase-design维持小快照Interface，原x86比对与布局/消费者交叉核对区分格式和业务证明。成员/职位/基本建设进度及实际登录刷新已在临时加密运行/真实TCP验证；完整帮派、建设玩法、扩展字段及原客户端GUI仍待恢复。
