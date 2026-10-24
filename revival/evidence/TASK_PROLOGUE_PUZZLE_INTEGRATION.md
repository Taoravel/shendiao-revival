# 序章画卷：独立任务 Module 交接

2026-10-23。`task_prologue_puzzle.py` 已实现独立菜单、声明准入、奖励/后继同事务和重连投影。**现已加载中央正式`2026-10-23.newbie-puzzle.1`政策并通过隔离检查；没有共享入口或部署。** 主策划裁定见[NEWBIE_PUZZLE_DECISION.md](NEWBIE_PUZZLE_DECISION.md)，不因政策或模块存在而推定运行服已启用。先前未批准fixture反馈单独保留。

## 原证与范围

开始接入前读 [PROLOGUE_PUZZLE_RESEARCH.md](PROLOGUE_PUZZLE_RESEARCH.md) 和 `ARCHITECTURE.md`。原43路线沿真实Post边汇入十任务：100120、100219、100319、100419、100519、100619、100719、100819、100919、103220。原目标是type59/NPC0/map1501，列表11106；不能借普通对话、装备或参战宠路径完成。

原NPC11106是1501的静态placement16，坐标5870,1541。原SVisit服务553打开专用画卷UI；原固定2x2经过本地交换，最后只发`CCommit(taskID,0,0)`。**没有棋盘/步骤证据上传。** 此Module的准入叫`authorized_client_assertion`，回执明确`server_verified_board=false`，不宣称服务器验证了解题。

保留原奖励：人物EXP十条均360；100719宠EXP350，其他九条360；货币和道具奖励原零。前驱是各路线程英对话，后继是各路线黄药师梦醒传送，均取原边，不按ID规律算。后继只active0，原传送仍独立恢复。

## Interface 与调用顺序

1. 启动普通连接调用`prepare_puzzle_storage(db)`；世界目录表由世界启动Interface准备。本Module不在玩法事务建表、读配置或开连接。
2. 启动调用`policy=load_puzzle_policy()`读取唯一中央`design/newbie-puzzle-v1.json`，严格核revision、十ID、source/553、minimum0、timeout300000、声明模式及`server_verified_board=false`等；冻结完整政策的规范JSON fingerprint。再调用`load_puzzle_resources(resources,chapter_rules,story_rules,placements,policy=policy)`核十条原域、43路线、实际NPC摆放、原前后继与奖励差异。热路径不读文件或代写中央政策。`PuzzlePolicy`仍供显式隔离fixture注入；历史`isolated-unapproved-puzzle-fixture`1000ms不再作为默认检查/生产规则，原反馈保留`task-prologue-puzzle-fixture-check.json`。
3. 原程英前驱完成后，在同一当前租约事务调用`reconcile_puzzle_successor_transaction(db,aid,rid,epoch,resources,puzzles,predecessor_id)`。它核真实已完成创建章节、人物形象/门派、原唯一前驱及持久effect，只激活本路线画卷一次。通用`task_chains.py`保持未接线门槛；没有显式政策时仍pending。
4. 地图Owner确认当前11106/placement16交互后，角色事务调用`open_puzzle_menu_transaction(db,...,task_id,proof,current,generation=...,map_generation=...,now_ms=...)`。map_generation来自实际MapOwner公开快照的owner_generation或已验证ProjectionHandle.map_generation，不是客户端字段；跨Owner调用按世界公开pin契约保持此代有效。函数重读原创建身份对应的真实世界目录及已采用完整地址，要求当前唯一100000..199999主线正是画卷（原本地getter会取该范围第一项，含糊状态不能开错任务）。返回`PuzzleMenu(ticket,messages)`：Accept0恢复bean，再SVisit(saved_key,[553],[])。它不发奖、不完成任务，也不把发菜单等同客户端实际开始。
5. 角色Owner只持有当前有效ticket；已接受移动/位置版本变化、其他菜单、可观察取消、战斗、换图、断线/新世代或任务变更应清除它。本地关闭而无上行不可直接观察。新登录不恢复旧ticket，active画卷重新访问NPC取新许可；过期可重新访问，无罚款或冷却。最短等待0，只表示不另加解题时间门槛；300000ms是菜单许可有效期，二者均为正式designed规则。
6. 收到原`CCommit`时只能路由到匹配的当前画卷ticket。用**服务器保存**的ticket.entity_key向正确完整地址的地图Owner重新核NPC；在SQL事务外等待取得新`NpcInteraction`，随后调用`complete_puzzle_transaction(db,...,ticket,command,inventory,proof=fresh_proof,location=current,generation=...,map_generation=...,now_ms=...,**reward_rules)`。原包的zero key不用于找实体；真实proof必须11106/placement16、相同实例/位置版本/key，fresh提交的地图generation须匹配原ticket。早于菜单打开、过期、移动、错角色/章节/世代、任务revision改变、错误key/option/End均拒绝。
7. 函数在同一个角色租约事务内保存专用任务证据、固定原奖励接收宠、公共人物/宠物经验及共同奖励凭据、原唯一后继active0、专用声明receipt。人物/资产仍用公开Interface，不复制Inventory或世界SQL。新资源profile必须成对传resource/equipment规则；本批未单独验迁移profile，不能由当前唯一资源检查反推已完成所有迁移接线。
8. 调用方在同事务内完成最终角色/Finish等编码，成功commit后才发布结果、投递并消费ticket。晚期编码失败整笔回滚。正常世界移动检查点按世界原Interface处理，本Module不成为第二份坐标权威。
9. 精确已付ticket重试确认本角色原receipt与任务证据，再用公共奖励恢复读取当前余额/固定宠物结果；不重奖、不重放state1/Finish、不重置后继。此确认可传`proof=None,location=None,map_generation=None`，不需要重新加载旧地图；它不能成为fresh完成授权，仍须当前连接世代和角色租约。该公共恢复可能更新既有effect，**不宣称全表只读**。新世代/新租约不能使用旧ticket。
10. 重登按可信角色事务调用`resume_puzzle_messages(db,...,resources,puzzles,already_projected=...)`，只恢复当前路线已有active画卷或原黄药师后继bean0；可去重通用投影。它不重新开菜单、发许可、发奖、播放旧Finish或换图。未知/冲突阶段明确拒绝。

