# 帮派研究选择与修炼开关

第23批组织关系历程增量与研究/现金丹修炼一同进行28项固定回归；当前完整组织候选以guild-research-current-review.json及FAMILY_GUILD_HISTORY_RUNTIME.md为准。建筑来源新调查见GUILD_BUILDING_MAINTENANCE_SOURCES.md，原计算线索见GUILD_BUILDING_NATIVE_PRELIMINARY.md；调查不表示建筑事务已实现或成本已正式采用。

第二十二批已将已知研究列表接入登录presence/原查询/选择/奖励后的收件人Owner投影与重登恢复，未知使用原空列表失效旧cache，不补档。26固定脚本全绿、r2 Standards0/Spec0，r1提交后SQLite展示错误P2先红修复并保留证据，见GUILD_RESEARCH_PANEL_RUNTIME.md。原service120/c563b实际NPC仍未接，自动小时研究与建筑参数仍未实现。

第二十一批已补显式曲线下的研究持久状态/多级经验结算、事件重放/回滚/重启与既有组织Owner接入，原五i32已绑定当前等级/上限/经验/升级需求。24固定脚本全绿、Standards0/Spec0，见GUILD_RESEARCH_MAIN_HANDOFF.md及guild-research-current-review.json。无生产默认曲线、不回填旧帮派；真实正常维护/练功房参数及源证明仍未实现，不能据此说自动小时研究已经运行。下文“研究小时经验/上限未实现”是旧批次口径，当前缺口以新交单为准。

第十一批个人丹/现金NPC Adapter、原七类型map与登录恢复的当前接线见[GUILD_PRACTICE_NPC_RUNTIME.md](GUILD_PRACTICE_NPC_RUNTIME.md)。可信Adapter和已知登录投影已实现，实际NPC注册/共享购买分发、完整价格/上限面板、属性/生活/铭文及战斗仍未完成。

第十批补七项现金mode0后端：资材预留、角色现金/修炼XP/凭据同事务、取消补偿、恢复查询与原mode0/1/NPC Q证据，见[GUILD_PRACTICE_RUNTIME.md](GUILD_PRACTICE_RUNTIME.md)。个人原NPC购买/完整面板、丹/属性修炼/生活技能及战斗效果仍未接；下文第八批“个人未实现”是当时范围。

第八批完成组织事务内的管理设置，不表示个人修炼已完成。guild_training.py隐藏研究ID、独立授权、开放名额和持久状态；faction_domain使用原组织资金ledger，同一事务提交状态、费用、revision与receipt。原生NPC请求尚未路由，未操作真实角色、当前服务或GUI。

第九批已补原生帮派基础资料、跨家族名单、查询/任命/辞职与上下线，见[GUILD_NATIVE_RUNTIME.md](GUILD_NATIVE_RUNTIME.md)。此基础不代表NPC研究/修炼请求已接，也不产生个人经验或战斗效果。

## 当前Interface与实际验证

可信调用者通过既有OrganizationRuntime.command提交冻结OrganizationCommand：

- set_research，args=(skill_id,)：帮主或有bit0研究授权的现任副帮主；选择原clifeskill中14种bCanStudy=1技能。
- set_practice_open，args=(skill_id, bool)：帮主或有bit1修炼授权的现任副帮主；当前七种360001..360007。开启需至少6000000帮派资金，同事务扣3000000。关闭不返还开启费。
- OrganizationStore.guild_training_snapshot返回冻结研究ID、开放ID元组和来源。其同步存储访问经有界I/O调用，运行循环不直接调用SQL。

原生Adapter必须先验证NPC entity_key、地图实例归属、角色当前位置版本/距离和服务绑定，再由服务端查当前帮派及副帮主。组织事务再次验证lease、成员代次和权限。客户端Q字段不能直接用作organization或target角色ID。

verify_guild_training.py通过10组：研究幂等、bit0与bit1独立授权/撤销、名额释放、600万门槛与300万扣款/关闭、非法值/普通成员拒绝、receipt末端故障整体回滚、替换租约/重启、退出重入撤权、真实有界组织所有者竞争最后名额、未知旧状态不初始化。家族等级/帮派等级和资金充值均是显式临时夹具，未实现生产升级或收入。

TDD沿既有组织命令公开Seam逐条红→绿：set_research未支持；副帮主持研究授权仍被拒；修炼开关未支持；零帮派资金错误允许开启。后续补充失败、恢复与并发回归。真实启动另外复现JSON列表转元组误拒，见GUILD_TRAINING_STARTUP_FIX.md；实际启动快照3项与完整临时runtime_storage.prepare现已通过。

