# 资产领域接线交接

普通固定结果鉴定收费组合前读[EQUIPMENT_IDENTIFICATION_CAS_INTEGRATION](EQUIPMENT_IDENTIFICATION_CAS_INTEGRATION.md)：公开full-source/库存版本CAS、同事务当前tips和独立cash用途已验，NPC真实专用/共同/source凭据组合已独立通过；共享激活与发布/GUI待验，全量active。

灵石/驱灵散及与成长、年糕、血脉、进化、还童交叉接线前读[PET_STONES_INTEGRATION](PET_STONES_INTEGRATION.md)。所属服用/清除、原生独立属性刷新及真实共享驱灵散已验；70052共享固定随机受理、发布/GUI待验，全量active。以下此前灵石状态为历史阶段。

进化最新：普通kind1/3宝宝阶段、稀疏跳终阶、50次追加成长及材料/成长同事务、原生刷新与真实加密Owner共享链路已通过；普通/超级还童现保留已知进化成长。接线、原/设计边界、旧档来源及未验范围见PET_EVOLUTION_INTEGRATION.md。神兽蜕变/灵石/宠装、发布与原GUI提示/动画继续恢复，全量active。

年糕最新：五种实际服用、原预测37,920例、总20次、同事务/原生提示及真实加密Owner共享链路已通过；旧四字段审计升级、耗尽重试、故障回滚和重登已验。接线、浮点差异与设计边界见PET_CAKE_CONSUMABLES_INTEGRATION.md。未发布/GUI，进化、灵石、宠装及剩余装备道具继续恢复，全量active。

普通还童最新：31002/31087完整重置及15固定draw Adapter已实现；接这两类CUseItem前读PET_ORDINARY_RETURN_INTEGRATION.md。原模板uselevel95门槛316例、宝宝保色/血脉、野生转宝宝和13仙兽必带、12写入点回滚及实际root source/只读paid均绿。新增ordinary_return_rules仅启动加载，旧未知不补；共享分流/部署/GUI仍待。较早“普通重置未实现”为历史阶段。

超级还童当前交单：生成/查询/保存/清除、独立候选、稳定扣丹/历史只读、真实root source同事务已实现并离线验证；接31576与C0811/12/13前读PET_SUPER_RETURN_INTEGRATION.md。启动新增cake/return/score规则，新宠年糕显式0、旧未知不补；普通重置/年糕服用/高级评分/shared/GUI继续恢复。下段为此前置历史阶段。

还童前置字段/协议批次：PET_TRAITS_INTEGRATION.md提供已知悟性/野生宝宝存档、末尾PetState.traits和当前原生编码；新宠显式宝宝2/悟性0为designed，旧未知不补、可信完整一次导入。原Wuxing真正读1160，旧rootbone标签已纠正，590不是悟性。超级C0811/12/13单key、S0810九BE32的工厂/codec/UI参数顺序已验证，pet_protocol仅提供严格编码/解码，未新增路由或执行还童。完整随机/扣丹/预览保存和score继续恢复，不能将此前置当实际还童完成。

普通战斗养护后续交单：PET_BATTLE_CARE_SETTLEMENT.md提供冻结BattleCareEvent与settle_pet_battle_care同租约事务Interface，含每场寿命/每三场忠诚、原包≤30忠诚豁免、死亡替代/次数、擂台/神兽免损和明确设计余数计数。新宠初始化0，旧未知不猜；必须在本场growth/HP/XP改写前结算，之后外层同步当前root source、编码当前快照。领域四保存点/原生/current paid只读与实际source CAS后失败回滚已绿，未接shared实际宠物战斗或部署。旧defeat缺完整等级/模式/场次信息，不应替代新完整结算。

## 神兽养护最新交单

kind2原158行分类/永生显示分支已执行，9神兽免损、模板感知battle_care_ready、历史回执兼容及同事务失败回滚已补。详见PET_IMMORTALITY_INTEGRATION.md。现有change_pet_care签名不变；调用方继续当前租约事务，并读当前PetState编码。kind3普通fallback为designed，不按名字/6000归类。此批未改shared、未发布/操作实机，实际战斗计数与全量玩法继续恢复。

角色所有者、持久化、奖励或战斗接线前读本文。架构约束见 `../ARCHITECTURE.md`，全量范围见 `INVENTORY_FULL_RESTORE.md`，原生证据与历史批次见 `INVENTORY_DESIGN_GAPS.md`。共享入口由集成窗口维护。

中毒寿命食品32004/32009已完成所属事务与原生验证：receive_pet_consumable在precommit之后追加可位置draw=None，鲜请求须Owner固定0..9999，已付可None读历史；可信低层use_pet_toxic_food加入外层fenced事务。3%来自原文，降低五项基础各1/最低0与资源裁剪是明确恢复设计。正常/中毒、六保存点/晚期编码/root source回滚、SQL禁止写入历史重放均绿。接线前读PET_TOXIC_LIFETIME_INTEGRATION；旧context-free receive对这两物明确拒绝，共享稳定随机factory和部署仍待集成。