所有事务调用均经`accounts.leased(aid,rid,epoch)`；在持久化Adapter的有界执行资源内运行，不持有SQL事务等待地图或网络。目录通过`load_story_instance_transaction(...,expected_address=...)`确认原chapter/creation/route/source身份；不分配新实例，不改用公开1501。

## 本批实际决定与检查

codebase-design：把原路线、zero-key请求、菜单许可、当前NPC证明和幂等奖励藏在独立Module；输入为冻结票据/证明，输出为逻辑消息，连接、世界与提交仍由原Owner负责。TaskDomain只新增精确十条`supports_prologue_puzzle`和`prologue_puzzle_claim_accepted`可信事件；普通对话不能创建该事件。TaskConversation仅恢复已有画卷bean0。

research：使用上一批原PFS/native证据及主策划[PROLOGUE_INTERACTION_POLICY_RESEARCH.md](PROLOGUE_INTERACTION_POLICY_RESEARCH.md)，保留原特殊350宠EXP、专用菜单553以及无棋盘上行的限制。没有将通用40级杂学时限或测试1000ms复制成本族规则。正式0/300000是中央设计。writing-for-agents：把必需参数、顺序、错误和未接线门槛集中在本页。

`verify_task_prologue_puzzle.py`默认正式政策通过：严格loader拒绝错误数字/布尔/ID/553/解题验证标记；真实临时账户、自然创建/intro授权结束、真实目录与已采用私有地址、实际MapOwner generation/静态NpcScene交互、原native close包→专用准入；立即受理0、期限前1ms成功、到期拒绝、过期重开、未完成时换租约/重访发新ticket；错key/option/连接或地图generation/位置拒绝。结果返回后在调用方最终编码Seam、commit前注入受控异常，全库一致（模拟晚期编码失败，未执行共享最终角色编码器）；两个实际角色/原宠500138通过人物360与宠360/350两个公共奖励路径；已付不重奖/Finish、完成后新租约只恢复原后继0并拒绝旧ticket。

测试仅创建/intro是自然流程。首师父历史journal为已完成、后续剧情入册、程英已完成对话、NPC接近及临时私有地图加入/移交均为明确fixture；为保持公共创建章节重载契约，原选定师父journal保留，未删除它。没有发卡/穿装纵切或自然完成/伪造任何前置战斗胜利。历史1000ms结果单独保留；需要时`--fixture`另行运行，但不覆盖正式报告。

检查程序最初误用了FencedConnection.total_changes和不存在的role_growth.experience列；已改为公开SQL计数及read_growth/当前资产快照。这两项是检查适配错误，不作为游戏故障或红绿修复事实。最终脚本通过。新增纯任务能力后必要复跑`verify_task_prologue_touch.py`也通过；没有扩大整套战斗/卡片回归。

固定交付见`task-prologue-puzzle-delivery.json`，七组执行与前后SHA一致性见`task-prologue-puzzle-frozen-verification.json`。独立Standards与Spec复核见[双轴报告](task-prologue-puzzle-review.md)：规范硬性0、低优先级重复建议1；需求缺陷0。审查后保持四份候选源码字节不变。

未完成：当前共享路由/菜单许可保存与取消及全部projection pin接线；最初真人点击到CVisit前链；真实GPU拼图/Finish/重登；前置完整战斗链；原后继梦醒传送；迁移资源profile专项纵切；部署。任务系统和序章总目标仍未完成。
