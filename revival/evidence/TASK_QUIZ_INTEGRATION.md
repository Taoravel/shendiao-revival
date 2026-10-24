# 固定NPC答题：独立原生答案与任务事务

2026-10-23。原PFS和原指令证据见 [TASK_QUIZ_NATIVE_RESEARCH.md](TASK_QUIZ_NATIVE_RESEARCH.md)，12条原定义及派生范围见 [task-quiz-catalog.json](task-quiz-catalog.json)。本批提供5个非循环固定题的独立模块能力，7条动态/轮次题保留未实现；未接共享入口或部署，不能把5条能力当作原活动已开放。

## 原生事实与恢复政策

原type17进入phase4问题UI，使用独立 `CAnswerQuestion0xc4a48`，body为BE i32 taskID、u64 NPCkey、i32 answer-code。原taskID范围1001..499999，答案0..5；本地服务器NPC key另按当前世界支持的非负signed63域限制。正确显示项恒为code0，WrongAnswerList原第j项为code j+1；随机只改变显示顺序，不能用屏幕行号判正误。原230407的正确文本确实是字符串“2”，本批保留，不将其改成第二个错误选项。

五条固定题为229103/229110/229112/230407/232503，QuestionInfoNpcID与实际目标NPC一致，原奖励均0；原问题、正确/错误项、Start/Finish和后继全部保留。前三条多后继没有明确结果映射，当前只保留原边pending，不猜哪条是答对/答错分支。七条轮次没有这些静态问题字段，不能因原UI回退普通CCommit便当作已答题完成。

合法错误代码保留任务active、不发奖，调用方成功处理后清许可，下次重新访问真实NPC可重开，是本批明确的本地恢复政策，非已证原服活动失败算法。原客户端对两种答案都关闭phase4，没有在本地完成任务；`SSendAnswerResult0xc4a9e`属于另一独立小游戏UI，不在本模块用作错答反馈。当前不补造错误文字、失败任务或额外结果包。线包的稳定答案代码不能证明人类独立知晓答案，权限仍来自当前已接任务和真实NPC许可。

## 启动、菜单与答案Interface

1. 启动调用 `load_task_quiz_resources(resources)`得到只读5条TaskQuizDefinition及7条exclusions。原问题/稳定code→文本映射只作来源和审计；客户端继续从自己的配置显示，没有新增正文下行或服务器随机排列。请求路径不读文件/DDL。
2. 可信任务/活动规则先offer/accept；现有TaskConversation支持该固定题的active0恢复、目标NPC菜单和ready3。普通CCommit可作为现有授权offer的接取，**不能作为答题完成**。原CQuestDialogEnd也不能替代答案。
3. 当前真实NpcInteraction、Location、资产与任务同一角色事务下，调用：

```python
opening = open_task_quiz_transaction(
    db, account_id, role_id, epoch, resources, quiz, inventory,
    task_id, npc_proof, location, generation=generation,
    now_ms=now_ms, deadline_ms=deadline_ms)
```

返回冻结TaskQuizPermit（现有TaskConversationTicket、generation、任务revision、原定义指纹）和原ready3+SVisitNpc消息。提交后才发布许可和菜单。TaskConversation保持一个当前NPC ticket；共享角色所有者要与普通/交物/车夫等许可互斥管理。
4. 连接所有者收到0xc4a48，经 `decode_task_quiz_answer`解码为TaskQuizAnswer，再把当前连接generation和内部稳定request_id送入角色所有者；库存/租约使用真实公开Inventory.immutable_snapshot_transaction。调用：

```python
result = answer_task_quiz_transaction(
    db, account_id, role_id, epoch, resources, quiz, inventory,
    answer, permit, current_location, request_id,
    generation=generation, now_ms=now_ms,
    growth_rules=..., attribute_rules=..., currency_rules=...,
    pet_experience_rules=...)
```

首次答案核当前许可的角色/租约、generation、任务revision、原定义、NPCkey、位置/实例/version和deadline。答案须落本题实际错误项数量内，不能只凭全局0..5接受不存在的选项。code0发出 `npc_quiz_correct_answer`证据，TaskDomain再次检查固定题/目标/原代码；其余合法代码返回incorrect，没有完成计划和状态写入。
5. 正确答案沿现有 `complete_task_transaction`原子写任务、公共原奖励、可支持的唯一后继及回执；4条有原Finish，复用completion_finish_dialogue将原state1交给客户端显示，并标记相应后置字段。事务内另写quiz_answer原定义/NPCkey/code0清单，所有消息仍须在提交前编码。成功后清许可并投递首个state1/当前余额/新后继；失败整体回滚并保留可重试许可。

共享入口尚需注册0xc4a48、保存/清除冻结quiz许可、调用上述事务和既有最终装备/资源投影；应与TaskChain/菜单能力一起接入后再开放相应自然任务来源。本窗口未改game_runtime/runtime_storage/gateway等共享所属文件。正在进行的人物唯一资源迁移，仍按主策划指定Interface另行接线，不以答题模块绕过migrated围栏。

## 重试、后继与必要检查

正确任务已完成后，仅当原quiz_answer清单与当前定义、原NPCkey和code0完全匹配，才允许当前有效租约读公共已付回执；可省去旧permit/location，不重发state1/Finish、不重置后继、不重奖。返回当前经验/钱包/背包，旧租约始终拒绝。普通历史完成但没有quiz清单的记录不自动补造来源。

原230407→230408（交物任务）已在临时事务按唯一原边激活；229103/229110/229112的两条原边保持branch_selection_unconfirmed。232503后继232599原定义缺失，沿现有missing successor pending，不补造剧情。活动资格、实例和分支规则另由可信触发方提供。

[task-quiz-check.json](task-quiz-check.json)来自 `verify_task_quiz.py`：5条原固定题纯计划/原奖励/Finish/后继保留，7条排除；原NPC10215和230407临时库菜单/稳定code0与“2”文本、错误代码无写入、普通CCommit/DialogEnd拒绝、错误NPC/移动版本/generation/期限拒绝；晚期背包编码失败回滚，正确重试只结算一次并激活230408；新租约在后续+7XP后确认当前余额且不重播Finish，旧租约拒绝。因公共会话ticket/完成标记变化，既有普通workflow与122条Finish必要兼容再次通过，没有全面回归或重复root自然链。

research用后台原PFS/原parser/本地显示与发包探针确定稳定代码和独立协议，排除另一小游戏结果包；codebase-design将答案codec、启动定义及角色事务放在明确Seam，复用现有会话和公共奖励，未新造题目/资产账本；writing-for-agents共置错答政策、原分支缺口、提交顺序和完成判据。产物：答题两模块、领域/会话/续接增量、原表审计、必要检查及本说明。

未验证：原活动自然资格、原错答反馈/多后继映射、动态题/周期实例、每条NPC实际可见性、共享连接端到端、GUI/原随机显示、人类答题或在线状态。NPC点位/offer/钱包为明确测试夹具，未操作在线服、当前客户端、真实角色或正式战斗。