普通宠寿命参战门槛已按原36001/36002帮助收口：寿命0仍可选择，实际普通出战须>=50。所属选择门禁已修正；战斗侧可用启动冻结CareRules.ordinary_battle_care_ready(frozen_pet.care)，其余HP/级别/技能/特殊宠资格仍由Owner构建，见PET_BATTLE_CARE_GATE。每场寿命扣除/神兽例外和真实战斗接线尚未实现。

品质寿命食品32007已补：实例quality95→47、96→48，原maxNum1保留独立实例；未知/零效果/溢出不扣物，付后重试读当前。沿现有kind1/稳定Adapter及同事务root source，无新增共享方法。精确品质care tuple Interface、原证据/设计取整、实际回滚及当前新资源NPC all回归已绿见PET_QUALITY_LIFETIME_INTEGRATION。

固定寿命食品32036已接实际care/扣物/原生回复，沿原kind1及现有稳定命令Adapter，无新共享Interface；原包明确+1000/无副作用，signed32溢出设计为拒绝，不把初始life当封顶。来源全表原PFS对照、重试/回滚/根source验证及末次共享任务导入阻挡见PET_LIFETIME_ITEMS_INTEGRATION。其余带品质/随机副作用寿命食品继续待补。

真实穿戴的原性别资格已补：沿原equip_transaction/receive/equip同一实现，prepare新增冻结shape_sexes；原sexNeed0不限/其他精确相等，roleNeed仅武器槽检查、原20/21不裁剪、needLevel不换item level。精确Interface和30形象/实际事务/native验证见EQUIPMENT_ELIGIBILITY_INTEGRATION；root默认/v2政策不由此自动切换。

已付generic共同命令的当前只读消息已补：current_mutation_messages_transaction(db,kind,body,epoch,now_ms=None)，返回tuple。先核对领域fingerprint和根replayed=True严格source，再构造当前背包/名单/选择；不治疗、不扣点、不恢复旧ACK。接线及实际只读/native证明见INVENTORY_CURRENT_MUTATION_MESSAGES，支持集合为INVENTORY_CURRENT_MUTATION_TYPES，学习另列。

普通血脉精华消费已交付：先读PET_BLOOD_ITEMS_INTEGRATION。receive_pet_consumable(body,epoch,request_id,now_ms=None,precommit=None)统一支持原kind1精华/药/食物及稳定重试；低层use_pet_blood_essence加入调用方事务。当前回复、真实潜能/资源、扣物及根source同事务验证通过，共享入口接线与部署仍由集成方完成。

当前通用变更/秘籍接线：先读INVENTORY_RESOURCE_HOOK_INTEGRATION。receive新增第三位置参数precommit；receive_pet_skill_book新增第六位置参数precommit（在now_ms后）。hook同db看到当前冻结资产及真实领域replayed，供根synchronize_inventory_resource_source；移动/整理已在同一事务预编码回复。新profile须先具备该hook再放行相关变更，不能由历史请求修补pending来源。

当前药品新contract交付：已迁移角色的唯一资源消费者先读ROLE_CONSUMABLE_RESOURCE_INTEGRATION.md。可构造注入resource_rules/equipment_attribute_rules，或在receive_role_consumable末尾位置传resource_rules/equipment_rules；旧profile保持旧路径，调用不自动迁移。真实70/40、扣物source、已付重放、晚期原生编码回滚和opaque换租约通过，尚未在shared激活新profile。

当前新增：限时宠物技能的学习、查询、奖励、到期事件及战斗快照接入先读`PET_SKILL_EXPIRY_DECISION.md`。`receive_pet_skill_book`新增可位置传递的最后参数now_ms；`receive_pet_query(body,epoch,now_ms)`提供带当前c0007时钟的原c07de查询；`pet_skill_view`只返回当前有效ID。旧无到期存档保持未知，实际能力书189条、原映射191条。所属领域及原生指令验证通过，共享时间路由/定时/战斗尚待接，本批未改共享入口或部署。

## 接线顺序与验收

1. 启动调用 `config = Inventory.prepare(accounts)`，注入 `accounts.inventory_config` 或构造参数。只读配置、规则与数据库迁移在接连接前完成。验收：构造和命令热路径不再读取配置或建表。默认构造仍保留旧同步回退，生产应始终注入。携带栏回复另要求可信epoch和启动CurrencyRules：生产LeasedAccounts已携带两者，离线调用可显式传构造关键字epoch/currency_rules；不从数据库猜一个当前租约。
2. 只由 `role_id + login_epoch` 的角色所有者调用 Inventory；同步接口经有界持久化资源运行。`game_runtime.RoleOwner` 已通过 `io` 路由 `receive`，`runtime_storage.prepare` 已注入启动配置。验收以 `verify_runtime.py` 的慢I/O独立推进、FIFO、过期epoch和发送队列隔离为准。
3. `receive(kind, body)` 只返回逻辑 `(kind, bytes)`。跨所有者传冻结元组；目标连接所有者编码/发送。`InventoryNotReady` 是待恢复分支，`ValueError` 是拒绝；不伪装成功。验收：领域工作者不访问 Session、RC4、MPPC、writer。
4. 奖励和战斗结算在一个 fenced 角色事务中先校验公共凭据、资格和版本，再调用下述事务接口，保存任务/经验/资源/资产及公共凭据后一起提交。任意异常使整个事务回滚。验收：重复公共请求不会重复奖励，提交后重登可恢复。
5. 跨所有者只传 `immutable_snapshot()` 的冻结 InventorySnapshot。含 role_id、inventory_revision、ItemState/PetState 元组，宠物按实际初始化状态含冻结 progress/care。消费方不得持有 Inventory、数据库或 Session。战斗必须组合角色与资产版本，不能把 inventory_revision 称为统一人物版本。

