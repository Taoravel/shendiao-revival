# 序章血手印：任务侧 Module 与接线

2026-10-23。本批按用户“先补完序章”收敛范围；前一批师父/车夫修复已获人类授权交统一集成窗口发布。本文件不是该次部署范围，血手印未操作在线服、未接共享入口、未执行战斗。

## 实际产物

- `task_prologue_touch.py`：当前43创建路线覆盖的10个原血手印任务的启动校验、原前置恢复、NPC读条凭据、最早提交时间、目标实例身份冻结、公共世界事务与任务完成的原子组合、已付只读确认。
- `task_domain.py`：精确10个当前路线ID的`supports_prologue_touch`，专用`prologue_touch_transfer_committed`证据；普通NPC对白仍不能完成它们。
- `task_conversation.py`：已有active血手印在重连时恢复state0 bean。通用NPC菜单不据此擅自发ready或完成。
- `task_chains.py`最终**保持原行为**。未显式注入本Module政策时，100160→100106继续pending。显式政策入口恢复该边一次，避免尚未接线就自动启用计时传送。
- `verify_task_prologue_touch.py`及`task-prologue-touch-check.json`：实际临时账户/租约、Inventory、原NPC摆放、世界MapOwner和调用方事务检查。前置入册/NPC接近是可信fixture，未声称自然全链导航。

## 原来源与政策缺口

原表文本命中11 ID：100106/100206/100306/100406/100506/100606/100706/100806/100906/101002/103206。其中101002的前置101001/后继101003不属于当前43创建路线，不启用、不恢复其边。其余10条才是本Module定义与能力集合；原11条资料仍完整保留。它们的原目标均为嘉兴1006/NPC10498，ProcessBarTime=3，JumpType=3，Map=1501，X=63，Y=79，所有奖励为0；原前后继、Note、DisPlayNPCID均保留。

本批直接读取`artres/config.pfs → autoconfig/knight.gsp.task.cmainmissioninfo.xml`，PFS长度/CRC校验后BXML解码，11条所有属性及全部列表与现目录完全匹配，见`task-prologue-touch-source-check.json`。读条kind5→原16字节CCommit证据见[JIAXING_MAINLINE_NEXT_AUDIT.md](JIAXING_MAINLINE_NEXT_AUDIT.md)和[TASK_NPC_PROGRESS_RESEARCH.md](TASK_NPC_PROGRESS_RESEARCH.md)。不存在可信elapsed/目标坐标/独立读条开始ACK。

主策划正式政策现已交付：`design/newbie-bloodmark-v1.json`及`design/story-instance-v1.json`，裁定见[NEWBIE_BLOODMARK_INSTANCE_DECISION.md](NEWBIE_BLOODMARK_INSTANCE_DECISION.md)。本Module的`load_touch_policy()`实际读取两份单一来源，核十个ID、源placement13、3000ms最早提交/15000ms期限、原目标1501/63,79与采用1008,1264、私有命名空间[2**62,2**63)/partition0及对应政策revision。原3的绝对时钟单位仍未闭合；上述时间为designed，×16仍inferred+designed。加载只批准独立实现，不自动启用共享Runtime或部署。

1501由世界公开`world_story_instances`目录解析。本Module要求调用方明确给目录返回的`MapAddress`，在打开、授权及完成事务中调用公开`load_story_instance_transaction(...,expected_address=...)`，核实际角色、原章节、创建来源、路线与当前任务的完整身份。凭据冻结`directory_intent`和目标地址；范围合法但目录不存在的地址同样拒绝。本Module不分配实例、不复制目录SQL。检查程序已改用真实公开分配器，生产默认随机ID；同一原章节重试和新租约保持同一地址。

目录的正式Interface及未接范围见[WORLD_STORY_INSTANCE_DIRECTORY_HANDOFF.md](WORLD_STORY_INSTANCE_DIRECTORY_HANDOFF.md)；共享完整地址路由和生命周期仍待接入。Module要求源归属显式采用：打开读条前用公开`load_map_instance_transaction`确认源地址已绑定，未知legacy拒绝；首次完成前要求源地址/坐标/版本检查点完全匹配。调用方从真实源Owner取得精确检查点，按世界公开`bind_map_instance_transaction`显式采用后再打开读条。

