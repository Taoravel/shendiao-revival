# 角色成长 P0：2级梦境说书人未开战

2026-10-24，用户要求从当前角色成长顺序修复任务。当前先完成100107→100179→100190，再推进后续原剧情；远端轻功和房间研究不作为本段完成条件。任务资料、独立实现、共享接线、准确发布、真人画面分别报告。

## 现役副本的实际红例

运行 `diagnose_growth_first_battle_runtime.py --source runtime/deployments/npc-repair-20261024T023920Z/source --report evidence/growth-first-battle-runtime-red.json`，默认 exit1，实际复现“2级梦境说书人不触发”。原发布副本7项生产SHA前后不变，路径/哈希及唯一测试前缀适配见该JSON。

临时库自然创建→原intro→师父原CCommit/武器卡/穿装→车夫→嘉兴120XP自然升2级→公共说书人→血印真实3秒提交→私有1501→清格路径接近10908/placement10。原任务100107 active，菜单原0xc232a解码为`[entityKey, [], []]`；未准备task_battle_admissions；原12字节0xc4a4c发出后无返回、未创建battle，100107仍active。成功进入私有地图只是本段前置成功。

这是实际Owner/加密Peer/持久化Interface的反馈，不是GUI，也未启动监听、读真人库、操作真人或制造胜利。原NPC交互已通过，否则实际菜单不会返回对应key的0xc232a。首次两次运行分别修正验证脚本的target含额外字段比较和读取事务BEGIN要求，均为harness错误；最终红例断言才是现场症状。

## main需接的最小顺序

1. startup：使用root正式PVE政策的**精确任务白名单/engine revision**调用 `load_task_battle_resources`，再准备 `prepare_task_battle_storage`。当前默认集合为空。不要从全体相同AI自动放行。
2. 角色当前100107 active0、完整私有1501地址及本人章节/目录合法时，在原VISIT_NPC成功产生proof/current之后、普通TaskConversation菜单之前，调用 `open_task_battle_dialogue`。冻结其ticket到RoleOwner；返回原SVisitNpc第二vector含100107。原菜单分类3由客户端按type40产生；不把Scenario state改成failed2，也无需先假完成或设ready3。
3. 显式路由原 `CActiveScenarioQuestAIBattle=0xc4a4c`，经 `decode_task_battle_request`（精确BE i32任务+u64实体key，12字节）。向当前完整地图Owner重新取得真实NPC/位置证明，核ticket、当前位置/任务revision/租约/连接代和正式能力。它不是CCommit，不包含胜利字段。
4. 在角色调用方事务读取当前真实版本化人物/装备/资源/参战宠/技能，组成Participant，调用 `admit_task_battle_transaction`。同角色只一份未终结admission；角色Owner冻结冲突玩法，提交后由正式engine开启独立battle，不在DB事务内等待回合或网络。
5. 正式BattleFinished经角色Owner合并真实HP/MP/资产和唯一terminal收据，再同事务 `settle_task_battle_transaction(... resource_rules=..., equipment_rules=...)`。可信scope、engine/属性/角色/epoch/原任务定义须与admission匹配。训练/wild结果不具该资格。
6. 第一战胜利后同一事务接 `reconcile_first_skill_successor_transaction`，只激活原100179；原结束对白及10019字段保留。下一次真实说书人交互才开放教学，完成后只激活100190。通用TaskChain不自动完成这三步。10019不是本交单授权的额外SStartPlayCG。
7. 所有当前消息在提交前编码、提交后由连接Owner发送。移动/换NPC/换图/入战/断线撤销未受理票据；同admission重试不重开战。旧epoch terminal拒绝；已付确认读当前资产，不回放旧state1/对白/奖励。main持原shared唯一写入权。

现有 `TaskBattleTicket` 携完整Location，但通用Module只验证原map/NPC与active，不替代root要求的本人章节/已采用私有目录资格。此资格应由角色事务接入消费者核验，不能在本次接线时忽略；原始公共1501同模板不构成合法地址。

## 固定候选和源口径

root已接受离线正式设计 `design/task-pve-ai8001-v1.json`，SHA `2cbbe2cafe3151e49f21a4ec35dab0dd9d4aa9dca82b4b28016dfcb3c13a3c56`；验收在 `reviews/task-pve-ai8001-policy-root-20261024-r1/acceptance-root.json`。main单写新engine/storage/shared；本页任务契约即可据此实现，不再等待敌方数值。此设计接受仍不等于已开启生产或发布。

当前BASE Domain已有battle_won证据路径，当前BASE未导入/prepare/dispatch TaskBattle。优先复用任务接口，不整体复制workspace Domain：workspace还含未共享first-skill/dream-return增量。

需要当前资源参数向下传递及完成凭据纯读时，`task_battle.py`取已审梦醒r4 `evidence/reviews/task-dream-return-settlement-20261024-r4/source/task_battle.py`，SHA `fb978cb5eadfc5cb07c53a074c5b500bd783e79a2d61163caa20977e74269dd6`。原协议文件workspace与BASE相同。该r4交单的独立检查不等于本次准确shared候选已验。

首技能当前namespace纠正取first-skill r3固定source/manifest，原r2禁止据26个UI分组发完整Other map；r3独立审查状态另看 `task-first-skill-delivery.json`。策略参数仍中央newbie-first-skill-v1；完整Other账本未知的旧角色不推空。firstskill增量Domain需按本次闭环精确择取/复审。

同AI8001原记录总数14；其中type40/1501/10908为11。当前43创建路线的首学习前驱精确十个：100107、100205、100305、100405、100505、100605、100705、100805、100905、103207。旧101003和另三条任务不因AI相同开放。原十族皆120人物XP、SMoney400、PetExp0、无物品，后继为本族100179等教学；field10019及原Finish对白保留。root客户端五表报告 `task-pve-ai8001-root-client-sources-20261024.json` 为本次正式设计来源；敌阵/数值采用root明确designed参数，不从客户端AI提示表猜出。

## 连续成长的下一完成条件

先使同一红例自然菜单→原专用请求→真实战斗→真实胜利结算转绿；再将同一自然角色连续推进到100179学习100008、100190下一场真实战斗。单独手工offer、人工BattleFinished、直接激活后继不能替代。随后古墓9/11原链为100161(CG10001)→100110(AI8002)→100111梦醒→100112→100192/193/194→100195→100113驯宠(AI8003)，逐段依此接线；原Task ID不代表硬编码等级，每次奖励用当前成长Module计算实际等级。

方法：diagnosing-bugs用8.7秒可红自然反馈定位实际断点，因直接证实缺失生产路径不再编造距离/延迟假说；codebase-design复用Role/Map/Battle和caller事务Seam，保留唯一状态写者；writing-for-agents将入口顺序、固定来源及各步完成判据共置。当前只交Task范围和红例；正式engine、shared/准确发布、原生GUI与后续成长未完成。
