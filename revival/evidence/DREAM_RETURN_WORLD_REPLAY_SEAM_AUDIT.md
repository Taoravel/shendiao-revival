# 梦醒世界交接与paid只读重试：公开Interface审计

2026-10-24。按research Skill后台委派，只读当前公开源码、正式梦醒policy/decision与ARCHITECTURE；唯一写入本文。没有运行代码模块、数据库、verifier、战斗、客户端、网络或服务。本审计给出可复用Interface、精确缺口与待执行fixture序列，不表示实现/接线/部署通过。

## 结论：可组合首次事务，paid不能走通用settlement replay

正式`newbie-dream-return.1`批准20原任务/43路线、private1501→public(1006,1006,0)，两目标2720/1120与5360/2304；采用×16、期限300000ms/minimum0为designed，不改变原字段来源等级。首次结算可组合现有MapOwner预留/冻结/目标loading回执与`world_transfer_storage.commit_transfer_transaction`，在同一角色调用方事务里完成世界位置/完整地址、任务、资产、唯一后继和梦醒自有凭据，并在提交前验证最终编码。

**`task_workflow.replay_completed_task_transaction`不是只读Interface。** 它调用`_settle_completion`→`settle_task_reward`→通道settle/资源同步/`UPDATE task_effects`，还调用`continue_task_chain`。即使EXP不重复入账，仍可能更新effect、补付原pending渠道、变更资产source或激活后继；不能满足本policy的“paid只读当前”。禁止照搬车夫paid路径或仅加`replayed=True`掩盖这些写入。

paid分支应先用当前租约读取**梦醒Module自己的持久回执**并核对同一accepted intent/operation，再调用公开只读快照Interface；不再调用世界prepare/reserve/freeze/activate/ready，不返回历史target作为当前传送命令，不重复state1/旧后继投影。新收到相同CCommit不是新授权；旧epoch回调仍拒绝，新epoch恢复须由当前角色Owner持历史operation身份发起。

## 世界公开Interface及真实约束

| Interface / 源文件 | 可复用事实 | 对梦醒调用方的要求 |
|---|---|---|
| `MapOwner.prepare_transfer(expected,target_position,request_id,deadline_ms,now_ms)`，world_owner.py:585 | 源当前active Location/完整地址/版本须精确相等；登记offer，不freeze、不持久化；拒同map模板warp | 用正式政策resolver输出，不能信客户端坐标。offer只有target_position，**没有完整目标MapAddress** |
| `target.reserve(offer,now_ms)`，:613 | 目标Owner按自己的address生成Reservation，检查容量/期限；只有预留，没有membership | 严格选public MapAddress(1006,1006,0)。只检查mapID1006不足以排除其它1006实例 |
| `source.freeze(reservation,now_ms)`，:642 | 验源原offer，version V→V+1、state=frozen，返回FrozenTransfer | 在源Owner执行，不持角色SQL事务等地图响应 |
| `target.activate(frozen,now_ms)`，:665 | 按原proof得到target loading Location，version V+2，返回TransferCommit | 此时仅内存loading，**不是durable commit**，不能发场景包或清源 |
| `world_transfer_storage.begin(accounts,...,offer)`，:137 | 自开leased连接/BEGIN IMMEDIATE记录prepared，不改角色位置；检查已有完整source实例 | 只能在最终调用方事务外完成准备阶段；不要嵌入已经打开的角色写事务。prepared本身不授任务奖励 |
| `commit_transfer_transaction(db,...,receipt)`，:204 | 加入现有事务，不connect/commit；严验receipt/source checkpoint；原子写位置、版本、world_handoffs committed及已采用的完整实例地址 | 保持默认allow_source_checkpoint_lag=False；梦醒预先已采用私有源，不能借legacy wrapper放宽checkpoint |
| `source.finalize(receipt)` / `finalize_with_view`，:693/697 | durable后才清冻结源membership，保留可重试receipt | 最终db commit后调用；若有玩家投影使用配套with_view，不能只清authority遗漏view |
| `target.ready(...)` / `ready_with_view`，:728/732 | loading→active，version再+1，纯内存 | 必须等批准scene-transition精确发送屏障；不是客户端ready ACK，不在paid重放 |
| `load_map_instance_transaction(db,...,epoch)`，world_transfer_storage.py:93 | 纯读取当前lease的完整address+position+version+entry_version+transfer_id；None=未知实例 | 用此读取**当前**世界结果，不能拿旧receipt.location覆盖；无隐式adopt/迁移 |
| `load_story_instance_transaction(db,...,intent,rules,expected_address=...)`，world_story_instances.py:147 | 纯读取既有持久目录、严验创建来源/lease/身份；不会分配/移动 | 首次交接验证source私有地址；paid仍保留目录身份，不能把当前public地址当expected私有地址传入，不能重allocate目录 |

