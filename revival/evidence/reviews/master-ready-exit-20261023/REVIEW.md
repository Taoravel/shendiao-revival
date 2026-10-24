# 师父/车夫ready与普通退出初始化候选审查

固定基准为npc-20261023T102110Z，候选master-ready-exit-20261023T110056Z；非Git，无提交列表。5文件128行生产增量，root独立逐1423项manifest核对，并确认旧基准只有这5项明定差异（新exit政策另增），377项额外冻结evidence与基准原字节相同。汇总再次核对候选全部manifest与受审5文件SHA256一致。

# Standards

0项发现。仅审scope固定5文件，对npc-20261023T102110Z基准与候选快照比较；非Git，无提交列表，不评继承wild。

沿用code-review／codebase-design，按AGENTS、ARCHITECTURE、DESIGN_AUTHORITY及冻结两份裁定检查。task_master_card.py:212–214、task_cart_dialogue.py:158–160在可信NPC／任务检查后依次Accept→Refresh ready3→Visit，仅改变逻辑消息，不提前完成或发资产。role_protocol.py:24–33启动核policy/type/精确整数-1，返回冻结包；game_runtime.py:362–363每次合法入场ACK把c0039置于spawn与intro前，:1013只在Runtime创建时加载，无热配置读取。原退出保存／租约清理路由未改。

12项Fowler smell逐项作heuristic判断，未见有实际后果的问题；未增世界锁、第二份状态或额外转发层。

只读静态核对冻结diff／上下文，未运行DB、GUI、服务、战斗或退出验证。manifest实核由根完成，本轴未复跑；候选部署及真实确认窗／师父对白不由本报告证明。

# Spec

0项可确证缺陷、遗漏或越权。

沿用code-review独立Spec轴、codebase-design的逻辑消息/连接所有权Seam，审scope.json固定5文件；基准为真实npc不可变发布，非Git，无提交列表，不评继承wild/care。

SPEC_SOURCE.md:15要求“再发送同任务SRefreshScenarioQuestState(state3)，最后发送原任务NPC菜单”，:16要求车夫“相同次序”。current/task_master_card.py:207–214与task_cart_dialogue.py:152–161均为Accept→Refresh3→Visit，保留原任务ID、凭据与奖励时序。

Spec:48要求“signed32=-1（ffffffff）”，:50要求“启动加载冻结政策/逻辑消息”“每次合法角色入场”。current/role_protocol.py:21–32严格生成c0039及BE signed -1；game_runtime.py:1013启动保存tuple，:343–363在每次合法AFTER_ENTER_WORLD回复首项加入。原c0011/c0031及资产状态未改。

只读候选checks的初始化/生命周期/原已有bean结果均passed，未替代本轴静态证据。未执行代码、数据库、服务、GUI或战斗，未改候选；真实现场确认窗、对白及部署后效果仍待验。

Standards 0项、无最高问题；Spec 0项、无最高问题。两轴仅静态。root另独立在候选source/配置下执行真实exit Owner→原WM_CLOSE四次reset纵切，并检查4个production Module实际路径皆指向候选，输出candidate-exit-owner-root-verification.json；新版task_master_card完整43×2及原existingbean消费另在工作源码独立通过，候选同模块哈希与该检查一致，候选已有固定路径43×2结果亦通过。未运行真实客户端/战斗，未认证真实服或操作人类存档；实际发布由集成窗口按当前用户授权及一致备份完成，不把审查通过当作GUI验收。继承wild与未纳入的care/newcreation等不属于本次增量。
