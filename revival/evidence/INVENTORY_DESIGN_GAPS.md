# 召唤兽、装备、道具恢复记录

普通固定结果鉴定的资产侧当前状态见[EQUIPMENT_IDENTIFICATION_CAS_INTEGRATION](EQUIPMENT_IDENTIFICATION_CAS_INTEGRATION.md)：完整来源CAS/cash及真实NPC收费凭据组合已验，不以此声称完整随机鉴定/共享已通。较早“没有0→1写接口”为历史阶段。

灵石最新实现、原版/设计边界和未验范围统一见[PET_STONES_INTEGRATION](PET_STONES_INTEGRATION.md)；本文较早“灵石未实现”为历史记录。50点分配及还童保留采用独立policy明确设计，实际随机共享受理、发布与GUI继续恢复，全量active。

进化最新：普通kind1/3宝宝阶段、稀疏跳终阶、50次追加成长及材料/成长同事务、原生刷新与真实加密Owner共享链路已通过；普通/超级还童现保留已知进化成长。接线、原/设计边界、旧档来源及未验范围见PET_EVOLUTION_INTEGRATION.md。神兽蜕变/灵石/宠装、发布与原GUI提示/动画继续恢复，全量active。

年糕最新：五种实际服用、原预测37,920例、总20次、同事务/原生提示及真实加密Owner共享链路已通过；旧四字段审计升级、耗尽重试、故障回滚和重登已验。接线、浮点差异与设计边界见PET_CAKE_CONSUMABLES_INTEGRATION.md。未发布/GUI，进化、灵石、宠装及剩余装备道具继续恢复，全量active。

普通还童完整事务已补：原template uselevel95分丹、level0/新BASE/技能/养护/悟性、宝宝保血脉/颜色与野生重建、原NPC13仙兽必带、附属状态集中设计、单扣/当前paid及实际source回滚已过。见PET_ORDINARY_RETURN_INTEGRATION.md及PET_ORDINARY_RETURN_METADATA_RESEARCH.md；普通kind2许可、全体kind3资格和metadata/概率未知部分仍明确designed，未冒称原服。共享接线/发布/GUI、年糕服用及进阶/装备道具全量继续，目标active。

超级还童事务后续已实现：同角色每宠候选、生成单扣/查询/保存/清除、BASE/悟性/年糕联动、当前资源与技能保留、paid不复活候选和真实root source回滚已过。原当前wire评分316例、年糕count1540及20门禁4例已核；设计分布/支付/资源规则及未验范围集中PET_SUPER_RETURN_INTEGRATION.md。普通还童、实际年糕/高级进阶、共享路由/发布/GUI仍待，全量active；下文“尚无超级保存”为历史阶段。

还童字段批次：已沿原Wuxing控制与刷新指令确认1160是悟性，纠正旧“根骨”和590猜测；原生宝宝/野生身份和完整traits持久化/当前编码已补，见PET_TRAITS_INTEGRATION。新宝宝2/悟性0明确designed、旧未知保持None；实际foods刷新保留非零73，失败回滚/租约/重开已绿。普通与超级还童来源、95uselevel门槛、预览9BE32已核；完整重置/随机/扣丹/保存、原悟性范围/完整score、shared和GUI仍未完成。

普通战斗养护计数已补所属领域：每场1寿命、每3场1忠诚、≤30免忠诚、死亡替代普通计次、擂台与神兽例外；持久mod3余数保留明确designed，多死亡按次数乘数inferred。原入场版本、未知旧计数拒绝、paid当前不覆盖、四保存点及实际root source同事务均已验证，见PET_BATTLE_CARE_SETTLEMENT.md。实际战斗Owner/HP与奖励共享接线、低忠诚行为、特殊PK及现场仍未完成。

## 神兽永生最新状态

PET_IMMORTALITY_INTEGRATION.md已记录原kind2→永生显示158行、9模板忠诚/寿命免损及模板感知care gate。kind3原服务端免损仍未知，单独政策明确designed普通fallback；食品禁用/毒免疫没有借此推定。所属事务、历史回执/只读重放/失败回滚与NPC/食品/source回归绿，实际战斗参与计数、完整还童/进阶、shared发布和GUI仍待完成，整体目标active。

日期：2026-10-23；客户端 1.6.1 / 网络版本601。本批没有修改原始客户端、没有向真实角色发放测试资产、没有重启共享网关。

中毒寿命食品批次：32004/32009已按原品质公式和3%加可信固定draw恢复，精确资质下降点数未知，集中design/pet-toxic-food-v1设计五项基础各1/最低0、先基础后当前血脉/保留潜能、HP/MP只裁超新上限。真实原生decoder、六保存点/外层/钱包/晚期编码/source CAS后失败全回滚、低层和wrapper历史SQL严格只读、实际opaque鲜/历史请求和重开通过。接口、方法和共享随机接线/GUI未验范围见PET_TOXIC_LIFETIME_INTEGRATION；全量目标active。

