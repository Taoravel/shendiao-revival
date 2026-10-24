# 全量恢复执行清单

元魂真实动作前置最新：pure wear/remove资产计划已实现，原四→六字段/完整raw6、38045实际级报价/绑定优先扣符、保真新绑定返还、明确本地slot/raw6/零现金策略验证并经固定1396依赖双轴0项；见[PET_SOUL_ACTION_PLANS](PET_SOUL_ACTION_PLANS.md)。**尚未实际扣物、受理或幂等结算**；下一实现直接按[PET_SOUL_CONTROLLER_NEXT](PET_SOUL_CONTROLLER_NEXT.md)做真实Inventory/map/返还metadata/root source/多凭据事务，不再以纯层作为可玩完成条件，全量active。

装备原生列差异：已只读核对NPC/root原27组合，并在临时真实Inventory复现原query3拒绝、内部4有已穿物品，owned Bag/tips/endurance仍出4；最小协议Adapter方案与staging预期失败RED见[EQUIPMENT_NATIVE_COLUMNS_PLAN](EQUIPMENT_NATIVE_COLUMNS_PLAN.md)及equipment-native-column-red.json。内部归属/存档不迁，NPC货架4不全局alias；shared/main及旧paid4兼容待独立集成。此项未修，不计为绿灯，也不阻止元魂column1所属控制器继续。

元魂背包消息最新：普通Item原48scalar与TradeItem类型混淆已由原RTTI/参数和原消费者更正，当前Bag完整flags32位与逐珠独立tips的只读Adapter已实现；原Item/非空Bag、当前四项、普通物品原样、SQL只读/unknown拒绝及源报告两段lookup/parser反证复跑通过，固定1386依赖双轴0项；见[PET_SOUL_BAG_INTEGRATION](PET_SOUL_BAG_INTEGRATION.md)与[PET_SOUL_BAG_TIPS_SOURCE_RESEARCH](PET_SOUL_BAG_TIPS_SOURCE_RESEARCH.md)。未共享/发布/GUI，全量active。

背包元魂实例存档最新：四字段、完整非绑定flags和精确历史raw6/明确无历史None的来源已持久化，当前单实例/租约/来源与库存版本CAS、重复导入SQL只读、真实2处SQL和编码后异常全回滚、binding ABA来源失效均通过。固定1382依赖双轴0项，各独立2项验证，原23生产不改；见[PET_SOUL_ITEM_STORAGE_INTEGRATION](PET_SOUL_ITEM_STORAGE_INTEGRATION.md)与pet-soul-item-storage-batch.json。尚非资产动作；下一步闭合真实穿戴/38045摘除的材料交换、保真返还、稳定凭据及当前投影，再融合/技能与共享/实机，全量active。

背包元魂数据最新：原实例四项XP/魂技/raw5/raw4的独立数据Module、精确16字节及column1完整SItemTips已实现，原4项/外层codec与16个原parser/六→四转换组合通过，固定1378依赖双轴0项。显示的bagbit0与worn raw6非零不同；不提供有损逆写，精确raw6保留。见[PET_SOUL_ITEM_DATA_INTEGRATION](PET_SOUL_ITEM_DATA_INTEGRATION.md)及已完成[PET_SOUL_ITEM_SOURCE_RESEARCH](PET_SOUL_ITEM_SOURCE_RESEARCH.md)。下一步实现四字段实例持久化、完整旗标与历史raw6保真来源，再闭合真实穿戴/38045摘除/融合资产、费用与凭据；未shared/发布/GUI，全量active。

元魂来源联动补验：普通v2与完整宝石人物政策的真实root来源hook均已与元魂CAS同事务验证，保持70HP/40MP/原上限和资源数值版本；root凭据写入故障回滚元魂/库存/资源，paid拒绝修复pending并严格只读。仅新增验证，22个既有production SHA不变，固定1373依赖双轴0项；见[PET_SOUL_RESOURCE_SOURCE_VERIFICATION](PET_SOUL_RESOURCE_SOURCE_VERIFICATION.md)。尚非付费穿戴/摘除/融合或共享验收。追加原码研究已发现背包珠是独立四字段，不能套穿戴六字段；映射与入口继续追实，全量active。

