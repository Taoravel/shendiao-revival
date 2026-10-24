# 剧情私有地图：当前公开能力与共享接线缺口

最新源码复核：主集成已在shared增加runtime_map_address/RoleOwner.map_address、目录启动准备与私有load；本窗口未改这些共享代码。下面原共享缺口清单是此前调查，不代表当前仍全部缺失；完整私有自然入场以主集成纵切为准。现自然血手印红的精确几何阻碍见WORLD_BLOODMARK_APPROACH_BLOCKER，尚未用改坐标/半径绕过。

生命周期最终交付见WORLD_STORY_LIFECYCLE_HANDOFF及WORLD_STORY_LIFECYCLE_REVIEW，v2固定manifest给完整哈希。启动Rules本轮追加主策划64/64预算，目录库当前为f8a817…；以下868853…及初版审查仍是其固定历史版本，不冒充预算增补后的哈希。

生命周期独立实现新增 `WORLD_STORY_LIFECYCLE_HANDOFF.md`：128加载槽（含inflight）、操作pin、60秒实际MapOwner空闲退休、发送屏障ticket及旧对象enqueue围栏；18组和32次并发反馈通过，默认不启用旧Adapter回收。共享完整地址、全部外部邮箱/pin/delivery hooks和动态实体持久化仍须统一接线，不等于自然梦境入场已完成。

2026-10-23。嘉兴100106→1501梦境合同。**当前已新增公开持久分配/读取Interface，接入必须先读 `WORLD_STORY_INSTANCE_DIRECTORY_HANDOFF.md`。** 主策划已发布 `NEWBIE_BLOODMARK_INSTANCE_DECISION.md` 及story-instance/newbie-bloodmark两政策；下面原有能力/缺口调查保留为接线范围，政策待定表述以该正式决定为准。共享完整地址入场/重登仍未验收；`world_instance_positions` 本身仍只是可选位置归属，不充当目录。

本批目录交付已固定3文件diff/hash，两轴静态审查各0发现，见 `WORLD_STORY_INSTANCE_DIRECTORY_REVIEW.md`；主策划另独立运行同12组通过。公开库哈希 `868853fd6259c15a5c79aed98b96560985f020654b0aeaf0140e6892eae9255d`，本窗口未改shared或部署；后续集成按目录交单的外层角色事务/异步地图/再核完整地址顺序执行。

## 可以直接复用的世界Interface

|能力|实际公开入口|准确范围|
|---|---|---|
|持久剧情身份|`world_story_instances.allocate_story_instance_transaction` / `load_story_instance_transaction`|真实当前角色事务、原创建/章节/路线冻结；稳定私有地址、实际唯一约束及8次碰撞预算。目录不是任务资格/进入许可；12组新检查及顺序见目录交单|
|创建独立地图执行状态|`world_owner.MapOwner(MapAddress(map_id,instance_id,partition_id), catalog, capacity=...,transfer_capacity=...,mailbox_capacity=...,maze=...)`|接受调用方已经分配的完整地址；不分配ID、不持久登记或授权剧情所有者|
|受信任务提议|`prepare_transfer(expected_location,target_position,request_id=...,deadline_ms=...,now_ms=...)`|源Owner重新核完整当前Location/epoch/version/active、边界及唯一挂起offer；只允许不同map_id目标，不移动、不冻结、不完成任务|
|选择精确目标|目标Owner `reserve(offer,now_ms)`|Reservation绑定该Owner完整MapAddress；选择哪个目标实例由可信运行时决定，不由target_position单独决定|
|内存交接|源freeze→目标activate→持久提交后源finalize→目标ready|所有证明带完整源/目标地址；可用view配套方法；不自动访问SQL/网络或创建实例|
|持久原子目标|`commit_transfer_transaction(db,account_id,role_id,epoch,receipt)`|caller当前角色事务；任务/奖励可由caller在同事务组合；已显式绑定实例时同时保存完整目标地址/进入凭据/位置/journal|
|采用/读取实例存档|`bind_map_instance_transaction` / `load_map_instance_transaction`|精确可信active检查点显式采用；legacy返回None不猜默认实例。合同见WORLD_INSTANCE_PERSISTENCE_HANDOFF|
|同Runtime故障恢复|稳定 `prepare_transfer_recovery_transaction` → 各精确Owner inspect/retire|DB裁定先提交、精确清旧epoch，再新租约加载/加入；原三项Interface稳定，view变体另见WORLD_MAP_VIEW_HANDOFF|

1006→1501属于不同模板，可复用prepare_transfer。不需要为了它放开同map脚本传送；同模板换实例有受控底层交接验证，但不代表原住宅/1627或通用脚本入口已支持。

范围补充已fresh重读原CMainMissionInfo十行：100106..100906（每次+100）及103206都保留RewardMapJumpType3、目标1501、原63/79、当前AIInfoAIID0。不能把十门派任务理解为十人物一对一或把3直接解释为已存在的私有实例分配协议。角色＋该chapter稳定dream身份为主策划拟定政策，本Module没有先行发布；坐标乘16及唯一后继/后续AI由所属任务裁定/交单控制。

