# 原 NPC 装备鉴定：495 查询、496 确认及原费用读取

2026-10-24。仅离线第一方研究；未改共享入口、生产玩法、政策、真人库或客户端，未启动、停止或部署服务器。本文将原请求、原客户端行为与尚待裁定的服务器配方分开。

## 方法、产物与结论范围

本批按 `research/SKILL.md` 追溯第一方来源，已委派的研究子任务直接执行；按 `codebase-design/SKILL.md` 区分纯消息 Module 的 Interface 和角色授权/资产事务 Seam。实际决定：原线包仅表达客户端输入，不能承担 NPC 授权、费用币种或属性生成权限；查询回包不能冒充鉴定结算回执。按 `ARCHITECTURE.md`，后续修改装备/货币应由角色所有者在同一事务中完成；本批不实现这些写入。按 `DESIGN_AUTHORITY.md`，能由原客户端证明的字段、控件与数值保留原证，未知配方留主策划裁定。

可重放脚本：[research_npc_identification.py](../research_npc_identification.py)。结构化执行结果：[npc-identification-native.json](npc-identification-native.json)。原指令附证：[npc-identification-native-disassembly.txt](npc-identification-native-disassembly.txt)。本批最终 **56 个离线执行用例通过**；分类见下文。所有模拟依赖标明 Adapter，不称真实 GUI 或真实服务器行为。

主要结论：495 在原客户端先查询装备鉴定状态，收到查询回包才开选择窗口；496 是该窗口生成的本地确认选项，确认时另发 `CIdentifyEquip`。540 是购买鉴定符的父菜单。完整 NPC key 只在查询及回包中传输，最终鉴定请求不含 NPC key。原费用表及其 UI 读取可以确定，服务器币种、资产变更及鉴定生成规则仍未知。

## 第一方来源及完整性

离线映像 `native-image.bin` 的 SHA-256 为 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。下列地址均为该映像的虚拟地址；不是本批向真人客户端读写内存。PFS 读取同时检查解压长度和 CRC；BXML 解码保留原字段。

| 原包/条目 | 解压字节数 | CRC32 | SHA-256 |
|---|---:|---|---|
| config.pfs / autoconfig/knight.gsp.npc.cnpcserverconfig.xml | 420722 | 67481f85 | c6db03275d0d63106623e339742318a38b33d229bc73894d46136e8b9901aa26 |
| config.pfs / autoconfig/knight.gsp.item.cnpcidentifyneedmoneyconfig.xml | 595 | e80deb44 | 1a89aad26ce4601db6775f7da23159ca43ff13f04a37934fde850efa7efb7431 |
| config.pfs / autoconfig/knight.gsp.npc.cnpcconfig.xml | 619832 | cc437e13 | b4fc5d440380fb535a36b8e5315c5a1bf10a99f550f5bfde55bd156fca864f85 |
| map.pfs / map_1007_linan/npc.xml | 11666 | 1d815d03 | ad14d17f41bcbcf706420ab139e6bb43a4878b439220d47794278cf9c9f54aaa |

来源字节、原属性及本批测试数据均记录在 JSON 的 `sources/services/fees/npc_candidates/placements`。源码复用现有 `native_inspect`、`native_gameplay_probe`、`research_npc_submenu.Machine`，未改这些共用工具。

## 原菜单到窗口和最终请求

原服务配置明确：495 文本“鉴定装备”，496 文本“好吧，我要鉴定”，二者无 childservice；540 文本“购买鉴定符（临时）”，描述称可购买 50~80 级鉴定符，其 childservice 为 `[2,10001]`。540 的子项归属原商店/离开菜单，不是本批鉴定请求的授权依据。源：原 cnpcserverconfig 行及 JSON `services`。

495 的第二层服务分派表 `0x163f340`（索引基数 0x117）取值31，由跳转表 `0x163f2a8+31*4` 到 `0x1638310`。原分支调用 `0x109e890` 枚举实例，再用 `0x741740` 检查 vector 是否为空：

- 空列表：直接 `0x10831b0` 取得窗口，完整 NPC key、零参数和 UI mode10 传给 `0x168a1e0`；无查询发出。
- 非空列表：原构造 `0xe6c980`、原 vector 拷贝 `0xf441c0`，保存完整 NPC key 到对象 +0x18/+0x1c，+0x20 置1，在 `0x16383df` 所在调用发 `0xc04cc`。