元魂来源基础最新：原28元魂/420精确正负平值和比例、累计XP原row2..15等级、模板uselevel与魂技/已知flag22有效上限、完整六字段map存档CAS及原生空/2/5槽刷新已实现，固定1371依赖Standards0/Spec0，各独立3项验证。未知不补空、重复导入不重置、2处SQL和编码后异常全回滚、旧before/epoch拒绝；见[PET_SOUL_SOURCE_FOUNDATION](PET_SOUL_SOURCE_FOUNDATION.md)与pet-soul-source-foundation-batch.json。背包元魂实例数据、真实穿戴/38045摘除/融合材料及幂等控制器、完整属性/共享/发布/GUI仍继续；背包实例与穿戴原入口追加来源研究进行中，全量active。

人物宝石属性最新：14类原numid、六项显式额外基线、六件装备基础值与宝石独立相加、唯一HP/MP存档及27字段原生刷新已实现，固定1358依赖双轴均0项，各独立运行7项验证。真实事务证明上限增加不回血、下降只裁剪、修理不补血、死亡换装不复活，3处SQL和原生编码后异常全回滚，paid严格只读；见[ROLE_EQUIPMENT_GEMS_INTEGRATION](ROLE_EQUIPMENT_GEMS_INTEGRATION.md)与role-equipment-gems-batch.json。候选未接共享/发布/GUI，下一步仍是材料/现金/工具/绑定/返还/多凭据控制器及全部共享消费者切换，全量active。

宝石配对保存：独立设计评分/pre-gem基准与公开score/color Adapter已实现并各经双轴0项；列表CAS、三处真实写入故障及原native编码后异常全回滚，同阶presentation只读、摘光恢复原分且耐久保留。见[EQUIPMENT_GEM_SCORE_DESIGN](EQUIPMENT_GEM_SCORE_DESIGN.md)、[EQUIPMENT_GEM_PRESENTATION_INTEGRATION](EQUIPMENT_GEM_PRESENTATION_INTEGRATION.md)及对应batch。不把持久化片当收费可玩验收。宠装原版入口研究已落盘[PET_EQUIPMENT_SOURCE_RESEARCH](PET_EQUIPMENT_SOURCE_RESEARCH.md)，按元魂系统继续，不套手游人物六槽。

宝石来源与详情基础当前批：完整210普通原行/14族、有序GemState、精确source0=column1/source1=4、孔位/三族与双工具返还计划、显式完整来源CAS及原非空详情已实现并独立双轴0项，见[EQUIPMENT_GEM_SOCKET_FOUNDATION](EQUIPMENT_GEM_SOCKET_FOUNDATION.md)与equipment-gem-socket-foundation-batch.json。**尚非收费镶嵌/摘除action ready**；评分/颜色写入、实际资产收费/root人物属性/资源/shared/GUI是后续强制闭包，目标全量active。

普通宝石合成及独立体力450/630的所属事务已完成固定R2审验，Standards0/Spec0；同堆/混绑成功失败、原协议、来源失效、九处SQL/source/编码回滚、严格只读paid和鉴定SHA保留均已验证。接线见[EQUIPMENT_GEM_COMPOSITION_INTEGRATION](EQUIPMENT_GEM_COMPOSITION_INTEGRATION.md)，固定交付见equipment-gem-composition-ready.json。原杂学键为600005/class4，旧研究602053已由新原证据纠正；真实技能账本、体力恢复、shared RNG/发布/GUI及镶嵌摘除继续推进，全量active。

装备鉴定的公开资产CAS、同事务当前详情回复、独立cash用途与真实NPC专用/共同/root source凭据组合已验，见[EQUIPMENT_IDENTIFICATION_CAS_INTEGRATION](EQUIPMENT_IDENTIFICATION_CAS_INTEGRATION.md)。共享接线/发布与原GUI待验；继续高级装备、宝石/宠装及共享随机入口，全量active。

灵石当前进度和下一接线条件见[PET_STONES_INTEGRATION](PET_STONES_INTEGRATION.md)：所属服用/清除与交叉来源、真实共享驱灵散已验；70052共享固定随机受理、发布与原GUI待验。下批衔接主策已裁定普通固定结果鉴定的资产CAS/cash purpose，再继续高级装备/宠装及共享随机入口，全量active。

