# 任务系统恢复与对接记录（2026-10-23）

下一成长批（2026-10-24）：第二战Task侧已交 [task-second-battle-delivery.json](task-second-battle-delivery.json) / [TASK_SECOND_BATTLE_INTEGRATION.md](TASK_SECOND_BATTLE_INTEGRATION.md)。仅新 `task_first_skill_proof.py` 与 `task_second_battle.py`；053218 BASE自然创建→真实首战胜利→教学后，纯读教学证明/原第二战菜单及12字节准入检查通过，保留技能高值、同准入幂等和事务回滚，固定两新生产源码。用户明确“不要过度复核”，本批必要链通过即交main，不再重复宽泛检查或多轮审查。AI8027 registry仅Task契约fixture；其实际engine/资源consumer/shared、CG10001及发布仍待main，不把本交单称在线第二战已通。已发布首战/教学和真人客户端均未操作。

2026-10-24 13:50:22 CST 发布更新：main 已确认 `task-pve-20261024T053218Z` / PID37096 替换旧7456，本次说书人 AI8001 首战、真实终态结算恢复、首次太祖长拳教学及已知范围内旧角色技能兼容已实装。实际启动在监听前加载首战、教学和 local-prologue baseline 规则；1454份冻结输入与启动一致，原110表结构及数据保留。发布依据仅引用 [task-pve-deployment-verification.json](task-pve-deployment-verification.json) 与 [主策发布验收](reviews/task-pve-root-20261024-r1/acceptance-root.json)，旧段落的“未发布”属于历史批次。角色4原档副本已跑通真胜→教学→重登；本窗口未操作在线服或真人客户端，现场 GUI 仍待人类重登。下一成长节点为100190/AI8027，再到100161/CG10001；10019自动动画桥也另待补，不将本首战与教学发布称全序章完成。

本批方法记录：diagnosing-bugs 沿用旧运行版自然复现与最终存档副本结果，核对实际发布回执、启动源码和规则采用路径，避免把工作区修复当已部署；writing-for-agents 将当前实装范围、证据和下一节点集中置顶。产物为本段交接更新；未改冻结生产源码，未重复宽泛测试。运行验证由main完成，本窗口只读核实，完整GUI与后续剧情仍未验证。

2026-10-24 当前P0改为按真人角色成长连续修复：最新截图已进入梦境嘉兴，卡在2级100107说书人；不再沿用旧“NPC消失/100160无后继”作为当前断点。`diagnose_growth_first_battle_runtime.py`在现役npc-repair-20261024T023920Z不可变源码自然创建/成长/血印进入本人私有1501后实际复现：原菜单无100107、task_battle_admissions未准备、原0xc4a4c无开战、原任务仍active，默认exit1。只用新临时库、真实Owner/加密Peer及清格路径见证，无真人/监听/战斗/手工激活。最小shared顺序、固定候选、十族范围和下一自然完成条件见[TASK_GROWTH_FIRST_BATTLE_HANDOFF.md](TASK_GROWTH_FIRST_BATTLE_HANDOFF.md)；PVE设计由root、shared由main集中，未称已修好或已发布。随后先100179太祖长拳→100190，再按原序章边逐段推进；远端轻功研究停止扩展。

P0任务准入已单独交 `task-first-battle-gate-delivery.json`：本人creation/chapter/原路线、血印已完/唯一首战active、完整adopted checkpoint/private目录、fresh NPC/地图代及原TaskBattle open/admit的独立Module；准确BASE自然2级前缀上五组隔离候选检查绿，固定r1三源码/13输入，双轴0。它不提供engine或shared开关。新租约终态恢复另交 `task-battle-terminal-recovery-delivery.json`：固定r2两源码/21输入，六组Task契约及旧六组binding通过；producer/source CAS仍由main实际PVE消费者验证，Task不改原event epoch。r1 Spec P2同TEXT lease int/str误认新租约已真实跑红、canonical比较修正后绿，r2双轴硬0/建议0/Spec0。公开recover和same/new lease已付纯读见 [TASK_BATTLE_TERMINAL_RECOVERY_INTEGRATION.md](TASK_BATTLE_TERMINAL_RECOVERY_INTEGRATION.md)，尚无本批shared/准确发布/GUI。

已有本地角色首技兼容已完成限定r2交单：`local-prologue-first-skill-delivery.json` / [LOCAL_PROLOGUE_FIRST_SKILL_INTEGRATION.md](LOCAL_PROLOGUE_FIRST_SKILL_INTEGRATION.md)。只在合法教学commit，核完整本地creation/chapter/route、真实前驱Task胜利、原prefix的journal/command/effects/XP/items/zero-pet/原币种收据，才以独立designed origin/迁移receipt开始；NPC visit只读UNKNOWN permit、登录不补空、已有完整map不覆盖。r1 Spec缺损reward审计P2已两个真实missing/null红→r2拒绝绿并独立闭合，Standards硬0/非阻断耦合建议1、Spec未解决0。自然旧BASE+明确Task层/实际专用engine胜利到教学、late SQL回滚UNKNOWN、后续合法学习/成长paid禁DML当前值、ledger同新lease保7、旧known8组全过；独立root父签限定接受，尚不代表实际role4已合格、准确shared已验、已发布或GUI。

2026-10-24 梦醒结算候选r4：原20节点/43路线的两族独立契约及真实World已提交凭据/当前位置纯读已闭合，冻结输入八组实际通过。第一族走明确临时Participant/BattleFinished经真实任务admit/settle，不是假造won行；实际AI胜利和生产可达仍为false。第二族按完成时选宠450/450；第一族125/宠0；原唯一后继、当前paid的后来XP/HP/宠物和移动、晚期编码全表回滚、提交后实际World清源拒绝及新租约清旧成员/目标恢复已验。r3建议已改为公开TaskChain接续，r4 Standards硬性0/建议0、Spec确认0。接口与精确SHA见 [TASK_DREAM_RETURN_INTEGRATION.md](TASK_DREAM_RETURN_INTEGRATION.md) 和 task-dream-return-settlement-delivery.json；尚无shared接线/准确发布/原生GUI，不能称本候选已进测试服。嘉兴入口此前已由统一集成发布private-story-20261023T190051Z、PID14480，任务窗口只读观察；真实100107等战斗仍暂停，序章整体未完成。

运行版本记录补充：本批只读latest-deployment-verification.json / npc-repair-root-release-verification-20261024.json，最新报告为npc-repair-20261024T023920Z、PID7456；旧碰撞35568/恢复3396和本窗口14480私有剧情OS观察各为历史。自然P0红例使用7456对应不可变source、临时库且不接现役进程；没有据其它批发布宣称梦醒/首技已部署。

此前嘉兴阻断（保留原复现证据）：真人已越过首师父/车夫到嘉兴，反馈说书人对白后NPC消失、没有后续剧情。只读日志确认role4先后提交100105/100160；36632冻结玩法隔离自然前缀复现100160完成后active为空、原100106后继pending/unimplemented。跨进程保留同一新临时存档，当前公开load+显式prologue_resume恢复仅100106 active0，重复恢复不重奖、不改成长/装备/币/宠或位置，原100160凭据保持唯一；三组必要检查实际绿。已将真实断点、原生前缀、当前恢复及完整部署门槛交统一集成；此前只读复核45272仍加载同一7089408b旧运行源码，当时完整入梦接线尚未发布；现服状态以本页最新发布记录为准。原流程须先血手印再入梦，不在100160直接强跳公共剧情图。见[JIAXING_STORYTELLER_PENDING_FIX.md](JIAXING_STORYTELLER_PENDING_FIX.md)。NPC消失的GUI显隐原因未单独重放，不能与缺后继混为同一已证原因。