## 资产结算、绑定与品质

`apply_settlement(db, AssetChange)` 要求调用方已开事务；不 connect、BEGIN、COMMIT、发送。资产子账本同角色同键同内容返回原 AssetReceipt，异内容拒绝；它不替代覆盖任务、货币、经验的公共凭据。取消等待不等于取消已提交交易；角色所有者负责 request_id、deadline 与 epoch。

冻结 AssetChange 最多256个变更项。grants 支持 `(template_id,count)`、`(template_id,count,binding)`、`(template_id,count,binding,quality)`；binding 仅0/1，quality 是0..2147483647整数，省略代表未知 None。debits 是 `(owned_instance_key,count)`，pets 是模板ID元组。三元组和四元组语义不同，同键不能改写命令形状重试。

堆叠要求模板、绑定、品质相同；未知品质与0不同。拆分继承两项元数据，整理保留存续key并紧凑排位。prepare 为旧表补 binding 默认0、quality 默认NULL，不虚构旧实例品质。`require_transferable(db,key)` 是同事务门禁，绑定/已装备/不可用物品拒绝；跨角色交易状态机仍未实现。原生flags的bit0已由getter1072e70和给予分支168375b→提示140857（绑定道具不能给予）确证并编码；真实GUI绑定标记尚未验收。物品前四字段现为模板、flags、实例key、position。早先position/flags写反已由原消费者回归修正，详见item-position-binding-verification.json。任务窗口当前 `task_rewards.py` 已传0/1绑定三元组，本窗口未修改该文件。

## 原生请求与装备

INVENTORY_TYPES 当前15个请求（含要求可信上下文、普通receive仍pending的c07ff技能书），完整常量以 inventory.py 为准。已接查询背包/宠物、移动、整理、穿脱、改名、选择参战/休息、加点、放生、使用道具、受限物品提示和耐久查询。具体分支仍有目标/类型限制，不能把一个请求类型计作整个玩法完成。

携带栏1、装备栏4。穿脱两个i32，成功后回两栏完整快照；检查原等级、槽位与roleNeed形象。`equipment_attributes()` 返回 `(role_id,inventory_revision,((原属性ID,值),...))`，仅含原baseEffect。性别、强化、宝石及人物属性刷新待恢复；普通耐久/修理领域和原生耐久查询已补，NPC修理服务路由仍需接线。

`ITEM_TIPS 0xc03fd` 是栏号+key；`SItemTips 0xc03fe` 是栏号+key+Octets详情。受限食品保持原生bean：32000空详情；32001..32013、32042/32043用实例品质BE32。原FoodObject0x1081870到10818ec已执行验证。普通六槽的新恢复装备已补独立EquipObject详情存档/完整回复，栏1/4按实际所在栏查询；旧未知/神兵/高级状态保持pending，见EQUIPMENT_DETAILS.md。其他药品不套食品bean。

## 装备事务事实与新手type59接线

Inventory.equip_transaction(db,key,equipment_slot,epoch,request_id)要求调用方已有事务，检查当前角色归属与有效租约，按原装备/形象/等级/槽位校验后穿戴或替换。它不新开连接、不提交、不发包；旧equip方法复用相同私有实现。返回冻结EquipmentEvent：role_id、login_epoch、request_id、item_key、template_id、equipment_slot、inventory_revision、replaced_item_key、replayed。

request_id来自可信角色命令，是同一受理操作的稳定键；原CEquipement没有客户端重试ID，不能把两条相同线包当同一操作。首次事件的inventory_revision是该次全部穿戴/替换写入后的领域版本。同角色同键同意图返回历史事件并设replayed=True，不重新穿戴、不改版本，原login_epoch保留；同键异实例/槽位拒绝。过期租约连历史确认也拒绝。replayed是历史确认，不能再当成新任务事实，重连读当前状态须另走当前快照。

equip_transaction、immutable_snapshot_transaction与use_role_consumable现支持1..128字符opaque租约及正63位旧整数；保持原身份，不将00007归一成7。完整类型/新旧租约、历史事件与受控首武器字符串链路验证见INVENTORY_LEASE_TOKENS.md。