进化最新：普通kind1/3宝宝阶段、稀疏跳终阶、50次追加成长及材料/成长同事务、原生刷新与真实加密Owner共享链路已通过；普通/超级还童现保留已知进化成长。接线、原/设计边界、旧档来源及未验范围见PET_EVOLUTION_INTEGRATION.md。神兽蜕变/灵石/宠装、发布与原GUI提示/动画继续恢复，全量active。

年糕最新：五种实际服用、原预测37,920例、总20次、同事务/原生提示及真实加密Owner共享链路已通过；旧四字段审计升级、耗尽重试、故障回滚和重登已验。接线、浮点差异与设计边界见PET_CAKE_CONSUMABLES_INTEGRATION.md。未发布/GUI，进化、灵石、宠装及剩余装备道具继续恢复，全量active。

普通还童后续：31002/31087所属完整重置、持久化和原生Adapter已实现并通过316门槛/选丹、13仙兽必带、2844生成合法性及12写入点/实际root source回滚验证，接口和原/设计边界见PET_ORDINARY_RETURN_INTEGRATION.md。下一步恢复年糕实际服用与进化/高级宠装及剩余装备道具，普通/超级共享分流、部署和实机仍待验，全量active。以下为此前阶段。

超级还童后续：所属生成→查询→保存→清除已实现并通过真实事务/原生验证，血脉后候选展示与保存一致、年糕count/history重置、人物root source同事务回滚均绿。原评分当前wire316例与年糕1540/总20门禁4例通过，集成交单PET_SUPER_RETURN_INTEGRATION.md。接下来继续普通还童、实际年糕服用和高级进阶/剩余装备道具；共享接线/部署/实机仍不能算完成，全量目标active。下段为此前字段阶段。

还童继续推进：已完成原普通/超级来源矩阵、正确悟性1160及宝宝/野生身份的领域存档/原生读取，以及超级请求/预览布局。见PET_TRAITS_INTEGRATION、PET_REBIRTH_SOURCE_RESEARCH及pet-rebirth-native.json。普通重置与超级候选→保存、稳定随机/扣丹、完整score/年糕/进阶和实机仍继续恢复；前置字段完成不算还童已可玩，目标active。

普通战斗养护后续批次：可信冻结事件、持续mod3、普通每场/三场扣损、≤30忠诚豁免、死亡次数/替代计次及擂台/神兽免损已补；当前根source实际事务与失败回滚、历史SQL只读重放通过，见PET_BATTLE_CARE_SETTLEMENT.md。尚未接实际宠物战斗，低忠诚行为/完整技能/还童进阶及剩余装备道具继续恢复，全量目标active。

## 神兽永生后续批次

已继续完成原kind2分类/永生显示全158行执行、9神兽死亡免损、含模板养护门槛与旧回执兼容，见PET_IMMORTALITY_INTEGRATION。普通与kind3未按名字推定免损；kind3采用单独designed普通fallback。四种寿命食品、真实source和加密NPC恢复回归绿。实际每场/忠诚计数、完整战斗/还童/进阶、剩余装备道具与部署/实机继续推进，目标active。

目标保持active，阶段验证不作为整体结束条件。源代码、生产接线、部署、原生客户端实测分别判定。下一批先读INVENTORY_INTEGRATION.md与INVENTORY_DESIGN_GAPS.md；修改共享入口由集成窗口负责。

中毒食品后续批次：32004/32009真实品质寿命、3%固定受理draw、设计资质损失、当前血脉投影及扣物/凭据/source同事务已补并原生验证，见PET_TOXIC_LIFETIME_INTEGRATION。原四种寿命食品的所属消耗已覆盖，制作/取得渠道、毒提示、共享稳定随机路由/发布和GUI另验；还童/完整进阶、特殊宠与装备/其他道具全量缺口继续恢复。

原寿命门槛纠正：bookanswer36001/36002原包全表复核后，将“寿命0不能选择”改为“寿命低于50可选择，但普通实际战斗care资格不足”。原FIGHT_PET、0/1/49/50/51×六色、真实食品保留选择和重开通过；只读CareRules.ordinary_battle_care_ready已交，见PET_BATTLE_CARE_GATE。完整HP/技能/特殊宠资格、每场扣1及实际宠物战斗链路另待集成。

