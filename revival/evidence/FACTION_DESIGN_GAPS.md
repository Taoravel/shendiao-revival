# 家族、帮派恢复与接线记录

第十四批：family_maintenance/runtime已有新家族持久小时批次、normal/simple费率/库存设计、人气设计式、降级补偿、过期resume和16目录实际周期；15组新验证及必要回归通过。采用本包141507的1000人气，明确排除官网500冲突；零级保存代次outbox并撤销家族/帮派权限，跨角色/任务/帮派/地图消费者仍未实现，非完整解散。建设升级/银箱、实际NPC入口及GUI未完成。详见FAMILY_MAINTENANCE_RUNTIME.md和FAMILY_DEVELOPMENT_RESEARCH.md。

第十三批：family_products提供家族独立生产设置、明确新建库存基线、当前族长/租约面板、关闭50000家族资金与原事务/ledger/凭据；7组存储/实际有界运行时和5组原按钮/格式通过。旧未知不补、重试不重复扣；初始关闭空库和无变化零费明确设计，当前级未缩放报价亦区分原表值与服务器设计。实际NPC/线分发、小时人气/维护/产出/购买、建设升降级/解散与GUI仍未完成，见FAMILY_PRODUCTION_RUNTIME.md。

第十一批当前：丹mode1原物品36747/20或30XP、资产/技能/凭据/编码同事务；现金/丹孤立child持久异常不补发/不误退款。Npc Adapter及七类型map实现，登录已知技能与预留恢复已接所属social runtime。7组丹、5组NPC Adapter、5组实际加密登录及8组原native通过；正式NPC注册/共享分发、已迁移人物资源source消费者、完整面板/GUI、属性/生活/铭文/战斗及其余玩法仍待完成，接线合同集中见GUILD_PRACTICE_NPC_RUNTIME.md。

第十批：个人现金修炼后端已具备七项持久等级/XP、资材预留、角色现金同事务与失败补偿/恢复，12组通过；原按钮mode0/1和service1023 NPC Q及技能更新4组通过。价格/推进设计、资材未知拒绝与跨数据库限制集中见GUILD_PRACTICE_RUNTIME.md。原NPC购买路由/完整面板、丹/属性修炼、生活技能、特殊阶段/战斗效果及其他组织玩法仍未完成。

第九批当前进展：guild_protocol/projection/runtime接原帮派查询/任命/辞职三种请求、基础资料和跨家族当前名单、上下线/重登、家族加入持久交接及退出移除。原职位2族长已核验并推导显示；9组原编码/格式、5组存储投影、11组加密管理运行、4连接7组真实临时TCP通过。完整明细、NPC创建/授权/研究/个人修炼、维护生产建设及活动和GUI仍未完成，详见GUILD_NATIVE_RUNTIME.md。下文“帮派管理未路由”是先前历史。

第七/八批当前进展：guild_offices实现独立长老名额、巡察使、九位授权及卸任继任；guild_training实现研究选择、七种修炼开关、独立授权及300万组织扣费/600万资金门槛。各10组可信事务检查、22项职位原函数、25项设置原函数/格式及实际启动快照3项通过。来源、当前七项名额推定、零关闭/研究费设计和NPC接线条件见GUILD_OFFICES_RUNTIME.md、GUILD_TRAINING_RUNTIME.md；个人学习/经验/结算、完整帮派投影与NPC、维护建设生产活动及GUI仍未完成。

第六批接线：5种家族原生申请/审批/任免/退出/驱逐、当前面板/名单、在线/重登已进入运行路径，见FAMILY_MANAGEMENT_RUNTIME.md。持久新成员generation/声望/离线源，旧未知不补零；申请详情和清理ID均按出队权限及目标实际缓存过滤。29项格式、9组原管理函数、9组加密运行与4条真实临时TCP通过。原生创建支付/共同同意、完整帮派、历程/库存/特殊确认、建设维护及GUI继续未完成，下文先前“家族管理未路由”是历史。

