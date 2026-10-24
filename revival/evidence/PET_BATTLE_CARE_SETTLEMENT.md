# 普通战斗宠物养护结算与累计场次

2026-10-23。所属领域与真实调用方事务已实现并离线验证，未接共享实际宠物战斗、未发布、未执行真实战斗或操作客户端。神兽分类和免损详见PET_IMMORTALITY_INTEGRATION；本批继续其后的普通参与、死亡、低等级、擂台及累计计数，不代表召唤兽全量已完成。

## 来源及设计

原bookanswer36002/36003：普通参战每场寿命1，每3场忠诚1，死亡寿命50/忠诚20，等级≤30不消耗忠诚，神兽忠诚/寿命永不减少，均为client_verified文字。后台research已重新HTTP 200读取官方PC原页133548/133541并记录正文摘要：死亡场不计普通参战/忠诚场次，擂台不计损耗，战斗中召回仍计参战。这些为guide_supported；死亡一场总扣50而非51，且不额外推进每三场计数。官方≤20死亡免忠诚与原包冲突，遵循原包≤30的完整忠诚豁免，不豁免普通寿命。

原计数器余数存储/清零未证。政策唯一来源design/pet-battle-care-v1.json：新宠明确mod3=0；死亡、≤30、擂台及未实际参与保留此前余数，不推进或清零，标designed。kind2完全免损；kind3仍独立、普通fallback为designed。可信死亡次数death_count>0按每次50/20乘数计费并floor0，不另扣参战1或推进计数；多次死亡线性合并是inferred，不把最终HP0/胜负推成死亡次数。

## 角色与战斗Owner的Interface

启动Inventory.prepare增加只读battle_care_rules及两表迁移；全新grant_pet在同一奖励事务明确初始化计数0。未知旧宠计数保持未知；`initialize_pet_battle_care_counter(db,pet_id,mod3)`仅用于可信一次完整导入0/1/2，已有不可重置。它不改宠物成长、血脉、寿命、忠诚或HP。`pet_battle_care_counter(db,pet_id)`在当前拥有宠事务返回冻结BattleCareCounter(version,mod3)，无新连接或文件读取。

入场时角色Owner读取冻结PetState及上述counter，和战斗参与快照一起固定template/care_version/growth_version/counter_version。可信最终结果构造冻结`pet_battle_care.BattleCareEvent(settlement_id,pet_id,template_id,expected_care_version,expected_growth_version,expected_counter_version,mode='ordinary',participated=True,death_count=0)`；mode仅ordinary或sparring，death_count严格非负int，participated严格bool。其余PK/决斗/特殊战斗模式明确拒绝，不靠客户端标志解释为擂台。

在角色Owner现有同一epoch事务调用`Inventory.settle_pet_battle_care(db,event,epoch)`，取得冻结BattleCareReceipt。**必须在修改入场growth/resources或兑现本场宠物XP之前调用**，否则原成长版本/入场等级不再匹配。它校验当前租约、归属、未放生、原模板、care/growth/counter三个版本；实际参与还须已知HP>0及模板感知care gate。战斗Owner必须提供真实参与/擂台/死亡次数；召回后仍participated=True，不用最终fighting状态替代参战历史。该Interface没有客户端opcode，不允许用客户端报死亡或HP赋值触发费用。

普通>30存活参战扣寿命1、mod3推进；第三场再扣忠诚1并回0。≤30只扣寿命，死亡按次数扣寿命但免忠诚；>30死亡按次数20忠诚/50寿命，计数不推进。擂台、未参与、kind2免扣且计数不变，只保存唯一结算凭据；无实际资产变化不制造care/counter/inventory版本。无随机不服从逻辑；忠诚<60指令行为由战斗模块另恢复。

同事务写care、counter、领域/养护子凭据和inventory_revision。失败全部回滚，没有内部commit/新连接/发送，也不治疗、不写HP、不替代战斗资源结算。根人物资源仍使用唯一profile载体；外层必须将当前资产快照交现有synchronize_inventory_resource_source，fresh使用replayed=False，paid使用True严格读取，最后编码当前原生消息与本场资源/奖励一起提交。

回执是历史ack，含entry level、care/counter before/after和replayed。重试必须使用原捕获event，不用当前版本重构同键；载荷冲突拒绝。已付不再扣损或推进计数，读历史前不要求当前版本仍等于入场版本；重登、后来喂养/受伤均保持当前状态。同角色已软放生宠物的旧回执仍可读，不复活、重建或重新扣损；放生后鲜结算拒绝。当前刷新须另读当前PetState（已放生则移除），不序列化receipt.care_after冒充现在。回执指纹固定battle/care/kind/growth/blood政策，不兼容升级需显式协调。

旧通用change_pet_care('defeat',1)仍保留原普通损失及神兽免损兼容，用于已有受信调用与旧回执；它没有入场等级/场次/模式，**完整战斗接线应使用本Interface，不能直接重复调用defeat再另算参与**。内部battle_loss tuple不是新的客户端入口。

## 已验证与剩余

verify_pet_battle_settlement通过：31级三场5997/99、死亡50非51且20忠诚、mod2死亡后保留/下场扣1忠诚；0/30级包括死亡均忠诚不减且不累加低级场数；擂台/未参与/神兽不改版本；可信两次死亡100/40；未知旧counter拒绝后完整导入不可重置；寿命49、HP0、他人宠、版本/模板/载荷/bool/未知模式拒绝；实际SQL四保存点及外层后续奖励失败整体回滚，同事件恢复一次；opaque当前租约/过期拒绝/重开；无热文件/嵌套连接。后来98忠诚/5944寿命/7HP保留，paid SQL禁止写入仍通过，原Pet decoder读取当前值。

verify_inventory_resource_hook新增实际根source集成：真实31级宠物care、counter及根source在一事务保存，source CAS后故障全部回滚，同原event重试fresh一次；paid再用SQL禁止任何写入的Inventory及根strict True成功，人物70/40/version0不变。现有食品/血脉/命令/NPC回归按本批json记录复跑。

方法：沿同一角色Inventory事务/冻结消息Seam使用tdd，从缺少普通三场计费的红信号开始实现并逐条扩展；codebase-design将计数、死亡替代、政策和凭据放入pet_battle_care，角色只持有冻结事件/回执；research追原包及官方PC并明确冲突与补全。产物为本交单、单一policy、领域模块、验证与batch记录。

未验：实际战斗Owner捕获/死亡次数/资源和奖励统一调用、低忠诚不服从、特殊PK政策、完整宠物技能/召唤/还童与进阶、原UI、发布和容量；SQLite临时事务通过不等于商业存储并发验收。后续继续还童/进阶及剩余装备道具，实际战斗接线由原始集成窗口统一修改shared。
