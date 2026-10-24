# AI8001正式开战：当前接口与最小缺口

2026-10-24。适用于100107“序章缘起”及AI8001入战接线。准确输入、文件SHA及固定快照见同目录`ai8001-battle-contract-ready.json`。本交付为**契约ready、正式开战not ready**；不启用任务，不提供人工胜利，不更改共享入口或真人。长期目标保持暂停。

## 当前结论

所核BASE为`runtime/deployments/npc-repair-20261024T023920Z/source`，启动记录PID7456；本窗口未查询进程、端口或真人数据。BASE的战斗所有者可执行单角色训练/单敌野外战斗，但没有AI8001正式战斗生产者。最新Task事务契约在工作区候选中，不能把它当作此BASE已接线。

启动元数据分类实际返回326可绑定候选、36排除、enabled集合为空、engine_revision为空。100107指纹为`20782cecdae8a87cff41cdb85b9cec27e4c04978b85c28d947fb8a71c2b5b2a9`，原关联为AI8001、1501、10908说书人。326是元数据筛选数量，不是可玩覆盖数。

原任务AI8001族有11条，其中101003不属于当前43新角色路线授权，不能因共享AIID一起开放。本文不授权任何一条。

## 已支持与拒绝范围

| 项目 | 可复用的现成能力 | AI8001现状/拒绝范围 |
|---|---|---|
| 原怪物 | 原CMonsterConfig 5635条仅提供名字/模型等显示；野外目录46地图、64个不同模板，39暗雷图与7可见图分别处理 | 未找到AI8001到任一monster模板/数量/位置的原对应；正式敌方列表为空，不把野外怪物拼成任务敌阵 |
| AI | 普通确定性攻防与速度顺序；现Training/Wild的敌人使用普攻 | 原CBattleAIConfig 2194条是提示/表现表且不含8001，没有AI8001技能、回合脚本、召唤、捕捉、特殊胜负生产者 |
| 阵型 | 现Single-enemy Adapter投射人物1、宠物可选位置、敌人21；战斗开场双方阵型ID/等级为0 | 无正式AI8001阵型/队列规则；原team字段1不能直接解释成必须组队，也不能由单人文字推完全部团队规则 |
| 人物 | Participant可承载真实HP/maxHP/MP/maxMP、物攻/物防/速度及角色/租约/连接代/属性版本 | 训练缺省100/100不是正式属性。未知旧profile、死亡、上限/装备投影不一致拒绝；本窗口未核实真人profile |
| 资源 | 已知无伤势唯一RoleResources；ordinary battle_terminal保留完整caps/source，只消耗HP/MP | 不隐式迁移/治疗/复活；未知伤势、特殊阶段及会增加最终资源的战斗恢复规则不由普通消费planner覆盖 |
| 技能/宠物 | 现基础操作1普攻/4防御/9逃跑；2仅显式授权的实现技能。OwnedBattlePet来自真实保存成长 | wild participant builder默认空技能不是完整已学证明；role_skills完整账本为独立候选、BASE未含该文件。训练宠物被Task admission明确拒绝；不能把所有原宠物技能或已学ID视为可施放 |
| 任务胜利 | Task模块已有身份绑定、胜负校验、奖励与回执的caller事务 | 没有真实task_quest_v1 BattleFinished生产者，训练/野外改scope或人工终局fixture不构成正式胜利 |

完整64个野外模板ID在ready JSON，仅表示既有野外目录支持范围；其中太湖小花猫21102/6062和小灰狗21101/6013的表现/普通战斗不能证明AI8001对应这些模板。

## 当前可用Interface

1. **角色输入。** `Participant(role_id, login_epoch, connection_generation, attribute_version, name, shape, level, stats=Fighter(...), authorized_skills=tuple, pet=OwnedBattlePet|None)`。正式任务要求stats在位置1/side0，当前活HP与有效上限；Task契约会拒绝TrainingPet。角色所有者仍须在同一租约事务确认完整资源投影/装备/库存/技能/宠物来源，单个attribute_version不代替全部来源CAS。
2. **战斗所有者。** `BattleOwner(participant, rules, mailbox_capacity=..., receipt_capacity=..., playback_timeout_ms=..., now_ms=..., engine_factory=...)`；随后`initial()`、`submit(BattleCommand, now_ms)`/`process_one(now_ms)`、`advance(now_ms)`、`close(reason,now_ms)`、`terminal()`。每个battle_id独立唯一调度，不传Session/DB/writer。BattleCommand带battle/role/epoch/generation、request_id、sequence、state_version、round_number、deadline_ms及kind/body。
3. **Engine factory。** 现Seam为`factory(participant, rules, clock)->engine`。engine须提供`id`、`battle`（round/phase/fighters/pending）、`last_rejection`、`opening()`、`receive(kind,body)`、`tick()`、`finished()`、`close()`。可选`abort_finished(reason)`会被BattleOwner转为finished；否则close产生BattleAborted。这里没有现成TaskBattleEngine；默认仍为TrainingBattle。构造函数还会先创建一次TrainingBattle再替换factory，正式技能超出训练registry时会提前拒绝，正式接入应让factory分支直接创建对应engine。
4. **原生输入/播放。** `CSendAction=0xc1b5c`精确14字节，按操作/目标/操作ID/isRole/isAuto；`CSendRoundPlayEnd=0xc1b5e`是compact+i32列表。输出经目标连接所有者发送。领域结算后phase=playback，只有受认可播放完成才推进/结束；超时是宿主策略。现规则30秒/200回合为历史参考与训练值，正式AI政策另批准。
5. **任务对白。** 启动`load_task_battle_resources(resources, enabled_task_ids=frozenset(...), engine_revision=...)`，准备schema一次。当前能力集为空时`open_task_battle_dialogue(...)`会拒绝，不会给可开战菜单；开启必须来自已实现并获准的逐task能力。授权票据含完整Location/任务版本/NPC实体key/连接代/期限/定义指纹，私有1501须与本人章节采用目录同址。
6. **任务专用请求。** `C_ACTIVE_SCENARIO_QUEST_AI_BATTLE=0xc4a4c`；`decode_task_battle_request(body)`只返回TaskBattleRequest(task_id,npc_key)，精确12字节BE i32+u64。客户端不提供AI、敌阵或胜负。普通CCommit、NPC点击、播放结束均不是入战/胜利凭证。
7. **持久admit。** `admit_task_battle_transaction(db, account_id, role_id, epoch, resources, registry, ticket, request, location, participant, battle_id, generation=..., now_ms=...)`加入调用方事务，固定AI/原定义指纹/规则版本/真实Participant/全地址；同角色仅一笔admitted。同ID重试返回既有绑定，不重开；错身份/版本/过期拒绝。
8. **正式terminal与Task settle。** 真实Owner的BattleFinished必须`scope='task_quest_v1'`、`task_event_eligible=True`、`settlement_id='task-battle:'+battle_id`；revision等于入场engine_revision，snapshot_version等于入场属性版本。won/winner_side/outcome须一致，只有真实victory完成任务。额外currency_reward=0、item_rewards=()，原任务奖励另走Task共同事务。

