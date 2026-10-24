# 家族小时维护与解散待办

第十四批补 family_maintenance 与 family_maintenance_runtime：显式新建家族的持久时钟、正常/简易维护、人气设计式、总库存刷新、降级补偿、超时停表恢复与实际周期调度。零级进入持久 dissolution_pending 并撤销组织权限；跨帮派、角色、任务、地图的清理消费者尚未完成，**不是完整自动解散或整套家族发展完成**。

## 来源与设计

第一手调查及失败检索见 FAMILY_DEVELOPMENT_RESEARCH.md。本包 family.layout 支持人气按小时变化、在线越多增长越多、人气不足1000维护费+50%、正常生产资金门槛48倍。cmessagetip141692支持资金不足时仅扣基本维护费、不增加药品/特产；144353支持小时周期。五级原 base/drug/productconsume 与 drugmax/productmax 原值保留。

本包141507为降级获得500万资金与1000人气，优先于2012官网的500人气；金额/人气数字是 client_verified 文本事实，执行顺序/加法仍是设计。配置唯一来源 recovery-baseline.json.organizations.family_maintenance，不把字段原值当成服务器公式。

| 项目 | 当前明确设计 |
|---|---|
| 小时边界 | 新家族创建时刻+3600000ms，每次成功批次推进一小时；历史家族未知时钟不初始化 |
| 正常费用 | 当前等级基本费+已开启药/特产费；开始时人气<1000，则总额×3/2向下取整 |
| 正常门槛 | 扣费前资金严格大于48×上述有效费用；等号按简易处理，原文字在等号处不能共同确定 |
| 简易维护 | 只扣基本费（同样按开始人气加50%），不足时扣现有余额至0；不生产、不清旧库存 |
| 人气 | clamp(原人气+2×本次有效在线人数−10,0,5000)，系数为 designed；没有借用个人PK人气+12 |
| 产出 | 正常且相应生产开启时，将该行总库存补到当前级 drugmax/productmax，保留已有超额；这是 designed 补满，不称原每批新增量，也不是每种药品各一份容量 |
| 降级 | 扣费和人气变化后，资金或人气<1时降一级；尚有级别则加500万、加1000人气并裁到上限，建设清0；本批不实现建设升级 |
| 零级 | 同事务写零级、clock=dissolution_pending、带成员/帮派代次的outbox，停后续维护；暂不清角色声望/任务或直接替帮派选继任 |
| 过期时钟 | 超过5分钟延误则拒绝普通tick，系统按持久resume凭据把下一期移到恢复时刻+一小时，资金/库存/人气不变；不虚构历史在线或倒扣停服费用 |

以上含设计处均不是原服完整平衡证明。停止期间不补算是明确设计；历史数据迁移须另行授权，而非登录推定新建。

## 公开 Interface 与事务

`FamilyClock`、`MaintenanceCommand`、`MaintenanceReceipt`、`ClockResumeCommand/Receipt`、`FamilyDissolution`均冻结。MaintenanceCommand包含family、due_ms、最多40个(role,epoch)观测、服务器request_id与deadline；不含Session/连接/可变目录。角色租约只用于验证在线观测，系统tick不冒用离线族长的login_epoch。

`OrganizationStore.maintain_family(command,now)`是可信系统 Adapter，在传入family对应组织所有者的有界I/O工作中执行。读当前时钟/政策、组织/资产/产品recipe和成员租约；外族/旧epoch不计在线。family+due_ms是持久批次键，保存观测与policy的指纹。相同意图取旧冻结凭据，改变观测拒绝；不因请求重试再次扣款、产出或补偿。

费用、资金/人气、库存、产品/组织/时钟版本、降级或解散outbox、结果凭据在同一事务。系统凭据保留变化前后绝对值、实际费额、补偿额、级别和recipe，作为系统资金审计；不捏造actor0写角色资金ledger。角色cash/背包不由维护直接改。晚期凭据失败整体回滚。

`family_maintenance_snapshot(identity)`是可信冻结诊断读；`family_dissolution_pending(identity)`返回带(family,due,guild,guild_token,((role,member_generation),...),state)的冻结待办。`resume_family_maintenance`也是按family所有者执行，旧due键保证恢复重试不反复延后；暂停区间与新时刻持久保存。

