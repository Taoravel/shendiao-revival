# 任务战斗：专用请求、持久绑定与结果事务

本批完成任务窗口所属的协议与事务Interface，**默认开放正式任务战斗数为0**。没有实现或替代战斗窗口的敌阵/AI/属性，也没有修改共享入口、在线状态或启动客户端/战斗。部署临时冻结期间停止代码/政策写入，只交付本文与已有离线证据。

原始证据统一见 [TASK_BATTLE_ADMISSION_RESEARCH.md](TASK_BATTLE_ADMISSION_RESEARCH.md) 与task-battle-admission-static.json。362条type40引用244个任务AI；客户端提示AI表直接关联0，无法据此生成原敌阵。研究中的301条零额外字段族、当前模块326条可绑定元数据候选都不是可玩覆盖数。

## 启动与开放条件

新增`task_battle_protocol.py`、`task_battle.py`。启动时准备既有任务/奖励/资产schema后调用`prepare_task_battle_storage(db)`；调用`load_task_battle_resources(resources, enabled_task_ids=frozenset(...), engine_revision=...)`，只读快照注入角色所有者。

默认空enabled集合不允许开任何任务战斗。显式启用必须来自战斗窗口实际实现并由主策划批准的任务ID集合和正式敌阵规则版本，包含对应原AI、组队/捕捉/特殊胜负条件；按任务ID开放，不能仅因多个任务同AI就全部放行。测试的offline_binding_fixture_v1只验证消息/事务契约，不能作为正式战斗政策。

本模块排除无AI、未知结果模式、非NPC触发、进度条、计时、用物/交物/交钱/交宠、其他特殊目标/转生条件。原AIInfoBattleResult=1沿用既有恢复的可信胜利判定；0保持未确认，不称作“失败也完成”。动画、完成对白及RewardMapJumpType等后置原值可保留为pending，不表示已执行。326只是此绑定筛选口径；研究301口径连后置字段也要求零，两者分别保存。

## NPC菜单和专用开战请求

1. 当前角色已经被可信任务链明确激活，且正确正常active bean由主集成同步后，地图核实真实实体/实例/位置版本/距离，调用`open_task_battle_dialogue(db, account_id, role_id, epoch, resources, registry, task_id, proof, location, generation=..., now_ms=..., deadline_ms=...)`。
2. 它核验当前角色租约、任务active/原等级与形象资格、正式能力开关及实际NPC，返回冻结TaskBattleTicket和SVisitNpc任务菜单。**不生成active完整bean、不修改共享显示状态**。原type40的菜单类3与tracker状态是不同概念；主集成核准active0/failed2/ready3/remove1见TASK_TRACKER_FAILURE_RESEARCH，不能因菜单返回3授权失败/过期任务。
3. 原本地对白结束发送`CActiveScenarioQuestAIBattle=0xc4a4c`，body精确12字节BE i32任务ID + BE u64 NPC实体key。`decode_task_battle_request(body)`严格长度与原任务范围1001..499999，返回TaskBattleRequest；AI、敌人、option、result均不在包内。主集成需单独路由该type，当前TaskSession/共享运行时尚未接入。普通CCommit可能接取任务，不能代替本专用开战请求。
4. 正式原生解码器允许任意u64 key，本业务仍要求与真实当前实体匹配。对白阅读不是协议可证明的事实；服务器授权来源为有效任务、NPC证明和当前冻结票据。

## 同事务admission

`admit_task_battle_transaction(... ticket, request, location, participant, battle_id, generation=..., now_ms=...)` 在调用方角色事务冻结原AI、任务全定义指纹、角色/租约/连接代、位置/任务版本、正式战斗规则版本和完整Participant副本，写入task_battle_admissions。

Participant是角色所有者提供的真实当前版本化战斗快照，必须有有效HP/MP上限、实际属性及明确版本；不接受训练宠物/缺失stats。模块核对身份/等级/形象/版本格式，**不代替角色所有者核对最新装备/宠物/技能权限和全部资源版本**。集成必须先读取并冻结真实loadout，再在本角色邮箱禁止冲突操作，提交后才创建正式battle owner。

