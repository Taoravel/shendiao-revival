# 普通六槽973模板：装备资格与干净实例范围

2026-10-23；本地端游1.6.1、网络601。按research/codebase-design重读技能及DESIGN_AUTHORITY/ARCHITECTURE后，只读原PFS、原映像和当前源码。本批仅写本文，不改生产、政策、共享入口或存档；没有GUI、服务、认证现场、真实角色或战斗操作。v1默认10件师承白名单保持。

## 可交接结论

原1038集合中，**973条非空flat**仍为875+98（增加独立1240封印抗性基线后）；资格元数据可以完整带入模板DTO：`template_id、itemtypeid、equipment_slot、need_level、item_level、allowed_character_ids、sex_need、base_properties`。roleNeed空表示该检查不限制，sexNeed0表示不限，1/2须匹配原人物性别值；**49197原roleNeed=[20,21]确实落973**，不能把全表角色ID强限定1..10或改成空列表。当前十角色没有匹配即可拒绝它。[S1–S4、N1–N3]

当前Inventory实际函数名是 `_equip`，没有 `_equip_item`。它已检查角色/实例归属、数量1、未装备、原槽号、非空roleNeed和needLevel；**尚未检查sexNeed**。不能把“已经Inventory穿上”当作新六槽投影所有资格已经有效。[inventory.py](../inventory.py:956)

`identified=1、prefix_quality=1、score=0、实例base_properties与原模板有效配对精确相等`是可给root采用的**明确干净恢复设计范围**，不是由这四项就证明任意旧实例绝无高级效果。未知旧详情、改造/宝石/附加/强化/扩展、神兵、百分比1条及基础列表缺失64条仍独立拒绝/待补；不自动升级旧档。[EQUIPMENT_DETAILS.md](EQUIPMENT_DETAILS.md)、[equipment_detail.py](../equipment_detail.py:114)

## 原始来源和全量校验

沿 [ORDINARY_EQUIPMENT_ATTRIBUTE_RESEARCH.md](ORDINARY_EQUIPMENT_ATTRIBUTE_RESEARCH.md) 的口径：cequipeffect与citemattr同ID，`itemtypeid & 15 == 8`，`(itemtypeid >> 4) & 15 ∈ 0..5`，排除明确cgodweapon ID集合；不筛givetype。原属性映射必须通过cattributedesconfig.numid/percentid逆索引，不能末位减1。

本轮直接 `PfsArchive.read` 验目录/本地头、解压长度、CRC，再BXML解码；citemattr、cequipeffect、createroleconfig的**全表属性和全部lists**与当前catalog逐条一致。973重新从原表非空baseEffectType且全部命中numid构成，和既有 [ordinary-equipment-base-effects-audit.json](ordinary-equipment-base-effects-audit.json) 的875/98分组一致。

| 来源 | artres/config.pfs中的autoconfig路径 | 行数 / 字节 / CRC32 |
|---|---|---|
| S1 | knight.gsp.item.citemattr.xml | 12280 / 4096369 / a3add081 |
| S2 | knight.gsp.item.cequipeffect.xml | 1521 / 467441 / e354a76d |
| S3 | knight.gsp.item.cattributedesconfig.xml | 195 / 19508 / 56e2ca7e（沿既有原包审计映射） |
| S4 | knight.gsp.item.cgodweapon.xml | 85 / 3704 / 65746fc2 |
| S5 | knight.gsp.role.createroleconfig.xml | 10 / 13107 / 0758d770 |
| S6 | knight.gsp.item.cequipprefixconfig.xml | 6 / 291 / c8592725 |

S1 SHA256 `974a3b38049c5f5f7cdae418718ffadd2741d373a5846a40fb71289af25e726f`；S2 `8ef1aacae8d016f875a37a8cf907b16a077b89fa522a87e349dd54d320572fe8`；S4 `295fbe76d7deaef3bb4c17733f329ce41384c5724b6aef713b93a7a6abfa86a2`；S5 `770da32d88784144e453c386c9cce05de03746943eb6004158d3cc53c9428132`；S6 `3b36fed5bf4e62e41ceec422d902f8479bdcc487e82351750168ba130805e7ae`。原native-image.bin及VA沿既有同版映像，未重新采集或执行原生代码。

root已修正旧报告三个误抄示例，并追加 [ordinary-equipment-example-correction.json](ordinary-equipment-example-correction.json)。本轮直接原包再次确认：44000青布衣101/141=**33/4**；45000百草结141/821=**16/3**；46000灰布鞋101/821/131/121=**4/2/4/10**。42000蓝布腕1241/101/151=6/13/10不变，师承49001..10=25/15/8不变。原包哈希没有变化，不是原数值修订。

