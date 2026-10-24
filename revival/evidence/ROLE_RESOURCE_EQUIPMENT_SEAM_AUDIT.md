# 人物资源与六槽装备接入Seam审计

2026-10-23；审计当前工作源码，非8724已部署版本。沿research与codebase-design，已读根AGENTS、ARCHITECTURE、DESIGN_AUTHORITY及现属性、装备、药品、NPC、成长/显示消费者。本轮只写本文，不改生产/shared/政策，不读真实库、不运行GUI/服务/战斗或大回归。行号对应本次读取快照，多窗口后续改动需重新对照。

## 关键结论

当前只有一份已实现的人物持久资源：`role_attribute_snapshots.vitals`中的VitalState。问题是多个公开Interface假定它的maxHP/maxMP恒等于**裸身成长属性**上限。师承武器只改攻击/封印，未触及这个假定；六槽衣服/腰带/护腕改变上限后，仅扩装备加算会导致药品/客栈用错上限、CAS拒绝、编码拒绝，或后续成长把上限改回裸身值。

应保留**一份角色权威资源状态**，把裸身成长属性、当前装备最终投影与资源状态的职责分开。可以复用现vitals载体并迁移其契约；若另建资源表，旧vitals必须一次性转为只读兼容或退出写入，不能永久双写两本HP/MP账。本文提供迁移顺序与待裁定政策选项，不代主策划发布数值规则。

## 当前权威数据、读写与CAS

| 源码 / 函数与行 | 当前行为 | 六槽上限变化的影响 |
|---|---|---|
| [item_effects.py:10](/D:/神雕侠侣/revival/item_effects.py:10) `VitalState` | 冻结target_id/version/hp/max_hp/mp/max_mp；构造约束0≤当前≤上限、maxHP>0 | **没有伤势上限字段**；并非两本资源，只是一个数据值类型。不能让裸身和装备各持久一份当前HP |
| [role_attribute_storage.py:18](/D:/神雕侠侣/revival/role_attribute_storage.py:18) `prepare_attribute_storage` | baseline独立表；snapshot表同一行保存attributes与vitals两份JSON | attributes当前是裸身成长结果，vitals唯一HP/MP权威却隐含裸身caps |
| 同文件:45 `read_attribute_snapshot` | 校验当前事务/账号/有效epoch；读JSON；校验roles.level和growth.revision与attrs一致 | 此函数本身**没有**检查vitals.max==attrs.max；不代表后续消费者接受不等。把装备caps写进去后，会先读出混合快照，再在下表公开Interface失败 |
| 同文件:57 `initialize_attribute_baseline` | 真实基线只初始化一次；若给定vitals caps与derive后的裸身caps不同，:71调用growth_vitals | 不能拿它作“装备总上限初始化”；会按裸身caps重调资源。已有基线重试返回当前，不允许重设 |
| 同文件:85 `update_role_vitals` | :91重读当前；完整`current.vitals == before`；after.version=before.version+1、同角色；:94要求after.max==**current.attributes裸身max**，:96写唯一vitals | 若after带装备caps，明确报`Vital snapshot version or maximum mismatch`。只把after.max改回裸身会使药品使用错误上限 |
| 同文件:101 `sync_growth_attributes` | derive当前裸身attrs；:115读最新vitals；:117只要caps不等就growth_vitals，随后:118同事务写attrs和vitals | 将装备总caps存入vitals却不改此处，会在升级/加点或成长写入时降回裸身caps，即使装备没变 |
| [role_attributes.py:145](/D:/神雕侠侣/revival/role_attributes.py:145) `growth_vitals` | HP存活时加max差、至少1并裁剪；死亡保持0；MP加max差后裁剪，version+1 | 是现**成长**设计，不是通用装备变化政策；直接用于穿脱/耐久恢复可能产生免费资源增加与缺失量截断 |

CAS强度需准确表述：这里是**调用方角色围栏事务内的应用层完整before比较+version推进**，SQL UPDATE没有额外`WHERE version=?`或rowcount检查。当前账号租约、角色单Owner和调用方SQLite写事务共同提供执行条件；迁移商业持久化Adapter时应把相同语义落为真实条件更新/事务冲突处理，而非加全局世界锁。

成长侧入口为[role_growth.py:182](/D:/神雕侠侣/revival/role_growth.py:182) `_write_growth`：比较当前GrowthState后，写角色level/经验/成长revision，:191调用sync_growth_attributes，全部依赖同一个外层事务。资源版本不是growth.revision的别名；用药可以只推进资源版本，加点可以只改属性/投影而不改当前资源，不能让其中一种版本替代其它来源。

## 已有装备投影和编码的硬耦合