前一首师父发卡阻断：原native证明Start phase2只发CCommit，旧Module错误等Finish phase3的DialogEnd。已改为合法CCommit持久授权原卡，选择时才发物；新actual Owner检查直接喂原native消息（没有合成End）红→绿，43路线两选项/10车夫及迁移资源领域链通过。首次部署44084、后经39796/36632继承同一修复；最近45272启动元数据的master哈希仍一致。真人已继续到车夫并抵达嘉兴，确认该流程已越过；未以此扩称全部卡选项GUI已验，见 [FIRST_MASTER_CARD_COMMIT_FIX.md](FIRST_MASTER_CARD_COMMIT_FIX.md)。序章整体仍未完成。

序章血手印原表11条保留资料，其中当前43路线覆盖10条独立读条/换图Module，旧101002排除。已采用正式newbie-bloodmark/story-instance政策并接真实世界目录Interface：3秒/15秒、placement13、×16目标、原章节/创建/路线/任务身份、提交时新地图NPC证明；源实例须显式采用。真实目录分配、MapOwner/Inventory联合检查通过：同章地址不变、无目录/改创建来源拒绝、零奖励、完整地址/任务/原唯一type40后继active0同事务、晚期全库回滚、已付只读确认及新租约同地址。通用TaskChain保持未接线门槛，目录生命周期/共享完整地址路由仍待所属窗口；正式AI8001入战结算继续禁用。见 [TASK_PROLOGUE_TOUCH_INTEGRATION.md](TASK_PROLOGUE_TOUCH_INTEGRATION.md)。

前一处ready缺陷已发布：师父/车夫重复SAccept(state3)被原客户端忽略，已改为NPC菜单前显式RefreshState3并被当前运行版本继承。人类随后反馈“对话完没有武器”，故继续处理本页最上方的发卡触发缺陷；不能将ready修复或候选检查通过称序章打通。部署证据见 [FIRST_MASTER_READY_FIX.md](FIRST_MASTER_READY_FIX.md)。

序章首技能r3独立候选已交：原授100008/value1免费、保留高值/全部旧技能、原120XP与唯一战斗后继active0，10节点/43路线不改。按原生新证将26个UI class6显示项与native OtherSkills manager+40分开，完整支持身份为100007/100008/100009/310202特殊/700004，350001等跨容器baseline/grant拒绝；原r2来源指纹不静默迁移。两原路线、人工AI8001终局仅作任务契约、late SQL/native编码全表回滚、paid当前XP/profile/完整map及重登围栏，八组实际通过；原消费者保留310202/700004，故意漏项真删除已验。r3固定5源码/28输入，双轴Standards硬0/建议0、Spec确认0。入口见 [TASK_FIRST_SKILL_INTEGRATION.md](TASK_FIRST_SKILL_INTEGRATION.md) / task-first-skill-delivery.json。main建角/登录/shared仍待接；旧角色unknown须独立完整基线或root明确designed兼容迁移，不能伪造Verified空值；实际AI、网络故障、准确发布及GUI未验。

后续室内NPC目标差异已接研究：原102002/200602把10157目标图写1007，而原102005/102006/200490写1376；本批直接PFS核五行、与NPC窗口实际1376交互成功但Task acceptance NPC mismatch的red报告分别保存。官方叙事支持去临安客栈，不证明数字地图受理规则。现有菜单/接取/Domain各自比较地图，单改菜单不能闭合，完整真实物理proof继续保留。任务侧来源/接缝见 [TASK_ROOM_TARGET_SEAM_AUDIT.md](TASK_ROOM_TARGET_SEAM_AUDIT.md)，原生导航独立研究已收敛：真实原段在1007/1376均选定义1376，原有序path表不是任意连通图等价；但原server接受规则仍unknown。精确交单 task-room-target-research-delivery.json，后续根设计精确task allowlist；当前不开放alias。

三本轻功教学书的原生缺口已闭合：原50190/50191/50192确经TaskObject/TaskRelative raw15/usemap0、右键分派与kind2尾部发CUseItem16字节；旧QingGongMiJiObject关联实际是36843【师授】/type2198，不能混类。task_item_use只对精确206104/206204/206304更正只读范围，并增加server_learning_rule_unconfirmed，仍不扣书/授轻功/完成或发奖。原58/41及三原native包→当前真实Inventory/journal检查七组通过，16输入哈希稳定，全库/资产不变；双轴硬0/建议0、Spec确认0。原赠书分别206102/206203/206303，入口30/50/70和官方35/气力100对30/气力200的版本冲突分列，均不采用未知server时值。精确交单task-qinggong-book-use-delivery.json；学习/消费/计时/World能力规则及完整GUI/shared仍待根裁定和所属接线。

画卷十条现已实现独立`task_prologue_puzzle.py`并加载中央正式`2026-10-23.newbie-puzzle.1`：真实私有目录/原章节/11106 placement16、原菜单553、zero-key客户端声明、当前NPC新证明与地图世代、任务/共同人物及宠物奖励/原唯一后继active0/receipt同事务，付后不重放Finish，新租约仅恢复已有任务。默认正式0/300000ms政策七组必要检查通过，保留360/360与360/350；固定源码双轴审查Standards硬性0/低建议1，Spec缺陷0。历史未批准1000ms fixture单独留档；无shared/部署，不能称服务端验证棋盘或自然打过前置战斗。通用TaskChain仍pending。精确候选见`task-prologue-puzzle-delivery.json`与[双轴报告](task-prologue-puzzle-review.md)，当前Interface及未验范围见 [TASK_PROLOGUE_PUZZLE_INTEGRATION.md](TASK_PROLOGUE_PUZZLE_INTEGRATION.md)。下文画卷source-only为上一批原证阶段记录。

两次梦醒回嘉兴的20原节点、20立即后继及43路线原边已核：[PROLOGUE_DREAM_RETURN_RESEARCH.md](PROLOGUE_DREAM_RETURN_RESEARCH.md)。第一族125人物XP/0宠XP、第二族450/450；第二族后继丐帮100221独有200/200，不抹平为其他九条500/500。原边盘点已增加`original_dream_return_families`和每条路线的两次梦醒ID，核43路线均依序经过两族、每族恰十条、原奖励及前后边一致。新增`task_prologue_return_dialogue.py`仅准备已有任务对白、原NPC菜单及真实key提交→未解析raw intent，不激活/完成/奖励/换图。五组隔离检查通过，第一族有效战斗后及单独前驱负例未验、不造胜利；双轴Standards硬性0/建议0，Spec原P3仅报告文案已在r2解决、当前未解决0。固定清单`task-dream-return-dialogue-delivery.json`与[双轴报告](task-dream-return-dialogue-review.md)，Interface见[TASK_DREAM_RETURN_DIALOGUE_INTEGRATION.md](TASK_DREAM_RETURN_DIALOGUE_INTEGRATION.md)。codebase-design将资格/目录/原包检查集中在只读Interface，期限注入既有NPC规则，无新默认。raw×16落点有旁证，但采用、完整结算与第二次入梦目录策略仍等主策划裁定；当前传送完成Module尚未实现。

全序章原边盘点已生成 `prologue-restore-scope.json`（`audit_prologue_restore_scope.py`）：43条创建选择逐条跟原Post边，共333个不同原目录节点；在100199等十个原目录缺失定义处明确停止。每节点保留原类型/目标/奖励/表现/读条/传送和当前独立能力谓词，匹配只说明领域Interface可处理，不能当共享接线、激活或可玩数量。下一原生研究聚焦1501任务NPC列表语义、陆立鼎10001及破窑10002表现；不为缺失节点造结尾，不执行前置正式战斗。