## 原证据、推定与设计

verify_guild_training_native.py固化25项原设置按钮/编解码及3项catalog检查：原研究按钮、旧修炼开关/等级名额、重复/未选择拒绝；三个组织请求布局及个人两个请求raw mode0..4；返回bean的ID/状态双i32。七节点活跃列表由原1497db0/1497e10查找和计数，测试未替换这两个函数；UI选择、网络、对话框边缘有适配，没有运行GUI。

| 规则 | 来源与状态 |
|---|---|
| 研究bit0、修炼bit1 | 原授权说明822/824与九位列表，client_verified |
| 14种可学生活技能、七种当前修炼ID | 原clifeskill、GangSkillStudy固定控件，client_verified；不把49行全部当可研究技能 |
| 开启扣300万帮派资金 | cmessagetip140373/140374、144152，client_verified |
| 当前七项流程不足600万不可开 | cmessagetip144155，client_verified；旧140372为不足300万，不将两条旧/新消息抹成相同原规则 |
| 旧开关名额=帮派等级-1 | 原14e07ba读取manager+280再减1，与1497e10比较，client_verified；由此也绑定FactionData+40为等级 |
| 当前七项共用等级-1名额 | 从旧路径推定，inferred；新CFactionSetPractice未发现相同服务端公式证据，集中登记guild_practice_open_level_offset及替换来源 |
| 关闭及更换研究不收费 | 本地designed零费用，缺少明确原扣费证据；不冒称原服事实 |
| 新帮派无研究选择、全部修炼关闭 | designed，新建事务内一次创建；未知旧帮派不回填 |

开启费与门槛属于组织资金，不使用角色现金、储备金或存款。个人学习的支付是另一条角色所有者结算链；本批没有实现或虚构个人经验、声望、技能等级与伤害奖励。

## 原生接线交付

| 请求/响应 | 原生布局 | 状态 |
|---|---|---|
| CSetFactionResearchSkill c563b | 上下文Q、研究技能i32 | 原按钮/序列化通过；Q候选NPC key的完整调用链继续核验；组织set_research已实现，NPC路由待接 |
| CSetFactionPracticeOpen c563d | 上下文Q、类型i32、开启/关闭i32 | 旧列表流程；原限额及flag通过；旧类型/新类型兼容映射及Q上下文待补，不直接扩大SOCIAL_TYPES |
| CFactionSetPractice c5655 | 上下文Q、类型i32、开启/关闭i32 | 当前固定七项流程；须完整绑定NPC上下文后接set_practice_open |
| SFactionSetPracticeOK c5656 | 类型i32、状态i32 | 原编码/Process14d9f30确认给当前修炼对话框；待在接收者邮箱编码 |
| SFactionPractice c5654 | 原map<int,int> | 更新当前对话框的七项状态；容器编码与完整原响应待接 |
| SRefreshFactionPracticeData c563c | 原list<FactionPractice(id,status)> | 更新旧manager+328，status按非零转bool；不代替新响应 |
| CPractiseSkill c36cc / CUpdaetAssistSkillLevel c36b6 | Q、i32、i8 | 修炼0现金/1丹及service1023 NPC Q已由第十批原函数确认；现金后端已接可信事务，原NPC购买、其他模式与学习支付仍待接 |

原NPC服务标签119授权、120研究、121学习生活技能、122旧修炼设置、1023个人修炼；NPC模板10076帮派师爷、10077教头来自原配置。服务菜单对NPC的完整绑定、组织地图实例准入仍须核验后注入NpcServices。根共享入口保持原始集成窗口单写；本窗口提供组织命令与上述接线条件。

继续恢复个人学习/修炼时，读取原cnpcserverconfig1242..1247、3133的修炼效果说明：基础战斗修炼影响战斗结算，不应直接伪造成角色属性面板加成。其数值/取整和九项属性修炼须分别绑定原调用，不能仅凭文本套用所有类别。研究小时经验/上限、建设维护、生产、活动及原GUI仍未完成。全量恢复目标保持active。

方法：codebase-design集中事务规则、冻结快照和NPC校验Seam；tdd逐条公共命令红绿；diagnosing-bugs修实际启动快照误拒；writing-for-agents保留接入顺序、来源差异和可判定剩余项。没有声称Standards/Spec双轴审查。