源：`0x1638310..0x1638406`；脚本 `menu495` 实际执行空/非空两分支，网络出口只捕获原对象。枚举函数本身未整段执行：原 `0x109e994..0x109e9bc` 静态可见仅选 wrapper+8 低4位为8、底层 bean+0x50 字节非零的实例，取 bean+0x14 作 key。**+0x50 的业务名称未恢复**，不能把它叫 identified；原 identified 判据另在 +0x58。枚举以有序 vector 交出，未证明与 UI 排序一致或所有背包栏都能查询。

窗口工厂 `0x10831b0` 对应构造 `0x1683b70`，原 vtable `0x22c6bfc` 的 RTTI 为 `CGiveDialog`。`0x168a1e0` 存完整 NPC key 到 UI+0x58/+0x5c、参数到+0x60、UI mode 到+0x64。不是普通修理窗口。收到状态后开该窗口的真实消费者见下节。

选择窗口确认入口 `0x1688990` 在 UI mode10 调 `0x1688170`。该函数通过原 getter 检查所选物品、读取原费用，然后 `0x1688364` 取底层 bean+0x14 实例 key，调用 `0x1648a80` 保存完整 NPC key、实例 key 和 UI mode0 到确认窗口（+0x38/+0x3c、+0x48、+0x64）。`0x16883ba` 添加496，`0x16883d0` 添加497，再显示确认选项。

确认窗口原入口 `0x1648d00` 在 UI mode0、选496时走 `0x1648fb0`，构造并发送 `CIdentifyEquip(选中实例key,0,1)`；选497取消不发包。脚本既分别执行496/497，也执行一次“原 getter/费用15000 → 原上下文保存 → 原496发送”的串联纵切。文本格式化与窗口绘制依赖适配，不能称整套原 GUI 自动操作。

**496 的含义取决于原 UI 上下文**：主 NPC 菜单的496分派落通用路径 `0x163efbb → 0x163aed1 → 0x1627be0`；不能只按服务号把任何通用 CNpcService496 当成本批三字段鉴定请求。540 有子项，先由父菜单展开机制处理，不把其通用分派地址误记为实际发送。

## 三个原消息的精确 Interface

所有固定宽度字段为大端。i32 指保留 signed32 的全32位；NPC key 保留整个64位 bit pattern，不能截成 NPC 模板 id。count 为原 GNET compact unsigned count，不是固定32位；本批动态覆盖0/1/2/3/127/128，127=`7f`，128=`8080`。没有据此宣称原服务器最大条目数或内存预算。

| 类型/原 RTTI 名称 | ctor | marshal | unmarshal | wire 顺序 |
|---|---|---|---|---|
| 0xc04cc / CRequestEquipsIsIdentify@item@gsp@knight@@ | e6c980 | e6cae0 | e6ca20 | compact count；count 个 i32 实例key；64位 NPCkey；i32 mode |
| 0xc04cd / SSendEquipsIdentifyState@item@gsp@knight@@ | f04490 | f04e70 | f04f10 | 64位 NPCkey；compact count；count 个 `(i32 实例key,i32 state)`；i32 mode |
| 0xc4276 / CIdentifyEquip@product@gsp@knight@@ | dc78e0 | e55760 | dc7980 | i32 field1；i32 field2；i32 mode，共12字节 |

原 vtable 分别 `0x2281584`、`0x22845f0`、`0x227bfdc`。每个测试先原 ctor→原 decoder，再对同一个解码对象用原 marshal 重新输出，要求逐字节相同；不是拿 Python 编码器互相比较。实际原网络发送另由 UI 执行用例捕获。

`0xc04cc` 对象 +8 为 vector<int>，真实 begin/end/cap 在 +0xc/+0x10/+0x14；NPC key 在 +0x18/+0x1c，mode 在+0x20。`0xe6ca20` 在解码 vector 后读取 key 与 mode，没有字段范围验证。原样往返已证：乱序与重复 `[92,91,92]`、key `[-2147483648,0,2147483647]`、mode 最小/最大 signed32、NPC key 高32位 `0xfedcba98` 和全零。**这些只是 codec 接受度，不是合法请求授权范围**。495 原按钮填 mode1。