## N1：真实装备槽

原装备发送路径 `0x10e1dd4–0x10e1dda` 对物品itemtypeid右移4再&15；实际CEquipement0xc03f5带实例key和slot两个BEi32（既有原codec），不由模板名称决定部位。另原穿戴调度 `0x10a95d9–0x10a95e4`同样计算slot；超六槽的9/10另有分支，不能收进普通0..5政策。

| slot | 本版部位 | 1038中条数 | 973非空flat条数 | 973中roleNeed空 | 973中sexNeed 0/1/2 |
|---|---|---:|---:|---:|---|
| 0 | 武器 | 632 | 579 | 17 | 578 / 1 / 0 |
| 1 | 护腕 | 102 | 98 | 98 | 1 / 49 / 48 |
| 2 | 项链 | 58 | 58 | 58 | 58 / 0 / 0 |
| 3 | 衣服 | 114 | 107 | 107 | 5 / 51 / 51 |
| 4 | 腰带 | 67 | 67 | 67 | 67 / 0 / 0 |
| 5 | 鞋 | 65 | 64 | 64 | 64 / 0 / 0 |
| 合计 | 六槽 | 1038 | **973** | **411** | **773 / 101 / 99** |

“空”包含没有roleNeed子节点的情况；解析后vector无元素，与原消费者空长度分支一致。没有独立头盔槽。1038全体sexNeed0/1/2=828/106/104，roleNeed空423/非空615；不要与973子集混用。[S1/S2]

## N2：roleNeed空列表与角色身份

原字段/对象链：

1. CEquipEffect parser `0xbac3df–0xbac3fb`认UTF16 roleNeed（`0x2265988`），读列表到配置`+0x38`。
2. Item装备对象创建 `0x1080e9a → 0x89d4c0`按template查配置；`0x1080f10–0x1080f17`把该列表复制至EquipObject`+0x70`，vector begin/end在`+0x74/+0x78`。
3. 真实穿戴调度 `0x10a93e5–0x10a93ee`调用 `0x10771d0`；失败拒绝并给本地提示。
4. `0x10771d1–0x10771e9`先检查低位装备类型，非武器槽在该函数直接true；武器进入`0x10771fb–0x1077210`，begin空或(end−begin)/4为0时直接true。**不是空列表代表无人可用。**
5. 武器非空时，`0x1077216–0x1077259`逐条比较；`0x107724d`调用人物 `0x1129490`，后者以当前人物shape`+0x120`除10取余，余0转10。任一匹配true，遍历结束false，即OR集合。

S5把十个CreateRoleConfig ID与三色shape完整关联；973 DTO宜保留该30形象显式映射，拒绝未知shape，不能让客户端另传character/gender。原shape余数逻辑解释本30形象，但不能据此自动支持任意未知新shape。

973中17件空roleNeed武器为：40109、41100..41108、41202..41208。非空562件全部是武器；无需把空列表补为十ID，DTO保持原空，资格判定实现其不限语义。

**49197例外**：原“似曾相识的武器”，itemtypeid1288→slot0，level/needLevel=10/10，roleNeed=[20,21]，原baseEffect81/811/1231=80/80/30；用途文本为冲星/镶嵌任务引导。它有非空flat因此在973，但原消费者当前character返回1..10，不会匹配20/21。保留该条是模板数据覆盖；不能称其当前角色可穿或用名字排除后偷偷减少计数。

## N3：sexNeed与原人物性别值

字段和真实穿戴判断闭合，不依赖角色名字：

- parser `0xbac1ae–0xbac1da`识别sexNeed（字符串`0x226b1b0`），写CEquipEffect`+0x24`。
- 装备创建 `0x1080f1c–0x1080f23`将该值复制到EquipObject`+0x6c`。
- 真实穿戴 `0x10a93a2–0x10a93b9`取`[EquipObject+0x6c]`比较人物`+0x160`；相等通过，不等时sexNeed0仍通过，非0拒绝。**0不限，其他值按精确相等，不按奇偶。**
- SEnterWorld `0x833908–0x83393c`对原shape除10取余：余1..5写临时人物信息sex=1，余0/6..9写2。`0x833f66`取临时结构esp+24，`0x833f84–0x833f99`交人物初始化；`0x113b430–0x113b437`将结构复制到人物+f8，内部 `0x113ac20–0x113ac2b`复制source+68到dest+68，即人物+160。临时sex原地址esp+8c正是结构+68。

