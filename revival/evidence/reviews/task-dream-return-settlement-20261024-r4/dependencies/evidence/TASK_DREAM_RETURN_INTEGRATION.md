# 两次梦醒结算候选 Interface

2026-10-24。本候选实现正式 [newbie-dream-return.1](../design/newbie-dream-return-v1.json) 的任务侧许可、原子结算、前驱纯读查询和原后继接续。两族隔离任务契约、World 真实纯读提供方与 paid 当前结果现已通过八组检查。第一族使用主策划 decision 明确批准的人工 Participant/BattleFinished 契约输入，不代表 AI8002 实战胜利或生产可达。**共享接线、准确发布与 GUI 仍须另批验收。** 原对白模块仍只输出 `settlement_authorized=False`，默认生产战斗 registry 为空。

原任务、NPC、边与奖励依据 [PROLOGUE_DREAM_RETURN_RESEARCH.md](PROLOGUE_DREAM_RETURN_RESEARCH.md)。20 节点覆盖 43 原创建路线；第一族 125/0 返回 public1006 的 2720,1120，第二族 450/450 返回 5360,2304。×16 采用和时限属于正式设计，不能称原服已验证。第二次入梦、CG10001/10002、前置战斗与原节点间顺序仍分别处理。

## 调用顺序与失败处理

1. 启动时加载 `load_dream_return_rules(resources,chapters,story,placements,catalog,grids,puzzles=...,battles=...)`。严格核中央字段、两个正常可走的精确目标、20 原节点、原前驱及 43 路线。传入批准的 puzzle policy；battle registry 保持默认不启用。启动事务调用 `prepare_dream_return_storage(db)`；前驱及 World 各自准备自有表，不在角色请求中执行 DDL/读文件。
2. 完成原 AI8002 前驱的角色调用方，在**同一结算事务**内调用 `reconcile_dream_return_successor_transaction(db,aid,rid,epoch,resources,rules,previous_task_id)`，再编码和提交。通用 TaskChain 不会自动开放带 Jump 的梦醒节点；专用接续核原章节/路线、可信前驱凭据与本人已采用的 private1501 目录，按原边激活唯一梦醒 active0 并解析原前驱的 chain 字段；不完成前驱、不授奖、不播放旧表现。重复已有 active/completed 返回空。第二族的批准画卷事务已经原子激活梦醒，保持现有路径。恢复既有真实前驱的调用同样不能凭 journal 字段补造完成来源。
3. 当前角色已通过公开创建章节并采用自己的 private1501 目录。角色 Owner 获取真实当前 NPC 证明后，在当前租约事务调用 `open_dream_return_transaction(...,q,proof,current,generation=...,map_generation=...,now_ms=...)`。返回原 ready3 菜单和 300000ms 票据，不在此刻冻结宠物接收者。第一族的 `read_completed_task_battle_proof` 核唯一 won 入场/任务结算凭据及原 AI；第二族的 `read_completed_puzzle_proof` 核批准画卷自身记录、源指纹及 effect。两者均不恢复奖励；仅 journal completed 不能通过。
4. 原客户端 `CCommit(q,真实key,0)` 经原 decoder 后，在 SQL 事务外向原地图取得新证明并 pin 当前代。调用 `inspect_return_commit_transaction` 获得未授权 raw 意图，然后 `resolve_dream_return_transaction(...,raw,command,fresh_proof,current,generation=...,map_generation=...,now_ms=...,movement_state=0)` 得到 `AuthorizedDreamReturn`。观察到移动、其他菜单、换图、战斗、断线或世代替换，调用方撤销未提交票据。过期重新访问，无费用或冷却。
5. 数据库事务外，World 公开 Interface 顺序为 `source.prepare_transfer(current,target_position,request_id=...,deadline_ms=...,now_ms=...)` → `world_transfer_storage.begin(...)` → `target.reserve` → `source.freeze` → `target.activate`。实际 `TransferCommit` 必须保留同一 request、精确源、source+1 frozen 与 source+2 target loading。不得复制 World SQL 或为梦醒创建第二套位置权威。
6. 角色 Owner 开一个写事务，调用 `complete_dream_return_transaction(...,permit,receipt,inventory,generation=...,map_generation=...,now_ms=...,movement_state=0,各现有奖励规则)`。首次路径重核前驱、版本/许可、已采用源，然后同事务提交 World 交接、原任务、125/0 或 450/450、原唯一后继 active0、自有持久凭据。完成时才选择宠物；原零货币/道具不增加，后继奖励不提前发。返回不可变结果与逻辑消息；调用方必须在提交前编码全部最终角色/场景消息。任何异常回滚整个事务。
7. 提交后才发布角色投影、刷新实际宠物并经精确目标连接发送屏障发送场景；屏障不是客户端加载确认。World 精确 finalize 源转移；目录身份保留，投影按已有 pin/交付终止和空闲政策回收。提交前失败通过 World 公开取消/解冻，含糊结果保持 fence 等持久恢复；提交后失败关闭连接，public1006 保持唯一持久权威，下一租约恢复目标、任务和资产，不回私有源、不补奖。

