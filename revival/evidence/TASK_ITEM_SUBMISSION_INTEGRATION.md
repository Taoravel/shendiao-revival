# 普通交物任务：独立模块交接

2026-10-23。方法沿用research、codebase-design、writing-for-agents。原字段、x86布局与UI判据的单一证据来源为 [TASK_ITEM_SUBMISSION_RESEARCH.md](TASK_ITEM_SUBMISSION_RESEARCH.md)。本批只恢复所属任务模块；没有改Inventory或共享运行入口、配置/在线库，没有部署或操作客户端/战斗。

## 当前范围与来源

原236条MissionType12中，202条满足本模块静态单模板交物条件。原TargetID/Num、NPC/地图、对白、奖励及后继原样保留；34条含零/动态目标、计时、动画、传送等条件，未通过此入口完成。四条特殊221112/221117/232003/812001明确排除。数量是独立领域支持覆盖，不是可玩/实机验收数量。

`supports_item_submission(task)`集中定义能力。精确总量等于原TargetNum、拒绝超额/不足/重复key、未装备、租约和票据期限是本地恢复的designed执行政策。原UI允许选全堆，并未证明原服如何处理超额；这里拒绝超额而不偷偷多扣或截取。请求上限256为本地有界命令策略，原UI通常5格与此上限分别记录。

绑定0/1均可交任务；submitType1在原UI绕过submitType0的绑定拒绝，任务物品也可为不可交易/不可卖店，不调用require_transferable。当前恢复资产模型只有binding0/1等明确字段；原flags0xA0及另两个特殊成员尚未完整映射，本批不宣称恢复全部原实例特殊资格或品质细则。未来增加这些资产状态时，应在资产Interface与任务选择校验中显式传递，不能当成普通binding。

## 集成顺序与完成条件

1. 沿原启动准备TaskResources、InventoryConfig、任务/奖励表；无需新增交物schema。`TaskPlan.objective_debits`只在交物计划非空时加入task_command_receipts指纹和task_effects，原普通任务空字段不改变既有请求指纹。
2. **当前同caller事务读取已由资产窗口提供**：使用`Inventory.immutable_snapshot_transaction(db, epoch=...).items`，把冻结结果交下列`item_states`参数。snapshot/immutable_snapshot仍会另开连接，不用于事务内读取。本批新增`task_item_transactions.py`，将实际公开读取、冻结连接许可、指定扣物、公共奖励、当前背包编码集中在同一角色事务；下节列出调用顺序。实际AccountStore.acquire_lease返回正整数，与资产入口一致；此前因SQLite TEXT列误报的字符串兼容缺口已撤销，详见TASK_MASTER_CARD_INTEGRATION的校正。
3. 角色所有者收到真实NPC交互证明及最新Location后，在当前角色事务加载actor/snapshot与上述item_states，调用`TaskConversation.menu_messages(...,item_states=rows)`。现有单票据同时覆盖普通对话和交物，换NPC、移动、换epoch、超时仍使原票据无效。
4. 服务器明确offer后，交物任务可以通过原CCommit接取，plan_accept检查原NPC/地图和静态能力，SAccept仍state2。没有物品也可接取。库存不足时菜单给state2进行中、不发可消费票据；满足时open_items建立票据并给state3+SVisitNpc任务菜单，保留原本地对白→专用选择UI路径。备用`item_prompt_messages()`是原SSubmit2Npc(0xc233f)、空targetIDs、构造默认opaque0，直接按已接原配置开选择器；它也要求已验证的交物票据。
5. 上行`task_session.decode_task_item_intent(kind,body)`仅接CSubmit2Npc(0xc2340)且submit_type1；其他submitType交其所属玩法，勿混入任务。body携任务ID、真实NPCkey、选中实例key/count列表；模板、角色、绑定、品质均从资产快照取得。严格拒绝空/畸形/超限/尾随数据。
6. 在新鲜租约事务中重新加载actor/snapshot和当前item_states，调用`conversation.plan_item_submission(...,command,current,item_states,now_ms=...)`。它核对原任务、NPC票据/位置版本、所有实例owner、原模板、未装备及数量，输出TaskPlan；普通CCommit或CQuestDialogEnd无法直接完成交物任务。
7. `complete_task_transaction`先固定奖励宠，再apply_task_plan，按`task:role:task:objective_items`将计划原选定key/count交Inventory.apply_settlement(debits=...)，再结算人物/道具/钱币/宠经验、后继与成长刷新。扣物早于奖励物品，因此腾出的格子可用于奖励。完成、指定扣物、宠物接收者、所有奖励与凭据共用外层事务，异常全部回滚。
8. commit后才acknowledge(plan)、刷新角色缓存及发送completion_messages。`TaskCompletion.consumed_items`保留原扣物key/count；集成方还需走库存所属的当前背包刷新，而不是只发任务state1。宠物显示按TASK_PET_EXPERIENCE_INTEGRATION的提交后固定key重读流程。消息全部交目标连接所有者发送。

## 重登与重复请求