`0xc04cd` 明确是 vector 而不是 map：原 RTTI `STLContainer<vector<EquipIdentifyState>>`、bean vtable `0x2284614`，内存元素 stride12（含4字节vtable），线上每项仅8字节。bean marshal `0xf04d80`、decoder `0xf047a0`，依次两个整数。原 decoder `0xf04fb3` 调 `0xf04e10`，逐项在 `0xf04e42` 检查 **signed key>0**；key=0、-1、min 均由原 `0x1919292` 抛错，max 通过。state 和 mode 没有枚举限制，min/max 原样通过；空 vector 通过。乱序、重复和128项原样往返，不能去重或转 dict 改写消息语义。

`0xc4276` 原 serializer `0xe55760` 三次调 `0x770960`；decoder `0xdc7980` 三次读4字节并 bswap，无业务范围验证，原校验函数 `0xdc7900` 返回1。`(-1,-2,-3)` 和 `(min,0,max)` 可原样往返。**没有 NPC key、物品栏、币种、费用、重试ID**。NPC确认路径字段为 `(实例key,0,1)`；另一原物品交互静态路径 `0x10f25b0..0x10f25fd` 从两个底层 bean+0x14 取不同实例 key，填 mode2。后者未执行完整交互前置，field2 不据此强命名为鉴定符，也不授予 NPC mode2。三个包各缺末字节时原 decoder 均抛错。

例：fixture NPC key `0x1234567800002a8a`、实例91和92、mode1 的查询体为 `02 0000005b 0000005c 1234567800002a8a 00000001`；最终NPC确认体为 `0000005b 00000000 00000001`。fixture 高位任意，用于证明64位保留，不代表真实地图 NPC 实例key。

## 状态回包的原消费者

`0x10934a0` 逐项调用 `0x1091670(key,1)`，此处 **物品栏固定1**；若找到已存在的 wrapper，将 state 原样写底层 bean+0x58；找不到则跳过。之后拿回包完整 NPC key 打开 CGiveDialog，mode==2 选UI43，其他mode选UI10。源：`0x10934e3..0x1093539`。

六个 handler 执行用例：mode1/2；重复key按vector顺序写最终值；state=-1按原32位原样写入；找不到实例不造新物品；空vector仍打开窗口。库存查找和窗口工厂为 Adapter，原循环/栏位参数/写入/模式分支实际运行。回包 mode2 的 UI43 完整业务未恢复，不能与 NPC496 配方混用。

这是查询结果同步，不是“鉴定已成功”的独立回执。没有证明最终鉴定使用此包回报，也没有证明鉴定只把 +0x58 从0翻到1；没有证明属性是否重随机或具体参数。最终扣款、生成结果、原消息刷新顺序及失败码仍需独立证据/设计。

## 原选择资格和费用

`0x1688170` 检查5个选择位置（stride0x138，共0x618字节）；最多一个：第二件立即到 `0x1688283`，无选择到 `0x16882a4`。原 getter `0x1073110` 先要求 wrapper+8 低4位为8，再看 bean+0x58；非装备或该值非零在 `0x168825d` 拒绝。调用原等级 getter `0x1074d10` 后，`0x16882bb` 拒绝>150，`0x89d820` 取得原费用表，虚函数+8以同一 getter 等级精确查记录；记录 id=-1 在 `0x16882e3` 拒绝。没有插值公式。

本批 fixture 的普通 kind8 实际从 wrapper+0x28 读等级；**尚未追通 CItemAttr.needLevel/equiplevel 等真实配置字段复制到 wrapper+0x28 的路径**，因此这里只证明原 getter 到费用 lookup，不命名为真实模板等级已证。fixture 也不证明所有普通六槽模板都有鉴定权限。原 `0x1074d10` 对完整 kind0x1c8/0x2c8/0x3c8，会优先取 bean+0xd0 的正数且≤1000，否则回 wrapper+0x28。本批未证明这些特殊类型的实际物品生成/鉴定资格，也未将其纳入普通实例配方。

费用表 reader 的 `0x8703b6` 使用 UTF16 字段名 `0x2253b68 = needmoney`，`0x8703df` 写记录+4；选择 UI 在 **0x168830f 读记录+4，0x1688312 push** 用于确认金额文字。16行原 PFS 值如下，各行均执行原 getter→lookup参数→真实记录+4读取，不拟新数值：

