# 社交全量恢复状态

用户目标是全量恢复，包含好友、聊天、玩家群组、家族帮派及扩展、师徒、结拜、婚姻等。目标持续active；协议/领域/临时TCP通过均不能替代原客户端完整验收。原生范围social-full-recovery-inventory.json全部complete=false，其类数量仅用于发现范围。

## 当前进展

最新用户明确要求家族帮派整套玩法及修炼全部实现。完整范围与各项当前状态见[GUILD_GAMEPLAY_RECOVERY.md](GUILD_GAMEPLAY_RECOVERY.md)，权限进展见[GUILD_OFFICES_RUNTIME.md](GUILD_OFFICES_RUNTIME.md)；没有缩减为基础社交。

| 系统 | 已有产物及验证 | 主要剩余 |
|---|---|---|
| 好友/基础聊天 | 29项原生格式；申请审批、离线恢复、黑名单、持久化、角色独立有界邮箱及真实临时TCP通过 | 实机GUI、富文本/离线私信/完整扩展设置 |
| 玩家群组 | group_protocol/store/runtime；28项原生格式、4个原按钮模拟；主流程及邀请、管理员任免、公告/个人提示、踢人、原历史分页；真实TCP、迁移/重启/撤权旧投递过滤与独立群并发通过 | 生命周期/群主通知、在线变化、系统/富文本、GUI；原转让证据仍缺 |
| 家族/帮派 | 独立组织所有者；原生管理、名单/频道、职位/授权、研究/七项开关；现金/丹结算、NPC Adapter及登录恢复；生产设置、分区维护/降级/帮派解散；银箱结算及自动升级候选 | 原NPC正式创建/捐献/购买、完整面板、属性/铭文/生活学习/战斗效果、研究进度、生产购买、解散任务/物品/场景清理、任务/Boss/帮战及GUI |
| 师徒/结拜/婚姻 | 原生候选类及功能范围已盘点 | 逐项原协议、完整玩法、运行接线、实机验收 |
| 组队/契约/交易协作 | 明确跨系统依赖范围 | 与角色资产、地图、战斗的所属Module接通及验收 |

好友、群组、家族原生管理与家族/帮派频道已通过social_runtime接到GameRuntime源码路径。目标连接独占加密/发送；群和组织所有者不等待其他角色邮箱。取消请求等待仍保留已提交工作的所有权，独立群/家族与路人心跳可在另一实体存储受控暂停期间继续；不同群审批同一个角色的群额在事务中竞争，不能超额加入。

各项规则来源与本地设计分别见SOCIAL_RELATIONS.md、COMMON_GROUPS.md、FACTION_DESIGN_GAPS.md和design/recovery-baseline.json。群主退群当前为明确designed的原子解散，不能当作原服转让规则；过期申请后台清理和原生错误提示待补。

## 最近验证与实际部署

第十七批银箱扣物/家族确认/自动升级/周期恢复候选在固定r2通过17组新检查及14项回归，独立两轴均0；r1审查P1“成员仍在却档案丢失被误当离开”已先红复现再修复，r1证据保留。r2数值标记保留历史；当前数值已按FAMILY_DONATION_ROOT_DECISION批准。第十八批原296/选择器/选中key与驻地标识补证见FAMILY_DONATION_NATIVE_HANDOFF；真实准入、共享入口与GUI未接，见FAMILY_DONATION_RUNTIME及FAMILY_DONATION_NUMERIC_HANDOFF；未改共享入口、部署或启停进程。

第十五批当前频道延迟投递候选已通过独立Standards0/Spec0，固定基线、依赖和交单见SOCIAL_SCENE_DELIVERY_HANDOFF.md；真实共享ticket/pin/queue/drain由主集成另验。第十六批解散帮派消费者14组新检查、13项回归在固定源通过，实际周期源与原生加密消息已验，见GUILD_DISSOLUTION_RUNTIME.md及guild-dissolution-current-review.json。两批均未由本窗口部署或开启游戏；工作区进展不代表运行服已激活。