`due_family_maintenance(partition,now,after=None)`为有界索引提示，按next_due/family续读，每批最多16。它不授权写状态，所有者仍检查当前due；续读游标只存IDs/时间，扫到末尾再绕回，避免前排异常家族永久饿死后排。

## 周期执行和隔离

FamilyRuntime启动FamilyMaintenanceRuntime，当前配置启用16个独立目录循环，每5秒读一次各自有界索引。实际tick与管理、扣费共用 `('organization',family_id)` 的已有邮箱；没有全服维护命令队列。目录循环只派发有界独立jobs，不等待一家族提交后才允许另一家族开始。每family合并一个job，job总数受batch×partition及owner_limit共同约束；满载保留持久due等待后续扫描。

到期时，从本家族有限成员与只读在线目录构造观测，交组织邮箱；过期则交同一邮箱写resume。网络循环不读文件、建表、做同步数据库；跨所有者只投递冻结逻辑数据。普通维护后沿已有FamilyWake投影当前面板，目标连接仍独占原加密/发送。

关闭时只取消目录的睡眠/只读扫描，已受理维护job及组织事务排空；取消等待不能撤销已提交资金变化。I/O超时沿原组织所有者的未知结果围栏处理，旧工作不能被下一条写越过。SQLite仍为本地兼容Adapter，不宣称商业多写能力。

## 零级的当前能力与剩余消费者

零级pending保留历史成员和任务/资产数据供恢复，不将“写了一个outbox”计作清理完成。家族普通命令/面板停止，membership视为无有效家族；guild_scope、职位资格、帮派名单、发送和出队授权过滤该家族；旧scope不能继续使用NPC修炼或组织权力。FamilyWake通知在线角色离开家族，独立guild nudge刷新成员。没有清掉物品、声望或新关系。

组织表本身仍无MapAddress/准入绑定。主集成的组织NPC准入须同时遵循当前有效成员资格与完整地图政策；不能拿可信诊断快照或旧member行授权。原成员行暂留会阻止重新加入/创建，直到后续清理按代次完成，不能跳过这一阶段抢先授权新组织。

还需完成：家族所有者按持久成员代次交付角色声望/任务/特产清理；帮派所有者按guild_token移除家族、选帮主或解散末家族帮派；地图所有者清退实例。各消费者须幂等/恢复/不误清新加入关系，全部确认后才提交解散终态。原提示141510..512/142935支持继任/末家族解散，但候选顺序及跨系统合同仍需实现。当前不能手工把outbox改committed冒充完成。

## 验证与交付范围

verify_family_maintenance十五组通过：新建/重启时钟、normal/simple/倍率/库存、批次重试与冲突、降级补偿/零级待办、resume不补扣、真实组织邮箱重复tick、受控暂停另一家族和原生加密心跳继续、目录续读、过早/过期/非法观测、晚receipt整体回滚、实际5秒周期自动派发及停机排空、pending权限和排队消息失效、未知历史时钟不补。周期测试只加速临时库中家族年龄，没有把生产周期改短。心跳允许同时收到合法家族刷新；原先仅匹配唯一回包的测试断言已修正。

必要回归包括组织领域/资金、家族生产/管理/临时TCP、组织运行、帮派职务/投影、研究初始化、现金修炼和登录恢复；结果与固定源码哈希见 family-maintenance-batch.json。未打开游戏、部署、重启运行服、实际战斗或改真人数据；原GUI、真实NPC创建/生产/购买、商业容量和完整解散仍未验证。

启动依赖须一起交付：family_maintenance/runtime、faction_domain/runtime、family_runtime/projection、guild_offices/projection、family_products及baseline/catalog。OrganizationStore.initialize先准备维护表，再迁移会查询资格的帮派表；热路径不兜底建表。共享game_runtime/runtime_storage/accounts/serve/gateway本批未编辑，social_runtime的guild.initial仍属第十一批。

方法：research后台完成原包/官方定向调查；codebase-design将系统时钟和资产结算隐藏在既有family所有者的深Module；tdd逐条公开Interface先红后绿（缺时钟、normal、simple、downgrade、resume、runtime、目录续读、pending资格失效），并补必要故障/回归，未声称每条补充检查都先红；writing-for-agents共置来源、恢复规则、接入与完成标准。没有声称Standards/Spec双轴审查。