immutable_snapshot_transaction(db, *, epoch=None)新增：在调用方活动事务/有效角色租约读取冻结InventorySnapshot，含未提交的当前物品、耐久、详情、宠物、成长/养护和精确inventory_revision；无新连接/提交/写入。epoch默认可信Inventory上下文，或由角色命令显式提供；旧/停用/他人租约拒绝。人物属性重算应在该快照上进行，与任务与装备共同提交。详情可能包含显式已知的实例属性，窄template投影仍需核对是否支持，详见EQUIPMENT_DETAILS。

任务/集成接线顺序：在当前租约事务调用equip_transaction；仅对本次fresh事件结合实际active type59任务校验接受者/模板/槽位并保存进度与公共凭据；调用equipment_bag_messages(db,epoch)取得同事务携带栏1和装备栏4逻辑回复；提交成功后交连接所有者发送。无钱包/回复编码失败或任务保存失败均回滚，不能先提交装备再开第二个任务事务。事件是服务器实际写入后的内部消息，不能接受客户端构造的EquipmentEvent或“已装备”声明。

现有原生receive穿脱也已把实际变更和两栏回复编码合并为同一事务；它没有可信request_id，因此不自行生成type59事实。共享RoleOwner应为需要任务验证的穿戴路径使用上述context Interface，当前本窗口不改共享入口，也没有把type59直接判完成。根窗口和任务窗口维护任务资格及卡牌赠武器；NEWBIE_MASTER_CARD_DECISION与newbie-master-card-v1现已发布43原卡选择、绑定1的designed政策及精确获领实例slot0判定。普通干净实例沿用本窗口条件/详情工厂，不由物品文字颜色推评分；本批未接发卡/选卡/type59共享路由。

verify_equipment_events.py通过：同事务没有嵌套连接、冻结字段与当前库一致、两栏回复含实际cash、重试标历史/异意图拒绝、旧回执不重穿、替换保数量与绑定、任务式外层失败同时回滚事件/资产/版本/标记、他人/角色不符/错槽不发事实、真实旧租约拒绝。只是资产Interface与事务验证，真实type59链路及客户端未验收。

## 背包现金字段与未知钱包

SGetBagInfo的u64字段已确认为当前cash，不是可保留默认0的未知标量。原handler10a8f40把嵌套bean交10a4840，column1在10a4876..84将嵌套+8/+c覆盖wallet+b0/+b4；此槽的cash/UI桥已由currency模块独立确认。column4跳过此写入，包内0被忽略。verify_inventory_cash执行原decoder和这一原生覆盖路径，64位2^40+7保持原值；旧代码填0会导致客户端现金显示归零，已建立红例并修正。

携带栏查询从同一读取事务取得当前wallet和物品，read_wallet沿用有效角色租约/政策检查。没有显式钱包基线、缺启动规则、缺可信epoch时返回InventoryNotReady，不能为恢复背包伪造0或静默建钱包。旧档需可信显式迁移；新恢复角色按集成方已有创建来源兑现零基线。装备栏不覆盖cash，可独立查询。

移动/整理等回复携带栏的原生命令先检查cash可读取，再执行自身资产事务；穿脱已把变更及两栏编码合并为同一事务；无钱包时不先改资产后失败。人物/宠物原生用药、喂养已将效果、扣物品、领域回执及两条逻辑回复编码放入同一事务，缺钱包或编码失败全部回滚。低层use_pet_consumable/use_role_consumable和不发送的资产Interface仍由调用方决定共同事务及通知，不因缺钱包擅自补数据。

测试fixture现显式初始化自己的临时钱包，inventory_test_support只供测试且生产无引用；共享运行时测试保留旧档未知钱包拒绝，再显式迁移非零64位cash验证背包。NPC任务和人物用药运行时切片也用明确临时现金基线，检查回复不覆盖它。没有修改生产serve/gateway/accounts/runtime_storage或操作现场库。

## 道具效果

`CUseItem 0xc03ff`：i32实例key、i32目标种类、u64目标ID。原 PetInfoDialog 0x141b1c0 证实种类1是指定宠物key，角色种类0是完整role_id。

种类1已接 `use_pet_consumable(key,pet_id)`：检查拥有的携带道具、等级与非战斗使用限制；读取服务器品质与宠物资源；回复函数1/2/4的HP/MP，或食物忠诚；效果、扣1、版本及凭据同事务。成功回复完整 SRefreshPetData 与携带栏快照。全值/无效/缺品质/他人宠拒绝而不扣药；失败保存回滚全部。生产角色路由在战斗时拒绝世界道具操作。

种类0已补权威资源事务与逻辑回复Adapter，当前game_runtime.RoleOwner已接线且verify_role_consumable_runtime通过临时运行时/原生加密流验证（未部署现场）：角色所有者在非战斗且验证当前命令后，调用 `receive_role_consumable(body,epoch,settlement_id)`，其中epoch和稳定请求键来自可信命令上下文，不能来自包字段。原二参数receive的角色分支仍pending，不能替它猜租约或请求身份。成功返回普通世界SRefreshRoleData（0xc32c8）和携带栏完整快照，由连接所有者发送。