| 源码 / 位置 | 现有契约与具体失败点 |
|---|---|
| [role_equipment.py:113](/D:/神雕侠侣/revival/role_equipment.py:113) `project_equipment` | 只接精确type为RoleAttributeSnapshot的裸身快照；:125..130要求vitals caps==裸身attrs caps。若资源改成装备总caps，输入在此拒绝。当前投影只替换外伤/内伤并原样返回vitals，恰因师承三项不改caps才安全 |
| [role_equipment_storage.py:80](/D:/神雕侠侣/revival/role_equipment_storage.py:80) `current_equipment_projection` | 校验角色/租约、显式封印基线、inventory_revision；:97读裸身属性快照，再投影。没有持久第二份最终属性账，本迁移应保持这个优点 |
| [role_attribute_protocol.py:51](/D:/神雕侠侣/revival/role_attribute_protocol.py:51) `_snapshot` | 校验snapshot.vitals caps==snapshot.attributes caps；最终attrs更新而vitals不更新，编码在此拒绝。该检查在**最终展示快照**仍有价值，应移除的是裸身读取对总资源的相等假设，而非无条件删掉此一致性检查 |
| 同文件:75 `growth_refresh` | 发送0xc32c8，当前HP/MP用vitals，上限140/150用attrs；:83..84将640写为attrs.hp_max | 已混合取值但有上述相等门禁；伤势640是“无伤势profile”设计值，不是已持久的独立伤势权威 |
| 同文件:111 `role_detail_vitals` | 返回`(v.hp,a.hp_max,a.hp_max,v.mp,a.mp_max)` | 入场伤势cap/maxHP重复当前最终maxHP；迁移若支持伤势，应改为显式cap，不能继续从裸身或当前HP猜 |
| 同文件:92 `role_detail_profile` | 32i前五槽来自上述helper，其他已知属性/五维/潜能也取同一次profile | 保留同一最终投影供入场/动态刷新，不能各自重新计算不同装备版本 |
| [world_protocol.py:15](/D:/神雕侠侣/revival/world_protocol.py:15) `world_snapshot` | 显式growth/profile路径→role_detail_profile；无profile另走旧100兼容值 | 未初始化旧角色仍是兼容路径，不得借迁移把旧100写成持久真实资源。intro判别字段独立，不混入资源迁移 |
| [item_effect_protocol.py:13](/D:/神雕侠侣/revival/item_effect_protocol.py:13) `role_resource_refresh` | 普通0xc32c8仅发60HP/70MP，signed32且float32精确 | 药品仅改变当前值时可继续用；装备同时改变caps必须发140/150及适用640，不能靠这个两项包让客户端获知新上限 |

原生字段事实已在ROLE_GROWTH_UI_RESEARCH / EQUIPMENT_ROLE_ATTRIBUTE_RESEARCH闭合，本轮未重复反汇编：60/70为当前值、140/150为总上限、640为当前生命上限（伤势cap），普通map绝对覆盖；RoleDetail前五依次HP/伤势cap/maxHP/MP/maxMP。保持普通世界与battle初始化包区分。

## 真实药品、NPC与成长消费者

**人物药品**：[game_runtime.py:576](/D:/神雕侠侣/revival/game_runtime.py:576)解析CUseItem并核对目标为本角色，:585交Inventory.receive_role_consumable；战斗中世界玩法门禁在:406..410。实际链为：

`Inventory.receive_role_consumable :585 → use_role_consumable :558 → read_attribute_snapshot :572 → use_consumable :535 → Consumables.apply :40 → update_role_vitals :580`。

Consumables.apply按传入target.maxHP/maxMP封顶，不读裸身属性或装备；因此纯效果函数可以继续消费统一权威资源，但当前调用方给的是裸身绑定snapshot.vitals。外层:602重读当前、:605编码普通资源刷新，背包扣物与资源写/领域凭据同事务。重放:575..578返回历史确认而**不改当前vitals**，响应仍重读当前；该正确行为应保持，不能让装备迁移后从历史药品回执恢复旧caps/HP。

**客栈恢复**：[npc_recovery.py:100](/D:/神雕侠侣/revival/npc_recovery.py:100) `_rest` :101读同一属性snapshot，检查活人/未满及当前策略，:115调用update_role_vitals，把当前HP/MP恢复到该vitals中的max。扣体力/可能扣现金、资源与npc_recovery_receipts在`settle :121`同一调用方事务；:168重读当前资源作回复。若caps仍裸身，客栈会按裸身判已满/只恢复裸身上限；若改caps但未迁移CAS则可能连同付费一起回滚。NPC“付费休息到当前上限”是明确资源操作，与穿装备/修耐久必须分因。