`TransferCommit`的完整形状来自world_owner.py:48–71：offer(transfer_id,source,target_position,deadline)→Reservation(offer,target完整地址)→FrozenTransfer(reservation,source frozen)→TransferCommit(frozen,target loading)。world storage `_receipt_scope`会验证V/V+1/V+2、非负signed16坐标与合法MapAddress拓扑，但**不替policy验证public1006固定实例或maze mask1**。这些仍由梦醒resolver与对应MapOwner上下文负责。目标点检查与服务器普通movement_state0必须显式注入；不可移植旧cart verifier里的MapAddress(1006,1,0)。

### 同lease历史world receipt确认：已有有条件只读分支，没有纯read公开getter

`commit_transfer_transaction`在world_handoffs已committed/ready、编码receipt完全一致时返回**False**，不执行位置或journal写入；允许current durable version更新及后来合法坐标/实例，验证entry provenance而不倒退位置。`task_prologue_touch.py:391–404`正用该分支核对paid世界决策后返回空messages。

但该方法的prepared分支会首次写入；**它整体不是纯读API**。paid调用方若历史row不一致或prepared，本应拒绝，不能让“核对历史”尝试修复成commit。现有公共接口未提供专门`read/confirm committed transfer`，这是需要world storage所属Module补的小Seam，不能在任务模块复制world_handoffs SQL或导入私有_decode/_receipt_scope。

建议缺口契约（仅建议名称，当前未实现）：`confirm_committed_transfer_transaction(db,account_id,role_id,current_epoch,transfer_id,expected_receipt)`只SELECT；验当前lease、历史receipt原epoch/完整intent、stage committed/ready及当前checkpoint的版本/provenance，返回冻结的历史决策与**当前checkpoint**；缺失/prepared/cancelled/冲突一律拒绝，不补commit/cancel。这个单一Interface应同时覆盖同lease与新lease，避免两个任务调用方复制编码/SQL规则。

### 新lease恢复与paid读取必须分层

`prepare_transfer_recovery_transaction(db,account_id,role_id,new_epoch,transfer_id=None)`（world_transfer_storage.py:325）要求先取得新有效lease，旧writer已fence；显式transfer_id可恢复精确旧operation。历史committed/ready分支不写位置，返回`TransferRecoveryDecision`，包括旧source/offer/receipt、new_epoch及**当前**authority_position/version；prepared分支则会UPDATE为cancelled。因此它是恢复Interface，不能无条件称纯read。

恢复处理应先在自己的role恢复事务提交prepared取消等必要动作，再按`MapOwner.inspect_transfer`→`retire_recovered_transfer[_with_view]`清精确旧epoch/owner_generation的内存状态。该方法核对冻结MapTransferSnapshot，拒删替换lease的membership。之后按当前持久checkpoint恢复目标。**这是恢复工作，不是paid acknowledgement，也不是第二次搬家。** 已committed目标不因未发包/未ready退回source；原持久story目录不删除或另分配。

`commit_transfer_transaction(...new_epoch,old_receipt)`会因offer.source.login_epoch不符而拒绝，不能用它当新lease通用历史读取。`prepare_transfer_recovery_transaction`能提供旧lease决策，但prepared分支带取消写入，且不是独立的paid纯读receipt reader；上述world只读确认Seam仍有价值。若省略transfer_id，它会选最新旧lease handoff，**不能**把那个结果随意绑定到另一历史梦醒回执；本任务应带明确稳定operation ID。

## 人物、资产、资源：可复用公开只读Interface

全部调用共享当前角色Owner的同一读事务。`accounts.leased(...).connect()`返回FencedConnection；BEGIN核lease，过期写入也fence。部分下列读函数自身只验account/transaction，不能因为传入了epoch就误称内部已校验epoch；进入事务时的当前lease、角色所有权与退出前Owner世代隔离仍必须成立。

