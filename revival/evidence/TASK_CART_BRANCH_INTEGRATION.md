# 新手车夫分支后续接线与裁定输入

2026-10-23。原分支、可信菜单和冻结意图已恢复；主策划随后发布坐标政策，新增同调用方事务的世界目标/车夫完成/原奖励/唯一后继组合入口，十条独立流程通过。**当前实现与接线读 [TASK_CART_TRANSFER_INTEGRATION.md](TASK_CART_TRANSFER_INTEGRATION.md)**；本文保留原分支与坐标证据，以下历史裁定输入不再表示政策/世界事务Interface仍缺失。未修改共享运行时、地图实现或在线现场；共享接线仍由主集成安排。

## 已确认事实

原始依据及原指令fixture集中见 [TASK_CART_BRANCH_RESEARCH.md](TASK_CART_BRANCH_RESEARCH.md)。十条车夫任务均type10、两句本地对白、BranchNote非空、一个原选项、RewardMapJumpType1。state3完整bean/SVisitNpc原菜单能驱动本地对白→phase5分支；第一项CCommit末字段为0。它与普通接取/提交共用包型和0值，服务器必须持有已授权阶段，无法证明玩家逐字播放完对白。取消10003不发包；不需要猜额外分支下行，也不要求CQuestDialogEnd作为选项前置。

少林103204的原ActiveNpc/对白Npc13290与BranchNpc10260不一致；原UI菜单门槛实际是BranchNote长度，所查函数不读取BranchNpc。服务端交互应如何使用字段由统一政策明确，保持原表不改。建议继续以ActiveNpc的真实地图实体/距离证明授权，不能由BranchNpc名字推断UI跳NPC。

## 已实现的可信菜单与请求Interface

`task_cart_dialogue.py`只管理角色一侧的资格/对白授权与原字段冻结，不开连接、不提交、不发包、不完成任务/发奖或修改位置。

1. 启动调用`load_cart_resources(resources, master_rules)`，从实际43路线汇成10个原车夫节点，验证两句对白、BranchNote非空、一个原选项、JumpType1、原唯一60001后继，完整保留BranchNpcID错配和RewardMap原值，返回冻结CartResources。
2. 在当前角色caller事务、真实车夫NpcInteraction和最新Location下，调用`open_cart_dialogue_transaction(db, account_id, role_id, epoch, resources, cart_resources, proof, location, generation=..., now_ms=..., deadline_ms=...)`。它经新公开`read_master_choice`核验独立章节、实际已选武器凭据、master/type59均completed且该角色原车夫active；以ActiveNpc真实实体/距离证明建立冻结CartDialogueTicket，返回完整原state3 bean→SVisitNpc。此角色侧授权策略是本地恢复，未改少林原表。
3. 提交后角色所有者保存单个冻结ticket。客户端本地两句对白和菜单后，解码出的TaskIntent交`authorize_cart_transfer_transaction(...ticket, intent, location, generation=..., now_ms=...)`。它再次核对当前章节/任务revision/租约/连接generation/位置/期限，严格只接受CCommit同任务、原实体key、option0；CQuestDialogEnd、1-based值1和保留10003均拒绝。
4. 返回冻结`CartTransferIntent`，包含稳定request_id、源Location、task revision、角色章节、原NPC、option0、唯一后继与RawCartDestination。后者显式标`coordinate_space=original_reward_fields_unresolved`，不提供逻辑像素position，不能直接交MapOwner.prepare_transfer。相同ticket重试返回相同request_id/内容，供后续世界journal使用；本模块未替代世界durable prepared/committed receipt，也没有落一个会让任务提前完成的请求状态。
5. deadline由集成方既有NPC政策显式传入，本模块没有新增超时数字。任何任务revision变化、移动、换连接或期限失效都需新验证。以下统一目标换算和世界同事务接线就绪之前，集成方应保留该分支为未启用；不能发送成功/完成状态或让角色只在客户端换图。

必要验证已附入verify_task_master_card.py：实际完整前置事务后，十个真实原车夫实体分别建立菜单，仅匹配option0产生稳定冻结原目标；错误选项/NPC/generation/位置版本拒绝，任务、奖励、服务器持久位置不变。复用既有受控前置，仅增加十个不同节点的此段检查，不表示实际走路到车夫或自然传送已验证。

## 目标坐标候选

`research_task_cart_targets.py`直接重读原PFS条目并核验CRC，再调用世界所属maps/maze_grids/maze_clear；结果在 [task-cart-target-candidates.json](task-cart-target-candidates.json)。地图1006有效范围6144×4736逻辑像素，十条原目标只有两组：

| 原X/Y | 原数字作逻辑像素 | 候选×16逻辑像素 | mask1 | mask8 |
|---|---|---|---|---|
| 36/221 | 边界内，但两mask均阻挡 | 576/3536 | 可走 | 阻挡 |
| 71/242 | 边界内，但两mask均阻挡 | 1136/3872 | 可走 | 阻挡 |