`use_role_consumable(db,key,epoch,settlement_id)` 加入外层事务：read_attribute_snapshot读取实际资源，use_consumable计算并扣药，update_role_vitals比较完整旧快照并写version+1，inventory_role_consumables写领域回执。调用方同事务保存公共请求凭据；领域回执不是跨模块总账。没有显式人物属性基线时拒绝，未使用100HP训练值。完整RoleConsumableReceipt冻结保存当次vitals，但它只是历史确认；重试只确认不再扣药，也不把旧vitals写回。原生Adapter在同事务读最新资源、当前钱包与背包并编码，因此重复请求刷新的是最新伤势和余额；回复编码失败连同扣药、资源与回执一起回滚。

世界刷新原构造ec3590、marshal ec36b0、decoder ec3730；容器元素BE32属性ID+BE float32值，60当前HP、70当前MP。只刷新两项当前值，未推定伤势上限640或改最大值。原普通handler113f5f0..113f630的float转整数与赋值已执行验证；宿主仅提供属性map槽位，未执行UI观察者。为避免原float静默改变整数，不可精确表示的资源在提交前拒绝并回滚。verify_role_resource_protocol.py与verify_role_consumables.py验证原codec/赋值分支及真实角色资源库；这仍不等于实机UI。

低层 `use_consumable(db,key,VitalState,quality=None)` 保留为调用方事务Interface，品质总是读取已拥有实例，旧quality参数仅允许相等断言。固定/品质计算的Decimal取整是本地确定性恢复规则，未宣称原服舍入。

## 宠物成长与养护

成长单一来源 `design/pet-growth-v1.json`，是主策划designed公式，原资质/成长整数/经验表保留。新发宠同事务生成Profile与成长；旧实例仅显式 `initialize_pet_growth(db,pet_id)`，已有实例禁止重掷。

`pet_progress(db,pet_id)` 返回冻结 PetProgress。`change_pet_growth(db,pet_id,settlement_id,expected_version,operation,value)` 支持 experience整数、allocate五元素整数元组、resources权威(hp,mp)元组。事务/版本/子凭据与公共账本要求同上。XP用普通当前等级表，150封顶留余，特殊1001..1150不猜映射。升级保留缺血缺蓝，死亡不复活；成长只增加点数。原记录已编码等级、资源、攻防速、五维/潜能、XP和五资质；成长显示float与血脉颜色已补原读取和原显示算术验证，普通已学技能列表现已补存档和原消费者验证；成长显示见PET_PRESENTATION.md，技能及秘籍接线见PET_SKILLS_INTEGRATION.md。

养护单一来源 `design/pet-care-v1.json`。原 cpetxuemaiconfig 的六级maxloy为100/100/125/200/300/400，原食物31000/31001/31089分别+5/+20/+5；life来自原宠物模板。新宠grade1和初始满忠诚是明确designed基线，与中档成长不建立虚假对应；现已确认并编码bean+3c→原血脉颜色lookup，独立于进化字段，见PET_PRESENTATION.md。特殊不死宠另恢复。

PetState.care 是冻结 PetCare(version,grade,loyalty,lifetime)。已有宠无care时读取保持未知；`initialize_pet_care(db,pet_id,grade,loyalty,lifetime)` 必须提供实际值且只允许一次。`change_pet_care(db,pet_id,settlement_id,expected_version,operation,value)` 加入公共角色事务：feed传模板ID；defeat仅传整数1，表示已验证普通战斗死亡。忠诚和寿命分别减20/50，最低0，采用2012年历史官方规则，非已证明的1.6.1原服公式；擂台/特殊/PK不得无差别调用。不得从客户端包或单次HP赋值推断死亡。战斗接线仍待集成。

原生消费者将 Pet bean+90写属性510（忠诚），+b0写属性460（寿命）；已编码并与原序列化器比对。所有完整宠物刷新保留成长和care，避免用药/加点将另一组字段刷零。当前忠诚0禁止选择，寿命低于50仍可选但普通实际战斗care门槛为50，见PET_BATTLE_CARE_GATE；低忠诚不服从概率尚未恢复。旧未知养护宠物沿用兼容选择，不代表可用于完整战斗验收。

加点回复完整宠物与XP；查询恢复XP与参战选择。放生使用released软删除，保留成长/养护/结算审计与历史FK，容量仅计active；参战宠先休息。释放后不可再成长、喂养、改名或参战，新宠不复用key。特殊绑定/锁定放生约束仍待恢复。

## 普通已学技能与秘籍

PetState.skills为冻结PetSkills(version,learned)，新宠按pet-skills-v1明确designed选前2个不同正候选，旧未知保持None。普通非绑定/无保护书的同事务learn_pet_skill及context Adapter receive_pet_skill_book已实现；c07ff需角色所有者提供epoch/稳定请求键/两个固定服务器draws，普通receive不猜上下文。原非空列表及原刷新复制→图标ID循环已执行，技能被动/战斗效果仍未实现。完整签名、回滚/回放、绑定/保护未恢复范围与共享接线条件统一见PET_SKILLS_INTEGRATION.md。

## 普通装备耐久与NPC修理