第二批verify_group_management、verify_group_ui、扩展verify_group_native/tcp通过。修正群消息时间和个人提示/加入标志顺序；原x86按钮模拟不是运行GUI。verify_group_runtime/concurrency/quotas及好友关系/运行/TCP、共享verify_runtime、verify_runtime_io_order回归通过。费用Module currency.py及CURRENCY_DECISION已核对，组织生产扣费/退款仍未接。所有级别、历史数据、付款凭据与家族等级仅在临时数据库，没有更改真实资产或联系人。

第三批新增faction_payments.py及revoke_funding，实际currency现金扣款、取消后一次退款、断线租约/恢复、丢回包和8次提交/撤销竞争均验证；原扣款凭据丢失由单条TDD先复现后拦截。FamilyData创始人/家族名/宗旨/等级/独立64位资金已沿原控件核对并编码，尚非完整原面板。具体接线完成条件见FACTION_PAYMENTS.md；字段证据见FAMILY_VIEW_CONTRACT.md。原生创建与角色支付入口仍未接，不能称为游戏内建帮已完成。

第四批新增faction_runtime.py，家族/帮派成员频道、禁言、冷却、去重、黑名单、重登恢复及家族退出再加入后旧帮派消息过滤通过。每组织有界所有者同时处理可信命令及撤销；实际钱包验证确认取消等待仍按原队列先提交后判定撤销，不会误退款。原生名单/移除/退出编码新增11项，4次原职位查找确认族长2、副族长1；成员其余四i32与附加文本显式待绑定，不伪造完整名单。具体方法/接线/未验证见FACTION_RUNTIME.md、FAMILY_ROSTER_CONTRACT.md。好友/群管理、共享运行时/I/O顺序、货币及好友TCP回归通过。

本窗口未启动或操作当前游戏，未部署/重启真实28993服务。当前进程加载、原客户端GUI、多进程商业数据库及完整容量/故障恢复仍待验收。共享serve.py、gateway.py、accounts.py本轮未改，亦未与主集成窗口并行重写game_runtime.py。

第五批依据原141482/140318费用文本修正宗旨资金池，新增家族/帮派独立资产及组织ledger；家族新建初始资金/人气有官方端游依据，帮派新建0资金明确designed，旧档未知不补发。旧现金宗旨意图可一次退款或按已提交结果恢复，不能双池扣款。原任命函数确认自己选成员/副族长为退位，普通成员须先任副族长；巡察使走帮派协议，不能猜成第四家族职位。名单等级、声望显示对及离线文字已追到原列。决定与验证见ORGANIZATION_FUNDS.md；本批仍非原生完整管理入口/面板完成。

## 方法与产物

第十四批FAMILY_MAINTENANCE_RUNTIME：显式新家族持久小时维护、normal/simple模式和单次费用/库存/时钟/凭据同事务，人气与补满方式明确设计；降级按本包文本500万/1000而非早期官网500。实际16分区有界目录和每家族所有者派发、暂停存储时另一家族/心跳继续、重试/晚失败/恢复和pending资格撤销等15组通过。零级只是解散outbox，角色/帮派/任务/地图消费者、建设升级/银箱/NPC/GUI仍未完成，全量目标继续active。

第十三批FAMILY_PRODUCTION_RUNTIME：家族药品/特产开关与新建空库基线、族长权限/租约当前面板、关闭50000家族资金同事务/ledger/幂等，7组通过并含实际有界组织最后费用竞争。原c5607四按钮(-1保留另一项)及c5606的QiiQii格式离线执行5组通过；NPC正式入口、小时维护/产出/购买、建设升降级/解散未接，不以开关代替整套生产完成。未知历史状态不补零，设计初始值及报价语义单独标记。

第十二批按主策划PRIVATE_SCENE_SCOPE_DECISION补RoleSnapshot可选冻结scene_scope/唯一scene_key，CURRENT_CHANNEL输出完整实例及分区键，旧七参数与显式公共地址保持原整数键，门派/世界不变。公开Interface三条纵切先红后绿，六组新验证及好友/群/组织运行与临时TCP回归通过；主集成负责真实角色地址与索引接入，未计实际私有聊天或GUI验收。固定交单见SOCIAL_SCENE_SCOPE_HANDOFF.md。GUILD_NPC_ACCESS_HANDOFF.md另核已有真实资格Interface，实测家族增加帮派派生成员但guild revision不变，记录组织→完整地址授权缺口，不新增重复后端。