品质寿命食品后续批次：32007荷叶羹真实存档品质、精确公式/设计取整、扣件/原生刷新/paid当前重放和根source同事务已绿，见PET_QUALITY_LIFETIME_INTEGRATION。当前shared新资源NPC all回归已由本窗口复跑通过，较早的完整map缺口不再是当前结论；未部署或做GUI。带副作用寿命食品、完整还童/进阶、剩余高级装备与其他全量缺口继续恢复。

寿命道具后续批次：原32036福寿糕+1000寿命、实际扣件/原生显示、历史当前重放/失败回滚和根来源联动通过，见PET_LIFETIME_ITEMS_INTEGRATION。其余品质寿命食品/随机副作用/还童重置仍待恢复。共享任务导入错误已由其他窗口调整，共同Inventory命令和旧宠物恢复Owner回归末次已绿；新资源NPC care检查仍缺完整人物属性map，交主集成，领域通过不替代部署或客户端验收。

装备资格后续批次：原sexNeed已进入实际穿戴事务，30原shape正反组合、当前未提交形象、原20/21不裁剪、needLevel与item level分离均通过，见EQUIPMENT_ELIGIBILITY_INTEGRATION。默认/v2投影和Owner共同命令回归绿；旧修理hook测试因fixture缺当前resource_rules未通过，已单列交主集成，未把此项写成全绿。

最新：普通血脉精华36117消费事务和稳定命令原生Adapter已补，实际+200/扣一件、有效资质/真实潜能、保留缺失量/死亡不复活、历史当前回复及完整回滚已验证，见PET_BLOOD_ITEMS_INTEGRATION。通用paid命令当前只读消息已交，见INVENTORY_CURRENT_MUTATION_MESSAGES；主集成共同receipt接线另验。通用precommit及实际根source验证见INVENTORY_RESOURCE_HOOK_INTEGRATION。共享部署/实机与奖励、完整进阶仍待完成，整体目标active。

本批新增人物药品唯一资源消费者：显式规则注入、实际物品/资源/source/领域凭据同事务、新profile历史请求只回当前值、晚期编码失败回滚已验证，旧profile兼容且不自动迁移；交单ROLE_CONSUMABLE_RESOURCE_INTEGRATION.md。普通血脉原消费者113例及后续精华事务见PET_BLOOD_RESEARCH、PET_BLOOD_ITEMS_INTEGRATION。当前均不冒称在线全量完成。

最新阶段：限时技能的明确到期map、有效快照、过期空格复用、可信绝对期限发放/延长及带时钟查询已完成所属源码和离线验证，方法/来源/接口/失败回滚见`PET_SKILL_EXPIRY_DECISION.md`。新宠已知空map，旧存档未知不猜永久；原时钟已证Unix毫秒，严格过期才空格。仍需共享Owner时间接线、内容发放渠道、定时刷新、战斗实际能力与GUI，整体未完成。

## 当前可判定状态

- 已实现并离线验证：携带栏非空同步、移动拆合换位；装备穿脱替换与两栏刷新；原baseEffect属性ID快照；物品堆叠/扣除；角色归属与事务回滚；幂等资产结算；实例绑定及绑定堆叠/转移门禁；宠物栏/改名/参战选择/休息基础消息。
- 道具效果：宠物HP/MP回复、食物忠诚和扣药已接原生请求/完整刷新；人物权威资源事务、幂等回执与普通世界HP/MP刷新Adapter已验证，共享入口现已传租约及请求上下文并通过临时运行时切片。品质取实例存档，支持品质提示和四元组奖励，旧未知品质保留NULL。
- 宠物成长/经验/加点与同事务存储已按designed方案实现，身份字段和部分属性的原生编码已验证。
- 已接原生加点、XP、五资质、参战恢复、放生软删除/容量与携带整理；成长float/颜色/技能列表有原消费者证据。宠物绑定、认证保护/消费与拓格进度领域及原生Adapter已补，当前学习概率依据官方端游公示，保证顺序另标设计。共享c07ff路由、GUI、到期及战斗效果仍待恢复。
- 未完成：人物用药现场部署与实机显示；宠物剩余显示字段、技能、养护战斗回写、寿命补充道具、血脉与进阶；装备NPC修理资格/路由、战斗磨损、强化、宝石、打造与其余进阶系统；其他背包/仓库/道具处理；奖励后自动刷新；原生绑定显示；客户端全流程与重登验收。