品质寿命/原门槛批次：32007荷叶羹已按真实品质与原0.5系数恢复；None/0/1无消耗、原maxNum1独立实例、47/48原生显示、真实保存/编码失败及root source同事务通过，见PET_QUALITY_LIFETIME_INTEGRATION。另原帮助36001/36002纠正0寿命选择，普通实际出战care最低50的只读Interface与边界验证见PET_BATTLE_CARE_GATE。当前新资源NPC all实际连接回归已绿，较早导入/map缺口不是当前结论；实际部署、GUI和宠物战斗链路仍未验收。

后续当前状态：普通血脉精华消费已完成所属实现与离线原生验证，见PET_BLOOD_ITEMS_INTEGRATION；下文“暂停精华/生产待继续”是较早阶段。新增统一kind1稳定命令Adapter、真实+200/扣件/潜能分配、保留缺失量且死亡不复活、晚期编码与真实保存失败回滚、低层已付严格只读及实际根来源False/True联动。另通用已付命令当前只读消息已交INVENTORY_CURRENT_MUTATION_MESSAGES。共享接线/部署、奖励/进阶、GUI与实际战斗仍未完成。

本批两项实际进展：血脉基线的基础Profile/有效资质与10×血脉潜能预算已用公开加点/XP/重开验证；原包45级帮助冲突已显式记录并将1级选择标designed。随后按根急需暂停精华接线，交付通用Inventory precommit(callback db/inventory/current_snapshot,*,replayed)。tdd实际MOVE签名红→同事务移动及来源CAS绿；移动/整理回复改为提交前编码，秘籍的真实历史True只经领域意图校验后传出。实际source收据abort、回调晚期失败、原bag溢出均回滚，opaque/current与obsolete租约验证通过。方法/接口/必要回归与未验范围见INVENTORY_RESOURCE_HOOK_INTEGRATION及PET_BLOOD_BASELINE_DECISION；无shared/数值写入、无服务/GUI/实际战斗，目标active。

新人物资源药品消费者批次已完成所属inventory.py分支及离线验证，见ROLE_CONSUMABLE_RESOURCE_INTEGRATION.md。tdd实际红于新构造规则参数缺失→70/40真实药品/扣物/source同事务绿；codebase-design集中显式contract切换与当前重放，writing-for-agents交付构造/位置/同事务三种接线。真实载体与两份凭据保存中断、外层异常、未知cash和原bag数量溢出均回滚，旧profile/迁移前已付凭据/中文租约/reopen通过；未改shared/根数值、未自动迁移、未扩六槽、未部署GUI。另113例普通血脉原指令证据见PET_BLOOD_RESEARCH，生产玩法尚待继续。

当前到期分支更新：`PET_SKILL_EXPIRY_DECISION.md`替代历史“单位未知/到期状态待实现”的阶段结论。原SGameTime解码/全局赋值/除1000/匹配CRT导出及九组原UI边界证明Unix毫秒；所属领域已补冻结完整map、有效快照、空格复用、绝对期限可信奖励与延长、原生带时钟查询及旧v1/v3回执兼容。tdd经既定公开事务/快照Seam完成red→green；codebase-design集中时间注入和同事务保存；writing-for-agents按查询/学习/奖励/定时/battle分支提供接口。实际保存abort、外层失败、缺钱包、opaque LeasedAccounts、原生完整栏和喂养/改名/XP保留map验证通过。规则未知处（普通书永久授予、时槽复用/进度保持等）标designed；造型书原时长仍未知。root时间路由/定时、battle实际效果、部署/GUI未验收，全量目标active。

## 本批实际接入

`inventory.py` 的 `Inventory(accounts, account_id, role_id)` 在选角进入世界时建立，SQLite表与原账号角色共库，所有操作检查归属；`gateway.py` 局部接入消息分派，保留其他窗口的移动、任务和社交改动。

| 能力 | 服务端状态 | 原生协议状态 | 客户端画面实测 |
|---|---|---|---|
| 空/非空背包查询 | 已接入；第三批补非空 | 原物品编码器字节比对、非空整包解码通过 | 未测 |
| 召唤兽栏查询（含非空） | 已接入 | 原解码器完整消费通过 | 未测 |
| 召唤兽改名 | 已接入并保存 | 原SModPetName解码通过 | 未测 |
| 选择参战、休息 | 已接入并保存；选择时查原uselevel | 4字节选择、空休息包来自原marshal | 未测；尚未接战斗属性 |
| 物品发放、堆叠、扣除 | 已有持久化与结算接口 | 第三批补携带物品快照下发，部分语义仍为推定 | 未测 |
| 携带背包移动/拆分/合并/换位 | 第三批已接入领域receive | CMoveItem布局确认，业务规则为本地恢复实现 | 未测 |
| 装备穿脱 | 已接入领域receive，含替换、槽位、等级与角色限制 | 原客户端查询栏4；两栏快照原生解码通过 | 未测 |
| 道具效果 | 宠物回复/喂养已接；人物权威资源事务及上下文Adapter已实现 | 宠物完整刷新与普通世界HP/MP刷新原codec通过；人物共享入口待接 | 未测 |
| 宠物成长 | 已实现主策划designed生成/经验/加点与同事务保存 | 身份顺序修正；等级/资源/五维等原生字节比对通过；其余字段待确认 | 未测 |
| 实例绑定/品质 | 已保存，堆叠/拆分/整理/重登与奖励回放保留元数据 | 原生绑定bit0及给予门禁已确认；受限食品品质详情原读取分支通过 | 未测 |