`settle_task_battle_transaction(... finished, inventory, growth_rules=..., attribute_rules=..., currency_rules=..., pet_experience_rules=..., resource_rules=..., equipment_rules=...)`不写战斗HP/MP或捕捉资产。宿主同一外层事务先校验精确入场资源来源并应用战斗结果，再调用Task settle、写公共terminal/outbox。结果相同重试读当前状态、不重播state1；冲突拒绝。败/平/逃保持任务active，不发奖励。

最新`task_battle.py`须取Task梦醒r4/首技能r2交付要求的`fb978cb5eadfc5cb07c53a074c5b500bd783e79a2d61163caa20977e74269dd6`版本，包含成对resource/equipment规则透传；BASE旧版不能当最新契约。新租约只能`acknowledge_task_battle_transaction`确认已有terminal；实际停止Owner后才可`cancel_task_battle_transaction(... BattleAborted)`，对话/请求超时不是取消证据。

## 交给主集成的最小Seam与顺序

当前缺口分为四项，均完成前保持enabled为空：

1. **正式recipe与engine（战斗所属/主策批准）。** 显式给100107原AI8001一个受版本约束的敌方模板/数量/站位/属性来源/操作策略/胜负/逃跑/死亡处罚/捕捉与团队规则；未知字段按DESIGN_AUTHORITY标为designed并逐task批准。实现上述engine Interface和真实terminal生产者。完成条件为真实command→resolve→playback ack能产生绑定终态，人工BattleFinished不计通过。
2. **准入快照与标识（角色/任务/地图接线）。** 提供公开caller事务读当前combat loadout+完整资源来源Seam，不直接跨模块调用wild私有_snapshot。先验证同一角色已采用的私有1501全地址、NPC证明和任务active。Owner必须与admission使用同一个battle_id；可先构造未注册/未opening的正式Owner以保留ID，admit提交成功后才注册/initial。提交失败丢弃未启动Owner；replayed admission找已有Owner或进入持久恢复，不再开一场。
3. **Task combat持久副本与结算（角色持久化Adapter）。** 增加Task身份的checkpoint/terminal outbox和全来源CAS，投递前持久化副本；断线按批准策略保存真实损耗/取消或恢复，绝不补胜利。可以复用通用资源planner/连接投递逻辑，但不能直接调用wild_runtime_storage.admit/settle：它们会登记野外奖励、掉落和wild scope。完成条件为资源+Task奖励+terminal凭据原子提交，晚期失败全回滚，重连不重复发奖。
4. **共享分派（main统一）。** ScheduledBattle目前只区分Training/Wild，finish_battle按wild_ticket分支，须加入显式Task kind/engine/ticket与结算路由；接0xc4a4c及票据失效、冻结冲突玩法、播放/取消/回收。完成条件为已批准100107完整Owner/持久化/连接链，且其他Task仍拒绝。Task现有人工终局事务检查只验证接口，不能用作该完成条件。

Mailbox/receipt上限由宿主明确配置并覆盖合法整场。既有512份收据覆盖200回合单人物400条输入/ACK，却不足人物+宠物最坏600条；正式政策必须核准回合数/控制人数与容量，不照抄默认。

## 本批记录与验证边界

方法：codebase-design定位真正已有factory与角色事务Seam，避免将AI生成或存储散进Task/连接；writing-for-agents把可调用接口、开放门槛及完成条件共同放置。产物为本文、固定源快照和ready JSON。验证为只读BASE/工作区差异、原catalog字段与ID统计，以及当前startup loader实际分类（无数据库、无admit/settle、无人工terminal、无真实战斗）。既有六组Task绑定结果明确enemy_ai_tested=false，仍保持该边界。

本批没有执行新的战斗/GUI测试，没有验证真人属性、正式AI胜利或生产可达，也未实施上述四项缺失Module。ready的activation_ready=false不是可发布开关，不代表AI8001已经实现。