`resume_messages`为受支持静态type12恢复state2/value1=0/value2=0 bean。原普通选择器读TargetID和真实bag，不借value1/2伪造计数。此规则排除动态特殊任务，不代表追踪栏数字已全部恢复。

内存原计划重试可直接再走complete_task_transaction，相同任务/库存稳定凭据不再扣物或发奖。跨重连没有旧计划时，先确认已完成，再调用`replay_item_completion_transaction(db,actor,command,resources,inventory,...同组规则)`：原effect必须有完全一致的选中key/count，函数只回放已有完成和奖励凭据、读取当前余额，不寻找替代物、不再次扣物/选宠。不同选中清单拒绝；原凭据缺失的旧completed不能借新物品补造交物记录。返回TaskCompletion.task为None表示已有操作确认。

唯一后继的既有designed续接政策现在允许静态交物目标；多分支、缺失节点、未确认RequestMissionList与其他条件仍pending。原四段对话后续战斗不会被跳过。循环任务实例尚未恢复，仍不得清记录重领奖。

## 已补齐的事务入口

共享路由集成时可直接使用`task_item_transactions.py`，无需在角色/持久化工作线程之间共享可变TaskConversation。

1. 角色已active且当前物品满足要求时，在 caller 事务调用`open_item_task_transaction(db, account_id, role_id, epoch, resources, inventory, task_id, proof, location, generation=..., now_ms=..., deadline_ms=...)`。它实际读取Inventory当前冻结快照，只在事务内建立短生命周期TaskConversation，返回`ItemTaskOpening(permit, messages, prompt_messages)`。提交后角色所有者保存冻结`ItemTaskPermit(ticket, generation)`并发送messages；prompt_messages是原选择UI的备用入口，按此前原生流程择一路径，不双开。
2. 未满足时仍可用既有menu_messages配当前items给state2；open_item_task_transaction本身只创建ready任务许可，库存不足拒绝且不留下许可。offer/accept继续走原有可信激活与NPC接取。
3. CSubmit2Npc解码并确认为submit_type1后，同一角色事务调用`submit_item_task_transaction(db, account_id, role_id, epoch, resources, inventory, command, permit, location, request_id, generation=..., now_ms=..., **reward_rules)`。它再次读取当前真实物品，检查连接generation、原NPC票据/位置/期限和指定清单，完成扣物/任务/奖励/后继，并在提交前编码当前背包与普通完成消息。缺钱包、编码错误或任何后续故障须外层整笔rollback。
4. 成功提交后清除角色许可，再投递`ItemTaskResult.messages`。失败保留原冻结许可以便重试。宠物奖励仍按`refresh_completion_pet`在新fenced事务读取固定原接收者再追加宠物消息；该返回completion的预提交宠物结果没有可发送旧快照。
5. 已完成任务的精确已付清单重试可传permit/location=None；当前租约和实际背包读取仍先验证，只确认持久化同一清单，不新扣、改选或发新宠物。返回replayed=True；不同已付清单拒绝。

新增`verify_task_item_transactions.py`与`task-item-transactions-check.json`通过：原101101/NPC10527/map1006使用真实Inventory公开snapshot/settlement/refresh，冻结许可的generation/期限拒绝，编码晚期失败时任务/绑定50062/400XP/凭据一起回滚，重试一次完成和新租约精确清单确认。仅故障注入覆盖公开equipment_bag_messages；资产读取不再用私有SQL Adapter。测试直接使用实际acquire_lease获取和替换租约，没有人为覆盖其值、修改共享入口或操作现场。

## 必要检查与产物

- 新文件task_item_protocol.py、task_item_submission.py；扩展task_conversation/task_domain/task_persistence/task_workflow/task_session/task_chains。协议与业务规则分开，资产读取/扣除仍封装在资产Interface后。
- research_task_item_submission执行原CSubmit marshal/vector/SubmitUnit得到25字节，与Python codec逐字节一致；不借此推断原服扣物算法。
- verify_task_item_submission.py及task-item-submission-check.json：原101101、真实地图1006/NPC10527证明，CCommit接取；没有50062时进行中，有绑定50062时ready和选择UI；选中实例只扣一次并得原400人物XP。重登bean与已付清单确认、错角色/模板/NPC/submitType/装备/位置版本/重复key/超额等拒绝，奖励晚期故障恢复物品及任务/XP/凭据。
- 原102012的需求为50014×5：受控角色票据配真实临时背包，两堆绑定数量5+1，玩家指定4+1提交后只扣原5，未选中余量1及绑定不变。此项隔离数量/事务，不宣称已经跑过该地图NPC交互。
- 相关原工作流、续接、奖励、宠经验及成长检查按本批实际运行记录保存；未扩大为游戏/战斗或完整回归。

未完成：共享CSubmit路由接线、源代码部署、原客户端选择/提交/追踪栏实测、34条特殊/附加目标、原特殊flags/品质细则、多进程与商业数据库验收。上述接线完成前不能把202条领域覆盖称为202条已经可玩。