原生入口总表是inventory-protocol-catalog.json：326个相关收发消息入口，其中c0800及另补核的c0801进度对已有专门证据；目前INVENTORY_TYPES为16类，c07ff仍要求可信上下文，c0800空查询已提供。该数包含服务端消息，不能当作独立玩法数；歧义候选采用时人工核对。原包配置不是服务器业务实现。

## 接下来顺序与完成条件

1. 绑定奖励生产契约：当前任务窗口已将原bind=1传AssetChange三元组，仍在任务公共事务结算；继续验证奖励自动刷新与客户端绑定标记。原flags bit0已确认并编码；已修复旧position/flags互换，原消费者给予门禁通过，真实GUI标记仍待验收。
2. 完成原生CUseItem与效果刷新：人物事务及逻辑回复已提供receive_role_consumable，角色所有者需传epoch/稳定请求键；宠物回复已接receive。已确认布局i32实例key+i32使用目标种类+u64目标ID，PetInfoDialog调用点0x141b1c0使用种类1与宠物key，角色调用点种类0使用完整角色ID。角色生命值由角色所有者持有，使用和扣药在同一fenced事务。完成条件为真实客户端数值/数量同步变化且无效果不扣药。
3. 宠物记录语义及生成：pet-native-field-layout.json记录32个标量的原生位移差分，仅有布局没有语义。等级、XP、HP/MP、五资质、忠诚与寿命已映射；成长显示单位及血脉颜色已确认并接入；普通技能列表与非绑定无保护秘籍领域已补；继续保护/绑定、扩格进度及战斗效果。growrate保存原整数；cpetproportion是外观资料，不能当属性倍率；经验表0–150与1001–1150需分段确认。
4. 宠物玩法：取得/召唤/参战/休息/改名、经验升级/加点、喂养/寿命、技能、资质成长与进阶。完成条件为每条玩法有保存、原生消息、重复请求限制、重登与战斗快照验证，未知数值按主策划流程补全而非停工。
5. 装备和道具扩展：普通耐久/现金修理事务、原费用10800例比对与耐久查询/刷新已完成离线验证；普通干净装备详情已补存档/原完整消费，继续接NPC服务资格/路由、高级详情和战斗磨损，再推进宝石/强化/打造等真实状态变化与资源扣除。
6. 在线验收与收尾：共享运行服由集成方部署当前模块；使用原客户端验收背包、装备、宠物和道具完整操作并重登；异常回滚/过期epoch/背压覆盖后才可以认定运行时链路完成。SQLite本地验证不等于商业容量。

## 本轮产物与验证

沿用codebase-design，以角色领域Interface和调用方事务Seam约束实现；diagnosing-bugs用真实receive及原生codec比较形成可失败回归；交接文档沿用writing-for-agents的步骤/完成条件方法。

verify_equipment_wire.py验证栏1/4原生解码、穿脱替换、原roleNeed限制与属性算例；verify_item_effects.py验证回复计算、限值、不消耗无效药、扣药事务回滚；verify_inventory_binding.py验证绑定分堆、拆分继承、转移拒绝、重开与幂等。其余原背包/事务验证保留。verify_runtime_contracts.py的4项契约检查通过；本模块未据此宣称整个架构容量已验收。

本批新增：verify_inventory_quality（旧schema/品质拆合/整理/重登/结算）、verify_pet_care（六级上限/食物/原生养护字段/回滚）、verify_pet_consumables、verify_item_tips；verify_role_consumables与verify_role_resource_protocol验证真实人物资源库、原普通世界属性map codec/赋值及历史回执不覆盖最新伤势。各项通过不改变全量目标active状态。

后续批次：原物品消费者揭示并修正position/flags互换，绑定bit0已原生验证；普通耐久/修理与cash原子扣费、当前/上限查询刷新已实现；任务宠物经验的selected/read快照与experience_capped接口已交并被任务窗口使用。原生UI、共享部署、NPC修理服务、战斗损耗仍未完成，全量目标保持active。