第五批修正：原cmessagetip141482/140318证实宗旨消耗家族/帮派资金，已更正旧家族扣现金、旧帮派免费行为，见ORGANIZATION_FUNDS.md。新建家族资产与创始人、独立组织支出/ledger、历史现金意图恢复、原族长退位规则已实现；11组组织资金/迁移验证与7组原任命函数模拟通过。家族等级/声望显示对/离线文字已绑定，尚余元数据与消费语义。下文旧“家族宗旨须现金凭据”是历史，原生管理/完整面板、建设与GUI仍未完成。

最新：组织频道、命令/撤销邮箱与投递接线读FACTION_RUNTIME.md；付费角色阶段和重登恢复读FACTION_PAYMENTS.md。faction_runtime已接家族10/帮派4、成员/禁言/冷却/黑名单及重登；11组运行验证和四条真实临时TCP连接通过。现金支付验证扩到13组，含实际组织邮箱的取消等待/顺序撤销。原生格式扩到25项及4次原客户端职位查找，名单字段见FAMILY_ROSTER_CONTRACT.md，面板见FAMILY_VIEW_CONTRACT.md。原生角色付费/恢复、完整管理面板及建设仍待完成。下文前批“仅测试付款凭据/没有支付Adapter/无运行接线”是历史；当前仍不能声称游戏内已开放建帮。

2026-10-23补充修复：共享AccountStore当前返回整数epoch，role_leases为TEXT列；此前直接比较导致创建者、家族共同创始人、帮派共同创始人及聊天有效租约均误拒。verify_factions先失败于stale_epoch；最小临时存档确认int/str类型差异且active=1，统一按字符串比较并保留active检查。16项领域回归通过，额外验证真正旧聊天epoch失败、新epoch成功。当前仍未接真实扣费、原面板与完整运行链路，此修复不代表帮派已可在游戏中创建。

2026-10-23。本批交付独立领域模块faction_domain.py、原请求编解码faction_protocol.py、verify_factions.py、verify_faction_native.py；不修改共享serve/gateway/accounts。真实账号、联系人和组织数据库没有被本批测试修改，所有验证使用临时数据库。

## 原资料和规则边界

本地faction.cfamilyprogress、cfactionprogress表和原版familyfound/family/familyapply布局确认“家族→帮派”结构。cfamilymaintainconfig含维护/生产数据，但不能当成完整升级规则；尚未接入建设、维护扣款及等级自动变化。