未知背包类型记录 `inventory_protocol_pending`，不伪装为空背包、不修改资产、不因此断开连接。非法请求记录 `inventory_request_rejected`。这些待接入情况目前没有原生错误提示回复，操作可能没有UI反馈。第三批已替换首批的非空物品pending分支，携带栏只返回未穿戴资产。

## 客户端证据（client_verified）

证据来自当前 `evidence/native-image.bin`、`native_inspect.py` 与原生代码离线执行，不采用其他游戏协议。

- CGetBagInfo `0xc03f2`：i32栏类型、u64目标角色；构造0xd91850，解码0xd918f0。
- SGetBagInfo `0xc03f3`：i32栏类型、u64货币类字段、i32容量、物品集合、u8末标记；构造0xef6220，编解码由vtable0x2284234定位。该u64后续已由原消费者10a4840确认栏1写cash槽+b0/+b4，已修正为当前权威余额；栏4忽略。初期默认0会清客户端现金，详见本批纠正。
- CGetPetcolumnInfo `0xc07de`：i32栏类型、u64角色；SGetPetcolumnInfo `0xc07df`：i32栏类型、宠物集合、i32容量、u8末标记。回复构造0xf20220，vtable0x2284dc4。
- 宠物基础记录构造0xf89ba0，marshal0xf5df70，unmarshal0xf5f1f0。正确起始是i32模板ID、i32实例key、UTF16LE Octets姓名。首批只验证布局而曾把两整数语义写反；本轮由SRefreshPetData 0x1134ff7→0x112ffd0的实例查找、0x1135013的模板字段保存确证并修正，verify_pet_identity.py在旧值失败、修正后通过。非空列表解码成功本身不能证明业务字段语义正确。
- CModPetName `0xc07e2`：i32key、姓名；SModPetName `0xc07e3`：u64角色、i32key、姓名；回复原构造0xdbf7f0、marshal0xe53d10、decode0xf77860。
- CSetFightPet `0xc07d8` / SSetFightPet `0xc07d9`：i32key；CSetFightPetRest `0xc07da` / SSetFightPetRest `0xc07db`：空体。
- 装备请求 `CEquipement 0xc03f5` 是两个i32；客户端0x10e1dd4..0x10e1dda以 `itemtypeid >> 4 & 15` 取得槽号。CUnequipement是0xc03f6；尚未确认完整穿脱及刷新序列。
- 物品记录vtable0x224d4fc，marshal0x822040、decoder0x81a590。第三批已结合消费者定位字段并接入携带栏：内存+4模板ID，+8 flags（bit0绑定），+0xc实例key，+0x10位置，+0x18时间类u64，+0x20数量，尾部u64/i32/u64暂为0。模板ID经0x1081790→0x1080720→0x89d730配置查找直接读取证实；原对象将记录复制到内部对象+8，0x1088e82读取内部+0x14传给CMoveItem的sourcekey，由此定位实例key。位置/flags在后续原消费者回归中纠正并确证；数量语义及整体UI仍需实测。非空生产字节与原序列化器逐字节相同，原整包解码通过，只证明布局，不消除业务语义推定。
- 原表 `citemattr` 提供maxNum、needLevel、itemtypeid；`cequipeffect`标识实际装备定义。`cequiprelative`还含图纸/材料，不能用“在该表中”作为可穿戴条件：37001是1级装备图纸，40100才是对应1级武器。本批已用回归拒绝图纸穿戴。
- `cpetattr` 500001小灰狗：takelevel=0、uselevel=5；服务器允许低级角色持有，但拒绝1级角色选择其参战。

## 来源核对与设计值