现金字段纠正：携带背包u64已由原消费者确认cash，当前余额与物品同事务读取，不再填0。旧档未知钱包保持pending且回复背包的操作不先改资产；角色/宠物用药与回复编码同事务回滚。字段与运行时切片验证通过，真实屏幕与部署仍未验收。下一步继续装备详情、NPC修理路由和进阶玩法。

装备详情批次：原基本41字节段及评分/品质限制颜色计算已执行；修理倍率纠正为颜色六档，不是品质五档，10800例原费用比对通过。旧实验耐久记录需显式颜色核对并保留原审计，不自动重解释。后续本批已补普通干净实例属性map和全段解析/详情回复；非空宝石/技能/高级扩展及真实GUI仍待恢复，见EQUIPMENT_DETAILS.md。

新手装备事实接口已交：equip_transaction使用既有租约事务返回冻结角色/实例/template/slot/revision事件，同键历史标记不重放新事实；equipment_bag_messages在同事务取得当前双栏回复。首师父卡牌赠武器/绑定由统一规则裁定，type59实际任务接线及自然客户端流程尚未完成。

普通装备详情与同事务快照批次：equipment-detail-v1明确designed普通工厂，1038个非神兵六槽模板按原baseEffect生成冻结详情；原SItemTips codec及EquipObject完整parser验证六槽、当前耐久和map替换。详情保存失败与奖励整体回滚，旧未知不自动生成。immutable_snapshot_transaction返回同一租约事务的完整冻结资产版本供任务/人物投影。详见EQUIPMENT_DETAILS.md；仍未部署、未做GUI、未接高级玩法，全量目标保持active。

宠物显示/租约批次：原宠物消费者和UI算术已确认growth float及颜色；修正已知值仍编码0和996 float截断995，保持成长存档整数及原点数公式。喂养/加点/重开保留，编码失败同事务回滚。装备/当前资产快照/人物用药支持opaque字符串和63位整数，实际首师父字符串事务切片通过。详见PET_PRESENTATION.md、INVENTORY_LEASE_TOKENS.md；共享路由/部署、技能/高级装备和实机仍未完成，目标保持active。

宠物技能批次：已学精确ID持久化、原非空列表/刷新复制/图标循环、普通非绑定无保护秘籍事务与上下文Adapter已补。当前共享路由未接，绑定/保护/真实扩格进度/被动与战斗效果未完成；15类入口不当作15套玩法完成。来源、设计初始2技能及250/1000扩格等规则、验证和完整缺口见PET_SKILLS_INTEGRATION.md，未部署或做GUI。

冻结期只读补证：宠物绑定bit1及单独标记刷新缓存问题通过256值原指令验证，见PET_BINDING_RESEARCH.md。已学技能旁的非空map已证实控制到期显示（14组原codec/复制/UI比较），过期显示原200534“技能空”，不将其误称保护状态；见PET_SKILLS_INTEGRATION.md末节。本批仅写证据/文档，绑定与到期领域实现仍待冻结解除后继续，整体目标active。

解除冻结后的绑定批次：96种原绑定秘籍现可使用已知标记，在同角色事务精确扣书/学习/置bit1/保存回执；旧未知标记不自动初始化。完整栏回复由原decoder→转换器→绑定查询验证；真实flags/receipt保存中断、缺钱包、外层失败均回滚，重开及重试保留当前状态。新增资格门禁拒绝绑定/未知/其他未恢复标记/参战/放生/他人宠物，跨角色交易仍未实现。见PET_BINDING_INTEGRATION.md；共享c07ff路由、认证符保护/进度、到期存档/战斗效果和GUI仍待恢复。

人物属性集成所需卸装事务：公开unequip_transaction现已补；独立UnequipEvent不误作为type59穿戴事件。角色租约/幂等、同事务快照/双栏回复、历史不卸后来装备、真实凭据失败/外层失败/缺钱包回滚及重开通过。见UNEQUIP_TRANSACTION_INTEGRATION.md；shared最终20属性与脱穿入口仍由集成方接入。

认证与进度批次：完整末四项认证身份、保护排除、精确扣除、SkillProgress存档及c0800/c0801当前查询刷新已补。原进度消费者18例及公开事务/真实失败回滚/opaque租约/旧v1回执/重开通过；当前16类入口。后续查到官方端游开格概率公示，已实际替代统一25%设计，当前v3按数量/认证组合、两draw0..9999，含11技能0.02%与2技能组合100%；1.6.1精确匹配仍未证，保底/消费状态机另标设计。见PET_SKILL_LEARNING_DECISION.md。共享c07ff路由、部署与GUI、到期/战斗效果及高级玩法仍未完成，整体目标active。

