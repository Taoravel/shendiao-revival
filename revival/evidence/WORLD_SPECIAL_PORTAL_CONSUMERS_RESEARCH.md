# 住宅与同图门户的原客户端消费者

2026-10-23。本批按 research 从原包、原映像消费者及原codec取得证据；本身是委派的后台研究。先读 [WORLD_RESOURCE_HANDOFF_AUDIT.md](WORLD_RESOURCE_HANDOFF_AUDIT.md) 和 `audit_world_special_portals.py` 两分支，再将“成对1..25可能是房号”收敛到真实消费者，而不修改原goto或现有Owner政策。沿用根AGENTS、ARCHITECTURE和DESIGN_AUTHORITY，来源与执行范围分别标明。

**可确认：1594的destx1..25是住宅位置键，客户端用它查询服务器下发的房屋信息，并与25条原房屋位置表一致；不是普通目标像素。1627在已执行的客户端生命周期和门户标记分支走普通地图路径，不触发住宅信息请求。但本批仍未证明1627门户原服实际下发哪一种位置/场景消息，亦未证明住宅进出实例的完整服务器合同。**

## 可复现产物与真实范围

- [verify_world_special_portal_consumers_native.py](../verify_world_special_portal_consumers_native.py)：独占新增离线脚本，不导入或运行MapOwner，不改冻结脚本。
- [world-special-portal-consumers-native.json](world-special-portal-consumers-native.json)：25个结构案例通过；25个住宅门口与原配置逐项一致；原PFS各entry/长度/CRC读取与SHA256保留。
- [world-special-portal-consumers-disassembly.txt](world-special-portal-consumers-disassembly.txt)：门户、住宅初始化/响应、UI拜访builder、位置表消费者的原指令。
- 唯一算法映像 [native-image.bin](native-image.bin)，基址0x400000，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。

原生fixture继承只读研究的NativePath内存环境，只适配CRT allocation/free、cookie、memset/memcpy。图形marker创建、加入显示列表、清表、XML刷新、Scene表赋值停在明确边界；这些边界被记录，**没有执行渲染或声称完整场景加载成功**。网络发送终点为隔离内存中的capture sink，无任何网络调用。codec使用既有probe的wstring/CRT/interlocked Adapters，原协议与map迭代/标量写读指令仍实际执行。普通场景通知fixture只在正常Scene回调边界捕获参数，未执行回调内部世界重载。

没有启动客户端、GUI、服务，没有访问运行进程/存档，没有修改生产Module、共享入口、政策或地图目标。

## 原资源与住宅位置键：client_verified

本批重新读取原config.pfs及map.pfs，非仅引用catalog：

|原entry|数量/事实|
|---|---|
|autoconfig/knight.gsp.map.cmapconfig.xml|1594..1598 dynamic1；1627 dynamic0|
|autoconfig/knight.gsp.home.chouseweizhi.xml|25行，id1..25；有npcid、xpos/ypos、xwaijing/ywaijing、xchuansong/ychuansong、jiayuanshape|
|autoconfig/knight.gsp.home.chousegoup.xml|20行；level1→1595、level2→1596、level3→1597、level4/5→1598；有xdaoda/ydaoda|
|autoconfig/knight.gsp.home.cxiaoqu.xml|17,992行，zoneid、小区id/name及housenum；全部housenum25|
|map_1594_shequ/goto.xml|625格；25组目标destx=desty=1..25，每组25格|
|map_1595_jiayuan /1596_jiayuan1 /1597_jiayuan2 /1598_jiayuan3 的goto.xml|每份25格，原target均为1594,(376,293)|
|map_1627_bishuihantan/goto.xml|25格；原destmap1627、destx101、desty115|

25组住宅门户源位置中心，逐项等于同id `Chouseweizhi.xchuansong/ychuansong`。例如id9：源5×5格(130..134,74..78)，中心(132,76)；位置表id9为npcid12707，xpos/ypos(137,72)、xwaijing/ywaijing(129,80)、xchuansong/ychuansong(132,76)。id1中心(20,31)，id25中心(45,199)。全部25项检查通过，而不是仅凭1..25数值重合。

这仍不独立证明desty业务含义；当前原消费者下面只读取destx。不能由成对字段推定它们组合编码社区/房主。

## 原goto消费者：源标记与住宅表查询，不是传送执行器

`CGameScene 0x11dec90` 由 `Scene+168` 资源目录拼接 `/goto.xml`（常量0x22972c8），经 `11c6030` 读表。`11ded9f..11dedaf` 每条原记录跨度8字节，至少25项；首轮取index12，之后每次+25，因此为每组5×5入口取中间一格。后续读取 `posx`（常量225b650）、`posy`（225b644）、`destmap`（22972b8）、`destx`（22972ac），本链没有desty读取。

`11def6d` 按**当前场景模板**选择：

1. **1594**：`11def7e..11def90` 以原destx为key调用 `11cf0b0`，在 `Scene+454` 的std::map查房屋信息。缺key即不建marker；若命中节点 `+20/+24` 的q64全0，也不建。非0才调用World虚表+94创建标记。
2. **1595..1598**：`11df053..11df085` 创建另一种marker，传给World+94的第二参数为1。
3. **其它普通场景，含1627**：`11df087..11df0bd` 创建marker，第二参数0。这里不查住宅表。