## 已付操作读取

`complete_dream_return_transaction` 的 paid 分支只接受同一持久操作、同一 immutable permit/TransferCommit；它不进入通用任务奖励恢复，也不调用可能取消 prepared 的 World recovery。调用方注入 `read_committed_world=world_transfer_storage.load_committed_transfer_transaction`，其形状是 `(db,aid,rid,current_epoch,expected_receipt) -> (精确历史 TransferCommit, 当前 MapInstanceCheckpoint)`。World 所属实现只 SELECT 校验历史决定和当前完整 checkpoint；之后合法移动、更换实例的当前权威由其返回，不重放旧目标。缺注入继续拒绝，本候选已用实际提供方验证，未用假的成功 reader。

有效 paid 返回 `replayed=True,target=None,completion=None,current_position=...`，只含当前 EXP/成长/固定奖励宠物的当前信息，不含旧 Finish、state1、后继激活或场景。最小冻结宠物决策保存于本 Module，后续切换宠物不会改变奖励接收者。当前入口要求原 permit 的租约/连接 scope；新租约通过现有 World 持久恢复和公开角色加载恢复，不将旧 permit 变成新完成授权。

## 本批方法、证据与未验范围

diagnosing-bugs 沿已冻结运行版本复现的嘉兴断链证据，当前人报入口的恢复交单仍为 [JIAXING_STORYTELLER_PENDING_FIX.md](JIAXING_STORYTELLER_PENDING_FIX.md)；梦醒候选不等于该修复已部署。codebase-design 将原 raw 意图、正式许可、任务事务与 World 提供方分开，数据库连接/提交和地图等待保留调用方所有权。research 的两份只读接缝审计分别为 [前驱](DREAM_RETURN_PREDECESSOR_SEAM_AUDIT.md) 和 [World paid](DREAM_RETURN_WORLD_REPLAY_SEAM_AUDIT.md)。writing-for-agents 将使用次序、失败与恢复跟 Interface 共置。

`verify_task_prologue_return.py` 八组实际通过，报告为 [task-prologue-return-verification.json](task-prologue-return-verification.json)。第二族真实批准画卷结算后接梦醒；两族各自独立缺 active、缺完成前驱、缺专用凭据均拒绝，第二族另核 NPC/位置版本/任务版本/代际/期限和他人目录。第一族通过真实 task admit/settle 接收明确人工终局契约，任务包装已成对透传资源/装备规则，使用显式唯一资源 profile 完成前驱和125/0，再由专用接续激活梦醒。原 AI8002 的目标为陆立鼎10084，梦醒的黄药师10085是另一 NPC；测试分别显式接近原摆放位置，没有把两者合并。

调用方最终原生编码失败会回滚完整世界/任务/奖励；第一族前驱结算与梦醒接续的最终编码失败也全表回滚。第二族450/450在完成时选宠，第一族125/0保持完整宠物/背包不变，二者只激活各自原唯一后继。第二角色不同私有目录保持原位置和任务。第一族故意给 source.finalize 过期版本的回执，使真实 World Interface 在持久提交后拒绝；新租约按公开恢复决定清退旧源/目标成员，重入精确 public1006 目标，原目录身份仍在，成长和资产不重奖。此为实际跨 Owner 清理拒绝，未模拟共享网络发送失败。

paid 成功使用真实 World 提供方；SQLite authorizer 仅允许 SELECT/READ/FUNCTION，实际函数调用仍经过 FencedConnection，底层 SQLite handle 仅供检查器安装仪器。后来人物+7经验、原奖励宠+7经验、切换参战宠，以及已知 carrier 显式资源迁移/减量均为独立标注的状态 fixture；paid 精确返回当前 EXP/HP/MP、原接收宠当前包。目标 MapOwner 带原 maze、normal state0 的后来移动已真实执行，paid 返回当前位置，未回旧目标、不重发任务/场景、不改任何表。新租约保留当前位置及完整资产，并可纯读原 epoch 的 World 回执；旧 permit 不能成为新租约授权。

此前已回归画卷七组、血手印九组；本批对修改过参数的 task_battle 另回归既有契约检查。所有有效晚期故事的入册/历史师父 journal/程英前置与接近位置均是明确隔离 fixture；NPC Scene 使用明确32px fixture，未声称当前v2原生距离。报告将 first_family_task_contract_verified=true、first_family_actual_ai_victory_verified=false、first_family_production_reachable=false 分开。没有执行任何实际战斗、在线数据库或客户端；共享网络发送失败、共享接线、准确发布与 GUI 尚未验，实际 AI8002 仍不可据契约样例称已完成。严格准入继续以中央 decision 和统一集成验收为准。