按主策划最新要求，CG1/2、两次梦醒、原完成奖励和原消费路径已合并到[PROLOGUE_DREAM_RETURN_RESEARCH.md](PROLOGUE_DREAM_RETURN_RESEARCH.md)的2026-10-24单一收敛节。原PFS独立复核与派生盘点一致：十组覆盖43路线，从CG1到第二梦醒各完整17节点，中间正式AI8002/8003/8028/8005均保留；AI8028另有30045，不混成CG10002。新增`original_story_phase_inventory`保存全路径及CG两个族的原字段/属性缺省差异，333节点另补原物品奖励与绑定列表。这里只补来源与原边，未采用×16、30分钟许可、CG确认时序或第二次入梦实例策略，仍待正式裁定。

陆立鼎10001/破窑10002各10节点原证已交 [PROLOGUE_STORY_EFFECT_RESEARCH.md](PROLOGUE_STORY_EFFECT_RESEARCH.md)：原前者直接CCommit、后者Start后kind5读条再CCommit；state1只暂存小于20000的表现ID，原dispatcher早退，未找到自动CG桥。原movie存在且显式SStart可播放，不证明原服发送时点或必须等CEnd才完成。已交集成协调主策划补显式CG/任务顺序和破窑再次入梦目录政策，尚未开放此20节点。画卷100120等10条type59另外复跑原1711af0：受控phase3发送CCommit(task,0,0)，其他phase无包；仅原包构造证据，不代表自然解题/服务器可验证棋盘，研究继续。

梦境NPC原证已交 [PROLOGUE_NPC_VISIBILITY_RESEARCH.md](PROLOGUE_NPC_VISIBILITY_RESEARCH.md)：原任务引用控制本地可见性，正常CNpc创建与任务刷新都会重算；100107 active0使10908/10909显示，100179及后继100190保持三怪引用。源列表10083/10491的hide5在完成刷新flag0下不立即隐藏；不能把列表当服务器删除动作，也未据客户端委托改followups_pending。画卷十条原奖励另保留差异：人物EXP均360，100719宠EXP350、其余九条360，不批量抹平。

画卷完整原证现已交 [PROLOGUE_PUZZLE_RESEARCH.md](PROLOGUE_PUZZLE_RESEARCH.md)：11106实际静态placement16，原SVisit服务553打开专用QuestPuzzle；固定2x2由原点击两次交换自然归位→phase3，最后按钮才提交CCommit(task,0,0)，不上传棋盘/步骤。当前只交原证及专用Interface建议，已交集成协调主策划直接制定菜单许可、重连/过期/移动失效和当前地图复验的client-assertion政策；不能将普通对话/装备/通用小游戏用于完成它，也不能宣称服务器验证了棋盘。首真人点击到CVisit前链及GUI仍未验。

新手“设置宠物参战”新增11条精确type59独立能力，原200XP/零其他奖励和前后边保留，按当前已选自有宠状态reconcile标designed。真实Inventory.receive参战→同事务source→任务/成长已通过，晚期全库回滚、原200XP→L2/111/free5、后来换宠/休息/新租约不重选或重奖；前驱捕捉/赠宠和后继AI8028战斗不伪造，原后继继续pending。共享hook及自然前置尚待主集成，见 [TASK_FIGHTING_PET_OBJECTIVES_INTEGRATION.md](TASK_FIGHTING_PET_OBJECTIVES_INTEGRATION.md)。

交宠type13原14条/模式2/宠32位key与宽NPCkey研究已闭合，新增独立意图codec；锁mask5与绑定mask2分开、50级只是防误交确认。当前尚缺实例野生/宝宝kind、展示宠权威来源及公开同事务交付Interface，不以放生代替交付；6周期/1变身继续独立保留，正式完成0。精确所需事实/资产契约及原证见 [TASK_PET_SUBMISSION_INTEGRATION.md](TASK_PET_SUBMISSION_INTEGRATION.md)。

NPC交钱type11新增5条独立领域能力和原mode3/25字节CSubmit2Npc专用codec：金额两字段相同，不能按交物key/count解释。3条实际静态NPC临时事务检查通过，含原500000/2000000/1现金与两件绑定奖励、晚期全库回滚、新租约当前余额确认及唯一资源保持；另2条13874活动NPC不在静态场景，仅纯原计划，不造活动NPC。生产CurrencyRules尚未批准task_money_submission现金用途，正式启用0；本窗口只提供显式recipe gate和受控临时规则检查，不改主策划货币配置、不借npc_shop。精确接口、原生现金证据、支付政策及共享所需接线见 [TASK_MONEY_SUBMISSION_INTEGRATION.md](TASK_MONEY_SUBMISSION_INTEGRATION.md)。

任务共同奖励/完成已显式接根GrowthResourceContext与唯一资源：交物/宠XP后source-only→同库存人物成长→奖励物品后source-only→内层当前最终profile编码；progression和交物/Quiz/到区/车夫/intro/master-card/独立type59 reconcile已透传成对资源/装备规则。新profile在intro前显式转交的完整前置领域链到嘉兴，原120XP→L2/31/free5、80/110HP46/106MP、49/38/8检查通过。卡发物单独source-only，装备资源过渡由调用方先做再独立reconcile；旧equip组合包装不对新profile隐式补资源。库存血脉漏规则已由所属窗口修复，复合任务和延后宠7000XP检查现全部绿，人物累计20500XP不重复。精确签名、阶段、检查与仍待shared集成的范围见 [TASK_RESOURCE_GROWTH_INTEGRATION.md](TASK_RESOURCE_GROWTH_INTEGRATION.md)。未改shared/root独占模块或在线状态。

固定NPC答题新增5条独立能力，7条动态/轮次保留：原CAnswerQuestion0xc4a48，正确项code0/错误项原序号+1，与随机显示行号分开；230407原正确文本“2”保留。原NPC10215临时事务、错答无写/重开、晚期失败回滚、唯一230408及已付当前余额检查通过，多后继映射不猜。当前接口/本地错答政策/共享所需接线见 [TASK_QUIZ_INTEGRATION.md](TASK_QUIZ_INTEGRATION.md)。任务/成长唯一资源迁移另按主策划最新公开Interface规划，未改共享入口或root独占模块。

任务/成长资源接线静态审计见 [TASK_GROWTH_RESOURCE_SEAM_AUDIT.md](TASK_GROWTH_RESOURCE_SEAM_AUDIT.md)：objective扣物及宠XP都在人物EXP前推进资产revision，items奖励在EXP后；分别source-only同步后才使用同库存版本的ordinary_growth，已付EXP但新补宠XP也不能漏同步。根窗口GrowthResourceContext已交付，本窗口已实际实现上述共同路径；该审计保留研究过程，当前实现按本页首段及交接说明。

type22新增原CUseItem解码及58条/41道具真实实例和当前任务候选的只读Module：普通静态准用51、动态春联4、type73秘籍3；真实InventorySnapshot/journal/Location，完整64位目标、资产/任务版本、多目标歧义及原两套矩形分别保留。临时库检查确认不写任务/不扣物，错误实例/装备/战斗/旧租约拒绝；正式完成开放数仍0，待明确消费/时序规则。接口与原生依据见 [TASK_ITEM_USE_INSPECTION_INTEGRATION.md](TASK_ITEM_USE_INSPECTION_INTEGRATION.md)，未接shared或在线服。

新增203601/205701/233701三个真实NPC空表现交接，静态NPC type50能力现127条。原203601/NPC10958临时事务0奖励/唯一203690/重试重登通过，Start2及Finish122必要兼容通过。234条中另有intro10，剩余97条按真实触发/机制保留；SNotifyStart实为活动倒计时，不能启动这些任务；Note20只有state1显示证据、缺少接取/完成触发。当前接口、覆盖和缺口见 [TASK_SCENARIO_TRIGGER_INTEGRATION.md](TASK_SCENARIO_TRIGGER_INTEGRATION.md)，未改shared或在线状态。

