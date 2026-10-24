# 家族、帮派整套玩法恢复范围

用户最新明确要求“家族帮派玩法修炼这些你都要实现”。这属于现有全量社交恢复目标，不以名单、聊天、职位或面板完成替代整套玩法完成。

| 范围 | 完成要求 | 当前状态 |
|---|---|---|
| 基础组织 | 原NPC创建与共同确认、扣费/退款/恢复、申请审核、退出/驱逐、传位/权限、公告/邮件 | 家族5种管理、帮派3种查询/任命/辞职、基础资料/跨家族名单及组织频道已接源码；NPC创建支付、完整明细/管理及GUI未完成 |
| 家族发展 | 人气/资金定时维护、建设自动升级/降级/解散、药品/特产生产开关和库存、银箱、家族任务/龙舟 | 生产设置、小时维护/设计库存、人气/降级及帮派解散消费者已实现；银箱扣物/贡献确认、自动升级/后台恢复候选已验证，数值已获主策批准；原NPC捐献/购买、角色任务/物品/场景清退与活动未完成 |
| 帮派发展 | 独立地图、建筑升级、帮费/欠费/奖励、捐赠、建设任务、日常及福利；原战场维修另计 | 独立资金/宗旨、建筑选择/费用/进度/升级/代次和当前查询已实现；显式政策下小时维护/资源/研究及降级终末衔接已补；正式政策、NPC/真实建设任务、其他Owner清退及其余仍待实现 |
| 技能研究 | 研究选择、每小时研究经验与等级、维护/建筑影响、权限及原面板 | 选择/bit0授权、显式曲线下持久成长、原生当前列表及真实维护同事务生产者已实现；正式生产曲线/激活、完整原面板与成员技能效果未完成 |
| 成员技能 | 原NPC资格、已研究等级上限、当前/需求声望、学习扣费、持久技能及角色属性/生产效果 | 客户端表与原请求发现；角色资产/经验/属性接线仍待实现 |
| 修炼 | 开放类型、个体修炼经验/等级/上限/消耗、角色/宠物及战斗效果、退出规则 | 七项开关/bit1/开启费，现金12组/丹7组，NPC Adapter5组和登录恢复5组；原NPC正式分发/完整面板与GUI、属性/铭文/特殊段/战斗效果仍未完成 |
| 组织活动 | 召集、组织任务、龙舟、Boss、帮战队伍/报名/竞标/战斗及奖励 | 已确认原Boss/竞标授权；玩法与跨地图/战斗/资产交接仍待实现 |

## 修炼与技能接入依据

第25批新增帮派小时维护/研究生产者，正常/基本费、当前在线人气、工坊资源与练功房XP同事务结算，含降级/终末家族衔接、无收益超时恢复和有界自动检查。参数只有显式fixture，未采用生产数值，guild_resources与修炼资材不合并。当前审查/完整范围见GUILD_MAINTENANCE_RUNTIME及guild-maintenance-current-review.json；此前各批“未接维护”是其当时范围，不替代此增量。完整目标仍active。

第24批GUILD_BUILDINGS_RUNTIME补建筑状态和选择/可信源固定+1/升级闭轮、当前bit5原c5627/28查询、真实加密Peer与重登。9事务/5原生组及30固定回归，两轴均0；原三个计算函数和三UI列已执行，初始值/caps/维护预估只有显式fixture，未采用生产默认值。真实任务生产者、NPC115选择及小时维护/研究联动仍未接；当前guild-buildings-current-review.json，不以此称整个帮派发展完成。

第十九批家族建族、直接传位/原生自退位、银箱升级和非零小时降级历程已同事务保存；第23批增加入帮/离帮真实源与跨组织顺序恢复，见FAMILY_HISTORY_RUNTIME、FAMILY_GUILD_HISTORY_RUNTIME和family-history-current-review.json。未知旧史不补造；活动历程生产者、真实GUI与完整玩法仍未完成。

第十七批银箱与自动升级候选见[FAMILY_DONATION_RUNTIME.md](FAMILY_DONATION_RUNTIME.md)，未知资金/结转/声望槽投影及上限的统一数值复核单见[FAMILY_DONATION_NUMERIC_HANDOFF.md](FAMILY_DONATION_NUMERIC_HANDOFF.md)。固定r2的17组新检查、14项回归及Standards0/Spec0已完成；r1缺档误判P1保留原记录并已修复。第十八批已追证296分派、原选择器/五行提交与完整64位家族驻地标识，已实现固定选中key付款及纯codec，见FAMILY_DONATION_NATIVE_HANDOFF。原服服务器窗口取值仍unknown；组织实例准入、正式资源precommit及GUI未接，不是上线交单。

第十六批家族解散帮派消费者、紧急继任、最后家族关闭、阶段凭据与恢复见[GUILD_DISSOLUTION_RUNTIME.md](GUILD_DISSOLUTION_RUNTIME.md)。14组新检查及13项兼容回归在固定源码下通过；独立两轴审查与精确差异见guild-dissolution-current-review.json指向目录。本批不是完整组织激活交单，也未完成角色任务/物品/地图清理。