规则单一来源design/equipment-condition-v1.json，仅普通六个槽位（itemtype低四位8、槽0..5）。新普通装备发放同事务建立EquipmentCondition(version,current,maximum,color_tier)，初始耐久100/100依据2012历史端游资料，颜色1白色是明确恢复基线。已有装备不隐式初始化；initialize_equipment_condition(db,key,current,maximum,color_tier)只允许一次实际值迁移。ItemState.condition是冻结状态；这里的color_tier是颜色1..6（白/绿/蓝/紫/橙/金），与装备普通/强化/无瑕/卓越/完美五档prefix品质、食品数字品质元数据分别独立。

原NPC报价函数10dbb20普通分支，level取原item.level（原字段读取86e95a→record+24，wrapper+4后getter+28），cequiprepairconfig.npcrepair（原字段读取86b4c6→record+4）逐行查找；系数unit×1.2^(tier−1)经原binary64存储再乘缺失耐久、截断。verify_equipment_native_cost已对原18行×6色×缺失1..100共10800例执行原getter、乘幂、运算和截断，仅配置查找由宿主Adapter提供；颜色5/level60/缺25原值1295，普通Python pow会算1296，故实现保留对应舍入顺序。缺修理等级行拒绝，不免费修理。

repair_equipment(db,key,epoch,settlement_id,expected_version,draw,currency_rules)加入同一fenced角色事务。调用方先验证当前NPC修理服务、位置/距离、角色非战斗及操作资格；原请求中的u64身份字段仅有布局证据，不应直接视为资格。draw由可信角色命令一次生成，0..999；不来自客户端，提交后的同键重试不重掷。稳定键1..120字，指纹含实例、版本、draw与等级。费用用currency-v1 cash/equipment_repair扣除，绑定银不代付，无显式钱包或余额不足拒绝；币、耐久、版本、领域回执与外层公共凭据一起提交。未新增共享入口或全服队列。

原概率表method2=600，采用千分制解释；成功恢复当前到上限、失败上限−10且当前夹到新上限、有效尝试失败仍扣费，以上概率/收费/夹值部分均明确designed。历史官方说明支持失败−10上限和上限≤10不可修理，不能称当前原服全规则已知。家族/技能/珍珠/特殊装备修理分别待接，未自动替换支付渠道。

wear_equipment(db,key,settlement_id,expected_version,amount)仅接可信正整数磨损事件，当前耐久最低0；实际战斗磨损公式未恢复、未接战斗窗口。已知耐久0的装备在equipment_attributes中不贡献baseEffect（designed），修复后恢复；旧未知条件维持兼容但不作为完整战斗验收。

equipment_refresh(db,key)在调用方事务内重读当前条件，返回当前耐久SRefreshEndure与上限SRefreshMaxEndure逻辑消息。RepairReceipt是历史确认，后续刷新不得用它覆盖新磨损；钱包刷新也须read_wallet后用encode_currency_balance('cash',当前余额)。原CRequestEndures 0xc04c6已进receive：仅栏1/4，返回该栏普通装备当前值和逐项上限；遇既有未知耐久拒绝，不能漏项或虚构全满。

原生布局：SRefreshEndure0xc0412是i32栏+compact数量+(i32实例key,i32当前耐久)集合；SRefreshMaxEndure0xc0414是栏/key/上限三个i32。原构造ef9850/当前marshal efa210/decoder efa2a0，以及上限d9dfb0/e4e950/d9e050均已执行比对。原handler1093380/1093470按栏/key调用1072d90/1072df0写装备+c8/+cc，验证执行真实循环与setter，宿主仅提供实例查找且不启动GUI观察者。原CRepairEquipItem0xc0413布局i32+u64+i32+i32已核验，NPC上下文及服务路由仍待集成，不把布局当授权。

## 装备详情前缀与颜色核对

原parser107d960到107de55已实际执行41字节基本前缀：7个BE32、UTF16 Octets文本、3个BE32。已确认鉴定标志→对象+58，current/max→+c8/+cc，prefix品质→+68，score→+60；原5c颜色输入对普通六槽会被评分重新计算。原helper1073110的调用分支使用提示142290“未鉴定的装备不能进行此项操作”，不能把鉴定标志统一留0。

品质用89d520（根配置+4b0，RTTI CEquipPrefixConfig），bestcolortype限制最高颜色；普通装备评分用89d4c0的CEquipEffect.scorecolor阈值，颜色从1逐档增加到品质允许上限。1073090读取+5c给修理公式，10730b0将同值传89d4a0（根+470，CEquipColorConfig）。因此先前把费用倍率称quality_tier/五档是语义错误，已纠正color_tier/六色，金色6原费用检查通过。原品质1/score0→白1，292→绿2，364→蓝3，9999仍蓝3；品质5/9999→金6。research_equipment_detail.py的equipment-detail-prefix.json运行原读取与计算，宿主仅提供原配置值/内存分配/空UTF16赋值。