World+94接收的是入口**源格**渲染位置 `posx*24,posy*16`，不是destx/desty目标位置。故“1627也会显示普通传送标记”不等于“已证明服务端同图瞬移合同”。这个函数既未把原目标坐标提交给网络，也没有自行改角色到目标。

本批实际执行10个分支案例：1594 key1/9/25命中且q64非0；q64零、缺key不创建；q64高32单独非0仍创建；四个住宅内景各走marker参数1；1627走参数0。查询运行真实 `11cf0b0` 红黑树查找，不由Host回传“房屋存在”。图形创建及list插入边界被捕获，没有假扮真实显示。

## 1594住宅表的服务器依赖：请求、回复和门控

地图加载成功后 `11e0449` 精确比较模板1594：

- 1594：`11e048a..11e04b3` 构造并发送 **CRequestXiaoquMapInfo 0xc0fdb**，原body为空；此处不立即调用goto标记刷新。
- 非1594：清 `Scene+454`，然后 `11dec90` 刷新普通goto；是否dynamic1不是该请求的条件。

本批以1594/1595/1627各执行这段：只有1594在capture sink产生0xc0fdb；另两图执行清表/刷新边界。不能把所有dynamic地图统一接到家园请求。

响应 **SRequestXiaoquMapInfo 0xc0fdc**，原构造 `f976c0`、marshal `f97c80`、decoder `f97d00`，Process `11e1970`。Process只接受当前Scene存在且 `Scene+110==1594`，随后把报文+8的map交给 `11e0f80`。后者静态链清/复制到 `Scene+454`，再 `11dec90` 重建标记，并向地图UI `1230850` 更新。响应handler在三种模板的门控已执行：仅1594进入表更新边界；实际表复制/整个UI未执行。

响应body为 `compact_count + 每项(BE i32位置key + MapHouseInfo)`。本批原nonempty std::map serializer/decoder完整往返一项key9，实际迭代、创建原树节点并还原两q64，不以Python解包替代原decoder。

MapHouseInfo原RTTI `.?AVMapHouseInfo@move@gsp@knight@@`，vt226f030，ctor d49880、marshal e3cc90、decoder f55e50。原布局/序列：

|对象偏移|原线格式|已知用途|
|---|---|---|
|+8/+c|BE q64|Scene门户是否有住户/房屋可展示的非零门控；UI与本地/关系身份作比较|
|+10原wstring|UTF16LE octets|房屋相关显示名字；不直接命名owner_name作为服务端合同|
|+30/+34|BE q64|原codec证实宽度与顺序，业务用途本批未确认|

两组bean往返分别使用(1,2)及(4294967303,8589934601)，防止将q64截为32位。`12309b7..12309d4` 将第一q64与RoleDataManager+f8/+fc比较，随后又与关系对象+18/+1c比较，用于不同标签；因此它参与住户/自身身份判断，不能因住宅动态就当成scene ID。第一q64正式字段名及第二q64精确身份仍保留未裁定，研究结果用first_q64/last_q64。

`1230850` 地图UI更新同样只在当前map1594遍历房屋表；取node+10位置key，通过 `89d200` 的原 `Chouseweizhi` 表getter（虚表+8）获取配置，并在 `1230a99..1230ab3` 将配置+18/+1c的**xpos/ypos**乘16作为UI位置。`89d200` 返回ConfigManager+320；`c993d1..dc → 865430` 对该成员写入ChouseweizhiTable原虚表224f3d8，连接到实际表类型。XML字段常量2252b2c/2252b20及 `a6bbc6/a6bc02` 证实+18/+1c是xpos/ypos；**xchuansong/ychuansong另在+28/+2c**（`a6bcb6/a6bcf2`），不能混认。这里把数值键真正接到房屋位置配置，强于“25条看起来像房子”；UI图标点和门户中心仍是两个位置。

## 家园专用请求：存在、真实producer与未知分开

本批原codec均已完整往返：

|原类型|type / body|已证producer范围|
|---|---|---|
|CRequestXiaoquMapInfo|0xc0fdb / 空|1594原地图加载后实际构造发送|
|SRequestXiaoquMapInfo|0xc0fdc / map<i32,MapHouseInfo>|handler只在1594接收并更新表；非空原codec已执行|
|CEnterCommunity|0xc4fbb / BE i32|RTTI/ctor/codec确认；本批未找到并执行UI发送producer|
|CBaifang|0xc4fd2 / BE i32|原住宅UI发送builder已执行，见下文|
|CHomeResetPosition|0xc0fdd / 两个BE i32|原codec确认；11e747c..74c5由候选逻辑点除16后填入两个字段并发送，非q64场景身份|