因此本包30种color1/2/3形象，CreateRoleConfig **1/2/3/4/5→sex1，6/7/8/9/10→sex2**，其中10的shape末位0，仍为sex2。此处1/2是原数值；官方防具表把蓝布腕等标适合“男”，可作1对应男性、2对应女性的guide_supported旁证，不用角色叙述推断数值。[S5、官方链接见末节]

当前 `_equip`只查level/shape并检查roleNeed/slot/needLevel，没有sexNeed检查。纯投影再次检查sexNeed可以阻止非法存档贡献，但真实穿戴操作也应在同事务提前拒绝不合格实例；这项接线由root/库存窗口决定，本报告未修改。

## N4：needLevel与level，不混为同一字段

原CItemAttr parser `0x86eb18–0x86eb41`将needLevel读至配置+74；ItemAttr复制 `0x10728ed–0x10728f0`保留同偏移，外层Item配置起于+4，故Item对象+78。原通用物品使用路径 `0x10a99ba–0x10a99ca`取Item+78，对比 `0x1135590`读取人物属性490，要求needLevel≤当前等级。[S1]

**证据边界**：本轮查到的直接装备调度 `0x10a9360`、右键入口 `0x10ace76–0x10ace91`没有同样needLevel比较；不能把通用使用路径冒充已经闭合的原客户端穿戴门槛或原服务器代码。官方端游说明必须达到装备“要求等级”方可用，支持恢复的等级限制方向；**采用needLevel作为服务端穿戴门槛仍应注明现恢复政策/原字段与旁证支持，未恢复原服务器校验实现**。不拿这个缺口替换原值或停止现Inventory既有校验。

当前 `_equip`确实比较 `citemattr.needLevel`；`Inventory.repair_equipment`使用 `citemattr.level`作修理算法输入。原level也体现模板档位/制造相关资料，不能因通常相同就以level替needLevel。973中的22个不相等实例：

- level100/needLevel1：45011、49529、49564..49572（11件）。
- level60/needLevel10：49191（1件）；百分比例外49192也为60/10，但不在973。
- level120/needLevel110：49573..49582（10件）。

这两字段应分别保存，不能将45011误判需100级或将原needLevel1改成100。givetype只保留原元数据，不用于推断掉落、奖励绑定、鉴定或穿戴许可；[NEWBIE_EQUIPMENT_RESEARCH.md](NEWBIE_EQUIPMENT_RESEARCH.md)已明确不给givetype偷加业务枚举。

## 干净实例与prefix/score的严格范围

现 [EquipmentDetail](../equipment_detail.py:16)是冻结值：identified 0/1、prefix_quality1..5、score非负signed32、唯一修饰ID的base_properties tuple。类型构造只证明可表达，**不证明任意prefix/score可按模板平加**。

原完整EquipObject parser/颜色差分已见 [EQUIPMENT_DETAILS.md](EQUIPMENT_DETAILS.md)：`research_equipment_detail_full.py`确认当前首属性map、附加三元组、宝石列表、强化及多组扩展独立存在；普通颜色由scorecolor阈值和prefix cap共同算。S6原bestcolortype为1→3、2→4、3→5、4/5/6→6；因此不能拿物品食品quality、颜色、评分和prefix当一个字段。`DetailRules.color`只复现颜色计算，不计算角色战斗总属性。[equipment_detail.py](../equipment_detail.py:87)

建议root新policy显式限定（当前root已提出，本文只记录依据/边界）：

1. 模板在973、非神兵六槽，原非空有效配对全是flat numid，保留原roleNeed/sexNeed/needLevel，真实角色30形象映射与原槽匹配。六件尾零填充只允许原已核验多余尾值全0截断，有效属性配对精确保存。
2. 当前ItemState的quantity=1、equipment_slot等于模板slot且0..5不重复、bag slot为`-equipment_slot-1`、role一致、实例ID唯一；不要保留v1只允许bag slot=-1的硬编码到其他槽。[inventory.py](../inventory.py:956)、[role_equipment.py](../role_equipment.py:169)
3. `quality is None`，EquipmentCondition与EquipmentDetail均显式存在；identified1、prefix_quality1、score0；base_properties与该模板原有效配对精确一致。已知其他值拒绝，不以同颜色或同评分替代精确属性。耐久0的贡献由既有版本化政策决定，不能把未知耐久当完好。
4. 详情必须来自已初始化版本和可信clean origin；新恢复授予或显式确认干净旧实例可走现 `initialize`，未知旧实例不可凭模板自动生成。当前持久load会检查revision/origin，但冻结ItemState.detail不携带这两个字段，跨Module投影必须把“由可信同事务Inventory读取产生”的Interface前提写清，不把外部任意构造四字段DTO当完整来源证明。[equipment_detail.py](../equipment_detail.py:129)、[inventory.py](../inventory.py:472)
5. 原map flat求和是本地基础投影设计；原服务器全部实例生成/求值并未恢复。已确认复杂实例有不同base_properties或prefix/score也不归此窄政策；现 `Inventory.equipment_attributes()`允许无详情回退模板及已知实例任意map合计，它不是严格人物投影资格检查器，不能直接拿其输出绕过上述条件。[inventory.py](../inventory.py:493)