历史官方[家族资料](https://sdxl.wanmei.com/info/newplayer/20to29/20120704/132338.shtml)提供创建等级、人数、费用和容量依据；[帮派资料](https://sdxl.wanmei.com/info/newplayer/20to29/20120704/132324.shtml)提供家族建帮、管理权限和传位/禁言依据。两页日期路径为2012-07-04，不能证明精确匹配本地1.6.1。规则参数及来源集中于design/recovery-baseline.json.organizations。申请容量100、帮派最多10家族、聊天256字符是明确设计值，不是原服数字。[聊天资料](https://sdxl.wanmei.com/info/system/chat/20120728/133496.shtml)支持家族/帮派独立频道与3秒发言间隔。

## 已实现与验证

- 家族创建：校验名字/宗旨、最低3位20级创始成员、在线租约快照、成员唯一归属及付款凭据；创建后族长与成员持久化。
- 成员申请/审批、容量检查、族长/副族长权限、职位变更和传位、普通成员退出、驱逐；副族长须先解除职务才可驱逐，族长须先传位。
- 帮派由家族创建；校验族长身份、人物40级、家族3级和至少半数容量的在线成员。帮派成员从所属家族派生，加入申请以家族为单位，帮主审批。
- 帮派副帮主设置、72小时入帮时限的帮主传位、家族离帮/被驱逐、保护现帮主所在家族不被移出。普通成员不能执行管理命令。
- 家族/帮派宗旨修改；家族修改依然要求费用凭据。帮派禁言持续现实时间1小时，保护帮主和副帮主；左右长老尚未实现。
- 组织聊天只接受本组织成员，3秒发言间隔持久化。OrganizationBroadcast返回独立类型，含组织revision与不可变成员名单；收件前authorize_delivery重新查权威成员，避免驱逐后收到旧名单排队消息。不能直接使用旧Publish默认世界广播路径。
- 每次写事务内核验role_leases，request_id结果和fingerprint在同一事务保存；重试不重复建组织，改参数复用request_id被拒绝。不同组织用不同所有者，创建按creator分区，不把organization=0变成全局队列。

verify_factions通过：缺付款拒绝、付款凭据消费幂等、家族成员/权限/审批、家族入帮、帮派传位/禁言、组织聊天与冷却、驱逐后排队收件复核、过期登录写拒绝和重开保存。测试中的付款凭据和家族3级是**测试夹具**，未模拟生产货币扣款或自动升级；见faction-domain-verification.json。

## 原生协议状态

12条请求布局执行原x86序列化器逐字节比对通过，见faction-native-verification.json；原始字段探查在faction-protocol-disasm.txt。覆盖创建家族、家族审批/任命/驱逐/退出、查询家族/帮派、申请入帮、建帮确认、帮派审批/任命/退出。

创建请求含u64上下文、i32模式、名称、宗旨、i32阵营；具体NPC上下文/模式和审批/职位枚举仍未绑定。faction_protocol.decode保留原始值，**不得直接将客户端自带的角色ID、模式或批准值当成可信命令**。CJoinOtherFamily的批量申请结构及FamilyData/FactionData的完整下行快照未恢复，当前不能宣称原客户端能显示家族/帮派面板。

## 集成要求

1. 启动时只读加载organizations策略，在有界持久化Adapter执行OrganizationStore.initialize，热路径不建表/读全配置。组织表为专用关系分片；SQLite仅本地Adapter，不具有横向多写扩展能力。
2. 原始字节仍由连接所有者解码；校验NPC上下文、当前角色归属与审批枚举后，构造OrganizationCommand。按OrganizationStore.owner_key路由到有界实体邮箱，事务运行在有界持久化分区；禁止网络循环同步调用execute/chat。
3. 多人建家族的founders必须来自团队及角色所有者确认的同意快照，不能直接信任客户端报上来的ID/epoch。当前模块只核对租约和已有归属，团队/同意收集需所属系统接线。
4. 建族/建帮/家族修改宗旨由角色已BEGIN租约事务调用OrganizationPayments.fund，封装cash扣款、grant和恢复意图。金额/用途从启动规则派生，组织只消费匹配actor/request_id/fingerprint的grant。原生角色入口接线前保持funding_required，不能用手填付款凭据绕过。
5. 失败先由组织owner_key下revoke_funding决定取消，角色resolve读取持久决定退款；已成功或结果未知不退款。详见FACTION_PAYMENTS.md。跨数据库outbox/inbox与实际原生入口尚未完成；同库扣款和建帮仍是两个事务，不能宣称整体原子提交。
6. 帮派/家族成员列表由snapshot取得。组织聊天使用独立OrganizationBroadcast，分批对名单执行authorize_delivery与社交黑名单过滤，再交目标连接邮箱并检查epoch；编码可用faction_protocol.organization_chat（家族频道10、帮派4，由原UI映射表确认）。旧GameRuntime.effects对不认识的Publish scope缺少显式拒绝，不能往该路径发送organization scope。
7. 模块已有按组织顺序处理约定及事务幂等；仍需集成成员归属变更事件以刷新角色/频道目录，未提供跨进程租约目录。成员派生查询在关系分片内进行，任务/地图/战斗不得持有组织可变对象。

## 尚未完成

共享入口与真实客户端UI接线、生产扣费/退款、家族等级建设与维护、左右长老和独立权限、帮费/捐赠/奖励、建筑/技能研究、帮派地图/传送、帮战、联盟和家族生产。群组/结拜/师徒/婚姻属于其他社交模块，本批没有冒充已恢复。未做组织容量或商业并发压测。

方法记录：codebase-design用于组织所有权、持久化Adapter和不可变投递事件；diagnosing-bugs的反馈循环用于原生消息逐字节比对和权限/幂等回归。没有声称采用TDD或完成code-review双轴审查。当前产物是可测领域逻辑和请求布局，不是已在游戏中生效的完整帮派玩法。
