# type50：开始对白后提交的两个非循环NPC节点

2026-10-23。客户端证据见 [TASK_SCENARIO_START_RESEARCH.md](TASK_SCENARIO_START_RESEARCH.md)，原234条完整审计见 [task-scenario-catalog.json](task-scenario-catalog.json)。本批增加201201、230401的独立任务能力，沿用现有NPC会话、角色事务、奖励与续接Module；与此前122条完成对白合计124条静态NPC type50能力。数量表示独立模块支持，不表示自然任务来源、共享入口、部署或GUI已全部验收。

后续另增三个真实NPC空表现交接，当前静态NPC总数127及剩余97条触发缺口见 [TASK_SCENARIO_TRIGGER_INTEGRATION.md](TASK_SCENARIO_TRIGGER_INTEGRATION.md)；本页保留两个Start族自身范围。

## 支持条件和授权来源

`supports_npc_start_dialogue(task)`要求type50、真实ActiveNpc>0且非999999、目标地图>0、开始对白非空且speaker完整、完成对白为空，没有动画/传送/分支/交物/计时/变身/其他附加机制、Note或`$round$`轮次占位。

18条start-only中，无额外机制8条：101001无NPC，230701为999999，四个323x01是轮次活动；本次仅支持201201与230401。四个轮次的客户端发包虽已确认，任务实例尚未建立，仍不以角色+任务ID的一次性凭据结算。NPC0自动开始入口与十条入城传送分别待恢复，不拿对白speaker填补交互实体。

201201“毒草危机”原前置102099，230401“周伯通的新计划”为劳动节活动。调用方须先提供可信offer/活动授权，再调用现有accept；能力判断不登记offer、不解释未知前置AND/OR、不启用节日日程。230401目标NPC13286未在当前静态placement中找到，本批只验证其纯计划，实际活动生成由世界/活动所有者处理。

## 现有Interface与提交顺序

1. 启动载入不可变TaskResources；角色所有者读取当前任务快照，可信策略登记offer。完成条件为当前真实角色满足既有等级/形象条件且任务可接，客户端taskID本身不构成授权。
2. 使用世界所有者的真实NpcInteraction和当前Location，调用 `TaskConversation.plan_accept`；现有 `acceptance_messages/resume_messages`同步active0。已有active任务可直接进入后续open。
3. `menu_messages/open`校验当前NPC、地图、位置版本和期限并保存原有单个ticket，`opening_messages`仍发送ready3+SVisitNpc。`TaskDialogue.lines`保留原开始对白；原客户端按本地配置显示，无新正文协议。
4. 原客户端读尽Start后走type50默认CCommit(taskID、真实NPCkey、option0)。`plan_finish`仅接受当前ticket下的匹配CCommit，产生独立 `npc_start_dialogue_completed`证据，TaskDomain再次检查支持条件与目标。CQuestDialogEnd/CEndPlayCG不是本族首次完成依据。
5. 调用方在同一角色事务执行既有 `complete_task_transaction`及必要最终属性/背包/场景编码；任务、原奖励、已支持唯一后继和幂等凭据一并提交。成功后才acknowledge清ticket、发布缓存并由连接所有者发送state1/当前余额/后继。共享最终装备投影契约沿用既有普通任务流程，由集成方所属文件处理。

本批没有新TaskPlan字段、DDL或codec。`completion_finish_dialogue`仅用于此前Finish族；Start族不将开始对白伪记为后置Finish。原state1不读取NpcConversation，重复不会重播Start，仍沿现有普通完成消息行为；已有60001/122条Finish的重复状态抑制保持。客户端请求只说明请求提交，无法证明人类完整读过文字。

`TaskChain`已认识这两个静态能力，仍保留唯一原边、原角色/等级和未知前置约束。原201201后继201202为type40战斗，当前正式任务敌阵未开放，因此完成后原边保留pending；不跳过它、不创建训练替代战斗。230401后继230402仍按既有普通对白能力处理，活动资格须在首次offer时由可信规则限定。

## 必要验证、方法与未验证范围

[task-scenario-start-check.json](task-scenario-start-check.json)来自 `verify_task_scenario_start.py`：

- 两个原定义纯计划保持原奖励和后继；无NPC/999999/传送/轮次节点排除，普通type10及Finish族证据不能完成Start族。
- 原201201/NPC10903、大胜关1002的真实NpcScene加临时角色事务：未offer先拒绝；显式可信offer夹具后可接，active0恢复→ready3/原两句Start→匹配CCommit；错误key/位置版本/期限及CQuestDialogEnd拒绝。
- 当前节点原奖励明确0XP、0银，未拿可接摘要中的整线20000XP/10000银覆盖。201202战斗边正确保留pending。最初检查误期望自动激活战斗后继，按原type40与既有支持范围改正了检查预期，生产代码未因此放宽。
- 晚期背包回复失败回滚任务/效果/后继；相同请求重试不重复奖励，重登仍保留已完成和pending边，旧租约拒绝。
- 因公共能力抽取和会话分支变化，必要兼容 `verify_task_scenario_finish.py`（122条）与 `verify_task_workflow.py`再次通过；没有全量回归或重复root自然链验收。

research通过后台直接原PFS、指令分支和最少离线探针确认Start→CCommit、phase2不要求DialogEnd及state1不重播Start；codebase-design将Start/Finish公共条件收于同一私有实现，两种能力继续使用既有会话/领域/事务Seam；writing-for-agents将offer资格、交互、事务和发送完成条件共置在本交接。产物为领域/会话/续接变更、原生研究、必要检查和本说明。

未验证：201201自然前置获得、230401真实活动资格/NPC生成、四个周期实例、共享连接端到端、GUI对白显示/真实点击/活动重置、NPC0自动入口、在线服务器与真人角色。检查中的角色等级、offer和NPC位置均为明确测试夹具，没有部署、操作当前客户端或执行战斗。
