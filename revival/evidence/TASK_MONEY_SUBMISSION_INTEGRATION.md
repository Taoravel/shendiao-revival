# type11 NPC交钱任务接线

2026-10-23。按ARCHITECTURE/DESIGN_AUTHORITY实施，本批使用research原PFS/原生确认链、codebase-design把货币批准与任务事务留在明确Seam、writing-for-agents集中精确接线与未完成条件。用户要求批量恢复和必要检查，本批没有扩大为完整TDD或全面回归。

## 当前交付与启用条件

原5条type11已提供独立codec、纯领域计划、当前NPC交互、同事务支付/奖励/后继和已付确认Module。**当前共享CurrencyRules没有批准`task_money_submission`现金用途，本批没有修改它，也没有修改共享入口。** 正式支付启用数仍0，不能把下面的显式临时规则检查当成生产开放。

主策划/货币所有者须根据原现金证据明确批准专用用途，再由主集成启动时注入`TaskMoneyPaymentRule(revision,currency='cash',purpose='task_money_submission')`及允许该用途的CurrencyRules。Module会检查两者；不扩展输入规则、不借用`npc_shop`扣债、不混合绑银、不初始化未知钱包。政策修改、已有付费凭据的迁移仍归货币所有者，支付policy/revision/原金额保留在任务manifest。

| 原任务 | NPC/地图 | 原ActiveInfoGiveBackMoney | 原绑定奖励 | 原后继 | 本批检查范围 |
|---|---|---:|---|---|---|
| 205707 | 10857李百万/1007 | 500000 | 无 | 205708/type10 | 实际静态NpcScene+临时事务 |
| 230307 | 10381古董商人/1007 | 2000000 | 50397×1/绑定1 | 230308/type12 | 实际静态NpcScene+临时事务，显式唯一资源profile |
| 233307 | 13874西域商客/1011 | 100000 | 无 | 233318/type40 | 纯原任务计划；正式战斗未开放 |
| 233309 | 13874西域商客/1011 | 50000 | 无 | 233310/type10 | 纯原任务计划 |
| 233906 | 10381古董商人/1007 | 1 | 50417×1/绑定1 | 233907/type10 | 实际静态NpcScene+临时事务 |

5条原EXP/钱币/宠EXP奖励均0，保持原0。原Start/Finish、奖励绑定、DisPlayNPCID和后继列表完整保留。13874不存在于地图1011静态placements；两条活动任务的资格、活动实例及NPC生成/可见性另待所属所有者实现，不伪造placement或活动自然流程。

## 原协议与恢复政策

原来源和地址见 [TASK_MONEY_SUBMISSION_RESEARCH.md](TASK_MONEY_SUBMISSION_RESEARCH.md)。其本批PFS解码的五条完整attributes/lists又与当前TaskResources实际载入catalog逐项比对一致，记录见 [task-money-source-check.json](task-money-source-check.json)，未重写catalog。type11经本地对白进入统一提交UI mode3，确认发送`CSubmit2Npc=0xc2340`，不是普通CCommit，也不是type12交物。

body是`BE i32 taskID | u64 npcKey | i32 submitType3 | compact count1 | i32 amount | i32 amount`，共25字节。两项都是UI当前金额的低32位；第一项不是物品实例key。原通用validator只检正数，Module另要求两项相同、金额精确等于原配置、task1001..499999和服务器NPC key正signed63。拒绝部分支付、重复unit和额外unit是明确恢复政策，不能称原服验证已还原。

原mode3的金额输入/当前余额读取wallet+b0/+b4现金槽，未见绑银+c8合并或回退；原指令隔离探针也证明现金0/绑银很大时输入截到0。此证据证明客户端的现金意图，不能代替服务器扣款配方与货币用途批准。

原输入框初值0，玩家自行填写；原确认函数不核对是否等于任务要求。不要让集成说明或UI宣称原客户端自动代填配置金额；任务原文保留所需金额，服务端在收到提交时核对精确要求。

## 精确Interface及顺序

启动：`money=task_money.load_task_money_resources(task_resources)`，只载入冻结原定义/指纹，不做DDL、激活、钱包初始化或用途批准。

上行分流：同一个0xc2340必须先检查通用header的submit_type。type1继续走既有`decode_task_item_intent`/交物入口；type3走`task_session.decode_task_money_intent(kind,body)`或`task_money_protocol.decode_task_money_submission(body)`。其余模式交所属玩法，不根据任务ID猜模式。返回冻结`TaskMoneySubmission(task_id,npc_key,amount)`，不把单位pair传给Inventory扣物。

打开接口：

```python
opening = open_task_money_transaction(
    db, account_id, role_id, epoch, task_resources, money, inventory,
    task_id, npc_proof, current_location,
    generation=generation, now_ms=now_ms, deadline_ms=deadline_ms,
    currency_rules=currency_rules, payment_rule=payment_rule)
```

