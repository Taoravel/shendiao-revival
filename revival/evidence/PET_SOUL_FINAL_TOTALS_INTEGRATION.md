# 元魂最终属性与唯一宠物资源：实际候选 Interface

2026-10-24；完整目标active。已在真实临时库组合元魂资产控制器、最终宠物属性、原唯一HP/MP、人物root来源和原生编码；默认旧政策不自动采用，未部署/shared/GUI。原数学证据边界见 `PET_SOUL_FINAL_ATTRIBUTE_RESEARCH.md` / `pet-soul-final-attribute-research-batch.json`。本候选不是完整宠物技能、全部成长变更或比例战斗/显示验收。

## 政策、来源与明确设计

唯一政策 `design/pet-soul-totals-v1.json`。原7个flat、2个percentid、5个带正负比例的numid映射与420原数值为client_verified；14类全部保留。以下合计/界限/资源cause为designed：原成长+血脉+石头的canonical属性上只加一遍flat；命中/躲闪以显式基线乘(1+所有原percent之和)，最终只向下取整一次；五个比例在明确基线上精确相加并保留负号，结果必须在−1..1，否则整笔拒绝，不静默裁剪。最终整数非负signed31，HP上限/速度正。模式和界限在loader明确校验，变更须新政策审查。

`PetSoulExtraBasis` 必须有同角色/宠物、政策/source_ref与完整7项：110命中、120躲闪、740外伤修正、1550外穿、1560内穿、1580内伤减免、1590毒伤减免。值为规范化 `(id,numerator,denominator)`，前两项为非负整数，其余为精确有理数；缺一项都拒绝。此版额外基线恒定，不自动按等级、技能或其它体系增长。测试的0是明确known fixture，不能给真实旧档或新角色暗补0。

## 启动与共同读取 Seam

1. 启动加载 `PetSoulTotalsRules.load()`；原 `pet_growth_store.prepare_pet_growth` 统一准备两个新metadata/receipt表（没有第二份HP/MP）；额外启动准备SoulStorage、OrbStorage和Mingwen来源表。配置/DDL不进入角色热路径。
2. 角色所有者在当前epoch的调用方事务，使用原Inventory和已知宠物裸成长/血脉/石头、完整元魂map、完整铭文，调用 `pet_soul_totals_storage.initialize(..., extra, 'explicit_known_pet_soul_extras')`。这是显式逐宠采用，不是赠送铭文/装备或推断历史。它保持当前HP/MP，建立来源/上限metadata并推进库存版本；重复验证原baseline且不重置当前。初始化返回明确baseline，不是历史资源回执。
3. 通过公开dataclass replace把 `InventoryConfig.growth_rules.totals_rules` 设为冻结规则，构造当前角色Inventory。未采用宠物继续按原成长政策读取；已采用宠物的默认旧reader明确拒绝，防止忽略元魂。**共享入口必须先完成所需动作的政策分流，不能只选新读取就允许旧写者。**
4. 共同入口 `pet_growth_store.load_pet` 先用 `read_growth_source` 取得canonical growth/blood/stone，再 `project_loaded` 组合元魂、铭文和7项额外基线。新增 `SoulStorage.read_profile_source`、`Mingwen.read_state_source` 为已有调用方事务内的owned原始来源读者，不回调Inventory快照，不递归；原baseline/provenance/原始值验证集中复用。它们不授权session或写入，原外层 `read` 仍以实际Inventory校验当前epoch。原裸增长read是内部来源，不是最终native/battle属性。

来源stamp包括完整基线、原growth profile/state文本、canonical与final属性、extras、血脉/石头、完整元魂/铭文原始来源。JSON中的分数使用整数对/三元组，保持命令fingerprint可序列化；对外 `.attributes.extras` 可取精确Fraction。它不会因无关背包物变化而伪造宠物资源变更，实际变更仍推进角色库存来源。

## 结算中间态与正式资源读者

源map与资产CAS之间可暂时出现合法pending。内部快照仍能携带真实状态和计算结果，供原Source/Inventory写者完成组合；`PetSoulAttributes.settled=False` 时，普通属性Interface（max_hp等）、ratio读取、原pet_record和battle_loadout所需字段全部拒绝。因此不会把旧HP/MP配新caps当最终结果发出。元魂 `admit` 也在权限查找前检查已知/已结算资源，拒绝冻结pending状态。

正式读取 `read_profile(db, inventory, rules, pet)` 返回冻结 `PetSoulProfile`，严格匹配实际来源/上限和当前唯一HP/MP。来源缺失/未结算读者不自动修复；保存HP/MP的唯一位置仍是 **inventory_pet_growth.state**。新表只存额外基线、source/caps/version和凭据。