第十四批时钟/维护/降级与pending资格撤销、正常/简易模式、原包1000与官网500人气冲突、实际周期及完整解散消费者缺口见[FAMILY_MAINTENANCE_RUNTIME.md](FAMILY_MAINTENANCE_RUNTIME.md)，来源见[FAMILY_DEVELOPMENT_RESEARCH.md](FAMILY_DEVELOPMENT_RESEARCH.md)。

第十三批家族生产设置、关闭费用、原四按钮及QiiQii面板、未知历史档和完整维护接入条件见[FAMILY_PRODUCTION_RUNTIME.md](FAMILY_PRODUCTION_RUNTIME.md)。本批不是小时维护/自动升降级完成。

第八批已实现的组织设置、25项原函数/格式与费用证据、来源差异和接线条件集中见[GUILD_TRAINING_RUNTIME.md](GUILD_TRAINING_RUNTIME.md)。下文是原始发现记录，按该文的当前验证状态执行。

第十批个人现金结算与新增NPC/模式原证据见[GUILD_PRACTICE_RUNTIME.md](GUILD_PRACTICE_RUNTIME.md)，官网版本/消耗缺口见[GUILD_INDIVIDUAL_TRAINING_RESEARCH.md](GUILD_INDIVIDUAL_TRAINING_RESEARCH.md)。后端事务不替代原NPC与战斗效果验收。

第十一批修炼丹、原map/当前经验条索引、NPC Adapter与已接登录恢复见[GUILD_PRACTICE_NPC_RUNTIME.md](GUILD_PRACTICE_NPC_RUNTIME.md)。实际NPC registry/共享购买分发及已迁移资源source回调须统一集成，不将夹具NPC绑定当现场可玩。

原客户端保留clifeskill 49行、clifeskillcost 160行、cadvancedability 51行、cadvancedproperty 40行及cadvancedpropertyconsume 9行。行数只表示原表发现范围；字段单位、索引、公式顺序由调用者进一步核验。clifeskill既有14种可学生活技能，也有360001..360007、铭文与380001..380009等bCanStudy=0条目，不能把所有条目都当生活技能或一律套140上限。

已读原序列化/构造路径：

- CSetFactionResearchSkill c563b，e45740，布局Q+i32；原设置按钮14e16b2从对话框+20/+24和选中技能构造。Q上下文尚未绑定。
- CSetFactionPracticeOpen c563d，e45700，布局Q+i32+i32；原开启分支14e08e0尾值1、关闭分支14e0a87尾值0。类型取值与前置检查仍待完整核验。
- CFactionSetPractice c5655，e450b0，布局Q+i32+i32；与开放请求不同，不合并。
- CPractiseSkill c36cc，e56770，布局Q+i32+i8；原字节校验0..4，UI发送点14d426c、14d474f。Q和mode业务含义尚待绑定。
- CUpdaetAssistSkillLevel c36b6，e56880，布局Q+i32+i8；学习/升级的mode需从NPC调用链确定。
- FactionPractice bean e91320为两个i32；SFactionPractice、SRefreshFactionPracticeData、角色已学/更新技能各有独立原响应，尚未统一接线。

原[帮派技能资料](https://sdxl.wanmei.com/info/newplayer/40to49/20120705/132412.shtml)说明：组织研究依小时维护增长并升级；个人学习受需求/消耗声望约束，费用依次使用储备金、游戏币、存款。该页不是修炼公式来源，版本匹配也未证实。技能学习须调用角色所有者的现有货币/经验事务并写幂等凭据，不能由组织Module直接扣角色资产或在循环中跨所有者同步等待。

原[家族资料](https://sdxl.wanmei.com/info/newplayer/20to29/20120704/132338.shtml)说明自动升级/降级、小时人气维护、药品特产与生产开关。生产关闭费、维护周期和补偿须继续以原配置调用核对，保持资金ledger、批次ID及重启后不重复发放。

## 实现次序与完成判据

沿ARCHITECTURE.md使用角色、家族、帮派、地图、战斗各自所有者。当前组织研究选择/修炼开关可信事务及帮派基本读模型已实现，后者验证见GUILD_NATIVE_RUNTIME.md；继续补完整明细、NPC地图交互校验及原生响应。个人学习/修炼通过角色所有者结算，随后建设/维护/生产及任务、活动衔接。未知规则依DESIGN_AUTHORITY.md集中设计并注明替换条件。

每项同时记录资料、原编解码、服务端状态、运行接线、真实客户端五种状态。资金/声望/经验/库存须验证幂等、余额不足整体回滚、并发限额、退出重入、断线重登和跨所有者失败恢复。当前所有范围均未达到全量完成。

第二十批补guild_detail_protocol：0xc5624完整原详情、非空公告/历程/研究/修炼以及三驻地Q已恢复纯编码；原consumer三Q存储与1393/1395/1394各自gate离线通过。固定r2五脚本全绿、Standards0/Spec0；r1两轴同发现公告键错误缩窄，公开codec先红后改signed32并原marshal验证，历史保留。未绑定用途的字段仍按原偏移显式提供，不从形状猜金额/等级，不发送伪造面板。完整状态、生产查询/NPC/共享接线与GUI未实现，当前交单见GUILD_DETAILS_NATIVE_HANDOFF.md。