同一角色只允许一个admitted任务战斗；同battle ID/内容重试返回replayed收据，不再创建战斗；不同内容重用ID拒绝。初次NPC授权期限在入场时验证，已持久化的相同admission重试可以过期后确认；不能把旧对白期限当整场战斗超时。新租约不复用旧票据创建战斗。

## 结果、共同资产事务与取消

只接正式battle所有者发出的冻结BattleFinished，当前约定为内部`scope=task_quest_v1`、`task_event_eligible=True`、`settlement_id=task-battle:<battle_id>`。这是新服务端消息契约，未声称原wire字段。规则版本、参与属性版本、角色/epoch、战斗ID及原定义指纹都必须匹配持久admission。战斗窗口尚无此正式producer；**不能给TrainingBattle/WildBattle结果改scope/资格冒充它**。

角色所有者在同一外层事务先合并正式战斗资源/捕捉资产/outbox收据，再调用`settle_task_battle_transaction(... finished, inventory, **reward_rules)`。它只负责任务与公共奖励，不写战斗HP/MP、捕捉宠物或额外战斗掉落。本契约不接未登记的额外currency_reward/item_rewards；原任务自己的奖励继续走统一结算。

- 胜利：绑定的可信battle_won证据完成原任务，原奖励/支持的唯一后继与terminal receipt同事务；原完成对白、动画及传送字段继续保留，不被battle结果静默抹掉。未支持后继仍pending，不跳过。
- defeat/draw/escape：仅终态收据，原任务保持active，不发任务奖励。其余HP/MP/死亡规则由战斗/角色模块处理。
- 重复同结果：比对完整terminal指纹，返回当前余额；不重复state1，以免原完成对白/电影/特效再次播放。冲突结果拒绝。
- 新租约恢复：旧epoch的finished拒绝；可信`acknowledge_task_battle_transaction(... battle_id, inventory, **reward_rules)`只确认已存在terminal收据并读当前状态，不创造新胜利或重新选择奖励宠物。
- 取消：宿主先真实终止该battle，再提供BattleAborted给`cancel_task_battle_transaction(...)`。可由当前新租约退休匹配的旧epoch战斗；仅对白超时或客户端取消等待不构成取消证据。结果已终结不能被取消覆盖。

所有函数加入caller事务，不连接、提交、发送或加全局锁。异常必须整笔rollback；提交后角色所有者才投递TaskBattleSettlement.messages。宠物奖励仍按原固定接收者的提交后读取Interface追加刷新。战斗宿主负责持久outbox、可靠终态传递和回收，任务收据不证明消息已在客户端显示。

## 本批方法、验证与缺口

research后台重读原PFS/原sender/原codec，发现专用开战包并排除假AI关联；codebase-design把原协议、战斗身份绑定和统一资产事务放在现有Seam，不把敌人生成散到任务/共享路由；writing-for-agents将启动、菜单、admission、结果/重连分支集中成可判定的交接步骤。

`verify_task_battle_binding.py`与task-battle-binding-check.json已通过：原12字节固定样本/非法长度；默认关闭；原100107/真实NPC10908证明和显式Participant契约夹具；重复/冲突admission；错NPC/位置/版本/结果来源拒绝；失败/逃跑/平局/取消不结算；原120XP+SMoney400+原后续字段+receipt一起rollback/提交；新租约确认返回后来的125XP且不重放state1。使用真实临时库任务/钱包/资产结算，但终态为内部消息夹具，没有模拟战斗，更未证明原AI8001敌阵可用。

未完成：正式task-PVE敌阵/数值/AI/捕捉/组队政策、真实当前loadout与资源同事务整合、正式BattleFinished producer/outbox、共享原0xc4a4c路由、主动开战消息时序、自然主线战斗与GUI/部署。本批没有扩大TaskChain自动开放战斗；默认0和上述缺口由原窗口继续集成。