`settle_source(db, inventory, rules, before, request_id)` 在同事务map/资产变化后执行；要求原完整metadata和profile/state/blood/stones没有被其它操作改变。读取真实新来源，保持HP/MP绝对值，上限降低则裁剪；死亡0保持0。写入真实资源时完整CAS原state并推进原版本，接着CAS来源metadata、库存版本及新资源凭据。重试验证原冻结before/cause，严格只读当前，不拿历史caps/HP覆盖最新。

`change_resources(..., before, request_id, (hp,mp), cause='medicine'|'combat')` 是可信所有者低层资源写者，不是药品或战斗权限。只接受已结算来源；medicine不减值、不复活，combat只消耗不治疗，值不得超过当前最终caps。调用方仍须把真实药品/战斗资格、扣物/奖励和资源凭据合入同一事务。变化后的paid返回当前，旧epoch已付可在新有效登录确认；旧epoch未付拒绝。

## 与实际元魂资产控制器组合

在受理/新鲜结算前读取并保留 `before=read_profile(...)`，再按已有 `admit/apply` 处理真实珠/移魂符/map/返还。强制同步precommit：fresh调用 `settle_source(before, stable_pet_request_id)`；paid只 `read_profile`；随后用**重新读取的实际Inventory快照**执行已选root人物inventory-source hook。宠物写者会再次推进库存版本，不能使用写前snapshot。源、资产、唯一HP/MP、两种来源、凭据和原生编码任一失败，必须退出整个调用方事务回滚；提交后连接所有者投递。

已采用实例的旧 `change_pet`（包含旧receipt快分支）、aptitude-loss与blood写者明确拒绝走裸caps，避免绕过新政策。XP/加点/血脉/石头/蛋糕/返生等其它source-aware动作尚未全部实现；正式发布前必须逐项完成或拒绝，不能用此候选宣称这些玩法可用。人物资源仍属于root唯一存档，本批验证其70/40及100上限不变。

## 原生与战斗读者的当前范围

`pet_soul_totals_protocol.current_messages` 返回 `PetSoulMessages(profile,messages,ratio_display_pending)`：原完整宠物0xc07d5携当前7项派生整数及HP/MP/caps；0xc32c9只携110/120的最终整数，先验证float32精确可表达，防止整数失真。原两类codec已实际往返。五个Fraction比例不送入已知会截零的通用floatmap；`ratio_display_pending` 明列740/1550/1560/1580/1590，完整精确值仍在profile中。

现有 `battle_loadout.selected_pet` 的实际普通核心快照已验证读取最终HP/caps和核心攻防速度；它不是五比例战斗机制的实现。战斗所有者还需采用完整profile/来源并实现魔法、命中/躲闪、穿透/减免的规则和终局资源结算。比例客户端scale、完整展示/战斗、共享投递、GUI与容量保持未验，不能把编码或普通Fighter复制绿灯扩大到完整玩法。

## 实测与方法

- `verify_pet_soul_projection_sources`：同一来源的无递归owned读者、共享验证、SQL只读/他人拒绝。
- `verify_pet_soul_all_totals`：28原珠首级/14显式映射的独立字面算例，7flat及7比例/percent全覆盖；叠加一次取整命中113、负比例−7/50；缺基线、非规范数、越界拒绝。
- `verify_pet_soul_final_totals`：真实selected共同reader→太阳珠cap157→202、80HP/30MP保持；默认旧reader/旧paid写者、pending原生/药物/新受理拒绝；原Pet及整数mapcodec、实际普通battle核心copy通过。
- `verify_pet_soul_final_asset_cycle`：真实穿戴单扣珠→202不回血、明确低层药物195、摘除原表2符/唯一保真返还→157裁剪；旧paid在SQL禁DML下读当前、不重治/不重扣；死亡0穿戴不复活；7处真实SQL及2处原native编码后异常整笔回滚，旧epoch已付current/未付拒绝，人物资源/现金不变。

TDD沿已授权真实角色事务/共同read/原生和battle snapshot Seam，先无递归读者红→绿，再缺最终source Module红→共同reader与真实资产纵片绿；测试中的错误公开方法名、宠物L0不满足旧battle资格及初级移魂符2张而非1张均按原Interface/原表修正fixture，未放松生产判定。codebase-design把完整投影集中到实际load_pet而非旁路向量；同源原始读者避免循环，pending在最终消费点防护。writing-for-agents将显式采用、原因政策、实际写序和未验范围并列；code-review两轴固定清单结果另存批次。全量目标active，实际后续重点为其余成长/治疗/战斗cause闭合、比例显示/战斗消费者、共享/GUI与所有剩余玩法。
