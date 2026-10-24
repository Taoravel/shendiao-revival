# 原客户端角色协议研究（2026-10-23）

## 方法、证据与范围

采用 research：所有协议结论来自第一方客户端已解包映像 `native-image.bin`（BASE `0x400000`，SHA-256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`）及原资源配置。下文地址均为该映像的虚拟地址，能通过 `../research_roles.py --disasm <name>` 或 `../native_inspect.py` 复查。没有套用其他游戏协议。

采用 codebase-design：传输封包、账号会话和角色存档应在三个 module 内保持 locality；角色 module 的 interface 只暴露读取角色、创建角色、校验选角归属。字节字段及未知字段留在 codec implementation，不散布到 UI。没有为假设变化引入 adapter。

只读分析映像，未启动或修改进程。运行验证均在隔离 Unicorn 内：原生空角色列表解码，以及完整角色状态序列化/约束检查。建角请求及进世界尚未端到端验证；未知字段明确保留原偏移标识。

## 消息编号与字段

多字节定长数均为大端。wstring 是 compact 长度前缀的 UTF-16LE 字节，不含结尾 NUL。集合数量走原生 compact 编码。

| 类 | type | payload | 原生证据 |
|---|---:|---|---|
| CRoleList | `0xc0001` | 空 | 构造 `d51370`；marshal `d51390`、unmarshal `d513a0` 均只返回 stream |
| SRoleList | `0xc0002` | u64 account/selected-id, u8 flag, RoleInfo list, i32 tail | 构造 `fbffb0`；marshal `fc0090`；unmarshal `fc0160`；process `1007df0` |
| CCreateRole | `0xc0003` | wstring name, i32 school, i32 shape | 构造 `d4ed00` / `10089d0`；marshal `e3fc80`；UI send `100986f..1009899` |
| SCreateRole | `0xc0004` | 一条 RoleInfo，无 status | 构造 `ec0540`；marshal `ec05f0`；unmarshal `ec0660`；process `10080b0` |
| CEnterWorld | `0xc0005` | u64 roleid, wstring token/string, u8 flag | 构造 `83d3b0`；marshal `83f590`；unmarshal `840320` |
| SEnterWorld | `0xc0006` | 大型完整角色状态（下述） | 构造 `fe4160`；marshal `fe45f0` 包装 `fe0940`；unmarshal `fe4630` 包装 `fe2350` |
| SCreateRoleError | `0xc0008` | i32 error | 构造 `d52e60`；marshal `e406c0`；unmarshal `d52ef0`；process `10063a0` |

### 空角色列表与角色创建界面

payload = `pack('>QB', account_id, 0) + b'\0' + pack('>i', tail)`，共 14 字节。

`1007df0`：flag=1 时直接构造 CEnterWorld，取第一项 u64 作为 roleid，字符串来自客户端 `813830/813730`。flag 非1时将角色集合复制入本地 vector（每项0x50字节），把 u64 复制到管理器 +0x20/+0x24，调用 `1006700`。这里 u64 在普通路径更像上次选择 roleid，不能仅凭位置断言 accountid。

`1006700`：vector 为空跳 `1006500`，后者设置状态4，按屏幕尺寸调用建角 UI `1006090` / `1006000`；vector 非空设置状态3，调用选角 UI `1005f70`。

`tail==1` 被保存到管理器 +0xf8。第三阶段已确认该标记开启入世界验证码分支；本地未实现验证码时应发0。离线样例的tail1只是解码探针输入，不是生产默认值。

原生验证：`role-native-verification.json`。执行原 `fc0160`、`fbfdd0`（包括 compact 数量解码）和 `fc0030` 验证，输入 `1122334455667788000000000001`，正确消耗14字节，得到 u64 `0x1122334455667788`、flag0、空集合、tail1。仅绕过进程特定的 Windows CRT cookie checker `1919184`。

### CCreateRole 的参数语义

`100986f..1009899` 从建角 UI +0x2c、+0x38 取两个选值，依次传给 `10089d0`，存到请求 +0x24、+0x28。

门派选项构造 `100b715..100b785` 生成11..19及111，与原 `knight.gsp.role.createroleconfig.json` 的 `schools` 列表匹配，因此请求第一个 i32 是 school。第二个是 shape，**值来自 color1/color2/color3，不能直接使用 create config 的行 id1..10**。

证据：`100b240` 通过UI+0x28查create config行；`100b286..100b2b0` 将 UI+0x38 设为 config+0x1cc/+0x1d0/+0x1d4（由UI+0x30颜色选择1/2/其他决定），对应原配置三个color字段。之后 `1009881` 直接把UI+0x38传给CCreateRole。

例如云夕(row9)配古墓派(school11)，shape是1010109、1020209、1030309之一。服务端应从各行的color1/2/3建立 `shape -> create row` 映射，再检查该行schools。`knight.gsp.npc.cnpcshape.json` 与 `knight.gsp.role.crolecolorschemes.json` 均存在1010109。

原先将shape与行id直接对应的推断已被上述数据流否定；这正是首次实测invalid_choice的原因。

服务端应保留玩家请求的 school/shape，使用原 create config 检查合法配对；名字必须 UTF-16LE 解码后校验。

### RoleInfo（对象偏移从 RoleInfo 自身算，不含协议头）

| 顺序 | 内存偏移 | wire | 含义与依据 |
|---:|---:|---|---|
| 1 | +8 | u64 | roleid，必须>=1 |
| 2 | +0x10 | wstring | name，选角 `1020766..10207d8` 显示 |
| 3 | +0x2c | i32 | school，`10207ee..1020802` 查门派名称 |
| 4 | +0x30 | i32 | shape，`10206b3..1020703` 转模型id |
| 5 | +0x34 | i32 | level，必须>=1，`102088f..10208b4` 格式化显示 |
| 6 | +0x38 | map<i8,i32> | 外观/扩展属性 map，元素 codec `ec0070`；业务键语义未确认 |
| 7 | +0x44 | u8 | 未确认，新对象原默认0 |
| 8 | +0x48 | i32 | 进阶等级类字段，必须>=0；0显示普通level，非0减1000并取文本资源0xc4a |
| 9 | +0x4c | i32 | 未确认，新对象原默认0 |

完整顺序直接取 `ebfc20..ebfe75` marshal，`f5a0e0` unmarshal交叉。约束 `ec05a0`。原构造 `ebf940` 将所有标量置0、map为空；**有效新角色必须覆盖 roleid、level 为正数**。可用基础存档：roleid>0，name来自请求，school/shape来自合法配置，level1，map空，三个末尾未知字段0。该建议还需要原客户端联调验证。

SCreateRole process `10080b0` 删除空占位角色，将新 RoleInfo 加入列表，把新 roleid 写作当前选择，关闭建角 UI，调用选角 UI `1005f70`。

### 建角错误

`10063a0` 将 code4 映射到消息配置140404（角色名字重复），将3/6/7映射到140403（名字字符/长度等限制）；其他 code 直接作为消息配置 id 查找。原消息来自 `knight.gsp.message.cmessagetip.json`。

已确认可以用4返回重名、3返回非法名字，并保持连接。没有证据确认“非法门派”专用 code，不应冒称已还原。

## 进入世界的已知范围

CEnterWorld marshal `83f590` 验证 roleid>=1，随后写 wstring和flag。安全归属检查应在本地服务端确认 roleid属于已登录账号；原客户端无法证明服务器端校验。

SEnterWorld 内部状态 vtable `2286bbc`，marshal `fe0940..fe17f4`，unmarshal `fe2350`；对象共至少0x198字节。顺序：

1. u64@8(roleid)；wstring@10(name)；i32@2c(level),30(school),34(shape),38(未确认)；u64@40。
2. i32@48到c4（逐4字节）；内嵌@c8（vtable22702ac）。
3. i32@d8,dc,e0,e4,e8,ec；u64@f0,f8,100；i32@108,10c,110。
4. 容器@114,120,130,13c；i32@148,14c；map<i8,i32>@150；i32@15c,160；u64@168。
5. u8@170,171,172；容器@174,184；u8@194。

内嵌@c8为五个BE i16（原marshal `e40720`）。空嵌套集合各只写 compact0。

字段语义来自 process `8337c0`：协议对象含8字节头，因此 +0x34对应内层level(+0x2c)，+0x38对应school(+0x30)，+0x3c对应shape(+0x34)；`8338d2` 按shape生成模型id，与选角UI模型转换一致。

构造 `fdfe90`，合法性检查 `fe43b0` 至少要求roleid>=1、@2c>=1、@38>=-1，并遍历检查嵌套字段。不能把角色列表格式或空字节直接当作 SEnterWorld 回复。

`../research_roles.py --world-layout-probe` 已执行原生 `fe0940` serializer：roleid1、空名字、level1、school12、shape1010101，其余标量0和空STL容器，输出266字节 `world-layout-probe.bin`。同一对象通过原生 `fe43b0` 约束。Windows分配/释放、内存复制和InterlockedDecrement由宿主等价实现；没有替换序列化函数。约束通过不证明进入地图能完整加载；零生命值、资源模板、场景和坐标等仍须独立初始化。完整属性语义、场景/坐标初始化和成功入场景仍未验证。

## 产物与验证记录

- `../research_roles.py`：小 interface 提供离线命名函数反汇编和原生空列表验证；实现封装映像读取、对象内存布局和隔离模拟。
- `role-native-verification.json`：空列表通过原生解码与约束的证据。
- `world-layout-probe.bin` / `world-layout-probe.json`：完整状态的原生序列化与约束验证，仅用于布局研究。
- 本文：逐项标识已知、推断、未验证，不把“解码成功”写成“已进入游戏”。

## 场景通知的下一阶段证据

SRoleEnterScene（RTTI `.?AVSRoleEnterScene@move@gsp@knight@@`）type `0xc0fa9`。构造 `dac580` / 类型赋值 `dac5db`；marshal `e50b00`，unmarshal `f74260`，process `11e3140`。

字段顺序：wstring@8；Pos@24（两个BE i16，vtable `2278e54`，marshal `e50690`）；u8@2c；i32@30；u64@38；u8@40；wstring@44。

process把首wstring、坐标、u64和i32传给 `11e21f0` 加载场景。u64低32位与地图ID `0x5f7`/`0x57d` 比较，因此scene/mapid64的解释有较强依据；i32@30及两个字符串的准确产品含义尚未确认。不要把猜测的资源目录字符串当作已确证字段。

### 第二阶段确认与修正

首wstring由 `11e2928` 复制到场景管理器+0x3c；**资源读取不使用这个字符串**。`11e255e` 将u64低32位作为key，通过 `89dd50` 查原地图配置，`11c5960` 复制配置到管理器+0x110。原配置resdir位于+0x58，因此管理器+0x168是资源目录。`11e03dd..11e0411` 实际读取该目录下 `/maze.dat`；后续读取 `/regiontypeinfo.dat`、`/JumpBlock.dat`、`/Island.dat`、`/Island2.dat`。首wstring作为服务器提供的场景标签保存，准确UI含义尚未核实，本地候选使用“临安”。

Pos属于逻辑像素坐标。`11e0363..11e03a8` 将输入x乘全局浮点1.5（`2923784`），y保持原值，再传地图引擎；阻挡区域按24×16渲染格加载。原NPC配置的逻辑坐标与此相容：临安最大NPC x8310，小于地图渲染宽13056/1.5=8704。门户cell坐标应转换为逻辑像素，不能直接将cell当Pos。

i32@0x30控制进入原因/特殊场景流程。`0x7dfaf` = 十进制**516015**，其分支做首次入世界初始化；没有证据把它叫作普通地图类型或把它写成514991。

### 初始化生命与真气字段

以下为RoleDetail内层偏移，**不含协议对象8字节头**。证据是process `8337c0` 将字段写入属性map，对照原 `knight.gsp.item.cattributedesconfig.json` 的属性名。

| 内层偏移 | 属性id | 原属性名 | handler读取地址 |
|---:|---:|---|---:|
| +0x48 | 60 | 生命值 | `833a6e`，协议+0x50 |
| +0x4c | 640 | 当前生命值上限 | `833c7e`，协议+0x54 |
| +0x50 | 140 | 生命最大值 | `833c06`，协议+0x58 |
| +0x54 | 70 | 真气值 | `833a8c`，协议+0x5c |
| +0x58 | 150 | 真气最大值 | `833c24`，协议+0x60 |

原构造将五项都置0；原服务端初始数值没有在现有客户端中确证。探针中的100是明确的本地实验值，不是原作还原值。

最早必须有记录的资源key：shape→npcshape（process `8338d2` 模型映射），school→schoolinfo（`833967` 调 `89e790`），school→schoolmasterskillinfo（`833988` 调 `89e7a0`）。云夕shape1010109存在原 `npc.cnpcshape`，古墓school11同时存在两个门派配置，因此这组候选不会使用空门派/错误模型key。

### 出生地图证据

没有证据将临安1007或太湖之滨1014称为原出生地图。原 `task.cmainmissioninfo` mission100101播放电影11001；提取文件 `../extracted/config/movie/11001.txt` 开头为 `Setmap id=1009 pos=15,137`，末尾为 `Setmap id=1100 pos=22,55`。随后mission100184..100187的ActiveInfoMapID均为1100古墓；mission100104传往1006嘉兴，mission100106再传往1501梦境嘉兴。原新手流程包含剧情、任务状态和多张地图，不能以单张静态地图替代后声称完整还原。

本地首入候选临安1007仅作为可运行测试地图。坐标8480,6976为主任务从原门户目的cell530,436乘16所得，非原出生点。

### CAfterEnterWorld与先后顺序

CAfterEnterWorld type **0xc003d**，payload为空（构造 `d4e530`；marshal/unmarshal `d4e550`/`d4e560` 只返回stream）。原生发送唯一vtable引用在 `11e2d0d`：

1. 服务端SRoleEnterScene被 `11e3140` 处理，传入 `11e21f0`。
2. 地图配置加载、`11e0310` 读取地图资源成功，才继续角色定位与场景初始化。
3. 进入原因等于516015时，`11e2d00..11e2d33` 发送CAfterEnterWorld。

因此客户端自身的CAfterEnterWorld是有用的入场景进度证据；服务端不应替客户端伪造该消息。

### 含名字候选的原生codec验证

`../research_roles.py --world-layout-probe --name 初入江湖 --school 11 --shape 1010109 --experimental-vitals 100` 生成 `world-named-probe.bin/json`：roleid1、level1、上述中文名、门派11、外观1010109、五个生命/真气实验值100。真实原生构造 `fdfe90` → serialize `fe0940` → decode `fe2350`，完整消耗274字节，名字、roleid、门派、外观和五项值均还原；原生约束 `fe43b0` 通过。

`../research_roles.py --scene-layout-probe --name 临安` 生成 `scene-named-probe.bin/json`：Pos8480,6976、flag0、reason516015、sceneid1007、末尾byte0及空wstring。真实原生构造 `dac580` → serialize `e50b00` → decode `f74260`，完整消耗24字节，标签、坐标、进入原因和sceneid均还原。payload：`04344e895b21201b40000007dfaf00000000000003ef0000`。

模拟器对Windows分配/释放、复制、原子引用计数及STL wstring构造/迭代器赋值提供宿主adapter；wstring wire长度与取数仍由原OctetsStream消费，集合和所有标量codec仍执行原生代码。**这验证封包布局和原生解码兼容性，尚未验证实际UI地图加载、NPC、移动或持久化。**

## 第三阶段：进入按钮的实际前置协议

真实客户端在选角后首先发送 `0xc0078`，而不是马上发送 `0xc0005`。前者RTTI为 **CSendIgnoreRole@gsp@knight**，但不能凭名字把它解释成删除角色。

| 消息 | type | payload | 证据 |
|---|---:|---|---|
| CSendIgnoreRole | `0xc0078` | BE u64 roleid | vtable226ff9c，构造d51630，marshal e40360，decode d516d0 |
| SSendIgnoreRole | `0xc0079` | 空 | vtable22707a0，构造d56ca0，marshal d56cc0、decode d56cd0均只返回stream |

精确UI绑定：`1021c12` 使用ASCII字符串 `22899d8 = selectRoleDialog/gotoBtn` 查按钮，`1021c7c` 存到UI+0x40；`1021f7d..1021fc0` 把回调 **1020420** 绑定到该按钮。原 `../decoded/ui/layouts/selectroledialog.layout:10` 的gotoBtn文本正是“进入游戏”。

流程：

1. `1020420` 取当前选中角色id，某本地检查分支发CSendIgnoreRole；另一分支直接调用1020210。
2. 服务端应先校验roleid属于当前账号，然后回空SSendIgnoreRole；**不删除角色，不修改角色列表，也不直接把该消息当作CEnterWorld。**
3. 原SSendIgnoreRole handler `1020400` 仅调用选角UI的 `1020210`，没有删除或确认弹窗代码。
4. `1020210` 走普通路径调用 `101ff90`，在 `1020177` 构造原CEnterWorld（83d3b0），`102019f` 发送0xc0005。
5. 服务端收到真实CEnterWorld后，再校验角色归属并按已研究顺序发送角色状态/场景消息。

### 选角尾标记与验证码

`1005f20` 返回角色管理器+0xf8，正是SRoleList尾i32==1的布尔值。`1020294..10202cc` 若该flag为真，发送type **0xd13bf**，RTTI **ACRefreshCaptcha@gacdc@gacd**；若为假才调用101ff90直接发CEnterWorld。

因此不提供验证码的本地测试服务应令SRoleList tail=0。tail1虽然通过wire解码，但会引入额外前置验证码流程。本结论修正了早期仅凭反汇编布局无法明确tail含义的状态。

本阶段验证为原生地址与原UI资源的静态交叉；实际SSendIgnoreRole→CEnterWorld仍须由主任务记录真实会话确认。角色存档必须保留。