| Interface | 读取/前提 | paid用法与限制 |
|---|---|---|
| `progression.read_experience(db,account_id,role_id)` | 当前level+role_progress.experience，纯SELECT；未建progress时返回0，**不含epoch参数/检查** | 返回当前余额，不能credit_experience(0)假装读取；不初始化成长 |
| `role_growth.read_growth(db,account_id,role_id)` | 当前GrowthState，纯SELECT，要求已有ordinary baseline；自身无lease参数 | 已初始化角色读当前level/XP/free/allocated/revision，未知/缺baseline拒绝，不能initialize/auto_credit |
| `task_persistence.load_task_state(db,...,epoch)` / `get_task_receipt(db,...,request_id)` | 当前不可变TaskSnapshot / TaskReceipt(request_id,role_id,revision,effect_id) | 验completed及稳定任务command identity；两者依赖caller lease fencing；TaskReceipt**不是资产发奖凭据全集** |
| `inventory.immutable_snapshot_transaction(db,epoch=...)` | 当前、冻结InventorySnapshot；函数内部查当前lease | 读当前资产revision，供装备/资源投影；不用非transaction snapshot另开连接 |
| `role_resource_storage.read_role_resources(db,...,epoch,rules)` | 当前唯一资源carrier与caps/source；自身当前lease/规则校验，纯读 | 不转移资源、不修caps、不治疗。缺显式profile保持unknown |
| `role_equipment_storage.current_equipment_totals(...)` + `current_resource_profile(...,equipment_rules,resource_rules)` | 读当前裸身/basis、同txn资产revision和迁移资源，组合最终装备/资源快照 | 必须使用当前资产与匹配policy；pending source变化拒绝，不在paid路径synchronize/迁移 |
| `task_growth_resources.current_task_resource_profile(db,actor,inventory,resource_rules,equipment_rules)` | 上述组合的公开task侧只读入口；无profile时可None，成对rules必需 | migrated严格读；旧legacy情况才用公开attribute读取，不强行混用两个HP/MP契约 |
| `role_attribute_storage.attribute_snapshot_if_initialized(...)` / `read_attribute_snapshot(...)` | 已知legacy快照，纯读；migrated carrier拒绝legacy读取 | 仅按现有source/profile选择合法分支；不能把bare growth当装备后最终值 |
| `currency.read_wallet(db,...,epoch,rules)` | 当前余额、revision与policy，纯读 | 两族原钱为0，无新增钱包授权；需刷新时只读已初始化钱包，缺baseline不能造0 |
| `role_attribute_protocol.growth_refresh(growth,snapshot)` | 纯编码，校验growth revision/五维signed16/float32 | 使用以上当前同源快照；不能重发历史成长/旧HP，不能用旧settlement快照替当前 |

当前纯消息编码可用`task_dialog_protocol.encode_user_experience(current_balance)`、`growth_refresh`和对应wallet codec；它们不授奖。不要为了复用`completion_messages`而构造含旧state1、旧started_infos/target的假fresh completion；paid可只返回current读取结果/必要刷新，任务与场景旧表现不重放。

## 固定宠接收者：现有小Interface与真正缺口

`capture_fresh_recipient`仅在首次active→completed、人物EXP之前冻结参战宠/人物等级/原PetExpReward；不能在打开对白时提前选，也不能在paid时重捕。`settle_pet_experience`即使旧paid存在，也可能建立decision/channel记录、补付pending、改变growth；不能当getter。

已公开可复用：

- `TaskPetExperienceResult(status,reason,amount,recipient_id,current_pet=None)`，task_pet_experience.py:41：首次公开workflow返回该结果。
- `refresh_pet_experience(db,account_id,role_id,epoch,result,inventory)`，:178：**只读**并保留result.recipient_id；awarded时读这只原宠当前状态，切换参战宠不会改变接收者。原宠释放/缺baseline返回pending/audit，不选择替身、不补奖。
- `inventory.read_pet_state(db,pet_id)`，inventory.py:1654：纯读单个当前owned active宠；不存在/外来/释放返回None。自身只验owned transaction，配合公开snapshot/当前leased事务fence；不查当前fighting替换recipient。
- `pet_experience_messages(result)`，task_pet_experience.py:189：纯编码该原宠当前快照+绝对EXP。完成前原settle已用pet_record和i32 key/u64 EXP验证可编码，但刻意不把precommit宠对象装作ready-to-send；提交后再开当前只读角色事务refresh，不能重settle来取得current_pet。

**最低新增自有契约**：首次梦醒原子事务把公共completion.rewards.pet_experience的status/reason/amount/recipient_id及policy/source identity，连同accepted intent/epoch、world receipt、task command identity保存到梦醒自己的回执（不保存current_pet当当前缓存）。paid读取自有row后重建上述结果，调用公开refresh；第一族amount0不触碰宠，第二族450的零接收/不合格/pending状态均保持原决定，不重新判断或均分。这样新梦醒row无需复制其它Module的SQL。