type50开始对白新增201201/230401两个非循环真实NPC能力，与此前122条Finish合计124条静态NPC能力；原客户端Start读尽后CCommit，不加DialogEnd门槛。原201201/NPC10903临时事务保留节点0XP/0银，战斗201202正确pending，必要兼容通过，见 [TASK_SCENARIO_START_INTEGRATION.md](TASK_SCENARIO_START_INTEGRATION.md)。四个轮次活动、无NPC自动入口与未知活动资格仍待各自规则。另车夫规则校验值已在发版前排除三个纯进度字段，十路线必要检查通过，最终值见车夫交接；未改已付记录或shared。

type50全234条已按原PFS/原指令分组，并新增122条无额外机制的NPC完成对白支持：ready3/空start走普通CCommit，事务后state1读原Finish；重复state1会重播，已在公共完成结果中限本族省去重试状态。原200104实际NPC/临时库11000XP+2275绑定银/晚期编码回滚通过；未知前置和无NPC自动入口不放宽，见 [TASK_SCENARIO_FINISH_INTEGRATION.md](TASK_SCENARIO_FINISH_INTEGRATION.md)。车夫所属实现和shared本窗口保持稳定；其自然链/嘉兴标题的主策划独立转绿状态见下面最新指针。

主集成已接车夫和嘉兴60001，主策划独立自然GameRuntime流程转绿：原clear移动→车夫→目标场景精确发送barrier→嘉兴NPC→标题CCommit，原120XP自然L2/XP31/free5、穿装49/38/8，重试/重连不重奖不重播。证据 [newbie-cart-runtime-verification.json](newbie-cart-runtime-verification.json) / [newbie-jiaxing-runtime-verification.json](newbie-jiaxing-runtime-verification.json)，均临时库，无GUI/线上服/战斗。本窗口未重复执行或改root verifier。旧段落的“共享车夫/嘉兴尚未接线”按这组最新证据更新理解。其后提交前场景编码失败和提交后清源失败的同Runtime恢复也由世界/shared修复、主策划独立转绿，当前报告及公开恢复顺序集中见 [TASK_CART_TRANSFER_INTEGRATION.md](TASK_CART_TRANSFER_INTEGRATION.md)末段；不是本窗口新增部署或GUI证据。

主线车夫现新增 `task_cart_transfer.complete_cart_transfer_transaction`：按主策划×16政策、当前冻结intent与匹配TransferCommit，内部调用世界公开caller事务commit，和车夫/原0XP/唯一嘉兴后继及凭据原子组合。真实章节/卡片/实际武器装备前置的十条离线事务通过，晚期失败整体回滚、重复不拉回旧位置/不重奖。未动shared或root自然baseline，接口与共享接线顺序见 [TASK_CART_TRANSFER_INTEGRATION.md](TASK_CART_TRANSFER_INTEGRATION.md)。

使用道具type22的58任务/41物品已按原PFS联查；55条普通任务物品原使用CUseItem，3条轻功秘籍另有路径。物品准用范围与任务目标、readtime与任务ProcessBarTime分开，扣量/战斗前后时序仍未闭合；本批主线车夫优先，未开放这58条，见 [TASK_USE_ITEM_INTEGRATION.md](TASK_USE_ITEM_INTEGRATION.md)。

到区type56完成183条原配置/原指令研究；解除源码冻结后新增task_region.py和158条静态区域领域支持，25条额外机制保留。CCommit(key0/option0)+可信世界Location，半开四边×16；原奖励、任务与来源凭据同调用方事务；已付重试/重连确认当前余额并省去重复state1。158条计划及原102391临时库7500XP/晚期失败回滚必要检查通过；原唯一后继策略/已有active恢复已接静态区域。共享完成路由须与链变化一起集成，不授予轻功或移动角色，见 [TASK_REGION_OBJECTIVES_INTEGRATION.md](TASK_REGION_OBJECTIVES_INTEGRATION.md)。

任务战斗新增原专用0xc4a4c解码、NPC/任务/角色/场次持久绑定、可信终态与公共奖励同事务、失败/取消/重试恢复接口，见 [TASK_BATTLE_INTEGRATION.md](TASK_BATTLE_INTEGRATION.md)。必要契约夹具通过；默认正式任务战斗开放数0，326是绑定元数据候选，301是研究零额外字段族，都不能当已支持敌阵。训练/wild结果不能完成任务。

任务线显示由主集成依据 [TASK_TRACKER_FAILURE_RESEARCH.md](TASK_TRACKER_FAILURE_RESEARCH.md)统一纠正为active0/failed2/ready3/remove1。本批不并行修改其接取/恢复显示段；旧批文档state2 active说法属于已推翻历史，持久active/completed语义不变。

嘉兴10条60001任务已确认是本地章节标题特效，新增独立能力沿普通NPC提交结算各120XP/原后继，并避免重试state1重播；普通对白判定仍收窄，见 [TASK_NATIVE_EFFECT_DIALOGUE_INTEGRATION.md](TASK_NATIVE_EFFECT_DIALOGUE_INTEGRATION.md)。临时库十条及旧对白/续接必要检查通过，GUI与共享接线未验收。

车夫后续已确认原phase5的CCommit选项索引从0开始，无需额外分支下行；新增task_cart_dialogue.py按显式章节/获领装备/type59前置与真实ActiveNpc授权菜单，产生冻结原坐标传送请求，十个原节点必要检查通过。原坐标按原数字均被地图阻挡，×16候选正常mask1可走；换算仍需主策划集中裁定，世界同caller事务持久交接Interface也待提供，详见 [TASK_CART_BRANCH_INTEGRATION.md](TASK_CART_BRANCH_INTEGRATION.md)。不提前完成车夫或移动角色。

师父武器选择卡独立事务及精确获领实例type59已恢复：43路线两项原选择共86次受控发物/装备检查通过。本批已改用实际Inventory.immutable_snapshot_transaction并删除临时读取Adapter；直接使用真实acquire_lease验证成功，此前把存储TEXT误当公开字符串输入的兼容缺口已撤销。实际共享流程见 [TASK_MASTER_CARD_INTEGRATION.md](TASK_MASTER_CARD_INTEGRATION.md)；当前仅独立模块完成，不代表GUI或运行服已启用。装备后只激活原车夫后继，传送另待世界接线。

新手开场章节的独立创建来源、43原路线root授权/完成/唯一后继及重连持久化已实现，当前入口与限定临时库证据见 [TASK_NEWBIE_CHAPTER_INTEGRATION.md](TASK_NEWBIE_CHAPTER_INTEGRATION.md)；实际共享创建/运行时及GUI未验收。19条无额外效果的等级等待及6条角色条件奖励修复见 [TASK_LEVEL_GATES_INTEGRATION.md](TASK_LEVEL_GATES_INTEGRATION.md)。

普通交物任务新增原CSubmit2Npc专用入口、指定实例扣物与奖励同事务；202条静态单模板目标有领域支持，34条附加/特殊目标保持未实现。本批task_item_transactions.py已合并实际Inventory公开读取、冻结generation许可及扣物/奖励/当前背包编码，实际租约验证通过；共享路由仍待接，见 [TASK_ITEM_SUBMISSION_INTEGRATION.md](TASK_ITEM_SUBMISSION_INTEGRATION.md)，不能把领域条数当可玩验收数。

任务宠物经验冻结接收者、同事务渠道及人物普通成长刷新已实现；最新启动、提交后读取与历史核对条件见 [TASK_PET_EXPERIENCE_INTEGRATION.md](TASK_PET_EXPERIENCE_INTEGRATION.md)。旧批“宠物经验全部pending/人物刷新未核验”不是当前独立模块状态；原客户端显示与运行时部署仍待集成验收。