973中原suiting非0有212条、0有761条；本批只保留元数据，不恢复套装公式、不将其当穿戴许可。若policy支持973的基础项，应明确“仅基础投影、套装效果另待恢复”，不能因此宣称这些模板所有玩法/最终装备属性已经完整。百分比公式、五维附加、套装、神兵及宝石/强化未知状态不能被四字段clean表示静默吞掉。

### 可交接的最小模板DTO与验证责任

| 字段 | 来源/校验 | 用途/状态 |
|---|---|---|
| template_id | S1/S2同ID，明确不在S4 | 稳定模板身份；client_verified |
| itemtypeid / equipment_slot | S1原值；原位运算且低位8、slot0..5 | 真槽号；client_verified |
| need_level / item_level | S1原两个字段，均保留 | 前者用于现恢复穿戴限制，后者不代替前者；原服务器门槛实现未证 |
| allowed_character_ids | S2.roleNeed原tuple，包括空/20/21 | 原武器OR/空不限已闭合；不硬裁剪成1..10 |
| sex_need | S2.sexNeed原值0/1/2 | 原相等或0不限已闭合；形象映射来自S5+原指令 |
| base_properties | S2有效非空配对；S3真实numid→人物key | 只flat、保留原整数及顺序，不以显示色重新算 |
| raw_suiting / source fingerprint | S2原值、政策版本与原表指纹 | 范围审计；不授予套装/掉落资格 |

人物投影还须显式裸身1240基线（新角色0为designed、旧未知None拒绝）、当前裸身成长及同事务当前Inventory版本；这与模板覆盖是两个条件。默认v1和已有角色basis不能因新loader存在就隐式换policy。详情来源/资产资格集中在Inventory，属性组合集中于role_equipment这个Module的Interface，公共调用方不复制一套装备表/资格推断。

## 官方端游旁证与版本限制

本轮定向搜索官方“装备 穿戴 等级 性别 护腕”“装备 评分 基础属性 品质”：

- [2013-08-30装备系统解析](https://sdxl.wanmei.com/news/gamenews/20130830/149369.shtml)：达到装备要求等级才可用；六部位；基础、附加与强化、套装是不同来源。支持范围划分，未给本973的服务器资格函数或平加公式。
- [官方防具表（2012路径）](https://sdxl.wanmei.com/info/qita/drug/20120728/133476.shtml)：蓝布腕/青布衣等列男性、女性装备；与原sexNeed消费者合看，不依据角色名字推断数值。
- [2012-07-05装备打造](https://sdxl.wanmei.com/info/newplayer/50to69/20120705/132376.shtml)：品质五档与颜色六档分离，评分反映属性，品质限制颜色上限；不足以给出prefix_quality/score到本地原baseEffect的完整生成或总属性公式。

未用手游、神雕2、2023化境或其他后期规则覆盖本地1.6.1原值。官网没有给缺失原服公式，故严格clean范围仍由root设计登记，不能改标client_verified。

## 方法、产物、验证与未验证

research实际用于原PFS→完整属性/lists目录比对→973资格分布→parser复制→真实穿戴消费者与人物初始化链→官方窄旁证；发现20/21保留原数据，发现needLevel只闭合通用使用消费者则明确限制结论。codebase-design实际用于区分模板DTO、可信Inventory当前实例、人物基线/聚合和协议显示的Interface，不让“可构造详情”代替“已确认实例”，不新建账本或全局锁。

产物仅本文。完成的验证是原包CRC/长度、全表catalog一致、973/各槽/sex/roleNeed/例外计数，以及只读原指令追踪；没有新codec执行、脚本玩法测试或大回归。当前源码有其他窗口并发维护，本文函数行号取本轮末次读取，身份以函数名为准。

未验证：原服务器完整穿戴校验、全部时间/任务物品限制、prefix/score参与实例生成与全部属性求值、未知高级扩展、套装效果、真实客户端表现和旧档迁移。资格检查与973模板静态覆盖不等于已接入、已部署、已在真人角色生效。