**自动/手动成长**：[role_growth_actions.py:22](/D:/神雕侠侣/revival/role_growth_actions.py:22)要求显式属性profile；手动升级/加点最终`_result :31`重新读裸身并先调用growth_refresh。TaskWorkflow `_settle_completion`[task_workflow.py:55](/D:/神雕侠侣/revival/task_workflow.py:55)在奖励后:60..61同样先编码裸身snapshot。

外层[runtime_storage.py:288](/D:/神雕侠侣/revival/runtime_storage.py:288) manual_level / :302 allocate_potential之后用`_role_profile_transaction :336`替换为当前装备最终map；任务完成经`_project_completion :362`替换。**不能只改外层最终替换**：内层裸身growth_refresh会先在_snapshot相等门禁失败，事务到不了外层。因此迁移需要内层停止把裸身+权威资源拼成可编码最终profile，或让内外统一通过当前资源/最终投影Interface；不要先允许失败编码再期待覆盖。

**登录/初入图**：runtime_storage.role_load_profile :316与_role_profile_transaction :336只读已初始化基线并计算当前最终快照，不应在此执行caps迁移/治疗。GameRuntime首次ACK[game_runtime.py:316](/D:/神雕侠侣/revival/game_runtime.py:316)再次读取profile，不用较早登录资源缓存；继续保留。读取/重登/回执重放不应推进资源版本或改变HP/MP。

## 穿脱、修理、磨损与战斗接缝

穿脱在[runtime_storage.py:421](/D:/神雕侠侣/revival/runtime_storage.py:421) `equip_role`，同事务调用Inventory装备/卸装公开Interface及任务装备事实，再`_committed_master :409`重读当前profile作最终消息。当前只验证投影并编码，没有通用“装备caps变化→唯一资源状态”写入步骤。

NPC修理经[runtime_storage.py:442](/D:/神雕侠侣/revival/runtime_storage.py:442)→`npc_repairs.repair`；后者[npc_repairs.py:79](/D:/神雕侠侣/revival/npc_repairs.py:79)在同事务使用precommit(db,current_inventory,current_snapshot)，调用equipment_projection_messages :450。这是已有真实Seam，扩caps可在事务内计算/写资源/编码，任一错误回滚修理费、耐久、凭据；不能等资产提交后另开事务“补HP”。该hook也明确可供可信wear调用，但本轮未找到当前战斗结算实际穿透到这个hook的完整共享入口，不声称磨损已自然接入。

战斗资源必须单列：TrainingBattle `_resources`[training_battle.py:234](/D:/神雕侠侣/revival/training_battle.py:234)返回CombatResources角色HP/MP/max及source_version；战斗内_vitals :225用的是battle初始化属性包，**不等于持久化普通世界资源**。当前GameRuntime.ScheduledBattle[game_runtime.py:161](/D:/神雕侠侣/revival/game_runtime.py:161)创建Participant未传stats，finish_battle :715只清Owner并记录训练结束，没有调用update_role_vitals。wild_rewards.settle_wild_reward :244注释要求宿主同事务资源结算，实际此Module只见宠物资源写与角色奖励；task_battle的Participant/Finished校验也不代替角色资源CAS。故当前共享入口不能宣称真实人物战后资源已按装备最终caps落库。

未来真实战斗接入：入场用同一次最终属性/资源快照并保存资源版本与投影来源（成长、装备、基线等revision）；角色Owner接收战斗Owner唯一terminal结果，校验入场来源、当前租约/冲突政策后写统一资源，再结算成长/磨损/奖励并重新投影。战斗快照是有来源的临时状态，不能成为与世界资源并行可写的第二本持久账。装备/药品在战斗中是否允许及状态冲突处理沿现Owner门禁明确，不发明全服执行器。

## 最小可实施迁移顺序

