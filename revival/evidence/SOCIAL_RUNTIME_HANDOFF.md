# 社交所有者接口与共享入口接线交接

最新第二批：GROUP_TYPES从7增至13，已含邀请、接受拒绝、任免管理员、共享/个人配置、踢人和历史请求；GroupHistoryDelivery在目标重新授权和黑名单筛选后编码，邀请以当前token/权限复核。只修改群/社交所属模块，现有GameRuntime继续沿SOCIAL_TYPES路由。28项原x86格式、4个原按钮模拟、完整管理真实临时TCP、旧表迁移/重启通过，详见GROUP_MANAGEMENT.md。已读主策划currency.py和CURRENCY_DECISION，组织生产cash扣款/退款尚待按角色所有权衔接。本窗口未改当前手动客户端或部署/重启。

2026-10-23本轮新增玩家群组接线：social_runtime内GroupRuntime按群ID调度、GroupDelivery复核成员generation/version及黑名单，登录恢复群名单和待处理申请；social_protocol.SOCIAL_TYPES已包含7种主流程请求，现有GameRuntime无需增加分支。17项原x86、运行对象、两连接真实临时TCP、受控慢群I/O/取消等待、跨群群额并发均通过，详见COMMON_GROUPS.md。邀请/群管理等未完成，真实服务未由本窗口重启。下文早期“未接线”文字仅为历史，不代表当前源码状态。

最新状态：social_runtime.py及GameRuntime的社交挂钩已实际接入源码。每角色独立有界邮箱执行SocialCommand、RelationWake、离线补偿和Delivery过滤；跨角色只入队，不同步等待另一角色，避免双向私聊形成邮箱等待环。ConnectionOwner.close现在等待已进行的同一次清理，防止持久化资源早于断线通知关闭。serve.py/gateway.py/accounts.py未改。两个认证加密客户端的真实临时TCP、运行对象回归通过；正在使用的28993连接未被重启，新源码不等于当前进程已加载。交接中的旧“未接线”说明保留为历史依据。

最新补充：本批新增好友申请/审批、黑名单及带名称分组；SOCIAL_TYPES已扩展。集成前请读SOCIAL_RELATIONS.md：增加RelationWake效果、角色启动时补处理relation_events与pending_notices、所有私聊/公共聊天/申请通知须经收件角色filter_delivery后进入连接邮箱。新功能只在social_owner.py，不在旧social.py兼容Adapter。原生检查现为29项。

2026-10-23。根AGENTS.md和ARCHITECTURE.md新增约束后，本窗口停止修改serve.py、gateway.py、accounts.py。此前基础接线和真实网络检查已落盘；运行进程PID31844仍是旧单循环兼容路径，不代表商业并发迁移完成。后续共享入口由原始复原窗口统一集成。

## 已完成的独立领域路径

`social_owner.py`不导入Session、不引用目标会话、writer、RC4/MPPC，无全局锁、全服命令队列或线程池。

- `RoleSnapshot(role_id, login_epoch, name, level, school, shape, scene_id)`为冻结快照。角色ID、门派、姓名等从已认证角色所有者提供；地图变更后替换为新版快照，不让社交读其他Module的可变world对象。
- `SocialCommand(role_id,login_epoch,request_id,deadline_ms,kind,body)`为冻结命令。`RoleSocialOwner.execute(command, online_snapshot, now_ms)`先检查所属角色/epoch/截止时间，再处理查询、持久化联系人、私聊及公共聊天。`online_snapshot`只包含冻结RoleSnapshot，可以用MappingProxyType传入。
- `SocialResult.effects`只包含冻结`Delivery`或`Publish`。前者携带目标role_id、login_epoch、消息类型和bytes正文；后者携带scope、partition_key、sender_role_id、类型和正文，不在角色处理中遍历全服广播。
- `RoleMailbox(role_id,login_epoch,capacity)`每角色独立、有界、非阻塞提交；满载返回backpressure，旧epoch返回stale_epoch。容量由集成方明确注入，禁止共用一条全服队列。此类只做邮箱，不自建调度线程。
- `SQLiteSocialStore(path)`只负责关系持久化，构造不做DDL。`initialize()`在启动迁移执行一次。friends使用JOIN消除旧路径逐好友开连接；contact在单事务内判上限并幂等写入；watchers按owner游标分页且单批最多128，已有target索引。

## 集成方所需接线

1. 在启动阶段加载design/recovery-baseline.json.social只读策略，并执行SQLiteSocialStore.initialize。RoleSocialOwner的max_contacts、max_text明确注入该策略值；热路径不读配置/建表。
2. 已认证、拥有角色且进图确认后，由角色目录授予有效login_epoch，建立角色独立邮箱/所有者。消息种类只接收social_protocol.SOCIAL_TYPES。调度不能把整个Session.feed连同跨会话对象丢入一个线程池。
3. 将同步SQLite Adapter调用放到有界持久化资源或该角色的工作执行路径中，网络循环不调用execute/initial中的同步存储。当前提供的是可替换的本地SQLite Adapter，未声称异步商业数据库完成；同文件单写瓶颈仍在。
4. 初次注册读取`owner.initial(online_snapshot)`，把Delivery排入**目标连接所有者**的有界发送邮箱。连接所有者核验最新role_id/login_epoch后独占调用自身Session.send和writer，其他线程不得调用目标Session.push。
5. Delivery私聊按目标role_id分区路由；若目标epoch已变化，拒绝旧消息，不把旧登录消息送到新会话。满载明确返回拒绝/断开慢连接策略，不允许无限缓存或静默声称成功。
6. Publish按scope路由到scene、school、world频道所有者，再按成员快照和有界批次分发。当前频道语义为同场景，不宣称AOI距离已恢复。世界频道继续按channel_partition拆分成员投递，禁止全服阻塞广播循环。收到消息的发送人也由频道目录投递一次，避免重复回显。
7. 上下线通知由有效在线租约变化事件触发，分批调用store.watchers(target,after,limit)，为在线观察者生成Delivery(观察者role_id,当前epoch,ONLINE,pack('>Qi',角色ID,状态))。按分页游标继续，不能在网络循环同步查询/广播；断线旧epoch只撤销自己的租约。
8. 紧急兼容Adapter为social.py旧SocialHub，仍持有Session引用并跨连接push。集成完成后移除其运行引用及gateway中的`social.online.get(roleid) is self`检查，改为角色目录epoch校验；旧类不是目标Interface，不能用于跨线程部署。

## 验证与未迁移范围

`verify_social_owner.py`通过：角色邮箱容量1的满载拒绝、旧epoch在持久化之前拒绝、超时拒绝、添加幂等/重开保存、观察者分页、私聊冻结目标epoch、频道分区事件、好友初始化；使用受控阻塞事件暂停甲角色存储，乙角色独立所有者在1秒内完成查询。测试使用最多两个临时线程，只用于验收独立推进，不是生产调度实现。

`verify_social.py`保留旧兼容路径的两账号加密收发回归。`verify_social_native.py`覆盖16项原消息序列化布局，供新接线复用。`social-live-verification.json`只证明此前旧运行路径的真实socket检查。

未迁移：共享网络循环、目标连接有界发送队列/epoch目录、频道分区调度、持久化有界执行器、可靠日志/指标，均由集成窗口接线后再验证。未完成“慢写库期间另一地图与战斗仍前进”的完整服务验收，没有压测或商业容量结论。旧进程不加载本文件即不可能得到这些保证。