condition政策现为2026-10-23.equipment-condition.2。旧.1实验JSON的quality_tier绝不自动复制为实际color_tier；reconcile_equipment_color(db,key,expected_version,known_color_tier)要求可信实际颜色，保留current/max、推进版本并保存完整原JSON审计。同意图重试不重写新磨损，冲突拒绝；旧.1指纹不在新政策下盲目重放。verify_equipment_color_reconciliation.py验证保留、重试、冲突、整体回滚与重开；没有迁移真实资产。

后续已执行原构造107cf80及完整parser到107fd97，普通干净基线的属性map、空高级容器、固定扩展bean与末标志全部消费，接入equipment_detail存档及栏1/4详情回复。旧未知和启用高级扩展仍待恢复；来源、逐段布局、explicit初始化与验证统一见EQUIPMENT_DETAILS.md，真实GUI未验收。

## 普通任务宠物经验Interface

按主策划TASK_PET_EXPERIENCE_DECISION与task-pet-experience-v1执行。selected_fighting_pet(db)在已有角色事务返回冻结自有未放生PetState或无参战时None；未知旧成长返回PetState.progress=None，保留原key给任务审计，不新建成长。read_pet_state(db,pet_id)提供固定接受者当前快照：缺失/他人/放生返回None，非法角色/无事务拒绝。任务窗口当前已使用这两个公开Interface，不再查资产表或调用私有_pet_state；verify_task_pet_experience.py已通过新完成/切宠重试/原量与+5边界/角色和宠物整体失败回滚，真实运行时与客户端仍未验收。

change_pet_growth(...,'experience_capped',(amount,award_cap))在原experience之外提供明确上限，cap必须≤150且≥当前等级并进入指纹；到cap储存余XP，不降级、不丢XP，保留伤势和死亡。任务窗口负责完成前固定人物等级与宠物接受者、+5/+6资格和一次性决策，模块不自行读取当前人物等级重选。verify_pet_capped_awards验证人物20/宠24→25留余、宠25存XP、宠26拒绝、cap指纹冲突、旧版本、回滚和未知成长。任务后原生显示须固定key重读当前状态，不能将历史回执当当前资源。

## 验证与未验证范围

本批方法：codebase-design在角色事务Seam集中堆叠/成长/养护行为；diagnosing-bugs以真实receive、原生codec、真实SQLite失败触发器形成可失败反馈；writing-for-agents将当前契约集中于本文，替换过时接线描述。

