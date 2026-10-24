# 帮派成员学习整合交单

读取条件：接service121/原c36b6购买、学习费用政策、个人生活技能登录或旧hold恢复。准确固定候选与审查结果查guild-member-learning-current-review.json；当前新增Module与隔离验证不授权生产采用或发布。

第26批已有guild预留、角色付款/学习与guild确认/退款的持久链；角色购买尚未接main实际RoleOwner/raw分发。唯一机制与来源范围见GUILD_MEMBER_LEARNING_CONTRACT.md、GUILD_MEMBER_SKILL_NATIVE_RESEARCH.md。所有未知字段映射和支付顺序只有显式fixture；不要从verifier复制生产参数。

## 接入顺序与责任

1. 主策划明确唯一member_learning_policy，包含revision/origin/level_cap/minimum_role_level30/minimum_wallet10000/pending_limit及四字段映射。原30/10000与目标行费用有客户端证据；声望门槛/扣除、资源字段和熟练门槛保留仍需明确采用。须同时已有真实building/research/maintenance规则及guild_resources档，不补旧组织状态。
2. 正式货币决定明确绑银/银两/存款映射及可扣用途。目前currency-v1不允许bound_silver的skill_training，代码会拒绝；主策划未采用前不激活。测试仅复制CurrencyRules增加该用途，没有改生产文件。角色经验用现有role_progress，不创建第二XP账。
3. main在准确BASE中局部传OrganizationStore/Runtime(...,member_learning_policy=explicit)。schema在Store.initialize启动prepare；life catalog始终启动只读，已知个人技能即使新学习关闭也沿既有GuildRuntime.initial投14项增量。未知个人档不投0/空表。建角或显式迁移使用role_life_skills.initialize的完整14项基线，不以旧新手章节/曾发空包推断基线。
4. 主集成组织目录提供当前完整LearningResidence(guild,MapAddress,generation,evidence)，原地图1394/模板10076仅来源线索。取得新NpcServiceCommand与当前Location后，在角色Owner事务调用member_learning_npc.prepare_purchase(...,popularity=最新已知个人0x262人气)。未恢复该角色数据源就明确拒绝，不拿帮派人气/声望代替。
5. 角色prepare返回冻结PreparedLearning并释放Owner。独立有界协调者再调用已有OrganizationRuntime.command(prepared.command,now)，操作reserve_member_learning；该guild唯一Owner预留资源/声望。不在角色Owner内同步等待guild，也不让guild等待角色。
6. reserve返回后，重新取得目录结果及NPC/位置证明，在角色Owner新事务调用finish_purchase(...,inventory,currency_rules,popularity,precommit)。当前证明/代次变动拒绝。返回全部当前技能、余额/XP和当前资产投影消息；编码与费用/技能/凭据同事务，提交后只交当前目标连接Owner发送。涉及存款必须提供完整已知库存/存款precommit投影；main角色缓存/属性刷新也归原角色写者整合。
7. 角色返回后释放Owner，再以resolve_member_learning(args=(reservation,))到原guild Owner确认。失败/取消同样由该Owner据实际角色凭据决定退款；遇到orphan支付证明保留hold，不能盲目取消。当前同SQLite Adapter依事务顺序围栏，跨库outbox/inbox另补。

这七步中的独立购买协调者、current个人人气读源、实际组织目录、registry/raw路由与RoleOwner分发均由main统一接线；本批没有替它们建立第二套注册器/缓存或在social endpoint写角色资产。当前可直接复用Interface和所有权已经实现并用真实事务验证，完整购买运行验收仍待整合。

## 当前源与状态

role_life_skills管理14项个人等级/熟练及整体revision；guild_member_learning负责冻结费用/hold/角色学习父证明、确认/退款；role_learning_costs集中三来源费用/XP和子凭据；life_skill_protocol提供c36b6解码、c36b7增量及c36b8完整已知上限map；member_learning_npc保留fresh service/目录与precommit责任。faction_domain/runtime、guild_runtime只接所属Store/Owner/登录/恢复，无shared文件改动。

新请求不接受费用、经验量、等级奖励或客户端声望余额。prepared args只传skill/已知life revision；费用来自固定catalog目标级及显式政策。历史成功回放返回当前状态/绝对余额，不重放旧等级；新请求受当前研究上限与角色资格限制。退出重入后旧hold不能学习，补偿仅回原成员代次。初始熟练、个人制作/属性/战斗效果另补，不能把学习到等级称效果已生效。

原c36b7与七项practice共享客户端树，当前只发送个人生活14增量，绝不发送生活子集c36b5。原后者会删除未含七项修炼，已纳入原生回归。OtherSkills+40及任务窗口role_skills账本保持独立。

## 证据与未验范围

新事务验证11组、原生6组/18种按钮边界，合并旧32为34固定脚本。精确SHA/导入/资源、Standards和Spec结论以当前review指针的review-result.json为准；中间候选若有问题保留，不覆盖历史。r1有XP缺档、恢复隔离与可选登录展示三项P2，且root资源在运行间漂移，不能当完整通过。后续只从冻结source读取枚举资料，原map.pfs单独核摘要，以实际open审计补齐输入闭包；不回写其他窗口当前政策。

实际加密Peer已验证登录14项、关闭学习后仍恢复、旧epoch unpaid hold自动退款、8次同guild重复只预留一次，以及受控阻塞中另一family和4字节心跳继续。付款/NPC在真实当前角色事务Adapter测试，未通过main购买路由，未声称正式现场可达。

未改生产数值/货币政策、共享入口、真实服务/角色/存档，未打开游戏。真实制作/属性/战斗作用、熟练成长、完整NPC组织实例、商业容量/跨库与GUI仍未完成；全量社交目标保持active。