调用方需已有active任务、真实世界距离/实例/位置版本校验的NpcInteraction与Location、当前Inventory及已知钱包。该函数严格读当前租约/任务，返回冻结permit（ticket、连接世代、任务revision、原定义及支付规则指纹）和原ready3+SVisitNpc逻辑消息。事务提交后角色所有者保存permit并发送；客户端本地对白自然进入mode3，不另发假的付款popup。打开没有付款，最终余额以提交时重读为准。

通用`TaskConversation.menu_messages`不会自行把type11暴露成可付款会话；共享路由在专用现金用途已获准时选择本专用打开接口。原active任务仍能按active0恢复显示，避免仅因源码具备纯计划便绕过货币批准生成可付许可。

提交接口：

```python
result = submit_task_money_transaction(
    db, account_id, role_id, epoch, task_resources, money, inventory,
    command, permit, current_location, request_id,
    generation=generation, now_ms=now_ms,
    currency_rules=currency_rules, payment_rule=payment_rule,
    growth_rules=growth_rules, attribute_rules=attribute_rules,
    pet_experience_rules=pet_experience_rules,
    resource_rules=resource_rules, equipment_rules=equipment_rules)
```

resource/equipment规则沿唯一资源合约成对注入，旧角色不自动迁移。完整顺序在一个角色租约事务内：

1. 校验已批准的支付recipe、当前租约/钱包/任务和原定义；金额必须精确匹配原配置；已迁移profile须当前source正确。
2. 鲜提交验证冻结permit/generation/任务revision/支付指纹、NPC key、地图实例/位置版本和期限；普通CCommit/DialogEnd不能完成该类型。
3. 用纯`TaskConversation.plan_money_submission`生成可信计划。调用公开`apply_currency`扣现金，稳定键`task:{role_id}:{task_id}:objective_money`、专用purpose和含原字段/支付policy的source_ref。
4. 调公共TaskWorkflow完成原奖励/Finish委派及受支持的唯一后继；道具发放后由共同路径同步inventory source，零EXP也不先编码旧裸身。将支付manifest和所有原资料保存在同一task_effect中。
5. 在提交前编码当前背包、绝对钱包、最终属性及任务消息，任何失败回滚现金/物品/成长/资源/任务/各receipt。提交后清permit、发逻辑消息；编码/RC4/MPPC归连接所有者。

已付同manifest确认可以省略旧permit/location，但必须当前租约、金额/原定义/支付policy/原NPC key全部匹配。只读当前钱包并走共同已付确认，不再调用扣款；原state1/Finish不重复发送。未知旧完成记录没有支付manifest即拒绝核对，不默认再扣。新NPC key替换的重连确认不得冒充同manifest，需要独立历史确认路由；这不是一次新的收费。

原205706→205707、230306→230307、233905→233906唯一受支持边可按现有恢复政策进入任务。233306三个活动分支继续pending，不猜成功分支。后继233318正式战斗仍pending；没有跳过它或运行任何战斗。

## 已做必要检查与限制

[task-money-check.json](task-money-check.json)由`verify_task_money.py`生成：5原定义/所有金额/奖励/Finish和后继纯计划；三个唯一前置边；原25字节codec、完整64位NPC key、不等pair/错误模式/空unit拒绝，交物路由不会吞交钱；3条真实静态NpcScene临时事务；金额/NPC/移动/任务revision/generation/期限拒绝；不足现金不使用7000000绑银；晚期背包编码失败全库回滚，重试各扣一次；两件原绑定奖励；230307已迁移唯一资源保持70/40/version0且来源追上实际奖励背包；重登在后来+7现金后确认16余额、不再扣费或重播Finish，旧租约/变更已付NPC及policy拒绝。

测试只在临时不可变CurrencyRules快照中显式增加task_money_submission用途、传入`test-explicit-task-money-recipe.1`，这是受控配方输入，不是修改或批准生产货币政策。原任务offer、已知现金/绑银和NPC位置是可信测试夹具。普通TaskWorkflow、既有交物和5固定Quiz的必要兼容检查通过；未做全面回归。

定向官方检索使用“杨彪/赌债”和“古董商人/玉鸟”。[2012年官方古董玩法](https://sdxl.wanmei.com/info/newplayer/20to29/20120704/132332.shtml)讨论铲子及古董出售，与本五任务支付配方不同；未发现这些任务的原服金额不符/分次支付规则，未用其他古董玩法替代它们。七个本批源码AST解析与交接本地链接检查通过。

未完成：生产现金用途批准及共享type3路由/permit生命周期、活动13874生成/资格/实例、5条自然前置链、客户端GUI/现金实际显示、线上部署、真实角色和正式战斗。所有原生探针仅使用磁盘映像，不操作当前客户端或在线服务。
