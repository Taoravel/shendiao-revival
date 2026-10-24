# type50：NPC提交后播放完成对白

2026-10-23。原证据见 [TASK_SCENARIO_OBJECTIVES_RESEARCH.md](TASK_SCENARIO_OBJECTIVES_RESEARCH.md)，全234条原表/电影资源审计见 [task-scenario-catalog.json](task-scenario-catalog.json)。本批在既有领域、会话、事务和续接Module中新增 **122条无额外机制的NPC完成对白任务支持**，未新建共享入口、连接或影子任务账本，未操作在线服/当前客户端。独立模块实现与共享自然流程验收分开。

## 支持集合与来源

原type50共234，不是234个电影。12条有Animation，其中10个是已恢复intro，另外102622/206103分别引用原10026/10020；其余222条按字段分为开始对白18、完成对白142、Note20、空表现42。原表metadata无额外机制的200条也不是200条可自动完成。

完成对白142条先排除动画/传送/变身/分支等额外机制，剩130；再排除无目标NPC的6条与999999占位NPC的2条，支持122。`supports_npc_finish_dialogue(task)`还要求目标地图>0、无开始对白/Note/分支文案及选项、有非空且speaker完整的完成对白，额外计时/战斗/交物/物品使用/转生/步数等均拒绝。它不扩大 `supports_plain_dialogue`，也不将type50整体加入普通type10规则。

真实NPC实体、地图、距离、位置版本与角色租约依旧由地图/角色所有者提供。122是独立领域能力数，不代表122条NPC已在运行服刷出；26条含RequestMissionList，AND/OR/活动触发仍由可信offer提供者确认。没有把目录中存在的任务自动登记成可接，也没有给旧角色补任务或资源。

## 原生流程与现有 Interface

原客户端ready3→NPC菜单class3→空NpcConversation/空BranchNote→默认CCommit，正文仍为taskID、实际NPCkey、option0。完成对白不是点击之前要读的前置对白，而是在服务器结算后state1 handler播放的后置表现。`CQuestDialogEnd`不是首次完成依据，并非所有Finish结束都会发送它；不要求一条不存在的通用结束确认。

本批复用现有Interface，无新codec/启动DDL：

1. 启动注入既有不可变TaskResources。可信规则先offer/accept（或既有唯一原边续接），既有 `TaskConversation.resume_messages` 恢复active0；不靠failed2制造ready。
2. 当前真实NpcInteraction+Location下，`TaskConversation.menu_messages/open` 校验目标、任务active和领域能力，产生既有冻结TaskConversationTicket，返回 `SRefreshScenarioQuestState(ready3)` + `SVisitNpc`。该族 `TaskDialogue.lines` 为空是原行为；客户端点菜单会直接CCommit，不需要服务器补一段空对白或伪造NPC。
3. `plan_accept`仍只接受原server offer；`plan_finish`只接受匹配当前ticket、NPCkey和option0的CCommit，拒绝CQuestDialogEnd、过期票据和移动/位置版本变化。可信证据kind为 `npc_finish_dialogue_completed`，TaskDomain再次检查支持族和目标NPC/map，保留原奖励、后继及完成对白列表。
4. 调用方角色事务使用既有 `complete_task_transaction`，任务/公共人物与宠物经验/货币/物品/后继/凭据一起成功或回滚。TaskPlan追加 `completion_finish_dialogue=False` 缺省字段，本族为True；仅True才加入命令指纹，既有族False不改变旧事务指纹。任务效果保留原FinishConversation/FinishNpcID，并另记native_finish_dialogue handler=original_state1/status=delegated_to_original_client/gui_confirmed=False，相关字段标为原客户端处理；显示NPC等其他原后置项仍可pending。
5. 共享Adapter沿已有同事务最终装备投影路径替换裸身成长map，并在提交前完成所有消息编码。成功提交后才清ticket、由连接所有者发送首个state1及当前余额/后继；原客户端读取自己的Finish配置显示。状态投递只证明服务器已提交，不证明GUI已经显示或人类读完对白。

现有 `TaskChain` 已加入该能力，仍限制唯一原边、原角色/等级、未完成、非自环和无未知RequestMissionList。不跳过不支持后继。NPC为0、999999、自动入口、电影/换图/Note/空表现都保留独立机制。后续两个非循环真实NPC开始对白已单独恢复，见 [TASK_SCENARIO_START_INTEGRATION.md](TASK_SCENARIO_START_INTEGRATION.md)，没有扩大本Finish谓词或为200元数据候选创建统一“scenario_finished”捷径。

## 重试与后置副作用

原state1即使找不到active bean也会重新播放Finish；本批已执行原有bean/无bean两条指令分支确认。因此TaskCompletion追加缺省False的 `suppress_replayed_state`，本族由能力判定置True，`completion_messages`在replayed时省去state1，返回当前余额且不重置已有后继。60001特效已有同类保护，其他族默认行为保持原样。

相同计划/命令指纹重试复用公共回执；重连的可信历史确认仍用既有 `replay_completed_task_transaction`，不能拿客户端taskID直接补发奖励。旧租约依旧拒绝。既有数据没有新表迁移；原字段及未确认奖励绑定不被篡改，未支持的奖励渠道继续留pending。

本批没有新增完成对白的通用UI-end ack函数。对于当前122条普通族，首次完成只认CCommit；不会等待CEndPlayCG，也不会用可选/后置CQuestDialogEnd重新完成任务。具体有动画/传送/大任务号的UI清理分支属于其他族，其协议行为见研究报告，不扩到本族。

## 必要验证与未验证范围

`verify_task_scenario_finish.py`通过，结果见 [task-scenario-finish-check.json](task-scenario-finish-check.json)：

- 122条原定义的纯完成计划保持原奖励/后继/Finish列表；普通type10证据拒绝，NPC0/999999/电影/分支/传送排除；原唯一边到200104可按既有策略激活。
- 临时库原任务200104和真实NpcScene NPC10530：active0恢复→ready3→空start→匹配CCommit；错误NPC、位置版本、期限、CQuestDialogEnd拒绝。原11000人物经验和2275绑定银同事务，4句原Finish仅标原客户端处理；宠物经验沿既有固定接收者政策，不因本批补造宠物。
- 晚期背包编码失败回滚任务、余额、效果和回执；同请求重试提交一次。已付重试不再下发state1、不重奖。新租约在后续+7XP后确认当前11007，旧租约拒绝。
- 既有 `verify_task_workflow.py`、`verify_task_native_effect_dialogue.py`、十路线 `verify_task_cart_transfer.py`必要兼容检查通过，未运行全面回归。主策划自然车夫baseline和shared文件未修改。

research用一手PFS/原指令区分任务类型、菜单提交与后置表现；codebase-design复用现有NPC/领域/事务Seam，避免再造会话或奖励账本；writing-for-agents共置普通NPC提交与自动剧情的适用范围、重试和接口条件。产物为领域/会话/续接/持久化/消息变更、原表审计、原生报告及本交接。

未验证：122条自然接取来源和NPC实际可见/生成、未知前置/活动资格、共享连接端到端、每条真实GUI/对白资源呈现、原服全部任务规则。NPC位置在必要事务检查中是可信测试夹具，不是自然导航；没有部署或运行战斗。电影10020/10026、无NPC自动对白与Note/空节点仍未恢复完成。