这支持“原字段按cell×16”的推定候选，但不能证明原服换算。正常角色状态0对应mask1来自世界原指令研究；非0状态对应mask8，故即使统一采用×16，也要明确当前角色状态及到达校验，不能套世界统一mask。任务模块不自行搜索附近点、换地图或把blocked改成可走。

## 前批提交的裁定输入（现由新政策和事务Interface落实）

1. 集中裁定RewardMapX/Y是否采用cell×16，标为inferred/designed；正常state0到达条件、遇到不支持状态或候选blocked的拒绝/恢复政策一并明确。本批不创建已生效设计参数。
2. 明确选择后任务与传送的提交时点。建议有效NPC分支选择先冻结一次角色/任务/epoch/generation/位置版本/原选项与目标的传送意图；目标预留、源冻结后，在同一角色事务保存世界持久目标/交接决定、车夫完成/公共奖励和唯一后继。提交前失败任务仍active；提交后发送失败以已提交目标为唯一位置，重连恢复，不重新发奖。此为接线建议，尚非已裁定原服时序。
3. 前批world_transfer_storage.commit自开连接的缺口已由世界公开commit_transfer_transaction补齐；任务组合入口直接加入同caller事务，不复制世界SQL或先后两次提交，见新交接。
4. 实际地图交接沿用MapOwner.prepare_transfer及预留→冻结→目标决定→清源→精确发送屏障；普通换图没有已验证客户端通用ready，不套CAfterEnterWorld/CEndPlayCG。旧NPC/旧批次输入失效遵守scene-transition-v1。
5. 十条车夫后继100105/100204/100304/100404/100504/100604/100704/100804/100904/103205均type10，位于嘉兴NPC10212或10492、AnimationID60001。其原章节标题特效现已核验并增加专用能力，见 [TASK_NATIVE_EFFECT_DIALOGUE_INTEGRATION.md](TASK_NATIVE_EFFECT_DIALOGUE_INTEGRATION.md)；车夫成功交接后可激活原唯一后继，再由真实嘉兴NPC对话处理，不能提前跳过或扩大普通对白判定。

前批codebase-design用于区分分支选择、任务事务与世界持久化Seam；research后台直接追原字段与发送指令；writing-for-agents把候选证据、裁定输入和接线步骤集中。原0-based选项fixture、原PFS/地图目标比较、十个可信车夫菜单/冻结请求已通过；随后独立同事务交接/完成的证据见新交接。共享运行时、GUI、现场部署和真实传送仍未由本窗口验证。


## 2026-10-23 来源查找附注：车夫到嘉兴的坐标单位

本轮沿用research/codebase-design，只补来源核对；已读TASK_CART_BRANCH_RESEARCH的N4及task-cart-target-candidates.json，没有重复大范围反汇编或运行原生fixture。

定向检索限同款端游官方sdxl.wanmei.com，组合“车夫/门派车夫/序章缘起/嘉兴/坐标”、原两组数字36与221、71与242及带逗号形式，另查“坐标/像素”“坐标/16/地图”。取得[官方剧情任务（路径日期2012-07-28）](https://sdxl.wanmei.com/info/renwu/script/20120728/133491.shtml)：序章介绍支持玩家由本门师父取得武器、再经门派车夫前往嘉兴的流程，**没有提供这两组落点、RewardMapX/Y单位或cell×16换算**。坐标精确组合与单位查询未取得相关官方结果；“序章缘起”2012-06-26页和“第一次做任务”2012-06-28页本轮直接访问失败，未伪称重新取得全文。未引入手游、神雕侠侣2或后期活动传送规则。

原字段仍为client_verified：map1006及(36,221)/(71,242)。已有原生N4仅证明parser按整数保存、提交包不带坐标；本轮没有新增RewardMapX/Y实际传送消费者证据。候选×16分别为(576,3536)/(1136,3872)，与现有mask1可走结果共同支持**inferred**的cell单位解释；选择该转换作为恢复规则应另标**designed**，不能因官方证实“去嘉兴”便把换算或精确原服落点升级为guide_supported/client_verified。mask8阻挡结论保留，不能外推所有角色状态。

codebase-design的实际决定是保留RawCartDestination原数值及unresolved坐标契约，把统一换算放在主策划裁定后的世界目标Adapter；任务Interface不自行改字段、搜索邻近点或绕过传送交接。本附注仅记录检索与来源强度，不更改政策/运行时或启用车夫分支。验证范围：阅读现有原包/静态消费者与候选结果、定向官方资料核对；未新增地图探针、GUI、战斗、在线服、数据库或共享源码操作。精确原服单位与落点仍未确认。