续接明确普通任务、成长属性基线/快照及显式钱包货币渠道的最新接口与接线条件见 [TASK_CHAIN_ATTRIBUTES.md](TASK_CHAIN_ATTRIBUTES.md)。旧批限制按时间保留；最新GameRuntime源码已接NPC任务流程，本窗口没有据此声称运行进程已加载所有新代码。货币映射为主策划designed，未初始化钱包仍pending，旧批“所有货币均未接”的说明不再代表当前独立模块实现。

当前接线以文末“原生NPC任务交互与绑定奖励”节为准。TaskConversation负责角色范围的NPC任务票据和菜单，complete_task_transaction将完成与支持的奖励合并为一个事务，completion_messages提供提交后的原生逻辑消息。Inventory已新增0/1绑定实例支持，旧批“绑定道具全部pending”的说明保留为历史限制，不再是当前实现。未改共享在线入口，仍需集成窗口接线及真客户端验收。

人物普通升级/潜能增量账本已按主策划v1实现，接线见文末“普通成长与潜能增量”。默认未登记角色仍只记经验余额；仅显式初始化普通阶段并注入GrowthRules时启用自动升级。

本批按用户“先批量恢复、不需要过多验证”的指令执行。方法采用 codebase-design：原版内容与索引放在 tasks.json，持久化及可信事件集中到 TaskStore，小接口隐藏数据库事务和角色归属检查。research 子任务直接读取当前客户端内存映像，协议地址另见 TASK_PROTOCOL.md。tdd 的预先确认已询问，用户选择先批量恢复，因此没有开展测试先行和完整回归。

## 已落地

- recover_tasks.py 批量整理原始 cmainmissioninfo 2,460 条、cacceptabletask 129 条，保留全部 attributes/lists；另生成 NPC、地图、类型索引。
- 原版对话 6,886 句，后续关联 2,521 条，覆盖 689 个目标 NPC、88 张目标地图。数量代表资料覆盖，不代表可玩任务数量。
- tasks.py 的 TaskStore 提供可信服务器激活、任务记录查询、原版对话读取、普通 NPC 对话完成和待处理效果查询。记录存入 accounts 数据库的独立 task_journal/task_effects 表，完成与效果记录在同一事务内保存。
- 激活并不把原始前置列表解释成 AND/OR；调用方须先提供确定的触发规则。角色形象限制按建角配置的 color1/2/3 对照 RequestRoleIDList。
- task_session.py 已接入 gateway 的任务分支，处理原生 CRequestQuestCanAccept 查询和 CTrackQuest 追踪。可接列表读取服务器 offer() 登记，并排除已接/已完成及等级不符任务；默认没有登记，避免把全量静态内容直接开放。追踪只允许已接任务并持久化；单项回复使用原 STrackQuest。运行服尚未因本批单独重启。
- 普通 type=10 对话只在准确任务 NPC/地图下读取。带动画、战斗、传送、计时、交物、小游戏等任务等待相应可信玩法事件；没有把客户端发来的 task ID 当作完成证明。

## 缺口及跨模块需求

1. 世界窗口：将原生 NPC 实体 key 对照静态 NPC 配置 ID；NPC 坐标与玩家坐标单位需要换算并检查距离。调用 dialogue 的 map_id/npc_id 必须来自经服务器核实的实体，不能直接相信客户端字段。任务专用 NPC 的刷出、DisPlayNPCID 的精确显示语义尚待对接。
2. 战斗窗口：ActiveInfoNpcID/MapID 是目标，AIInfoAIID 是原配置的战斗关联。任务推进需要战斗实例与角色、任务绑定，胜利回调后再推进，不能单凭客户端提交消息完成。
3. 物品/数值窗口：任务显示奖励按原字段 ExpReward、MoneyReward、PetExpReward、ShengWang、SMoney 逐项保留；钱币单位、绑定规则、经验曲线和最终发奖协议尚未接通。task_effects 保存一次性待处理记录，目前没有修改任何实际余额、背包、等级。跨模块领取须在同一 SQLite 事务内发奖并确认 delivered，不能读出队列后先标记再发奖。
4. 剧情窗口：ScenarioInfoAnimationID、对话选项、ProcessBarTime、RewardMapJumpType 保留原值；需要关联动画结束、合法选项、服务器计时和真实传送完成。NPC 对话不能代替这些事件。
5. 激活规则：RequestMissionList 的 AND/OR、章节触发、100199 等客户端缺失节点、日常循环和活动日程未确认。graph 的 incoming_ids 仅表示边，不能当全部前置条件。
6. 可接列表：客户端129条展示入口有23条不在剧情定义表。不能把活动入口等同于可直接激活的剧情任务。

## 实验策略与验证范围

当前 TaskStore 普通 type=10 对话完成属于本地恢复策略；不是已经验证的原服任务判定。未补造奖励数值、剧情、缺失任务和出生主线，未自动给现有角色接任务。

已读取主策划 DESIGN_AUTHORITY.md 与 design/recovery-baseline.json。主表每条都有明确 ExpReward（包含0），所以本批保留原值，未用设计经验覆盖0奖励。将来确属“缺失原奖励”的任务才适用主策划20%/40%补全公式；不应把0自动判断为缺失。现阶段唯一结算键是角色+任务ID，周期实例尚未实现，所以循环活动不会复用该接口反复完成。

运行 recover_tasks.py 成功；一次临时数据库基本检查验证任务100160原版三句对话可读取、完成后重建 TaskStore 仍保留记录及一份待处理效果。报告 task-smoke.json。没有修改在线角色任务状态，也未声称原客户端界面已验证或完整任务流程已打通。

网关接入后执行语法检查及已有 verify_gateway.py，认证、持续加密压缩、建角和移动持久化检查通过；没有重复开展全面任务测试。真实客户端任务面板、可接标记、NPC对话、剧情播放、战斗任务、奖励入账和重登界面同步均未实测。

复现入口：在游戏目录运行 `python revival/recover_tasks.py`。详细缺失关联与列表长度问题见 task-recovery.json；原始数据仍保留，异常不会被填成零或被删除。

协议研究补充：已批量索引151个task命名空间原生消息，证据见 `task-protocol-evidence.json` / `task-native-disassembly.txt` / `TASK_PROTOCOL.md`。三个原生标量解码探针确认24/8/12字节布局。主线已接全量同步时序、value1/value2业务含义仍未确认；STrackQuest原Process为空，客户端发送时已本地改变追踪，持久化不等于重登界面同步已恢复。主策划后续找到的官方端游剧情奖励应先对齐任务ID，再接入统一结算，当前原表字段不覆盖。

## 2026-10-23 并发架构交接

本节供集成窗口迁移任务路径时读取；全局约束以 `../ARCHITECTURE.md` 为准。本批收敛共享文件修改：本轮只修改 tasks.py、task_session.py 和本记录；serve.py、gateway.py、accounts.py 后续由原始复原窗口统一接线。本节不表示运行时迁移已经完成。

### 已提供的路径

- 启动准备：`prepare_task_store(accounts)` 在接收连接前完成配置读取和任务表迁移，返回 TaskResources。该函数包含阻塞I/O，应由启动阶段或集成方有界持久化执行资源执行。
- 只读内容：TaskResources 深层冻结任务定义、列表和角色形象映射；多个角色所有者可以共享这个只读值。角色受限任务激活已改为查预计算形象映射，无逐请求读建角配置。
- 快速构造：`TaskStore(accounts, resources=resources)` 只绑定依赖，不做建表或配置读取。它仍是同步SQLite兼容Adapter，业务方法仍会读写数据库。
- 纯消息Seam：`decode_task_request(kind, body)` 返回冻结 TaskCommand；`encode_task_reply(command, result)` 返回 `(type, bytes)` 元组组成的不可变消息序列。这两端均不访问Session、writer、RC4/MPPC或数据库。
- 同步兼容执行：`execute_task_command(task_store, account_id, role_id, command)` 返回不可变结果；只处理可接查询与追踪。这是集成方受控存储工作路径的入口，不是网络循环入口，也不是角色所有者实现。