第十一批GUILD_PRACTICE_NPC_RUNTIME：修炼丹36747按原20/30XP且不花资材/现金，真实Inventory同事务和最终编码；孤立资产/钱包child无共同凭据时保留待核对，不补XP/误退款。NPC Adapter提供面板/准备/重新证明后结算，注册由共享集成方接；已知七项/旧预留恢复进入SocialEndpoint实际登录路径，独立有界任务不取消同epoch未过期购买。丹7组、NPC5组、登录5组、原native8组与现金/组织回归通过；原map非空与当前级+1索引补证，仍不宣称NPC正式可玩、已迁移人物资源消费接线或GUI。

第十批role_practice/guild_practice/practice_protocol补七项现金修炼后端，12组个人/组织资源/钱包事务及补偿通过，含8次购买/取消竞争、真实有界帮派所有者最后资材名额、重登租约/重入和未知状态。原按钮0现金/1丹、service1023的NPC Q来源与更新格式4组固化；丹、属性、生活技能、完整NPC原生路由/面板和战斗效果仍待接。原3资材/+10XP/7天与表值保留，现金价/递进设计及声望对应/上限推定分别记录。详见GUILD_PRACTICE_RUNTIME和研究报告，不据此声称已在游戏内开放修炼。

第九批GUILD_NATIVE_RUNTIME.md记录当前帮派读模型与三种原请求，原生9组/投影5组/运行11组/4连接TCP7组通过。家族持久加入记录与帮派独立cursor移交状态，不同步等另一组织；丢nudge可查询恢复，未知已消费基线不重置。原1486190确认2为族长，优先级明确inferred且不能直接任命。后台工作未排空引起的旧退休断言经最小反馈循环排除泄漏，新增等待该独立工作后原11组通过。tdd沿原Seam先红后绿，writing-for-agents集中交单。完整玩法、GUI和当前部署仍不据此认定完成。

第八批新增guild_training并通过既有组织Seam实现set_research、set_practice_open，实际组织所有者竞争最后付费名额只成功/扣款一次；个人经验、等级、效果与原NPC仍待接。原消息144152/144155补证300万组织扣费和600万门槛；旧路径等级-1名额与当前七项共用规则区分client_verified/inferred，关闭/研究零费用designed。verify_guild_training_native固化25项与catalog比对；verify_guild_office_native固化22项；原NPC授权Q确认是npcKey。实际启动政策list→tuple误拒已复现、缩小并修复，3项真实社交初始化及完整临时prepare通过。代码库名录已重生并纳入guild_offices/training哈希，所有系统仍complete=false。详情见GUILD_TRAINING_RUNTIME.md、GUILD_TRAINING_STARTUP_FIX.md。

第七批新增guild_offices，修正每类长老被旧唯一约束限制为一人的问题，接可信组织事务内任命/辞职/九位授权、继任/禁言和两层成员代次。10组事务/迁移/所有者检查通过，22项原任命/授权/辞职函数离线执行通过；家族管理、组织资金、组织运行及原编解码回归通过。原生帮派管理仍未路由，不能把原函数离线检查计为GUI。本窗口遵守主集成部署冻结，未改game_runtime/serve/gateway/accounts，冻结后只读/隔离验证/写证据文档；具体文件状态见SOCIAL_DEPLOY_FREEZE_STATUS.md。

第六批按codebase-design新增family_projection/family_runtime，原生5种请求、当前家族读模型、持久成员与目标缓存过滤进入原组织所有者Seam。原人气/建设四数字补证，目标值按下一等级表推定，初始建设/新成员保留元数据与声望明确设计；未知旧档不回填。9组管理运行、4条真实临时TCP及共享必要回归通过，组织presence故障不阻止角色租约释放。完整来源/产物/步骤/未完成项见FAMILY_MANAGEMENT_RUNTIME，仍未启动游戏或计GUI/全量完成。

codebase-design决定群ID所有权、持久化Seam、个人设置、冻结历史和目标授权/重编码；diagnosing-bugs的反馈循环先复现时间字段回显正文，再依原显示路径修复。前批帮派有效租约误拒亦已复现/修复。没有声称TDD或Standards/Spec双轴审查。第二批详细记录见GROUP_MANAGEMENT.md；第一批见COMMON_GROUPS.md；历史保留在PROGRESS.md。