本批新增verify_item_position_binding、verify_pet_capped_awards、verify_equipment_native_cost、verify_equipment_condition、verify_equipment_endurance_protocol均通过。原批通过 verify_inventory_quality、verify_pet_care、verify_pet_consumables、verify_item_tips、verify_item_effects、verify_role_consumables、verify_role_resource_protocol；原inventory、transactions、binding、arrange、equipment、growth、pet_native_commands及runtime回归均通过。结构化结果见相应 evidence/*-verification.json。品质和喂养验证覆盖重登、拒绝、幂等、版本和失败回滚；runtime覆盖本地Adapter角色隔离，不代表商业容量。

未验证：本轮未重启共享运行服、未改真实资产、未做原生客户端UI；人物用药现场部署/实机UI、战斗养护回写、奖励自动刷新、完整技能/血脉/进阶、NPC修理服务资格/路由、装备其他高级玩法、仓库/其他容器、跨角色交易、商业数据库与多进程容量均未完成。SQLite文件仍有单写瓶颈。

现金纠正批次方法与验证：diagnosing-bugs以原背包覆盖路径建立固定0清空余额的红例，修正同事务权威读取；codebase-design复用currency读取Seam并将用药回复编码移入效果事务。verify_inventory_cash、role_consumables与现有inventory/wire/equipment/arrange/pet_care/pet_consumables检查通过；verify_runtime、verify_role_consumable_runtime、verify_npc_task_runtime通过临时实际owner与连续RC4/原MPPC切片。真实GUI和部署仍未验证。

颜色核对批次：diagnosing-bugs以金色6合法输入建立旧五档限制的红例，再以原parser区分颜色/品质；codebase-design把显式语义迁移与历史指纹限制放在装备Module内部，不让调用方猜旧值。10800原费用对比、颜色迁移、耐久/修理/原生同步验证通过。详情后续容器和实机验收未完成。

装备事实批次采用codebase-design：把原校验/替换Implementation集中在同事务私有核心，公开equip_transaction返回冻结事实给任务Seam，equipment_bag_messages负责当前双栏逻辑回复。没有改共享入口；没有猜首师父赠送武器或绑定。事件/两栏/失败回滚验证通过，任务与运行接线仍由集成方继续。

普通装备详情本批验证：verify_equipment_details、verify_inventory_snapshot_transaction与equipment_events/wire通过；另复核inventory/transactions、condition/color迁移、cash、foodtips/arrange、role_consumables与不启动战斗的role_consumable_runtime。根窄人物投影verify_role_equipment也保持通过，但实际同事务人物投影/任务联动未在本批接入。原构造/完整读取范围、设计基线与所有未验收项以EQUIPMENT_DETAILS.md为准。

宠物显示本批：PET_PRESENTATION.md集中记录原growth float/颜色字段、111原成长值和4501输入×两条原转换验证，以及996最近float显示995的修正。加点回复现于提交前编码，真实旧字段溢出使扣点/版本/回执回滚。技能玩法与GUI仍未验收；未部署或运行战斗。

技能批次验证已收敛：verify_pet_skills、verify_pet_skill_protocol及原非空技能消费者通过，既有inventory/transactions/cash、pet growth/care/presentation/native commands/consumables、transaction snapshot与task_pet_experience回归通过。随后收到主集成临时运行源冻结通知，停止.py/政策修改；此次部署是否纳入技能新源按集成启动哈希确认，本窗口未部署或做GUI。

冻结紧急核对：本窗口未修改game_runtime.py；首次冻结后仅证据/文档与离线只读分析，没有运行时.py或政策JSON写入。当前观察inventory/pet_protocol最后14:29:27，pet_skills/其政策14:32:25，native_gameplay_probe14:22:09；game_runtime观察14:37:38，时间戳本身不指认写入者。完整观察时间、SHA256和声明见inventory-freeze-source-audit.json。仍保持冻结，未部署/重启/操作客户端或战斗。
# 2026-10-23 绑定学习后续批次

共享卸装投影所需的公开`unequip_transaction(db,key,target_slot,epoch,request_id)`已补并验证，返回独立冻结UnequipEvent（不作为type59穿戴事实）。同事务快照/双栏回复、幂等/opaque租约及真实凭据保存失败回滚通过；完整字段、shared接入步骤见`UNEQUIP_TRANSACTION_INTEGRATION.md`。现有穿戴接口签名保持稳定，本模块未改共享入口。

主策划通知063445Z不可变发布已启动后，解除所属模块源码冻结，本批继续离线开发；没有修改game_runtime/runtime_storage/accounts/serve/gateway，也未操作PID8724/客户端。装备snapshot/equip_event/equipment_bag_messages公开签名保持稳定。

绑定秘籍（96条原映射）已从明确拒绝推进为同角色事务学习：已知raw flags置bit1、精确扣一本、技能/资产版本/回执一起保存；未知旧标记保持pending。完整宠物栏在提交前编码以重建原绑定缓存。接入和必要验证见`PET_BINDING_INTEGRATION.md`，模块在共享Owner c07ff路由仍待接，不宣称进入当前部署。

认证符末四项与到期map语义已原指令查明，见`PET_SKILL_OPTIONS_RESEARCH.md`；认证符保护/进度及到期领域状态仍待恢复，默认末四项全-1限制保留。全量目标active。

## 2026-10-23 认证保护与进度当前接线

上述末四项全-1限制现已由完整认证Adapter替代；旧decode_skill_book仍是兼容默认解码器，生产用decode_skill_book_request。普通/绑定学习、认证保护/精确扣除、独立拓格进度及c0800/c0801查询刷新已完成领域/原生验证，当前16类入口。当前参数与来源以`PET_SKILL_LEARNING_DECISION.md`、`design/pet-skill-learning-v3.json`为准。

**集成须改用两个0..9999的可信固定服务器draw**，才能表示官方0.02%等概率；首批0..999范围不再是当前学习采样规范（装备修理自己的范围不变）。精确原技能/模板/保护身份仍client_verified，当前几率来自2017官方端游公示guide_supported、1.6.1完全一致未证明；累积/保底/失败消费顺序明确designed。临时v2未部署，已被v3替代。

shared只需在现有`if kind in INVENTORY_TYPES`中将c07ff专门路由到`await self.io(self.inventory.receive_pet_skill_book,body,self.epoch,cmd.request_id,draws)`；检查world joined，并沿用当前战斗/传送拒绝。draws在一次受理命令中固定，重试不得重新掷；原线包没有请求ID，新的一次相同点击是新尝试，不能把仅字节相同当幂等重放。返回逻辑消息只在提交后由目标连接发，I/O结果不明沿用Owner隔离策略。本模块没有改shared，当前仍缺该真实接线。

可选公共调用`learn_pet_skill(...,draws,*,options=SkillBookOptions(...))`加入外层事务；预编码当前Pet/实际cash/进度，绑定另需完整栏（参考现Adapter）。`pet_skill_progress_messages(db,epoch,pet_ids=None)`给同事务当前map；`receive_pet_skill_progress(body,epoch)`接c0800空体；普通receive(c0800,body)使用可信构造epoch。新宠进度0，旧未知不猜0，可信完整旧值通过initialize_pet_skill_progress一次导入；旧v1回执可读不补历史points。

原进度codec/合并/查询/阈值/算术18例与公开认证事务验证通过，含实际保存abort、外层失败、缺钱包、opaque fenced角色租约、原概率边界/12格上限、旧回执当前重放和重开。新增文件与验证见决定文档；equip/unequip/snapshot/双栏公开签名未改变，没有重启当前验收服、操作客户端或战斗。共享入口、GUI、到期技能、战斗效果和高级宠物/装备继续未完成，目标active。