### 接线顺序和完成条件

1. 启动阶段准备一次 TaskResources，按角色所有者绑定TaskStore。完成条件：角色登录/请求不再走 `TaskStore(accounts)` 的旧冷启动分支，网络收发循环中没有任务配置读取和DDL。
2. 连接所有者解码TaskCommand，用集成方既有信封携带 `role_id/login_epoch/request_id/deadline` 送入该角色有界邮箱。角色ID取服务器登录身份；邮箱满时明确拒绝/背压。完成条件：同角色命令顺序执行，不同角色不共用一个业务串行队列。
3. 角色所有者通过有界持久化Adapter执行同步存储部分，或替换成原生异步存储Adapter；所有权检查、提交结果和回调均受login_epoch约束。完成条件：一个角色等待慢存储时，其他角色的协议心跳与其他地图/战斗继续推进；此项本批未做架构测试。
4. 存储成功后返回不可变结果，由目标连接所有者编码并顺序加密发送；断线后旧epoch结果不会进入新连接。完成条件：玩法执行方不持有或访问其他Session的可变编码状态。
5. 奖励对接时，由角色资产所有者在同一事务更新资产和消费 task_effects 的唯一结算凭据；待处理效果不返回“奖励已到账”。当前只支持一次性任务，循环任务先建立实例ID。完成条件：重试、重登均返回既有结算，无重复增产、无先标记后发奖。

### 未迁移路径

- 原TaskSession.receive仍同步调用TaskStore；默认构造仍包含兼容冷启动的配置读取与建表。shared gateway 仍调用该兼容入口，集成方需按上述路径替换。没有通过把整个Session.feed塞进线程池来宣称迁移。
- TaskStore各业务方法仍使用accounts.connect/owned_role同步存储；自身没有角色邮箱、login_epoch租约、有界存储工作队列和超时控制，这些由集成方角色/持久化所有者提供。
- task_effects 尚未与资产结算形成统一事务；奖励入账、战斗/地图任务事件与跨分片outbox仍待接入。
- 本批没有新增全局锁、全局可变配置缓存、全服命令队列或线程池；SQLite文件级单写限制仍然存在。

### 方法与基本检查

codebase-design用于把静态配置、原生codec与持久化Adapter之间的Seam具体落到函数；writing-for-agents用于给出有先后顺序且带完成条件的接线。产物为任务两模块变更与本节交接。

一次临时数据库检查确认：注入准备好的TaskResources后，将accounts.connect替换为抛错函数仍能构造TaskStore；嵌套任务配置修改触发TypeError；纯请求/回复codec、普通对话完成和待处理效果保存通过。没有修改在线存档或重启服务，没有进行容量压测、慢存储故障隔离、邮箱满载或旧epoch回调验证，因此不能宣称商业容量或并发迁移已完成。

## 2026-10-23 继续恢复：角色任务推进与事务接线

沿用codebase-design：把原生请求意图、可信玩法证据、纯状态推进、存储事务放在不同Seam。TaskDomain只消费准备好的不可变TaskResources和角色快照，不读文件、数据库或会话。沿用writing-for-agents：以下接线说明集中记录条件和未完成范围。按用户批量优先要求，仅做状态写入所需的基本检查，未开展TDD或全量协议回归。

### 新增实现

- `task_domain.py`：冻结TaskActor/TaskSnapshot/TaskEvidence/TaskPlan；提供服务器登记offer、按原等级/角色形象检查后接取、追踪、普通NPC对话目标完成、指定AI胜利事件和指定剧情结束事件。完成会保留原奖励、绑定信息、后续原始ID（包括缺失定义）、结束对话、显示NPC和地图/动画原字段。
- 上述完成规则属于本地恢复策略；字段和内容来自客户端，原服务器完整事件规则尚未恢复。战斗事件必须由战斗所有者绑定角色、任务和场次后产生，剧情事件必须由剧情所有者确认，NPC事件必须来自地图校验。原网络“对话结束/提交/到达”消息无法自己变成可信证据。
- `task_persistence.py`：`load_task_state(db, account_id, role_id, login_epoch)`在调用方事务内读取一致角色/任务快照；`apply_task_plan(db, actor, plan, request_id)`加入同一角色事务，检查归属、计划版本及角色等级/形象快照；写入状态、一次性待处理效果与请求回执。它不打开连接，不begin/commit，不访问其他Module。
- 新增task_versions/task_command_receipts启动迁移及角色范围的旧Adapter变更触发器。旧同步接口改变任务后，新计划必须重新加载，防止新旧路径覆盖状态。无全局业务锁、全服队列或线程池。
- `get_task_receipt(db, account_id, role_id, request_id)`支持重连后先读取既有回执，已记录操作不再次执行。当前登录epoch的检查仍由角色所有者在事务内完成；本模块校验plan与actor中的epoch相符，并不自己维护在线租约。
- `task_session.decode_task_intent`纯解析CCommitScenarioQuest、CQuestDialogEnd、CQuestReachScene、CRequestReward，返回冻结TaskIntent。Intent保留NPC key和最后的不明i32，不能将其直接认作合法选项。TASK_INTENT_TYPES单独列出，尚未加入旧TASK_TYPES自动执行列表。

### 集成入口与完成条件

1. 启动时调用prepare_task_store一次，注入TaskResources。任务表新增迁移也在此完成；旧运行进程尚未加载本批代码。
2. 角色所有者持有当前login_epoch；按role_id顺序处理有界邮箱中的意图。原始客户端意图先交地图/战斗/剧情所有者校验，收到版本与epoch有效的TaskEvidence后再计算plan。
3. 存储工作资源内开启角色事务，核对当前在线租约，用load_task_state取得actor/snapshot，调用TaskDomain.plan，再apply_task_plan。任何异常由调用方回滚整个事务；不要在事务内部捕获异常后继续提交部分写入。若规划与提交分开，过期版本明确拒绝并重新规划。
4. 请求重试可用相同plan/request_id取得相同回执；重连先get_task_receipt，再决定是否规划新操作。receipt只确认任务操作已存储，不表示奖励已到账。
5. task_effects仍为待处理效果。物品43000在原任务100192中数量1、绑定1，同时ExpReward=150；这些原值完整保留。当前AssetChange没有绑定字段、人物经验/货币统一结算尚未接入，因此不把绑定物品转成普通grant，不丢弃经验或标为已发奖。
6. 角色资产所有者需要在同一个事务中写资产/经验及共同结算凭据、标记task_effects.delivered，才能通知奖励成功。原生任务状态码、任务面板重登同步和可接NPC标记仍待真客户端联调，不能从内部完成记录推断界面已恢复。

### 本批验证与范围

`verify_task_transitions.py`只使用临时数据库。原任务100192的登记、接取、可信NPC完成、原150经验/绑定物品待处理字段、同请求幂等回执、重连读取、调用方事务回滚均通过；旧Adapter变更后拒绝旧计划；不相关AI战斗结果被拒绝。纯available/accept运算在禁用文件打开时通过，语法检查通过。报告见task-transition-check.json。

本轮修改限定tasks.py/task_session.py及新增领域/存储/基本检查模块，未修改serve.py、gateway.py、accounts.py。角色所有者、NPC距离验证、有效租约事务、有界异步调度和统一资产结算由集成窗口接线；没有重启运行服、改在线角色、实际发奖或进行商业容量测试。批量资料、原消息布局继续有效，完整任务玩法仍未真客户端实测。

## 2026-10-23 奖励入账切片：人物EXP与分渠道事务