启动注入已有`chapter_rules`及世界`story_rules`，从每条原successor沿唯一原边得到43路线→10血手印的映射，核两方快照一致。每个事务通过公共`read_newbie_chapter`验证显式创建来源/intro已完成、当前shape和school、冻结路线及本任务前置；`TouchTransferIntent.chapter_id`和`directory_intent`固定原创建身份，授权与结算重新核对。没有章节来源的旧角色不静默追补，101002也不混入。

## 公开 Interface 与调用次序

1. 启动离线准备：普通连接分别调用`prepare_touch_storage(db)`和世界`prepare_story_instance_storage(db)`；`story_rules=load_story_instance_rules(resources,accounts.newbie_rules)`及`policy=load_touch_policy()`读取正式政策；`load_touch_resources(resources,policy,catalog,grids,chapter_rules=accounts.newbie_rules,story_rules=story_rules)`核10条原配置、43路线、两方目录快照、唯一原type40/10908/1501/AI8001后继、时间边界及正常通行。热路径不读配置/建表。
2. 100160原完成后，同一租约事务调用`reconcile_touch_successor_transaction(db,account_id,role_id,epoch,resources,touch,100160)`，也可在可信pending边恢复时调用。返回仅新激活ID；调用方为这些ID发送一次state0接取bean，重试返回空，不能重置已有客户端状态。原后继100107不被这个入口激活或完成。
3. 真实地图交互和当前任务资格通过后，从公共`read_newbie_chapter(...).origin`构造`StoryInstanceIntent(chapter_id,creation_id,policy,route_fingerprint,task_id)`，当前租约事务调用世界`allocate_story_instance_transaction`取得目标地址，再用`open_touch_transaction(db,...,task_id,proof,location,target_address=allocated.address,generation=...,now_ms=...)`取得`TouchDialogue(intent,messages)`。本Module复核目录归属、原前置已完成、当前任务active、NPC10498/1006、地图/位置版本和连接世代。目录事务可先提交空身份，但不代表进入/任务完成；事务提交后才能发布该地址。messages为Accept3→RefreshState3→原SVisitNpc，客户端自行走kind5读条。
4. RoleOwner只保留一个当前intent；任意移动请求、切NPC、断线/新世代、换图、进入战斗都清除。无独立取消上行，不能在取消后沿用老票据。未达到最早提交时拒绝，不能用任意延时伪造客户端确认。
5. 原`CCommitScenarioQuest`解成`TaskIntent`后，先在**SQL事务外**向地图Owner重新校验当前NPC/位置，取得本次提交的`NpcInteraction`；再调用`authorize_touch_transfer(db,...,intent,command,current_location,proof=current_npc_proof,generation=...,now_ms=...)`。只接受同task/完整NPCkey/option0，当前章节/任务revision、placement13、位置/实例/世代均一致且到时、未过期。只传旧菜单ticket不能跳过当前地图检查；CQuestDialogEnd不替代读完提交。等待地图回报期间不得持有SQL事务。
6. 由地图所有者将intent.source及intent.target_position解析为`prepare_transfer→reserve(intent.target_address)→freeze→activate`；持久化公共`world_transfer_storage.begin`。源坐标/版本须先按公开Interface检查点落盘。原生输入不能指定目标或实例。
7. 同一个已校验租约的调用方事务内调用`complete_touch_transfer_transaction(db,...,intent,receipt,inventory,generation=...,now_ms=...,movement_state=0,**reward_rules)`。该函数重读精确目录身份，调用公开`commit_transfer_transaction`，再专用任务完成/零奖励路径，通过TaskDomain激活唯一原type40后继active0，最后登记任务receipt；不进入或结算AI8001。所有内容及最后角色/场景编码同事务，不复制世界/Inventory SQL。新资源profile需成对传resource/equipment规则，严格读取当前唯一资源，不隐式修复/治疗。
8. 返回的新`TouchResult`携带loading目标、completion和消息；调用方在**同事务中完成最终角色/场景编码**再commit，之后才发布内存快照和投递。晚期错误全事务回滚，loading/frozen内存所有者按既有世界恢复契约隔离，不能随意恢复源继续跑。发送屏障不是客户端加载确认。
9. 完成后的精确同租约receipt重试只读当前资源、世界已提交决策、原任务证据；返回`replayed=True,target=None,completion=None,messages=()`，不重复state1/Note、发奖或重新传送。10个启用候选的原奖励全部为0，故不重跑通用reward/chain恢复流程。新租约依已存任务/世界恢复，不重放旧连接票据。
10. 可信重登入场调用`resume_touch_messages(db,...,resources,touch)`，根据原章节仅恢复本路线已有active血手印或唯一原战斗后继state0，不激活、不完成、不开始战斗；完整私有位置仍由世界目录/持久恢复负责，不能由任务bean猜地址。