已针对PC端资料检索背包、宠物栏容量。官方[宠物获得](https://sdxl.wanmei.com/info/newplayer/10to19/20120626/131962.shtml)是2012年端游资料；[2022年4月28日端游更新](https://sdxl.wanmei.com/news/gamebroad/20220428/237455.shtml)提及“宠物栏6-8”，只能支持后续版本有扩栏道具，不能证明当前1.6.1默认容量。未用手游资料代替。

本批补全集中登记在 `design/recovery-baseline.json` 的 `inventory` 键，不改动其他模块参数：背包40格、宠物6只、改名1至8字符。均为 `designed` 本地实验容量/限制，后续按当前客户端调用与资料替换；没有自动新手奖励。未改变已有角色属性。

宠物尚未确认字段沿用原构造器默认0。新生成宠物采用主策划pet-growth-v1.json的明确designed规则；已有实验宠物不会自动重建。原生消费者已映射的等级/HP/MP/攻防速/五维/潜能已编码，XP、寿命与忠诚后续已确认并编码，成长显示/技能等仍待确认；战斗接入仍要求与人物量级对照。装备已补原roleNeed形象限制与baseEffect快照，性别/耐久/强化等条件仍待完成。

## 方法、产物、验证

- `diagnosing-bugs`：在真实 `Session.feed` seam上先执行 `verify_inventory.py`，得到 `AssertionError: Bag query ignored`；接入后同一输入通过。原因是消息没有处理分支，属于直接可确认的缺失功能；未对它执行多假设插桩。另以原生编解码独立验证，避免自写编码器自证。
- `codebase-design`：资产、归属、容量、事务封装在Inventory的小接口后，Session只负责状态与消息分派；没有修改AccountStore接口。没有宣称本批完成TDD技能或代码审查双轴。
- 产物：`inventory.py`、`native_gameplay_probe.py`、`verify_inventory.py`、`evidence/inventory-verification.json`，以及gateway局部接入、baseline新增inventory键。`pet-default-native.bin`是原构造默认宠物的布局实验产物，不是角色存档。
- `verify_inventory.py`已通过：原生空背包字节对照、非空宠物栏与改名原生解码、99堆叠、部分扣除、背包满时整个发放回滚、跨角色隔离、重开保存、宠物改名/参战选择/休息保存、uselevel限制、装备存储穿脱、槽位拒绝、图纸拒绝、截断原生消息拒绝。
- `verify_gateway.py`已通过认证、加密/压缩、建角、选角、进图和已合入移动持久化回归。原生验证依赖现有capstone/Unicorn安装；生产Inventory只使用标准库。

## 下一批明确缺口与跨模块接口

1. 第三批已接入携带栏非空快照；继续核对数量的UI实际语义与实际拖动表现、其他栏类型、SAddItem/SRemoveItem和穿脱后刷新流程。增减后尚未形成自动逻辑通知/outbox，奖励模块不能仅调用资产写入便宣称客户端已收到刷新。
2. 依据原表恢复宠物HP/MP、五维属性、资质、成长率、经验/技能，记录字段单位后再接战斗；重新登录需同步已选参战宠。
3. 首批 `grant_item/consume_item/grant_pet` 各自开启事务；第二批已提供 `apply_settlement(db, AssetChange)` 加入调用方事务及资产子账本幂等。任务公共凭据、经验、租约检查仍由角色所有者统一接线，详见 `INVENTORY_INTEGRATION.md`。
4. 道具使用不能只减数量；须与人物/宠物效果及资源变更同一事务，原药品公式表已有值但尚未解析调用语义。
5. 尚未重启共享运行服、尚无客户端UI实测。本批只交付已验证源代码与离线结果，不能宣称原生装备、背包和召唤兽全部可玩。

## 第二批：按架构约束交接

已读取根AGENTS与ARCHITECTURE，停止修改共享入口。增加启动只读配置/迁移入口、冻结结算命令/回执、加入调用方事务的幂等资产变更、带inventory_revision的不可变快照。生产同步兼容路径仍明确列为待迁移；没有用全局锁或无界执行资源包裹它。接线顺序、事务语义、验证和未迁移范围集中在 `INVENTORY_INTEGRATION.md`，本批结果在 `inventory-transactions-verification.json`。

## 第三批：非空背包与携带栏操作

- 沿用codebase-design：物品序列化是纯函数item_record，携带栏操作留在Inventory的角色所有权范围；不改共享服务入口，不引入锁/队列/执行器。
- 沿用diagnosing-bugs建立反馈：`verify_inventory_wire.py`首次运行在真实receive接口报 `InventoryNotReady: Nonempty item wire mapping pending`；接入后同输入通过原物品编码器对照及原整包解码。该缺口是明确未实现分支，不进行无关多假设插桩。
- 接入CMoveItem（0xc03f7）：6个i32与1个i64。只支持携带栏1→1，拒绝跨角色及其他栏。source_slot=-1或当前位置；目标-1选空格；count=0表示整堆是本地恢复语义，原marshal只证明count非负。拆分生成新实例key、移动保留key、同模板堆叠不超过原maxNum、不同模板仅整堆换位；每次操作一个事务，回复完整SGetBagInfo快照。
- 产物：item_record、move_item、receive分支、`verify_inventory_wire.py`、`inventory-wire-verification.json`；更新原检查以反映非空查询已实现。
- 验证：非空生产物品与原序列化器逐字节一致，单物品和多物品快照均由原整包解码器完整消费；拆分/合并守恒、整堆移动、不同物品换位、超量拒绝且版本/存档不变、跨角色拒绝、重开位置/key保留；原inventory和事务验证均通过。
- 未验证：真实UI/鼠标拖动、装备穿脱客户端链路、物品效果、原生错误提示、共享入口并发隔离、客户端奖励推送、容量。未重启运行服、未改真实资产。新类型常量通过INVENTORY_TYPES暴露，接线仍需集成方在角色所有者中执行receive并向连接所有者投递逻辑回复。

## 品质、养护与人物用药接线批次

方法：沿用codebase-design，将品质、效果和养护隐藏在角色事务Interface；diagnosing-bugs在真实请求/事务Seam形成失败反馈；writing-for-agents合并当前接线契约，替换已经过时的同步入口、绑定生产者和刷新状态。未改共享入口，未操作正在手动测试的客户端或真实资产。

品质：实例quality为nullable整数，NULL未知与0真实品质区分；四元组AssetChange奖励可带品质，split/merge/arrange/reopen与幂等/回滚检查通过。旧schema启动补列，既有实例不猜品质。原FoodObject 1081870根据模板分支，仅32001..32013、32042/32043读BE32品质；32000不读。SItemTips容器原codec及食品读取到10818ec验证通过，其他道具/装备不能套此bean。

养护：原cpetxuemaiconfig.maxloy按grade1..6为100/100/125/200/300/400，cpetitemeffect和citemattr文本确认31000/31001/31089分别回复5/20/5忠诚；原cpetattr.life提供初始寿命。新宠grade1、初始满忠诚明确designed，未将中档成长擅自等同颜色；已有实例没有care时不初始化，显式迁移需实际grade/loyalty/lifetime。普通死亡扣20忠诚/50寿命采用[2012年官方战斗规则](https://sdxl.wanmei.com/info/qita/fight/20120729/133541.shtml)，仅guide_supported历史规则，当前1.6.1服务器原式未证；擂台、PK、特殊玩法另裁定。主策划/集成接线采用design/pet-care-v1.json。

pet_care.py提供冻结状态、显式初始化、同事务版本与幂等变更。原宠物bean+90经SRefreshPetData msg+98写attr510，bean+b0经msg+b8写attr460，已比对原marshal并执行完整刷新解码。用药/加点均保留完整growth/care字段。食物满值不扣除，部分溢出夹到各自上限；DB扣物品失败使care、版本、凭据一起回滚。死亡事件接口不会由任意HP赋值自动触发，战斗接线仍待集成。

人物：任务窗口的新role_attribute_storage.py现提供权威read_attribute_snapshot/update_role_vitals。本窗口新增use_role_consumable(db,key,epoch,settlement_id)，真实资源、实例品质、扣药、版本与领域回执同事务；外层公共结算仍须一起保存。缺基线不猜训练HP。原历史回执不回写资源，原生重试刷新最新伤势。原二参数receive不能猜epoch/请求身份，故明确交receive_role_consumable(body,epoch,settlement_id)给集成窗口在可信角色命令上下文调用，返回逻辑世界刷新与背包刷新。

世界资源原生证据：SRefreshRoleData 0xc32c8，构造ec3590、marshal ec36b0、decoder ec3730；map元素为i32键+BEfloat32，60当前生命、70当前真气（原cattributedesconfig对照）；原handler113f5f0..113f630执行float转整数后覆盖本地属性map。本批运行原非空map编解码与该赋值分支，宿主仅提供map槽位，UI观察者未运行。只刷新当前HP/MP，未改未知伤势上限或其他属性；float不能精确表示的整数在提交前拒绝回滚。

验证：verify_inventory_quality、verify_pet_care、verify_pet_consumables、verify_item_tips、verify_item_effects、verify_role_consumables、verify_role_resource_protocol均通过。新检查覆盖实际旧schema、原生codec、六种养护上限、外层故障/真实SQLite abort、被替换的真实租约、无基线拒绝、历史回执不覆盖后续伤势、编码失败提交前回滚。原库存/成长/加点/装备及runtime兼容回归通过。结构化证据见对应*-verification.json。

装备下一步证据：EquipObject vtable228c5f4的详情parser是107d960，SItemTips消费它；其prefix手读7个BE32后再读Octets。SEquiptips是单独网络类型0xc0419，构造ef5c50、marshal ef5d80、decoder f70360，前缀8个BE32、wstring及三个容器；不能将这两者当同一blob直接互换。当前只做静态核对，字段含义和耐久/修理等状态还未实现，未发送虚构装备详情。

未验证：本轮没有共享运行服部署、实机UI或商业容量验收；人物原生入口调度待集成；养护战斗回写、技能/血脉/进阶、寿命补充、装备高级系统、其他容器与奖励自动刷新继续在全量执行清单中保持未完成。

## 物品字段纠正、任务宠物经验与普通装备耐久批次

方法：diagnosing-bugs将原item_record送原decoder后，执行81a760复制、10817bc位置消费、1072e70绑定getter及168375b给予分支；codebase-design继续用角色事务Seam隔离任务资格、宠物成长和装备/钱包；writing-for-agents将已核验字段和最新公开Interface集中于INVENTORY_INTEGRATION，替换旧结论。本批未操作运行客户端、未改现场资产/共享入口，未调度已暂停的战斗窗口。

重大纠正：旧生产前四字段模板/位置/key/flags顺序写错。新增verify_item_position_binding首次红例为slot5/binding0在原消费者得到position0/binding1并拒绝给予；正确顺序是模板/flags/key/position。原因是仅序列化/解码比对并不能证明字段语义。原81a760将bean+8复制到对象+10供1072e70读bit0；10817c6将bean+10复制为显示位置+48；给予分支用此getter进入提示140857“绑定道具不能给予玩家”。修正后0/5/39格的绑定/非绑组合全部通过原消费路径，资产本身的绑定/位置存档未改，真实GUI仍未测。

任务经验：按主策划新task-pet-experience-v1，增加selected_fighting_pet/read_pet_state两个同事务冻结读取和experience_capped(amount,cap)结算，cap进入指纹。人物20、宠24获XP最多到25并存余；宠25可存XP，宠26拒绝；不降级、不复活、保持缺血缺蓝。旧未知成长保留实例key和progress=None；任务窗口现在已使用公开Seam，不直接查资产表或私有加载器。原experience保持150普通上限，特殊段未乱映射。verify_pet_capped_awards及既有成长检查通过。

耐久与修理：新增equipment_condition.py、equipment_protocol.py及equipment-condition-v1.json。新普通六槽装备100/100/品质1是明确恢复基线，旧装备需显式实际值初始化且禁止重置。磨损/修理有版本、稳定键、原子cash扣款及领域回执；绑定银不能代付，真实SQLite condition保存abort与外层公共结算故障均回滚全部。历史回执不覆盖后来的磨损；耐久0的已知装备不贡献baseEffect（designed），修复恢复。

原NPC报价函数10dbb20普通分支已离线执行9000例：18原等级行×5品质×缺失1..100。原npcrepair×1.2^(tier−1)的binary64存储与取整顺序保留，level60/tier5/缺25=1295，普通Python pow会给1296。宿主只提供配置查找，其余getter、乘幂、计算和截断为原代码。原600概率采用千分制、有效失败仍收费、失败current夹新max等是设计解释，未称原服务器算法。历史官方[装备打造](https://sdxl.wanmei.com/info/intro/20120623/131855.shtml)支持普通初始100、失败上限−10及max≤10不可修理；特殊修理另恢复。

原CRequestEndures0xc04c6已入receive，栏1/4返回已知普通装备current与maximum，既有未知不漏项、不猜0/满值。原SRefreshEndure0xc0412、SRefreshMaxEndure0xc0414的编解码及handler1093380/1093470按栏/key写+c8/+cc已运行；宿主仅提供物品实例查找，GUI观察者不运行。equipment_refresh(db,key)给集成方当前逻辑回复；修理服务需由地图/角色所有者验证NPC资格、位置与状态，再调用事务Interface。CRepairEquipItem仅布局i32/u64/i32/i32确认，未凭字段猜业务权限，未接裸包修理。

验证产物：item-position-binding-verification、pet-capped-awards-verification、equipment-native-cost-verification、equipment-condition-verification、equipment-endurance-protocol-verification。原inventory/wire/transactions/equipment/growth/role-consumables/runtime兼容检查通过。新repair仅领域/持久化和耐久原生同步完成，NPC服务、完整装备详情、实机UI、战斗磨损、强化/宝石/打造及全量运行验收继续未完成。

## 携带栏现金覆盖纠正批次

原背包处理10a8f40→10a4840证实column1将嵌套bean+8/+c覆盖wallet+b0/+b4（已独立确认cash槽）；column4跳过。固定0并非无害占位。verify_inventory_cash首次在真实原decoder/覆盖分支得到0而非当前2^40+7，红例命中现金显示清零；修正后非空查询、移动刷新、装备栏不覆盖、未知钱包/无租约不猜值均通过。此处沿用diagnosing-bugs的原消费Seam，不用编码字节自证语义。

codebase-design的实际决定：Inventory使用既有read_wallet和可信LeasedAccounts.epoch/currency_rules，不再建第二套币值或从库猜epoch。query的余额与物品在同一读事务，旧无钱包保持待迁移；不为清pending初始化。会回复携带栏的移动/整理/穿脱先验证余额；人物/宠物用药、喂养把效果、扣物品、领域回执、世界/宠物刷新与背包回复编码放入同一事务，缺钱包或编码失败撤销全部。

生产共享入口原RoleOwner已接人物用药context Adapter；本批未改生产入口。旧临时fixture改为显式已知钱包，verify_runtime额外验证未知不发零，再迁移2^40+7正常回复；人物用药切片现金1234、NPC任务切片现金4321保持。这是明确的临时基线，不改变旧角色政策。角色/宠物缺钱包效果回滚、原金额高位、字段消费与库存原兼容检查均通过。

writing-for-agents在INVENTORY_INTEGRATION集中新增cash语义、初始化/租约条件和回滚范围，改掉旧未知字段及共享入口未接线口径。证据inventory-cash-verification、更新role-consumables-verification、runtime-verification、role-consumable-runtime、npc-task-runtime。当前运行客户端/现场库未操作，屏幕现金表现与部署仍未验收；装备详情、NPC修理服务和进阶玩法仍继续。

## 装备颜色/品质纠正与基本详情原消费批次

原字段核验：EquipObject+68是CEquipPrefixConfig品质ID，89d520指向根配置+4b0，其实现RTTI由d41d82的2255884确证；+5c供1073090的费用倍率读取，且10730b0将它交89d4a0/root+470的CEquipColorConfig。普通parser按+60评分与原cequipeffect.scorecolor逐档计算+5c颜色，受prefix.bestcolortype上限约束。颜色六档与品质五档不能互称，早先condition.1里的quality_tier是误标，已修正。

diagnosing-bugs反馈：将原费用检查扩到颜色6时旧EquipmentCondition先拒绝，形成红例；修正政策.2/color_tier1..6后18等级×6色×100缺失量10800例通过原函数。research_equipment_detail.py另执行完整41字节基本详情原读取到107de55，原品质1评分0/292/364/9999得到颜色1/2/3/3，品质5评分9999得到6，验证品质只限制颜色上限，不能直接拿品质作修理倍率。鉴定标志对象+58的原getter分支进入提示142290“未鉴定的装备不能进行此项操作”，不统一留零。颜色、品质、评分、耐久各自字段已分别记录equipment-detail-prefix.json。

codebase-design决定：显式reconcile_equipment_color事务隐藏旧字段格式和审计，调用者提供可信已知颜色；保留旧current/max和完整旧JSON，版本推进，同意图幂等、异颜色冲突，旧迁移回执不覆盖后续磨损。旧政策命令指纹与新政策隔离，不把旧quality值猜成colour。verify_equipment_color_reconciliation覆盖外层失败/审计回滚、重开、旧回执拒绝；没有迁移真实数据。新装备恢复基线仍是白1，五档品质另在完整详情实例模型接入时保存。

当前完成的是基本段与错误语义修正，后续属性/宝石/技能容器未完整执行，未开放伪造的装备详情成功包；NPC修理路由、强化、宝石、打造、实际属性消费者及原客户端GUI仍在全量目标内。writing-for-agents已更新当前接线契约，历史9000/五档描述以本批纠正为准。

## 同事务装备事件接线批次

主策划提出自然新手首师父卡牌→实际穿武器→type59链路，原来源见世界窗口newbie-equipment-sources与newbie-master-cards；本窗口没有猜赠送模板、数量、绑定或改共享入口。按codebase-design，旧equip复用新私有_equip核心，角色/形象/等级查询进入同一个DB事务；新公开equip_transaction(db,key,slot,epoch,request_id)验证当前租约后返回冻结EquipmentEvent，记录服务器真实角色、item key、template、槽位、替换实例和最终inventory_revision。

同键回放明确replayed=True且保留原epoch，不改资产、不重新穿回后来卸下的装备、不给任务新事实；同键异意图拒绝。装备事件与任务窗口的type59资格/进度/公共凭据须同一外层事务；equipment_bag_messages(db,epoch)提供该事务当前携带/装备双栏逻辑回复，提交后连接所有者发送。现有native receive穿脱也合并变更和两栏编码；无钱包/编码失败会撤销穿脱，不能先写成功再掉刷新。

verify_equipment_events.py验证没有嵌套连接/提交、冻结字段、双栏实际cash、历史回放、意图冲突、替换数量/绑定、外层任务式标记失败整体回滚、他人/错形象/错槽拒绝、真实被替换租约拒绝。verify_inventory_cash补充原生穿脱缺钱包回滚；verify_equipment_wire继续通过。任务式marker只是事务Seam故障验证，不宣称真实type59完成或自然客户端已穿戴。writing-for-agents已将具体接口/时序/历史事件限制集中到INVENTORY_INTEGRATION。全量目标继续，实际任务/卡牌/场景接线及UI尚待联合验收。

## 普通装备完整详情与同事务快照批次

方法、决定、原布局、产物与未验证范围集中见EQUIPMENT_DETAILS.md。codebase-design将详情工厂/持久化/编码收在equipment_detail，并提供immutable_snapshot_transaction供角色当前事务组合；diagnosing-bugs执行原构造与完整消费者，并用原截断拒绝及真实SQLite保存失败验证。普通干净新装备详情/当前耐久已接栏1/4，识别1/品质1/评分0/原baseEffect/空高级状态明确designed；旧未知和神兵不套新档。六槽原parser、版本化冻结快照、保存失败全部回滚及既有资产回归通过，未操作现场库或GUI。

## 宠物显示与租约身份批次

原刷新bean+ac成长float、bean+3c血脉颜色已由完整codec/原存储/原UI算术和配置lookup核验，字段不再对已知实例填0。最近float996显示995的反例成立，确定性向上投影确保反显示整数一致，具体bit选择designed；不改growth_raw/100点数规则。加点提交前完成回复编码，真实旧字段溢出会整体回滚。另修装备/快照/人物用药int-only租约，支持原样opaque字符串及正63位整数，字符串00007与7不同；首武器字符串流程已做真实公开Interface事务切片。方法、产物、通过检查与未验证范围见PET_PRESENTATION和INVENTORY_LEASE_TOKENS；未部署、未做GUI或战斗。

## 宠物已学技能与普通秘籍批次

codebase-design将有序原ID和版本化回执放在pet_skills，原native list及原刷新/图标消费者执行闭环；新宠默认前2候选与学习扩格/覆盖规则明确designed。实际book扣除、技能、版本和领域回执同事务，当前Adapter先编码完整宠物和实际cash，缺钱包回滚；历史确认不恢复旧技能。tdd的原公开snapshot/pet_record红例、249/250边界与真实SQLite失败通过。旧未知、绑定/保护和战斗效果未自动补值；共享路由/GUI/进阶仍未完成，详见PET_SKILLS_INTEGRATION.md。

## 2026-10-23：绑定学习与公开卸装事务后续

源码冻结解除后，本模块完成显式PetFlags存档、96条原绑定秘籍在既有无认证学习规则下的原子绑定，以及完整当前宠物栏预编码；原Pet/栏decoder→原标记转换→原绑定查询验证，真实DB保存/回执失败、外层失败、缺钱包及旧租约无部分效果。旧未知flags保留None，其他位完整保留，已绑定不重复改变flags版本；转移资格拒绝未知/绑定/其他未恢复位/参战/放生/他人，完整交易未实现。依据与设计分界见PET_BINDING_INTEGRATION.md。

集成请求的公开unequip_transaction已补，返回独立UnequipEvent，与当前快照/双栏回复同事务；旧请求不会卸掉后来重新穿戴的装备，真实回执abort及外层失败/缺钱包整体回滚，opaque角色租约与重开通过。原EquipmentEvent及装备既有公开Interface不变。共享最终人物属性路径交集成方，见UNEQUIP_TRANSACTION_INTEGRATION.md。

只读原生研究：认证符请求末四项已识别为31254/31255实例key与两个受保护技能ID；Pet+c4是到期映射，原比较过期显示200534“技能空”，并非仅凭结构就能标为保护map。c0800空进度查询/c0801宠物key→16位进度已执行原codec，原UI按signed16消费；其进度条阈值路径仍需补完整执行。见PET_SKILL_OPTIONS_RESEARCH.md及对应三份结构化证据。认证保护/概率/进度/到期领域仍未开放，默认请求限制保持。

方法：codebase-design集中Pet flags/学习/卸装Interface，保持角色事务所有权；tdd在既有公开snapshot/receive及所需unequip_transaction处先红后绿；diagnosing-bugs以真实SQLite失败和原消费者差分验证；writing-for-agents记录接入步骤、完成条件、来源及未验范围。验证为临时库/离线原指令，成长/养护/技能/药品/任务宠物经验和装备事务相关回归通过；未触碰运行服/客户端/shared，当前发布不自动含新源，全量目标active。

## 2026-10-23：认证保护、原进度消费者与概率来源纠正

LearningRules/SkillProgress及完整认证选项已加入同一角色学习事务：精确扣书/认证符、排除受保护位置、累积与保底、绑定成功/失败分支及回执。新宠明确0，旧未知不猜历史。原c0800空查询和c0801按pet key进度map提供，原codec→合并→查询→当前技能数阈值→进度条算术18例通过。公开receive/snapshot、真实progress/receipt abort、外层失败/缺钱包、opaque fenced lease、旧v1回执与当前技能/进度、重开均通过。

原查不到概率时的统一250/1000以及本批临时增幅设计，现已被从官方端游资料站概率入口找到的2017公示原表替代。已读取原图、保存哈希和逐项表值，三认证模式按技能数0..11，含11技能0.02%；学习两draw改0..9999。guide_supported与目标1.6.1精确匹配仍未证，累积/保底/消费顺序保留designed；不冒称全部原服公式。临时v2未发布部署，当前v3。来源、产物、每项完成条件及实际方法集中PET_SKILL_LEARNING_DECISION.md，旧249/250等批次记录仅为历史。

共享c07ff仍需要专用当前上下文路由和固定服务器draw生命周期；本模块不改shared/在线进程。c0800已进INVENTORY_TYPES（16类），不以计数当玩法完成。到期状态、学习动画、被动/主动战斗效果、血脉/高级装备和实际GUI仍继续恢复，目标active。