1. **先固定数据/版本契约**。裸身属性保留现baseline+growth_revision；当前最终投影由裸身+当前装备+显式封印基线重算，不持久增量总值账。唯一资源记录含当前HP/MP、资源version及适用伤势cap；caps可继续保存为该次最终投影的缓存，但必须记录/校验其来源指纹，不等同裸身caps。新资源Interface明确读、CAS、上限变更计划、提交后快照；沿角色caller事务/epoch，不自行开连接或发包。
2. **显式profile版本迁移，一次转交权威**。新角色创建来源采用新资源契约；旧显式裸身profile必须在同一角色事务读取真实现HP/MP/version、当前装备/条件及现基线，写迁移凭据和新版本。若沿用现vitals JSON，则改变其语义并升级版本，不新建可独立治疗的资源副本。若换表则关闭旧写入口，兼容reader只委托新权威。未知旧角色无来源、不支持装备或非法资源明确等待核对，不能按100/满血或等级补造。
3. **拆开裸身更新与资源过渡**。sync_growth_attributes只产生/写裸身结果，不直接把权威caps重设为裸身；同一外层成长事务再用当前装备形成最终caps，以明确的“成长原因”政策执行一次资源过渡。initialize_attribute_baseline只初始化裸身属性/明确创建资源，不再接受装备caps后偷偷按裸身修正。project_equipment不再要求权威资源caps==裸身caps；最终输出必须与已提交资源caps一致。
4. **先迁移全部读写者，再开六槽**。药品和NPC客栈读新唯一资源Interface；所有写入由它做完整before/resource_version/来源caps CAS。role_growth_actions与TaskWorkflow不提前编码混合裸身快照，统一从最终profile编码。登录/ACK、任务、加点、升级、道具回复均重读当前，不拿旧receipt覆盖。
5. **将装备/穿脱/耐久阈值/修理的caps计划纳入现事务**。先取得before最终投影/资源，在资产改变后取after装备快照，计算after最终caps并应用原因限定政策；资源写、资产变更、任务装备事实、费用与幂等凭据同事务成功。precommit编码普通完整map/RoleDetail所需字段，提交后由目标连接投递。重放、只读刷新、未知提交结果恢复不再执行资源调整。只变攻击等、caps/资源均未变时无需伪造资源version+1。
6. **最后放开受支持六槽并做小而有意义的验收**。穿脱/替换、耐久降0/修复、升级同时改变caps、药品/客栈按最终上限、重连、同请求重放、过期CAS、失败回滚各一组；确认所有回复来自当前同一最终快照。真实战斗资源写回另按该Interface接入，本轮不提前称完成。不要复制一套NPC/战斗各自资源表，亦不对全服加世界锁。

上述是迁移建议，方法中的Module/Interface/Adapter/Seam用于集中复杂度与避免跨调用者散布裸身/装备caps判断，不授权本报告更改任何运行策略。

## 上限变化政策选项：留给主策划决定

穿装备、卸装、耐久降0/修复的防免费回血候选是**当前绝对HP/MP不增加，上限下降仅裁剪，死亡保持0**；它使加上限或修复耐久本身不治疗。代价是脱装可能永久损失超出新上限的当前资源，重新穿回也不返还。这是可审查的设计选项，非本报告发布的政策，也非原版事实。

另一种“保持缺失量/保持比例”会在上限上升时增加当前值；必须明确它是否属于允许的治疗收益，并审查穿脱/损坏/修理循环。**不能直接复用现growth_vitals的存活至少1规则**：如带装备10/200卸至裸身100，该函数会保留1；再升回200会变101，已丢失的缺失量被截断。这个纯代码算例说明原因分流必要，不是运行玩法测试或对原服行为的断言。

成长获得上限、付费客栈、药品、死亡/复活应分别给明确原因政策；装备变化不授权复活。伤势cap需要决定是否继续显式“无伤势=maxHP”profile、还是引入真正权威cap；若引入需保持`0≤HP≤伤势cap≤maxHP`并定义变化规则，不能以当前HP充当伤势上限。VitalState当前缺该字段，不能仅在编码填一个值声称伤势已实现。

## 方法、验证与未验证

research实际从当前唯一SQL资源写表反查所有直接writer/reader，再沿真实GameRuntime→Inventory/NPC/成长→编码链核对；排除runtime/deployments历史副本、verify/research脚本与宠物独立状态，以免将旧版本/测试路径当当前角色权威。codebase-design实际决定是复用一个资源Module和既有角色事务Seam，拆除裸身caps耦合，而不是放松所有相等检查或引入双账本。

静态定位的直接角色资源writer为initialize_attribute_baseline、sync_growth_attributes、update_role_vitals；直接业务写者为药品与客栈，成长经_write_growth触发。未在已查当前共享源码中发现另一个持久角色HP/MP表；战斗临时Fighter/CombatResources和兼容100不是第二份已实现权威资源。没有运行数据库、codec或回归；以上风险是从条件/写入次序推导，未伪称已复现在线故障。

取样文件SHA-256前16位用于识别后续漂移：role_attribute_storage `070566d66d670451`，role_attributes `129aec3497c5f8b5`，role_equipment `21a64087976a281e`，role_equipment_storage `9ad51ab32c086232`，inventory `1cac82fe4c927faf`，npc_recovery `aa7bfed51b379cb9`，role_attribute_protocol `964e774d8cbf3a71`，runtime_storage `052ef36f4020be80`，game_runtime `ce530c413da3d095`。本轮只读这些源码/既有原生证据并写本文；未验证新schema迁移、六槽真实显示、完整战斗结算、未知旧profile、原服上限调整算法或8724现场状态。