原 `SCommunityInfo::Process 154db50` 将报文+8标识、name、HomeInfo列表传UI `154d310`，后者 `154d34e..355` 保存标识至UI+34。原UI的 `154e368..154e3ae` 先检查模式和选中项身份非0；`154e3b0..154e3e0` 从UI+34填CBaifang+8并发送。随后 `154e3e2..154e400` 启动主角路径流程 `1142620`，其参数包括模板1595及选中条目键。相似builder在179036c..17903cd。

fixture只从通过先决检查后的builder开始，设置UI+34=101，实际捕获CBaifang i32字段101，且发送type为0xc4fd2。**没有**执行完整UI点击权限/路径，也没有证明CBaifang字段是portal位置key9。上下文支持它是社区标识，而不是房号；不能拿destx直接发此包，或把这个“拜访”请求称为已证明的直接住宅Enter协议。

同样不能仅因为CHomeResetPosition名字像进门就把它接作住宅传送；它的两个i32来自网格位置候选，原搜索/放置上下文仍需另外追踪。CEnterCommunity只有compiled协议存在和原codec，不足以确认该入口必发它。

## dynamic与实例：可确认到哪里

原CMapConfig XML loader `87a5b7..87a5dc` 将 `dynamic` 写配置+170。Scene复制配置 `11c5960` 中 `11c5b08..11c5b0e` 原样复制该字段，因此落在Scene+110+170=+280。原表1594..1598值1、1627值0；这证明资源配置差异，不独立规定实例所有者键或服务器创建方式。

SRoleEnterScene处理器将报文+38/+3c的完整q64交给 `11e21f0`；后者在 `11e2267..226a` 保存到Scene+30/+34，同时以低dword经 `89dd50` 取CMapConfig。故“资源模板配置”与“原Scene q64身份”不是可无条件混并的同一个32位字段。本批不猜测高32是实例号或反推住宅实例算法，也不为服务端生成新的house ID。

原位置表25个住宅位置、每个小区25户、多zoneid与17992个社区配置，加上住宅信息下行，证明仅凭map_id1594和goto raw_dest不够恢复住户状态。房主/社区选择、访问权限、房屋级别、活跃Scene q64和持久化归属仍必须经家园系统及地图Owner合同接入。本文不恢复购买、装修、家具或资产结算。

## 住宅返回与1627同图：仍不能替原服作决定

1595..1598原goto都给1594,(376,293)，该普通像素投影在前审计越界。本批表明客户端该goto链用它创建内景出口标记，不执行目标重定位；因此没有证据允许把越界数值强行用于权威传送。`Chouseweizhi.xchuansong/ychuansong` 是与住宅位置正确关联的候选返回来源，但**尚未追到“离开该房屋时服务器选用它”的原消费者**，不能据此发布自动替换规则。

1627 raw target(101,115)→逻辑(1616,1840)，原dynamic0；地图加载分支和goto标记分支都普通。额外执行原 `SRoleEnterScene::Process 11e3140`：当前map1627、收到目标q64=1627、位置(1616,1840)，Process实际转交普通 `11e21f0`，没有同模板直接忽略或住宅专用分发。fixture在该callback入口停止，未执行后续世界加载。

静态 `11e21f0` 即使当前与目标模板相等也保留same-map状态分支，并最终经 `11e2600` 调普通Scene地图加载。它证明客户端存在同图Scene通知入口；**不证明1627的原服实际选SRoleEnterScene、SSetRoleLocation或其它消息，也不证明触碰portal直接发专用请求**。目前未定位到1627专用CHouse/Enter producer，不能把“没在已查分支看到”写成全映像不存在。

此图服务端同实例的位置权威提交、客户端未来队列/history屏障应引用已知移动重同步研究及Owner设计，不能借本研究把同map offer直接reserve到原实例放行。住宅与1627应保持不同接线条件。

## 同款端游官方材料：guide_supported，非协议证据

[官方2015-09-30《我想有个家！家园系统送你金窝银窝》](https://sdxl.wanmei.com/news/gamenews/20150930/175676.shtml) 描述使用房契后经临安家园传送人进入，入住可选择地址，已占位置不能重复选择，达到入住率会开放新小区，并可自定义小区名。这是同款端游历史第一方资料，支持“社区可多份、位置有占用”的玩法解释；不是本地1.6.1逐字段验证，也未给出25户数量、房号编码、CBaifang参数或住宅返回坐标。25户与位置键由本包和原消费者独立证明。本批未采用同名手游、其他游戏或2025公告作为该版本规则。

## 本批交接条件与未验证

已证明的是住宅信息生命周期的原请求/handler门控、25个位置键与真实配置联系、普通/住宅门户标记分支差异、相关原codec，以及1627同图Scene Process的可接受分发。25结构例与25全表位置匹配均通过。

未证明：房主/配偶字段正式名、住宅实例选择/创建/归属与访问鉴权、CBaifang完整请求到Scene回复、内景退出时的实际返回点选择、1627原服消息序列、完整场景渲染/真人触发。完整SRequest表复制与UI执行也未覆盖，不把边界捕获称为GUI成功。生产恢复应先由所属家园模块提供这些有来源的状态及允许操作，再由父窗口集成地图Owner；本批不制定默认ID、坐标或政策。
