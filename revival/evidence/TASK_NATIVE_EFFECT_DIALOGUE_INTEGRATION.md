# 嘉兴60001本地标题特效任务接线

适用于原100105/100204/100304/100404/100504/100604/100704/100804/100904/103205。原资源和指令证据统一见 [TASK_JIAXING_SCENARIO_RESEARCH.md](TASK_JIAXING_SCENARIO_RESEARCH.md)：60001是CQuestEffect章节标题，不是CG或武器卡；合法普通CCommit之后的原state1会请求本地显示，重复state1也会重新请求。GUI、资源加载成功和原服时序未证明。

共享自然链已由主策划独立验证转绿，见 [newbie-jiaxing-runtime-verification.json](newbie-jiaxing-runtime-verification.json)：完整intro/师父卡/实际武器装备/车夫/barrier之后，以原clear报告到真实嘉兴NPC，合法CCommit才完成标题任务；120XP自然到L2/XP31/free5，穿装总值49/38/8，重试/重连不再奖励/重播且原入场包保持同源值。本窗口只读核对报告，按要求未重复跑root verifier。该结果来自临时库真实所有者/连接流程，无GUI、线上库、部署或实际战斗；不等于十个门派的全部自然路径均已验收。

## 当前实现与调用

`supports_plain_dialogue`保持原收窄判定。新增`supports_native_effect_dialogue(task)`只覆盖上述10个原ID、type10、嘉兴真实Npc10212/10492、AnimationID60001、三句开始对白、无Finish/Note/Branch/其他玩法字段。其他带动画任务仍不可借此完成，43条200xx师父卡不在此能力内。

沿既有可信激活/唯一后继进入active后，普通`TaskConversation`即可使用该能力：地图核验实体、同图/实例、位置版本/距离后，open/menu_messages建立同角色票据并发ready3+SVisitNpc；原客户端显示三句配置对白，合法CCommit(taskID, entityKey, opaque0)计划完成。新可信事件kind为`npc_native_effect_dialogue_completed`、reference60001。CQuestDialogEnd拒绝为该任务的完成意图，不发送SStartPlayCG或等待CEndPlayCG。

`complete_task_transaction`按原字段结算120XP、公共渠道、唯一后继及凭据，同caller角色事务。原ScenarioInfoAnimationID继续保留在task_effects.continuation_fields；新计划的completion_effect_id=60001进入请求指纹，仅该新能力增加字段，其他原任务空字段指纹不变。effect记录：

- continuation_resolved_fields含ScenarioInfoAnimationID，表示服务端无需再另开动画/等确认；
- native_completion_effect={id:60001,handler:original_state1,status:delegated_to_original_client,gui_confirmed:false}，表示提交后的state1委托原显示，不是GUI成功回执。

现有TaskCompletion末尾新增native_completion_effect_id/replayed默认字段；其他调用方可继续使用原字段。`completion_messages`首次完成仍给原state1、当前绝对XP及后继bean，原客户端负责60001。相同计划重复受理、可信`replay_completed_task_transaction`均设置replayed，**该能力重试不再发state1**，仍回当前余额/允许渠道，不重播旧标题。重连按当前active任务恢复，也不补播已完成标题。

避免重复state1是本地恢复的投递政策，与原生“重复会重播”的事实分开。本模块没有记录连接发送确认或建立视觉outbox；首次提交后投递失败不回滚资产、不保证标题最终出现，交连接所有者按既有故障/重连规则处理。若主策划后续要求持久化可靠视觉交付，须扩展有明确receipt的投递契约，不能重放资产凭据时无条件发state1。

`TaskChain`现在能续接唯一且符合上述能力的后继。车夫任务本身仍需单独的选项/地图交接，不能因为60001后继可处理就提前跳过车夫。

## 方法、产物与验证

research背景代理直接重读原config/effect PFS并执行少量原指令fixture，区分标题资源、普通CCommit、完成对白结束与CG。codebase-design把能力谓词/可信事件集中在TaskDomain，用既有对话和统一结算流程隐藏原生效果差异；同一completion_messages seam同时处理首次与重试投递。writing-for-agents将当前实现、元数据含义及投递限制集中于此，原事实只指向研究报告。

产物：task_domain/task_conversation/task_persistence/task_chains/task_workflow；verify_task_native_effect_dialogue.py及evidence/task-native-effect-dialogue-check.json；后台research_task_jiaxing_scenario.py和原证据报告。必要临时库验证通过：十个原任务的实际NPC proof/三句对白/CCommit、120XP与原唯一后继、晚期故障整笔回滚、同计划和新租约确认时不再次发state1。旧普通任务工作流与四段对白续接检查也通过，未扩大为全面回归。

该测试直接可信offer隔离十个原目标，不表示自然intro→师父→车夫→嘉兴全链已验收。共享入口仍由主集成接入；没有修改在线服、当前客户端或共享文件。真GUI、连续原生连接和源代码部署未验证。