所有事务入口要求调用方使用当前`accounts.leased(account_id,role_id,epoch)`写事务；`load_task_state`本身不是租约认证器。DDL仅启动普通连接执行，不在FencedConnection玩法路径执行。

## 方法、检查和未验范围

codebase-design：把原资格、时钟、票据和原子结算集中于一个任务Module；世界仅提供版本化位置/实例/receipt，状态仍归原所有者。保持通用TaskChain的未接线门槛，生产无默认政策。

diagnosing-bugs：围绕“读完后同事务换图”运行真实临时事务，最早时间前1ms拒绝；受控最终场景编码失败后全库快照一致。期间发现通用已付恢复会重写任务effect，改为本零奖励任务的只读凭据确认；修改后全表重试无变化。

后续按世界交单增加实例存档反馈：修改前未显式采用源实例仍能打开读条，新增拒绝断言实际失败；修复后未知源拒绝、公开bind明确采用后成功，同一目标提交将完整私有地址、任务完成及唯一战斗后继active0一起保存；晚期回滚保留源，替换租约后公开load仍返回同一私有地址。此证明是领域/真实临时存档的实例保持，仍不是共享Runtime分配或GUI重登验收。

章节身份检查使用真实创建、公共load_role及intro播放授权/结束事务产生的已完成章节；其后说书人前置/位置仍为明确fixture，不伪称全程自然。新凭据chapter_id与实际原章节一致，换成其他chapter即拒绝。已初始化profile按既有公共成长/属性/宠经验规则完成零奖励流程，未绕过初始化契约。

当前通过：原11条完整属性/列表比对、10条当前路线能力与101002排除；100160在显式政策后只激活100106一次；原客户端已有bean的ready消费；错误/过早/过期/NPC/位置/实例/移动模式拒绝；真实MapOwner loading receipt及世界任务原子提交；晚期失败全库回滚；已付重试全表无变化；新租约存档保留与旧租约拒绝。`verify_jiaxing_story_boundary_runtime.py`亦通过，证明未注入政策的共享自然链依然停在明确100106pending，未暗中开放传送/战斗。

本批目录联合检查采用真实公开分配器：同原章节重复分配相同地址，未分配地址/改变创建身份拒绝；原任务、精确完整地址及唯一后继同事务提交，晚期失败全表回滚，精确已付重试全表不变，新租约按完整检查点重读同一目录。提前提交的空目录在传送失败后保留，符合正式政策；未将它算作任务入场。

1501 NPC表现接线采用[PROLOGUE_NPC_VISIBILITY_RESEARCH.md](PROLOGUE_NPC_VISIBILITY_RESEARCH.md)：本Module发出的原唯一后继active0使说书人10908、梦魇10909参与客户端当前任务显隐；原正常CNpc创建与接取/刷新均会重算。不能把DisPlayNPCID当服务器增删指令，或因未来100179完成就永久删除仍被100190引用的三怪。源10083/10491的hide5另受更新flag控制，完成刷新不保证立即隐藏；本批保留continuation与followups_pending，不用客户端委托推定其服务器待办已兑现。真实GUI和全部静态loader次序仍未验证。

方法：codebase-design将目录分配归世界、任务资格和票据归本Module，调用方控制事务及跨Owner等待；writing-for-agents将必需参数、顺序和成功条件收敛在本页。检查包含源实例采用、真实目录归属、原章节身份、3000ms/15000ms、实例目标同存、唯一原后继active0及重连任务bean。未验证：目录生命周期、共享RoleOwner完整地址路由、真实客户端自然导航/读条/场景/Note，以及正式后继战斗AI8001。后继任务active0而正式入战/结算继续禁用，不假胜利、不授技能或跳战斗。