## 2026-10-24 元魂实际资产链路候选

`pet-soul-action-storage-batch.json`：实际穿戴→摘除→再穿戴已实现；真实扣珠/按原表扣移魂符/独立保真返还与map/source/成对凭据同角色事务。14个SQL故障、2次原生编码后异常及超时整笔回滚；历史paid SQL禁止DML，读当前租约/属性来源/伤后资源，不复活旧返还key。普通与完整宝石人物source hook均通过，独立source验证拒绝空回调和治疗。固定R2 1439依赖，Standards0 hard/0 judgement、Spec0；R1缺启动配置失败另存，不追改历史。接口与未验门槛查 `PET_SOUL_ACTION_STORAGE_INTEGRATION.md`。真实许可提供者、最终宠物属性/HPMP/技能/融合/战斗、shared/发布/GUI仍未完成。全量恢复目标active。

列适配正在所属新Module实现，封签Inventory和shared未改；当前legacy入口RED保持。新增NPC原生证据纠正：列4是回购；普通购买读取客户端本地模板，不虚构stock4。

## 2026-10-24 本人装备原生列适配候选

`equipment-native-columns-batch.json`：新增owned `equipment_native_columns`，真实当前资产→本人wire3 Bag/tips/endures，内部视图4不迁；普通已穿/携带、损耗/修理/脱下及宝石score/source当前验证通过。原codecs/完整gem parser、SQL禁DML、旧epoch/外国item/错容器/未配对source拒绝、编码后异常回滚通过。固定1445依赖独立Standards0 hard/0 judgement、Spec0；29既有生产hash不变。接线Interface查 `EQUIPMENT_NATIVE_COLUMNS_INTEGRATION.md`。旧Inventory.receive本人query3仍RED，shared替换/登录重连/真实GUI/NPC E648组合与历史paid4另验；本候选不表示已上线。NPC列4是回购，普通货架本地模板。全量目标active，继续真实勋章22来源与宠物最终属性/资源/战斗。

## 2026-10-24 铭文22实际来源与元魂组合

`role-mingwen-soul-source-batch.json`：新增真实角色完整22项CMingwen来源、原始4字段保真/current CAS，以及pet_soul_authority实际reader。known_flag22来自持久“铭文·简易”rawActive==1，缺档不推0；不再由flag fixture供应。真实元魂穿戴读当前有效2/scalar32，实际ledger改rawActive2后旧paid严格只读有效1/scalar11，人物70/40保持；未付source变化拒绝，新意图成功。2 SQL+caller异常回滚、空库存首次versionrow、旧epoch/外国/材料不完整/异步reader均验证。固定1458依赖，Standards0 hard/0 judgement、Spec0，30既有production不变。接口查 `ROLE_MINGWEN_SOUL_SOURCE_INTEGRATION.md`；真实铭文授予/费用、新建基线、外部世界/材料许可、宠物最终属性/唯一HPMP/战斗、shared/GUI未验。全量目标active。

## 2026-10-24 元魂最终属性与唯一宠物资源实际候选

`pet-soul-final-totals-batch.json`：完整14修正+7显式基线已在共同load_pet读者组合，原HP/MP仍只存inventory_pet_growth.state；来源/资产中间pending阻止native/battle/新受理使用，旧默认reader不忽略已采用政策。真实穿戴扣珠→cap202不回血、低层药物195、原2符摘除/唯一返还→cap157并裁HP157、paid只读当前/不重治、死亡0穿戴不复活；7 SQL+2 native后异常同事务回滚，人物70/40/100不变。28原珠/14类字面算例及精确signed ratio全部保留；原Pet和整数hit/dodge刷新、实际普通battle核心copy验证。5比例native scale/机制与其它已采用source-aware成长动作仍发布门槛，不能据核心绿灯称完整战斗/GUI。固定1481依赖Standards0 hard/0 judgement、Spec0，30既有production不变；用户7锁定文件/shared未改。Interface查 `PET_SOUL_FINAL_TOTALS_INTEGRATION.md`，整体目标active。