| 原等级id | needmoney | 原等级id | needmoney |
|---:|---:|---:|---:|
| 1 | 100 | 80 | 50000 |
| 10 | 250 | 90 | 100000 |
| 20 | 500 | 100 | 200000 |
| 30 | 1000 | 110 | 300000 |
| 40 | 2000 | 120 | 400000 |
| 50 | 15000 | 130 | 500000 |
| 60 | 20000 | 140 | 600000 |
| 70 | 30000 | 150 | 800000 |

六个原选择负例：已鉴定1、无选择、选择2件、等级151、等级51查不到行、非装备 kind=18（十进制18，即0x12，低4位2≠8；不是装备槽位18）。对应真实拒绝地址均保存在 `negative_selection`。费用 lookup 适配精确表行/缺失行，不把它称原 XML cache 初始化执行；所选物品 wrapper 为明确布局 fixture，不冒充真实服务器实例。

已证 slice 内未见钱包余额扣减或币种选择检查；它是客户端资格和报价文字链，**不是免费证据**。原 needmoney 可作为金额来源输入，但现金/绑银归属、旧实例准入、物品类型范围、失败是否消耗、服务距离复核与结算幂等需要主策划明确配方，不能套普通修理。

## 原 NPC 摆放与服务绑定的区别

原 CNpcConfig 的10890名为“装备鉴定师”，mapid1007、xPos248、yPos331、modelID5116、npctype1、bodytype0、hide0、leaveservice“什么都不干”。原 map_1007_linan/npc.xml 确有 id10890、posx3972、posy5299、dir5，证明原摆放；JSON `index_in_iter=75` 仅是遍历索引，不是地图实例key。

**两份原记录都没有495/496关联字段**，原服务表提供文本/子菜单模板，不能从 NPC 名称、图标或摆放反推其服务器菜单授权。本批没有确证10890→495/496真实绑定，也未找出另一个具有确证绑定的 NPC。查询试验的低32位取10890仅作高位保留 fixture；不把它写成已恢复真实 NPC 服务。若后续决定启用该绑定，应明确设计来源，或补原服务器菜单消息证据。

## 执行分层、Adapter 与交接缺口

| 层次 | 数量 | 证明范围 |
|---|---:|---|
| 原 ctor/decoder/marshal 往返 | 17 | 3包顺序、32/64位、vector保序/重复、compact128、字段范围接受度 |
| 原 codec 拒绝 | 6 | 回包key≤0三例，三包截断三例 |
| 原495菜单分支 | 2 | 空开窗、非空查询并保留完整key/mode1 |
| 原回包消费者 | 6 | 物品栏1、循环写入/重复/不存在/空、UI mode10/43 |
| 原 getter/费用读取 | 16 | 每个原费用行经真实选择路径读出 |
| 原选择负例 | 6 | 已鉴定、空、两件、超限、缺表行、非装备 |
| 原确认按钮 | 2 | 496发送、497取消 |
| 报价→上下文→实际确认串联 | 1 | level50/15000、完整NPCkey缓存、最终(91,0,1) |

Adapter 仅承担离线宿主 CRT 分配/释放/checked copy、库存枚举/查找、配置 lookup、网络发送出口、窗口工厂及绘制依赖。实际原集合/序列化/字段读写/分支保留。UI 选择使用布局 fixture；格式化在 `0x16882ec→0x168830f` 和金额读出到 `0x1688364` 之间跳过，确认窗工厂及绘制不模拟真实控件树。最终从原1648d00发包，未实际发网络。没有宣称一次从真人鼠标点击到真实服务器结算的端到端验收。

代码现状复核：`equipment_detail.py` 的 identified0/1 是明确干净实例的存储表示，不是鉴定结算配方。根任务同期另建 `npc_identification_protocol.py` 为纯消息 Module；本研究不重复修改或验证其实现，不因它存在而声称玩法已接线。研究输出只作为独立原 codec oracle 和领域设计输入。

留给根任务/主策划：确认 NPC→服务绑定及开放范围；冻结查询/选择/确认上下文的授权生命周期（最终请求无NPCkey）；定义只读状态查询与写入鉴定的不同 Interface；确定币种、资格、原等级getter对应的服务器数据、属性生成/保留规则、失败支付、同角色原子结算/凭据和完整原生刷新。原请求无重试ID，新命令与重复网络意图的语义也需明确。以上未完成项不由本批研究擅自补全。
