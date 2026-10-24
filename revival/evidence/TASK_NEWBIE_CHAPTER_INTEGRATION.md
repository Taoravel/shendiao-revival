# 新角色开场章节：任务事务交接

2026-10-23。实现按主策划NEWBIE_OPENING_DECISION与design/newbie-opening-v1.json；原路由/CG/完成显示依据NEWBIE_ORIGIN_RESEARCH、NEW_CHARACTER_OPENING_RESEARCH及TASK_NEWBIE_COMPLETION_DISPLAY。旧草案TASK_NEWBIE_CHAPTER_INTERFACE已由本文替代。首师父200xx字段采用世界窗口更正后的successor_card_effect_id，激活后继不等于完成其对白、选择卡或装备任务。

## 公开Interface与接线顺序

1. 启动时调用`load_newbie_chapter_rules(resources,routes,catalog,grids)`；routes复用world_newbie.load_newbie_routes，catalog/grids复用世界启动快照。加载已登记政策、校验43路由与全部设计落点的原资源、signed16逻辑边界、mask1可走。`prepare_newbie_chapter_storage(db)`只在启动建表/迁移。配置、地图资源读取均不在收包热路径。
2. **创建路径在插入新角色的同一事务**调用`record_newbie_creation(db,account_id,role_id,creation_id,resources,rules)`。creation_id为可信服务器建角操作的稳定ID，非客户端字段。返回NewbieOrigin，保存独立来源、章节实例、精确原路线、政策与route fingerprint；来源表与既有growth/wallet标记分开。返回origin.spawn，由创建/世界Adapter在同事务一次写入缺失的role_positions。任务Module不写位置，重试不得用设计落点覆盖已保存位置。
3. 首个有效租约事务调用`initialize_newbie_chapter(db,account_id,role_id,epoch,flow,rules)`，flow为**每事务局部**NewbieFlow，不能把RoleOwner持有的可变flow传到I/O线程。复用其initial_task_plans，将root offer/accept与authorized章节共同保存。没有独立来源返回None，已有任务/不同route/不一致章节拒绝；旧角色不能由XP0、等级1、钱包来源或成长档案推导新手身份。
4. `read_newbie_chapter(...)`返回冻结章节，intro_discriminator属性按已批准设计authorized/playing→0、completed→1；None保持旧兼容分支。此值与真实EXP完全独立，全部原root奖励零保持零。
5. 真实世界/场景初始化完成后，在角色租约事务调用`authorize_newbie_playback(...,location,generation=...,request_id=...,now_ms=...)`。复用NewbieFlow.start并持久化播放source ID、actor、epoch/generation、原Location/version、电影与30min授权期限。返回NewbiePlayback；成功commit后才发送其messages：先SAccept root(state0/value1=0/value2=0/npc0；原tracker正常活动态)，再原SStartPlayCG。角色入口需使用同一开场门禁，暂缓移动、NPC写入、成长、道具和换图，连接控制及匹配结束包仍可处理。
6. 原CEndPlayCG只带movie ID。当前角色事务调用`finish_newbie_chapter(...,body,location,inventory,generation=...,now_ms=...,同组reward rules)`，同时核对NewbieFlow内存票据和持久许可；精确root/movie、epoch、generation、Location/version、deadline必须匹配。复用现有type50完成与奖励事务，按NewbieFlow.successor_task_plans仅激活冻结角色专属next，章节completed与稳定completion key同事务提交。
7. RoleOwner只持NewbiePlayback.ticket这一冻结IntroTicket及冻结章节，成功commit后再发布。结束/同请求重试的I/O事务先通过世界公开`NewbieFlow.from_ticket(resources,routes,ticket)`在本地恢复flow，再传入本模块；不得访问私有_ticket或跨线程修改角色对象。返回NewbieCompletion后，commit成功才由RoleOwner清原冻结ticket、发布当前角色/任务快照并投递result.messages。异常只丢事务局部flow，原冻结ticket保留给同命令重试；不在I/O线程调用角色持有flow的committed/cancel。

章节/来源表封装在task_newbie_chapter.py；没有全局锁、电影阻塞等待、跨模块独立commit或网络发送。实际共享AccountStore/GameRuntime/runtime_storage的创建、初始化顺序与动作门禁由原集成窗口接入；本窗口没有修改这些文件。

## 重连、重复与原生限制

未完成章在新epoch/generation通过initialize恢复现存root，再authorize创建新播放许可；保留章节实例和人物位置。相同未过期请求的内部重试从原冻结ticket恢复局部flow，沿原deadline/source ID，不延长期限；不得创建新source假装原请求重试。真正丢失冻结票据则要求新连接重新授权；超时保持未完成，重连或可信显式trusted_resume才重开许可，不从超时生成完成。

已完成章保留原task与位置，不重播。相同movie重复结束在有效租约下只读取当前任务/奖励快照，evidence=None、messages为空，不重复奖励或重置next；错误movie即使章已完成也拒绝。历史回执不覆盖之后的等级/余额。

CEnd没有服务端nonce和自然结束/跳过原因；当前许可下接受匹配声明是designed跳过政策，不是完整观看证明。旧epoch回调会被拒绝，但同连接同movie完全相同迟到正文的歧义仍受原协议限制。客户端CG Setmap/Return不修改服务器权威位置。

原root的state1保留：原代码先删除活动记录，11001–11009/11032不进入>=20000的效果分发，不因state1重播root；不能把这个结论扩展到首师父选择卡。任务effect保留原动画/后继数组，通过chapter_id、原角色next与continuation_resolved_fields标记已执行root，不清原字段，也不让outbox再开一次片。

## 方法与限定检查

codebase-design：复用NewbieFlow路由/纯票据、既有TaskWorkflow资产结算，章Module隐藏来源、许可、CAS阶段与重复确认。research：原43组合和root state1从原数据/原分支核实；不把显示handler当原服交易代码。writing-for-agents：创建/初始化/播放/完成/失败/重连按调用顺序和完成条件共置。

verify_task_newbie_chapter使用同一临时库的受控创建/世界Adapter，验证全部43路线原root、正确CG、唯一专属next与原0XP；创建/来源/设计出生点失败一起回滚；每事务从原冻结ticket恢复局部flow，重试保留source/request/deadline；错误movie/位置版本/generation/过期及旧epoch拒绝；root/next/奖励/章晚期失败全回滚；重复已完成无消息/奖励；新连接可重授权pending；旧角色零经验不补章；位置始终不被CG改写。结果task-newbie-chapter-check.json。原对话/交物/续接、人物及宠物奖励必要检查本批仍通过。

未验收：实际共享创建与RoleOwner自然入口、连续原生加密/压缩初始化顺序、原客户端自然门派进图/开场/Return/走到师父、首师父卡与武器/type59、完整序章和商业存储容量。没有部署、重启、打开客户端或运行战斗。独立43路线事务检查不能替代这些验收。