方法：沿用codebase-design，把纯RewardPlan、人物经验余额操作和同事务奖励Adapter分开；research后台核对原任务字段/升级提示；writing-for-agents用于以下可执行接线说明。保留必要写入回归，没有扩展到完整原生UI测试。资料证据由TASK_REWARD_SOURCES.md集中维护。

### 已实现与来源

- `progression.py`：在已有role_progress.experience中保存人物可用经验余额。保持roles.level不变，不自动消费经验或升级，也没有另造经验曲线。原cresmoneyconfig.nextexp已有表值，但其完整消费/升级索引不在本切片中推断。
- `task_rewards.py`：plan_task_reward只读取不可变已加载任务和物品配置，核对effect奖励与原定义一致；不将0经验当缺失。当前ExpReward按1:1入人物经验余额是本地恢复策略，原字段名/64位值已证实，与PetExpReward分开；原服实际倍率/到账算法尚未证实。例如原任务100192=150、100107=120基础经验。
- 每个非零PetExpReward、MoneyReward、SMoney、ShengWang均保留为独立pending，不猜币种/宠物归属。研究发现MoneyReward当前2460行均0，SMoney有307行非0，不能据此映射成某种银两。
- 道具必须满足已知ID、正整数数量且bind=0，才调用Inventory.apply_settlement。当前原表物品奖励未找到明确bind=0的样本；绑定/绑定未知全部保持items渠道pending，人物EXP仍可单独入账。没有将绑定奖励降级为无绑定道具。
- task_reward_channels以(role_id,task_id,channel)为唯一键，保存原内容指纹及回执。已入账EXP/道具在整体pending期间重试也不会重复增加；内容变更要求显式迁移，不能绕过旧凭据重发。
- 若角色effect还有next_ids或非零/非空continuation_fields，奖励结清后依然保持outbox delivered=0及followups_pending=true，避免隐藏后续任务、传送和结束对话。只有全部奖励解决且没有未处理后续工作，奖励Adapter才置delivered=1。reward_status可单独表示settled/partially_settled。
- 所有新运行时操作不打开数据库连接、不begin/commit、不访问Session或网络、不加载配置、不新增全局锁/队列。奖励事务内查询角色归属和role_leases当前epoch/active，过期登录不能发奖。

### 新公开Interface与接线

1. 启动迁移时调用 `prepare_reward_storage(db)` 建立奖励渠道表；同时由现有启动流程准备AccountStore、TaskResources和InventoryConfig。该步骤含DDL，仅在启动阶段运行。
2. 集成方在角色所有者/有界持久化工作路径中开启一个角色事务并检查租约；已完成任务具有task_journal completed记录及task_effects原内容时，调用 `settle_task_reward(db, account_id, role_id, login_epoch, task_id, resources, inventory)`。inventory必须绑定同一account_id/role_id。
3. 同一事务内依次更新role_progress、Inventory.apply_settlement、渠道凭据及effect投递状态；任一异常必须让调用方回滚整个事务。背包满不会留下已加经验但道具失败的半笔操作。外部Module不能先单独调用grant_item再确认effect。
4. `TaskRewardReceipt`返回该任务已结算的经验/道具和完整pending列表。experience_awarded/items_awarded是稳定结算回执，不代表每次重试都新增加同样数量。rewards_complete仅指奖励渠道全部解决，不代表剧情/后续节点已执行。
5. `read_experience(db, account_id, role_id)`和`credit_experience(...)`使用调用方事务；credit本身没有幂等键，任务发奖必须通过上述渠道Adapter，其他奖励也应先保存自己的唯一凭据。
6. 后续补货币/宠物/绑定支持时，保持已有渠道唯一凭据，用新渠道补齐pending。需要角色资产事务内的绑定道具写入Interface；目前AssetChange只能表达(template_id,quantity)，因此不能安全发原表绑定道具。尚未修改其他窗口inventory.py。

### 必要检查及未接入范围

verify_task_rewards.py在临时数据库通过：原任务100192/100107基础经验共270只增加一次，绑定/SMoney仍pending；明确标注的“设计无绑定测试配置”验证真实inventory_items、EXP、渠道回执及delivered同事务入库；背包满回滚EXP及渠道凭据；跨角色Inventory及已替换登录epoch拒绝。无绑定设计测试配置不是原版任务奖励证据。报告task-reward-check.json。

verify_task_transitions.py仍通过。TaskActor/TaskEvidence/TaskPlan同时兼容集成方不透明字符串epoch和正整数epoch；奖励租约使用事务内SQL比较，兼容当前TEXT存储与整数接口，不修改共享accounts.py。

本批未接serve.py/gateway.py/accounts.py、未重启运行服，未发在线奖励；客户端经验/等级/背包显示、自动或手动升级、原任务绑定道具、货币/宠物EXP、后续剧情处理仍需集成。没有容量或高并发压测结论。

## 2026-10-23 原生NPC任务交互与绑定奖励

### 本批实际变化

- codebase-design用于将NPC菜单/对话票据、纯任务推进、同事务写入和提交后消息分开；research子任务直接追踪本客户端NPC菜单和经验刷新调用；writing-for-agents用于本节集成顺序及前置条件。研究产物为TASK_DIALOG_PROTOCOL.md和task_dialog_protocol.py。
- Inventory现有AssetChange已支持(template_id,quantity,binding)。task_rewards.py现在将原表明确0/1绑定值原样交给Inventory，绑定未知或无效条目仍pending。原任务100192的43000×1、binding=1已通过真实库存表入账检查；升级前已付150经验的旧渠道凭据也能直接重用，只补发物品，不重加经验。
- TaskRewardReceipt新增experience_balance：每次在当前事务读取人物余额，而非回用第一次发奖的历史余额。原SRefreshUserExp(0xc000d)是BE u64累计余额，不能发送本次经验增量。
- task_conversation.py新增TaskConversation，保留一份角色范围的有期限NPC票据。只接受地图所有者生成的NpcInteraction并对照最新Location，检查角色/epoch、场景实例、位置版本和目标NPC。玩家移动、换实例、换登录或超时后，旧票据无法完成任务。acknowledge只在持久化事务成功提交后消费票据。
- 本切片只开放无动画、无战斗/交物/计时等额外条件的type10原版对话任务；其余原任务继续由相应玩法事件推进。服务器先登记offer，不自动开放全部2460条任务，也未跳过章节前置或替现有角色播种主线。
- TaskConversation.menu_messages优先返回当前NPC的一条可完成已接任务，再返回一条服务器已授权的可接任务；该“每次访问一条”是本地恢复策略，单角色仅一张票据。原对白由客户端本地CMainMissionInfo绘制，TaskDialogue.lines仅供内部检查，不发送通用确认框冒充对白。

### 原生交互顺序