## 当前共享源码事实

本批重新读取game_runtime.py：

- `GameRuntime.map(instance)`仍是 `key=(instance,0)`，构造共享Adapter `MapOwner(instance,...)`。Adapter内部仍构造 `MapAddress(instance,instance,0)`，用instance当资源模板找catalog/NPC。直接传私有instance编号不能正确选1501资源。
- `registered_map(address)`仅查已有 `(address.instance_id,address.partition_id)`，并比较完整address。它不创建/注册目标，也不是私有实例分配器。
- RoleOwner加载位置仍从 `(map_id,x,y,version)`构造Position并调用 `map(pos[0])`；当前没有生产调用load/bind。普通移动/NPC/ready/close/传送路由仍有按 `position.value[0]` 或 `address.map_id` 选图的路径。只改map factory不足以保证完整归属。
- 因此不能把当前独立world实例验证和已接的普通传送/新租约恢复，升级为“私有梦境同Runtime或重登已恢复”。根窗口纠正的“map形参名不是完整地址合同”成立。

共享接线要让角色持有冻结完整地址/Location，并覆盖load/join、移动、NPC交互、源/目标handoff、ready、scene_sent、close及恢复后的新join。资源只按address.map_id选择，地图执行和目录按完整地址或保证唯一的instance/partition键选择。调用方需在每次await后继续核epoch/连接generation。

## 1501私有剧情还缺的状态与决定

1. **持久实例目录及分配幂等。** 由策划明确“角色＋哪一次剧情实例/章节revision”唯一键、MapAddress生成、分区路由、capacity和创建/恢复/回收时机。重试相同剧情入场须找到同一实例；role_id直接用作通用instance_id可能与公开地图或其他剧情实例冲突，不在世界Module里猜命名空间。
2. **进入权限及可信目的。** 任务Module提供当前100106合法完成/后续的冻结授权、可信目标坐标与稳定请求键；运行时先确定并固定目标地址再reserve。TransferOffer仅有target_position，直到Reservation/receipt才含完整目标地址；当前prepared journal不能独立恢复尚未冻结且内存已丢的目标实例选择，需要上述持久目录/分配凭据。
3. **已绑定源的迁移及提交。** 源完整地址须从真实Owner精确检查点显式采用，不能在向私有图提交后仍保持legacy未知。之后caller事务将任务/奖励/位置/实例决定共同提交；不先独立commit世界再完成任务。
4. **重登。** 新租约事务先稳定恢复裁定，再load完整实例快照，核位置/版本一致；提交后退役旧地址成员，再按持久目录找原实例或重建同一身份。缺目录/归属拒绝，不回退公开1501或新造另一实例。world_instance_positions只保存角色当前地址，未保存NPC/怪物/故事实体状态。
5. **客户端身份与状态。** 原Scene报文的q64会存Scene+30/+34，低位取资源配置；高位与服务器instance_id的编码未证。不要擅自把map_id与instance_id移位拼成原q64。服务器完整地址隔离与原线字段分别设计；不能用Actor电影临时Setmap改权威归属。

上述合同的身份分配/读取现由 `world_story_instances` 两个公开事务函数承担；共享完整地址选择/加载、实例GC及完整任务纵切仍需接线。主策划已给定剧情身份/预算政策，世界按其实现；100106→1501仍不授权触发AI8001或假胜利。

## 已有验证路径及未覆盖范围

- `verify_world_instance_persistence.py` / `world-instance-persistence-verification.json`：12组真实临时DB及MapOwner，包括完整地址采用、晚期全回滚、错源围栏、同模板不同实例保存、新租约与旧回执不倒退。不是分配器/shared接线检查。
- `verify_world_transfer_transaction.py` / `world-transfer-transaction-verification.json`：caller原子提交、晚期回滚、完整offer/deadline及回执重放九组。
- `verify_world_transfer_recovery.py` / `world-transfer-recovery-verification.json`：未提交、已提交、取消后继续走三支，容量1下精确退休、旧epoch围栏。
- WORLD_TRANSFER_RECOVERY_HANDOFF末节及根两故障报告：已接普通图同Runtime SQL失败/提交后清源失败恢复。它们当时不是私有目录及完整地址持久加载。
- `verify_world_resource_handoffs.py`：302资源MapOwner/view、同模板两实例及212普通有向跨图；无剧情分配或全图GUI。

后续最低验证应覆盖两个角色各获不同1501实例、同任务重试同实例、不同实例NPC/怪物状态不串、晚期SQL失败回源、commit后finalize失败恢复原私有地址、后续移动重登保留原实例及点、实例冷重建、完成后明确退出/回收。这里只交可判定条件，没有为尚无实现的目录编造通过报告。

方法：codebase-design按角色/任务/目录/地图/SQL权威分工核公开Seam；diagnosing-bugs区分已观察的模板路由与真正完整地址行为；writing-for-agents把可直接复用、必补状态、失败及未覆盖范围共置。此页为当前实查交单，不宣称已实现私有剧情地图或已部署。