若想从既有task-only历史记录重建，`task_pet_experience._read_decision`是私有函数，且没有公开的只读decision+channel receipt reader；`task_rewards`同样只有settle及plan，没有完整只读reward receipt读取。不得把私有函数当获准Interface、复制其SQL或用当前selected_fighting_pet猜历史。需要资产/宠奖励所属Module补公开reader，或对缺少自有接收者的历史row保持显式reconciliation unknown。`get_task_receipt`只证明任务command，不补出宠接收者/发奖status。

paid仍有pending时保持pending，另行授权的reconciliation才可写；“本次重试不再奖”与“一直没兑现的渠道永远丢弃”不同，不静默清pending。

## 两个已有verifier真实事务能借什么，不能借什么

`verify_task_cart_transfer.py`实际构造：合法intro/master/card/equip前置→source.prepare→target.reserve→source.freeze→target.activate→`handoffs.begin`→调用方BEGIN IMMEDIATE→`complete_cart_transfer_transaction`（内部world commit+task/rewards）→最终编码可抛错→caller commit→source.finalize/target.ready。它验证失败时world prepared、源坐标、task active/EXP等不变，后来合法重试提交；也验证后来checkpoint与EXP不被旧回执覆盖。

但其paid实现`task_cart_transfer.py:175`调用通用replay后返回历史receipt.location；其test并不断言全部SQL表严格无写，且目标fixture为MapAddress(1006,1,0)。这些都**不能直接沿用**到新policy的严格只读/public(1006,1006,0)要求。它的新lease段只拒绝旧epoch并读回状态，没有证明新梦醒跨lease paid reader可用。

`verify_task_prologue_touch.py`实际构造：显式intro/late-story enrollment/source checkpoint→公共bind源→公共story allocate目标→真实NpcScene proof→MapOwner完整transfer receipt→world.begin→单caller txn组合world+touch→晚期scene编码异常、全表snapshot rollback→合法提交→paid精确全表不变→新lease保留完整目标/旧epoch拒绝。其touch本身原全0奖励，paid无需重建EXP/宠，不能把这个空结果直接扩成梦醒125/450已读当前资产。

两者都以临时库/可信位置或late-story状态为fixture，不证明自然AI前驱、在线发送屏障或GUI。late SQL回滚不自动撤销地图内存：target.activate后target.cancel已拒绝，不能因DB回滚就任意source.resume；需保留fence并用已批准恢复/同一稳定operation安全继续。只有activate前取得匹配target.cancel，才可source.resume；expiry自身不解冻。

## 建议的最小隔离fixture序列（仅构造说明，本批未执行）

1. 临时AccountStore及公开startup prepare；显式创建/intro来源、当前growth/equipment/resource policies和资产profile。源1501用公开持久story目录与完整bind；建立private source MapOwner/public(1006,1006,0) target Owner及原NPC key/NpcScene proof。late-story enrollment/接近定位必须明示，不伪造自然走完或正式battle win。
2. 第二族可复用原puzzle公开完成Interface在其已明示late-story fixture上得到active100121；第一族若尚无可合法构造的可信AI8002 battle-settlement凭据，**保留有效正例缺口**，只做独立缺前驱和独立缺active负例，不能将合并失效上下文说成单条件验证。不能INSERT战斗胜利或拿训练/wild替代。
3. 当前已active梦醒读原Start→真实key CCommit→新的policy resolver/冻结结算许可（RawDreamReturnIntent继续false）；按政策normal state0、原maze mask1、精确public目标、source directory+checkpoint验证。用同一request identity做prepare/reserve/freeze/activate与独立world.begin。
4. 最终current-lease调用方BEGIN IMMEDIATE中执行world commit(default exact checkpoint)、任务完成、公开奖励settle、唯一后继与梦醒自有回执；保存公共宠结果身份。在全部native scene/role/XP/pet回复可编码后才commit，发包/地图等待在事务外。人为最后编码失败必须全表回滚；目标内存仍fenced，不能当作已撤销。
5. 成功后按精确发送屏障清源/ready及后续checkpoint。再通过公开角色/资产Interface改变当前EXP、装备/HP或原宠状态，之后paid只读返回**新的当前**结果；比较全表和world成员/位置不变，不重复state1、后继激活、目录分配或场景传送。应采用authorizer/query-only或SQL写跟踪证明没有DML尝试，单有total_changes相等还可能漏相同值UPDATE；勿通过credit_experience(0)取余额。
6. 新lease：先完成独立world recovery并清精确旧Owner状态，再按public当前checkpoint恢复；用当前Owner可信历史operation身份测试paid reader，旧ticket/epoch回调拒绝。提交后发送失败必须恢复public目标且资产不再奖；若后来已有合法新位置/新实例，历史receipt只确认过去，不二次搬家。
7. 两个不同角色/私有实例只允许各自NPC和目录证据；第二宠450按首次固定接收者，之后切换/释放/unknown baseline均不得选新宠或补奖。验证过期无损失/冷却、重开对白新票据、已付相同wire不生成新授权。