1. 启动时准备TaskResources、InventoryConfig、原地图NPC定义/摆放、prepare_reward_storage；由集成方实际地图所有者生成实体key并完成NpcScene绑定。
2. 角色收到CVisitNpc后，把请求交地图所有者校验；取得NpcInteraction和最新Location。使用当前事务加载actor/snapshot后，角色所有者调用TaskConversation.menu_messages。该函数返回的是逻辑(type,bytes)序列，发送仍由连接所有者处理。
3. 可接任务菜单先发SRequestQuestCanAccept，再SVisitNpc。SVisitNpc第一个列表为服务ID，第二个列表才是任务ID；本切片只提供任务菜单，其它NPC服务应由集成方的菜单组装统一合并。
4. 未接任务的CCommitScenarioQuest先decode_task_intent，再plan_accept，持久化accept计划；提交成功后发acceptance_messages（SAcceptScenarioQuest state2，本地进行中策略）。任务ID、NPC实体key和保留i32均检查，未知选项拒绝。复杂任务接取不通过这个普通对话切片。
5. 下次同NPC访问时，对已接普通任务先发SRefreshScenarioQuestState=3，然后把任务列入SVisitNpc第二列表。客户端状态2仅显示进行中提示；状态3才进入原版完成对白/选项、最终发送CCommit。该顺序由原调用路径确认，不能只发送state2后等待客户端提交。
6. 完成意图经plan_finish对当前票据和最新Location校验；在同一个角色租约事务内调用complete_task_transaction(db,actor,plan,request_id,resources,inventory)，同时apply_task_plan和settle_task_reward。任意异常回滚全部；只在成功commit后acknowledge(plan)，再由目标连接所有者发送completion_messages(result)：原任务state1完成/清理消息，以及当前总经验余额。
7. state1可能诱发CQuestDialogEnd后续确认。任务已完成且没有活动票据时，这种确认只能作为幂等确认处理，不新建完成计划、不重新发奖。网络消息本身不能变成TaskEvidence。
8. 重登时，resume_messages对受支持普通任务恢复SAcceptScenarioQuest bean（state2、无计数任务的value1/2=0、npc_key=0静态配置回退）。其它任务类型的进度字段/初态未确认，不用零值替代。NPC菜单始终回显真实交互实体key。

### 必要检查与剩余接线

verify_task_workflow.py使用原任务100192、原地图1006中NPC10899的摆放，在临时角色和数据库中走NpcScene.interact→NPC可接菜单→原CCommit接取→state3/任务菜单→完成意图→同事务任务/经验/绑定物品→原state1/经验余额消息。验证玩家位置版本变化拒绝完成、任务只保留一份效果、重放不重复发奖，并在随后另获经验后重放时刷新273当前余额而非历史150。报告task-workflow-check.json；未进行真实客户端交互。

verify_task_rewards.py已更新并通过：原绑定道具补发、旧经验渠道凭据复用、未明SMoney仍pending、背包失败回滚、跨角色/旧epoch拒绝。原绑定字段的客户端实际展示标志仍由物品窗口另核验，不能把数据库绑定正确等同原客户端标志已验收。

本批仅修改所属任务模块、新增TaskConversation/TaskWorkflow及必要检查，未修改serve.py/gateway.py/accounts.py/game_runtime.py/runtime_storage.py，也未重启服或修改在线角色。最新共享GameRuntime已经接可接查询与追踪，但尚未接本节NPC票据、接取/提交、奖励事务和经验通知；其启动准备还需调用prepare_reward_storage。地图NPC菜单路由由集成窗口统一接线，不能仅把新文件存在当在线生效。

## 2026-10-23 普通成长与潜能增量

方法：codebase-design将GrowthState/GrowthPlan纯运算、版本化规则和调用方事务分开；writing-for-agents将启动、显式启用、成功回执与界面限制集中于本节。按主策划role-progression-v1.json实施，阈值源于原表，消费/10级前自动/自动点等分等行为按裁定为designed。没有另造升级曲线，没有改在线角色或共享入口。

### 本批实现

- role_growth.py加载完整原nextexp为只读映射，普通阶段只允许1–155；155为上限，后段1001+原值保留但不能当普通等级使用。只支持明确版本2026-10-23.role.1，规则变更需要显式实现/迁移。
- credit_experience新增可选growth_rules。角色无普通成长档案时，保持原等级/经验余额行为；有档案但未传规则则拒绝，避免漏升。启用后正经验收入按当前级原门槛消费，自动连续升级至10级；10级及以后保留可用经验，手动合法请求一次只升级一级。零收入不触发升级。
- 每次升级记录自动五维各1、自由5的增量。只保存从baseline以后的automatic_points/allocated_points和自由余额，不猜初始五维或HP/MP/派生属性。已有角色初始化必须显式提供当前等级及已知自由点余额，历史已知分配可记录baseline_allocated；未知则存null，不补发历史升级点。
- role_growth与role_growth_receipts为独立角色表；等级、经验、自动增量、分配增量、自由余额、版本、成功请求回执在同一事务保存。未知阶段/政策、当前快照变化、溢出、点数不足、经验不足、基线重置均明确拒绝。
- progression_protocol.py仅解CReqLevelUp0xc32cd的一个BE32不明字段；普通策略只接受原构造默认0。不解释为目标等级/数量，非零拒绝。未编造SLevelUp/属性刷新的字段布局。
- TaskRewardReceipt新增level，experience_balance仍是扣除升级费用后的当前可用余额。complete_task_transaction/settle_task_reward可选传growth_rules，使任务完成、XP入账/升级/潜能、绑定道具、渠道幂等凭据在同一角色事务内提交。旧奖励渠道凭据继续去重，不补发已经结算奖励或重新触发升级。

### 公开Interface与接入条件

1. 启动阶段调用load_growth_rules和prepare_growth_storage(db)；前者只在启动读配置，后者只在启动执行DDL。不为任何角色自动建成长档案。
2. 在当前有效角色租约事务内，集成方明确选择普通阶段后调用initialize_growth(db,account_id,role_id,epoch,rules,expected_level=...,free_points=...,known_allocated=...)。新角色可明确登记L1/free0；已有角色须先确认阶段和自由点余额。该操作保存原等级与EXP，一次建立基线，后续相同基线可重试，不同基线拒绝覆盖。
3. 任务结算注入同一GrowthRules，不在热路径重读配置。升级后只在commit成功后发布新角色/任务快照，更新RoleOwner缓存等级，避免继续用旧等级检查任务/装备。提交后EXP消息发剩余余额，不能把原发奖数当余额。
4. 手动升级经decode_level_up_request获得原opaque字段，交角色所有者有界邮箱，再在租约事务内调用request_manual_level(...,opaque_field,request_id,rules)。该函数先查成功回执再加载当前快照；跨重连或之后已加点时，相同请求仍返回原成功结果，不重升。字段冲突拒绝。失败请求抛错且不动成长资产；成功请求有持久凭据。
5. 潜能分配先read_growth，再plan_potential_allocation(state,(体质,内力,力量,耐力,敏捷增量),expected_revision,rules)，apply_growth_plan同事务保存。过期版本、负值、超额和溢出拒绝。分配网络协议/最终五维属性刷新尚未确认，不能直接把任意客户端map当作本Interface参数。
6. 原生等级、五维和派生属性刷新另需核验。当前只明确SRefreshUserExp余额布局；不要只发余额就宣称客户端等级已经同步。开启普通profile之前，集成方需明确其显示与服务端快照策略。

### 必要检查与未验证范围

verify_role_growth.py通过：L1+150→L2余61、L1+270→L2余181；原阈值连续消费停在10，手动一次消费5781到11；自动五维/自由点与版本分配；成功请求在后续分配后重试不重升；错误模式、经验不足、基线覆盖拒绝；事务回滚；未初始化角色继续L1/150银行行为；155/1001不能按普通手动升级。报告role-growth-check.json。

verify_task_rewards.py新增已启用普通档案的任务100192切片：原150经验→L2余61+五维各1+自由5+原绑定道具；背包失败时连同成长全部回滚；重放不再增加经验/升级/潜能。verify_task_workflow.py原未启用档案行为仍通过。

未修改serve.py/gateway.py/accounts.py/game_runtime.py/runtime_storage.py、在线数据库或黑屏现场，未启用任何真实存档的普通阶段；没有验证客户端升级按钮/潜能面板/等级与属性刷新、特殊阶段、历史点数迁移和容量压测。本批是独立领域/事务实现，运行服需要集成方接线和实际客户端验收。

手动成功回执同样属于历史操作结果：若之后又升级/加点，重试旧request_id仍返回旧成功结果。集成方应在同事务或提交后的读取中用read_growth获得当前快照刷新缓存/客户端，不能用旧回执覆盖更高等级或新分配。任务奖励回执已专门读取当前EXP/level，因此其重放消息不会发送旧余额。