## 本批方法、产物与未验证范围

research实际方法：正式policy→公开Interface原实现及私有辅助的调用链→区分只SELECT/条件只读/必写settlement→核两个已有verifier真实caller事务→列最小新增read Seam及fixture序列。codebase-design用于把世界receipt确认留给world storage所属Module，把宠历史读取留给宠奖励Module，任务只持自有不可变回执和当前快照，不复制其他Owner SQL。

以下hash绑定本次读取时的源码版本；本审计不是冻结部署审核。所有Python只作AST静态解析，没有import或执行模块；没有运行所建议fixture/DB/verifier/CG/战斗/客户端或网络，不能把源代码存在或旧verifier的断言当成本次通过。唯一产物本文；未改实现、中央政策、shared或其它文档，未向其它聊天发消息。

| 文件 | SHA256 |
|---|---|
| design/newbie-dream-return-v1.json | fd369d20ba847764eb6436f83819628b52f7f8bc54c743669c708d22edf304f4 |
| evidence/NEWBIE_DREAM_RETURN_DECISION.md | e9f29a133785c2f08b6b8d4da6ef0882092abd8f3b0870bc27735ed73dc1294b |
| ARCHITECTURE.md | 0b98c5d027f33cf99071c2a316b77dbcd6a2a785b6658987209321bbadfc1d7d |
| world_owner.py | 3a893ec87feab966adf4f07f1917779296669f143177cb78da580758c3ef4d5b |
| world_transfer_storage.py | d034f37f3af952a79b3fdac4d4142051b9dfa3b8cd5dcb0a031f01191f9fca4a |
| world_story_instances.py | f8a817fb68aed25df3cfec580fe5731ce9659743aa252bdff538b2d0eb8b6268 |
| task_workflow.py | 2f1b5fbd8951a179c1ef86c01b9f69033e4a2a13575b18baa334dc387c96a218 |
| task_rewards.py | 797d309de3f40ba8056582ab513c817551b0d27a2ad0c5ec1556846e7717d586 |
| task_pet_experience.py | ec0bfd7710090b245c713541573b3e60a21e69a78806ab1dd988b4ee0f2c395b |
| task_growth_resources.py | 1198154c07d1ee8906274f1e91ee9b2ad573bc636ad80dc951f36b06f9fb38c0 |
| progression.py | 215b84b2a4b3222cf087c347c8b0f3b90bc13ee5b5066d3afe78d57cde4d9a13 |
| role_growth.py | cce96716ef80b1c38979592ff82558e72ac7be80c7979c42714c2fd4c553b224 |
| role_attribute_storage.py | 5fee6d62e1aff2a565ba8b8fa0d5c7f63fadf77a9ec1c34510a7a090bb5dabe1 |
| role_resource_storage.py | 8393d9567416a531fd865748464423fde25ea9349e387ca500436f98fdb5c64b |
| role_equipment_storage.py | f76faf99cc3eb13998ac1afd02f004582c56a8dbc60b59b6957c2b3d00485e33 |
| role_attribute_protocol.py | 6693945991973a03e8609c5edca72e67399b1bf722faeb17e09828c506551edd |
| currency.py | 6d637c2736baafd9ac1092a07edb88b4bd405d482716a432295bcac271929e36 |
| inventory.py | 45530ad6c01e52355e09ff9e1ca7887202ff94a68b3a04f54d9842054a06609c |
| task_persistence.py | 903686403c4ee87e03da6be412ecb07208e4726a7cce43a073d0bcf3610c69f7 |
| task_prologue_return_dialogue.py | c4de1011fd87760253091c30e080748eeb6fbbf71d88f752f368d589fa9935f8 |
| task_cart_transfer.py | c05ac679523fbd203fcef7a179530be8ce368cda3911414ba13c6cb0f874ab44 |
| task_prologue_touch.py | e7d6a0629c874f494a3afb38a5f881d7d6a772fcb1e1d142f90fa5629d0def2a |
| verify_task_cart_transfer.py | 6b0fcf9223cff04d9b6a3b9ffd2bef829f43893d4a3c790841975b07c6fe46a4 |
| verify_task_prologue_touch.py | c4615c328d72016dd71eeedb0276630c126775784d6dfe80eabd27e8c8f83f07 |
| accounts.py | 2f9022a4b40aaecffbd2bb57491f8f1678980e4a6405f8fc28e78d0099db34ff |
