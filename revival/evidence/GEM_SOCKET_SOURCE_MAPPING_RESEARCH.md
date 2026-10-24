# 普通装备镶嵌来源、详情定位与评分消费者调查

2026-10-24。本地 1.6.1 端游、网络版本 601。仅离线读取原包与原生映像，执行原机器码的受控片段/编解码；没有启动客户端、连接服务、读写真实角色或修改运行服。本批唯一文档产物为本文。

## 可实施结论

| 事项 | 结论 | 来源状态与执行范围 |
|---|---|---|
| 普通背包来源 | 原 column **1** → `EquipObject+0x4c=1` → 镶嵌/单摘/全摘 source byte **0** | `client_verified`：原解码、原 Item 复制、原字段赋值、实际发送分支、原请求 codec 均执行 |
| 装备栏来源 | 原 column **4** → `EquipObject+0x4c=4` → 三种请求 source byte **1** | `client_verified`，同上；原装备栏请求另有明确 column4 字面量 |
| 其他容器 | 客户端发送分支是 `source = (column != 1)`，不是完整可逆容器枚举 | `client_verified` 静态/执行；不能据此给仓库或其他容器操作权限 |
| 详情所有者定位 | `SItemTips` 用 `(column, item_key)` 两层索引找原 ItemRef；不存在时返回空，不跨容器兜底 | `client_verified`：完整原查找函数与实际消息消费者执行 |
| 已镶嵌列表顺序 | 原详情 parser 保留响应中的宝石模板列表顺序；不是按模板 ID、等级或属性排序 | `client_verified`：8 次完整 parser，含反序和清空后重载 |
| 替换后的顺序 | 是否把新宝石放在被替换项原位，客户端现有证据不能确定 | `unknown`：未取得原服务端列表生成/替换实现 |
| 普通宝石评分 | 仍未闭合原服务端增量公式；不能把每外/内攻 400 当作已证宝石系数 | `unknown`；真实 `cequipscoreconfig` 消费者已找到，但属于强化预览 |

这允许普通请求解码显式定义 `wire0 → bag column1`、`wire1 → equipped column4`。服务端仍须按当前角色权威资产确认容器、实例、装备资格及版本，不能只信来源字节，也不能搜索另一容器补救请求不匹配。

## 方法、边界与第一方材料

本批重读 `D:/User/Documents/Codex/.codex/skills/research/SKILL.md`、根 `AGENTS.md`、`revival/ARCHITECTURE.md`、`revival/DESIGN_AUTHORITY.md`。research 方法实际用于：从旧报告仅取定位线索，回到原消息 decoder、Item 生成链与真正发送调用，分别记录静态链和执行范围；不把字段相等、表存在或已有恢复实现当作原版业务证明。本身已是根任务派出的后台研究代理，未再次委派。

使用指定 Python `C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`；先导入 `native_inspect`/`native_gameplay_probe`，再导入 Unicorn/Capstone。临时 harness 在内存执行，没有新增研究脚本或 JSON。参考现有 harness 的原编解码/CRT Adapter，以及只读导入 `research_equipment_gem_detail.NativeGemEquipmentDetail`；结论仍由本批独立输入与断言产生。

原生来源是 `revival/evidence/native-image.bin`，映射基址 `0x400000`，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。下文地址均为该映像 VA，不是文件偏移。实际执行不注入最终 source、查找结果、宝石属性或评分结果；网络发送端替换为内存捕获，不向外发送。

本批直接从 `artres/config.pfs` 解压/校验并 BXML 解码下列原表，将全体 `(attributes, lists)` 逐行与 catalog 比较一致。没有把 XML 缩进/children 格式当作配置差异。

| 原包路径（均在 `autoconfig/`） | 行数 / 解压字节数 | 原字节 SHA256 |
|---|---:|---|
| `knight.gsp.item.cequipscoreconfig.xml` | 36 / 10245 | `c370650594da413d8870204e0820dab958f34cd9b9386f6102a54f0ba43be683` |
| `knight.gsp.item.cequipmakeupconfig.xml` | 1159 / 1365434 | `2af045f49ad08a66ee9c09ac4dd6bc3fb5feb34e392981c47ef2cedcfb291b23` |
| `knight.gsp.item.cgemeffect.xml` | 705 / 153697 | `935a82213b553808d7eb6c42fc6280518d2f31c01f33aaea572927e7f9f2b5ce` |

没有查询手游或《神雕侠侣2》，本批结论不依赖攻略；也没有用旧装备报告替代上述原表及原生消费者核验。

## 原容器到 EquipObject 的生成链

### 消息保留 column，不由 UI 临时发明

原 `SGetBagInfo`：vtable `0x2284234`，constructor `0xef6220`，marshal `0xef62d0`，unmarshal `0xef6350`，process `0x10a8f40`。本批执行的消息体：

```
BE32 column
BE64 cash
BE32 capacity
compact item_count
Item beans
byte trailing_flag
```

解码后 message `+8` 为 column；message `+0x10` 是 BagInfo；Item vector begin/end 分别为 message `+0x28/+0x2c`，每个原 Item bean 为 `0x40` 字节。此处 column 是原容器号，不是宝石请求中的单 byte 来源。

实际静态调用链：

1. `0x10a9054..0x10a9067`：从 `SGetBagInfo` 的 `+8` 取 column，与 `+0x10` BagInfo 一起传入 `0x10a4840`。
2. `0x10a4957..0x10a4979`：遍历原 Item beans，将同一 column 和当前 bean 传给 `0x10977b0`。
3. `0x1097815..0x1097821`：创建的 ItemRef 经 `0x1081790` 初始化，输入仍为 column 与 bean。
4. `0x1081790` 先用原 `0x1080720` 工厂按模板创建物品 Object，再由原 `0x81a760` 把 bean 复制到 Object `+8`。
5. **`0x10817bc..0x10817cc`**：`EDI=column`、`ESI=ItemRef`、`EBX=Item bean`；`[ItemRef]` 为 Object，执行 `Object+0x4c=EDI`，并把 bean `+0x10` 的物品位置写到 Object `+0x48`。紧邻 `cmp edi,4` 只影响随后 UI 路径，不会将其重编码为 0/1。

因此 `Object+0x4c` 是原容器 column，不是“背包0/装备1”。

### column1 / column4 的原用途区分

column1 的普通携带背包路径在 `0x10a486d..0x10a4892` 单列，更新普通背包现金槽及背包状态；`0x109783f..0x1097844` 将 column1 分流到 `0x1097a61` 的背包物品更新路径。它与 column2、6、0x12 等分支分开。

装备栏有独立的原请求字面量：`0x1103dff..0x1103e3b` 构造 `CGetBagInfo 0xc03f2`，请求 `+8=4`，并经原 sender 发送。对应装备视图生成点 `0x10a4b0d..0x10a4b12`、`0x10a4d1b..0x10a4d20` 将 **4** 与 Item bean 传给同一 `0x1081790`。管理器的 `0x10a4a17..0x10a4a33` 也显式以 key4 定位该容器。

以上原链给出了数字含义，下面执行矩阵再独立验证数字如何进入普通宝石请求。没有根据变量命名猜测 source0 的含义。

## 实际发送与原 codec 执行

### 镶嵌

原发送 **`0x131ede6..0x131ee56`**：UI `+0x2d8/+0x2dc` 指向装备/宝石控件，控件 `+0x278` 取 ItemRef。装备 Object `+0x14` 为装备实例 key，宝石 Object `+0x14` 为宝石实例 key。

`0x131ee12` 比较装备 Object `+0x4c` 是否为1，`0x131ee1e setne dl`，随后传入原 constructor `0x1302120`；`0x131ee43..0x131ee54` 调用真实 sender 和发送虚函数。

`CAddGemToEquip 0xc0425`：factory `0xd8d0d0`，marshal `0xe4b710`，unmarshal `0xd8d100`，体为：

```
BE32 equip_instance_key
byte source
BE32 gem_instance_key
```

source 所在的 DWORD 高三字节可能保留栈 padding。本批只捕获/编码 **byte**，没有把整个 DWORD 的 513 等值当作 mode。

### 单颗/全部摘除

`CRemoveDiamondFromEquip 0xc04ea`：factory `0xd94dc0`，marshal `0xe4ce00`，unmarshal `0xd94df0`，体为：

```
BE32 gem_template_or_minus1
BE32 equip_instance_key
byte source
```

单颗真实分支 `0x131f15d → 0x131f083 → 0x131f0a9`：所选 UI 项 `+0xc0` 给出宝石模板 ID；装备引用在 UI `+0x6c4`。`0x131f094..0x131f0a1` 用同一 `Object+0x4c != 1` 得 source。

全部真实分支 `0x131f0c1..0x131f121 → 0x131f0a9`：全摘控件 `+0x530` 为非零时，模板字段设置为 signed32 `-1`，同样从实际装备 Object 得到 key/source。两者都走原 sender；不是事后手工拼消息替代实际发送分支。

### 本批 12×3 执行矩阵

输入 column `{1,4}` × position `{0,5,39}` × binding `{0,1}`，共 **12 个**原 SGetBagInfo 完整解码。每个包含模板40100、装备实例701、数量1，解码后实际 Item bean 经原 `0x81a760` 和 `0x10817bc..cc`，再运行上述三条发送分支。宝石实例901，单颗选择模板35001。

| 从原消息来的 column | Object `+0x4c` | 镶嵌 source | 单摘 source | 全摘 source | 输入组合数 |
|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 0 | 0 | 0 | 6 |
| 4 | 4 | 1 | 1 | 1 | 6 |

**36 次真实发送捕获 + 36 次原 request marshal/unmarshal** 全部逐字节符合：

- 镶嵌 `>iBi` 为 `(701, expected_source, 901)`；
- 单摘 `>iiB` 为 `(35001, 701, expected_source)`；
- 全摘 `>iiB` 为 `(-1, 701, expected_source)`。

位置和绑定变化没有改变来源映射。这里只验证映射和报文，不以 position39 的诊断输入证明装备栏有40个合法槽位，也不以 binding0/1 证明原服务端的宝石绑定传播规则。

执行边界：没有执行含所有 UI/通知副作用的完整 Bag process 和完整 `0x1081790` 工厂生命周期；这些跨层传参为上述静态链。实际执行覆盖原消息完整 decoder、原 bean 复制、原字段赋值、原发送片段、原 constructor、原 request codec；源 column 来自原解码结果，并未手工注入最终 Object+4c 或 source。

## SItemTips 的所有者/容器读路径

原 `SItemTips 0xc03fe`：vtable `0x227781c`，constructor `0xd9c110`，marshal `0xe4e5c0`，unmarshal `0xe0a240`，process `0x107a080`。体为 `BE32 column + BE32 item_key + Octets detail`；解码后 `+8=column`、`+0xc=key`。

**`0x107a0d7..0x107a0f2`** 从实际消息取 column/key，调用原完整 **`0x1091670`**。该函数从全局物品管理器 `[0x2944628]` 的 `+0xa4` 外层 map 按 column 查找（原 `0x108dca0`），再在该节点 `+0x10` 的内层 map 按实例 key 查找（原 `0x1090930`）。任一层缺失均返回0，成功返回 ItemRef。原 `0x107a13c..0x107a148` 随后才对该引用调用详情 parser；不是新建一个无归属 Object 后给它猜来源。

本批在内存建立两层原 map 布局，column1 与 column4 故意各放一个**相同 key701**、但不同 ItemRef 的物品：

| key / column | 完整原 `0x1091670` 返回 |
|---|---|
| 701 / 1 | 仅 column1 的引用 |
| 701 / 4 | 仅 column4 的引用 |
| 702 / 1、702 / 4 | 0 |
| 701 / 2、701 / 0、701 / 5 | 0 |

完整原查找 **7 例**通过，没有替换两个 map 查找函数或最终返回值。此为内存布局 fixture，不是实际生成/插入 map 节点的生命周期测试。

另执行 **6 个原 SItemTips decoder → 实际 `0x107a0d7..f4` 消费片段 → 同一完整查找**：`(1,701)`、`(4,701)`、`(1,702)`、`(4,702)`、`(2,701)`、`(5,701)`，返回与上表一致。decoder 本身要求 column≥1、key≥1（`0xe0a2d0..0xe0a2ef`）；输入 `(0,701)`、`(1,0)` **2 例被原代码拒绝**。因此 column0 的完整查找诊断结果不能伪称有效详情消息。

这证明客户端详情消费按容器精确定位。服务端对“当前角色拥有”及 epoch/资产版本的校验仍是实现责任，不能用客户端只读管理器查找冒充原服务端授权规则。

## 评分表的真实消费者及不能推出的公式

### 已找到真实消费者，不能再说只有表没有引用

`CEquipScoreConfigTable` vtable `0x224f758`；实现表 vtable `0x2255b74`。初始化 `0xd41e2a` 将其装到配置根 `+0x4e0`，原 getter **`0x89d580`** 返回 `[0x2945aec]+0x4e0`。

对整份映像扫描 E8 relative-call destination，找到 getter 的 **7 个直接调用点**：

```
0x12f62a5  0x12f6425  0x12f67b5
0x12f6bef  0x12f6dab  0x12f7173  0x12f74a9
```

它们全部位于同一完整函数 **`0x12f60b0..0x12f771f`**。从合法函数入口连续反汇编1626条指令；没有靠未对齐地址的伪反汇编命名函数，也没有用 literal-DWORD refs 冒充 relative-call xref。

该函数的用途可由本体闭合为**强化下一级预览**：

- `0x12f60f4..0x12f6113` 先按模板查 `cequipmakeupconfig` 并检查装备 `+0xb0` 的当前强化等级。
- 用装备基本属性 map `+0x80`、强化系数 `+0xb4` 重建强化附加 map `+0xb8`，再对这些强化增量算评分；正常六槽取 `(itemtypeid >> 4) & 15`。
- `0x12f69c6` **将装备 `+0xb0` 加1**，后半函数计算下一强化阶段。
- `0x12f761d..0x12f7626` 将下一阶段分数与旧阶段分数的差值加到 Object `+0x60`。`0x12f7632..0x12f76f8` 再按原前缀、评分颜色阈值更新颜色。
- UI 直接调用点 `0x12f87e0`、`0x1322516`、`0x1322bf5`、`0x1322e62`、`0x1325bf0` 均针对复制后的预览装备对象；其中 `0x1322502..0x1322516` 等明确比较当前强化等级与强化上限后才调用。

原 `effectscore` 不是一个可直接随意取值的单系数：正常槽位取 row `+0x20` 的字符串 vector 对应下标，调用原 **`0x12f5ef0`**，参数 **2**，即按分号拆分后取零基第2项转换整数。例 `0x12f62c7..0x12f6320` 取该系数乘当前强化增量；`0x12f7173..0x12f71f1` 对下一阶段做对应计算。特殊 itemtype `0x1c8/0x2c8/0x3c8` 另走 `0x12f721c` 分支，`0x12f74a9..0x12f756b` 用字符串 vector 第10项，不能混入普通六槽。

常量原字节直接读取：`0x2473e98` 是 double **100.0**，`0x2473f70` 是 double **0.5**。`0x12f760d..0x12f7626` 的加0.5取整属于此强化预览表达式，不能外推为原服所有装备或宝石评分取整。

**以上评分调查为原生静态证据，没有完整执行该1626指令函数及 CEGUI/配置字符串生命周期。** 不将静态算式描述为本批已实际复跑的评分结果。

### 为什么仍不能采用“每点外攻400”的普通宝石公式

原表 row81（外功伤害）、row811（内功伤害）第0条字符串为 `400;408;420;432;440;448;460;440`；row111（命中）为 `160;163;168;172;176;179;184;176`；row131（速度）为 `1000;1020;1050;1080;1100;1120;1150;1100`；row141（生命最大值）为 `100;102;105;108;110;112;115;110`。这些原值已直接PFS核对。

但本批找到的消费者取的是**第2 token**（上述外/内攻字符串为420），输入是强化附加量，函数会递增强化等级。完整函数未读取普通已镶嵌列表 `+0x98` 或宝石效果 map `+0xa4`，也不调用 `cgemeffect` getter `0x89d670`。因此“表里存在400”不能证明“普通宝石外攻×400”；取420同样没有普通宝石语义证明。

静态搜索范围是整映像对 `0x89d580` 的直接 E8 调用及该函数/五个直接 UI 调用点。不宣称已经排除所有间接虚调用、内联表访问或原服务端实现。**普通宝石评分的基准、增量、是否按属性/宝石等级分别加成、累计取整和服务器颜色更新仍 unknown。**

可实施接缝（建议，不是原规则）：为普通宝石事务保留一个显式、可替换的评分/颜色策略，输入冻结的原装备 score、旧/新有序宝石列表及原表效果；未知时交主策划集中定义 `designed`，不要把恢复者拟合值标成 `client_verified`，也不要通过重新拟合裸装备分数覆盖原存档 score。

## 非空列表顺序与详情评分执行

本批实际运行完整原 `EquipObject` constructor **`0x107cf80`**、完整详情 parser **`0x107d960`** 到自然返回 **`0x107fd97`**。仅 CRT/配置终端作 Adapter：原 `cgemeffect` 各行 effecttype/effect vectors 提供给 parser；配置 row copy `0xcd0b30` 和 destructor `0xa00730` 用只读静态行 Adapter，不声称完整执行原配置对象生命周期。

原有序 gem list 位于 Object `+0x98`（head `+0x9c`；node `+8` 为模板 ID），聚合 gem effects map 位于 `+0xa4`。正常基础属性 map `+0x80` 与这份宝石效果分开。本批顺序/聚合输入如下，详情发送的 score 均为0：

| 输入 gem list（也是 parser 后原链表顺序） | parser 聚合 gem effects | 原 score 结果 |
|---|---|---:|
| `[]` | `[]` | 0 |
| `[35001]` | `81:12` | 0 |
| `[35014,35001]` | `81:25` | 0 |
| `[35001,35014]` | `81:25` | 0 |
| `[35006,35003,35001]` | `81:12,131:5,811:12` | 0 |
| `[35001,35003,35006]` | 同上 | 0 |
| 再次 `[]` | `[]` | 0 |
| 再次 `[35014,35001]` | `81:25` | 0 |

8次使用同一原对象，确认清空后重载不残留上一列表/效果。反序列表未被 parser 排序，聚合 map 的属性 ID 顺序与 gem list 顺序是不同结构。速度宝石35006放武器40100的两例仅是诊断 parser 列表/聚合输入，**不是镶嵌资格通过证据**。

因此 full detail wrapper 应保留已有列表次序，不能为方便序列化改为排序集合。但原 response parser 接受某种次序，仅证明如何呈现服务端给的列表；它没有证明原服务端新插入/升级替换/摘除后如何选择顺序。原同等级查找可用来判断候选，但不能据其“找到一个项目”推定服务端替换时保留位序。

这8例也实证：原 parser 从详情读入 score 后，聚合非空 gem effects **不会自动重算 score**。这不证明原服务端宝石没有评分，只说明客户端解析器不能替服务器补一份尚未知的评分公式。

## 验证台账与未验范围

| 本批验证 | 数量与结果 |
|---|---|
| 原PFS全行比对 | 3表，全部 attributes/lists 相同 |
| 原 SGetBagInfo 完整解码、Item copy、来源赋值 | 12例通过 |
| 原镶嵌/单摘/全摘实际发送构造 | 36次通过，均只捕获未联网 |
| 对捕获字段原 request marshal/unmarshal | 36例逐字节通过 |
| 完整原按 column/key 双层查找 | 7例通过 |
| 原 SItemTips decoder + 实际消费者 + 完整查找 | 6例通过 |
| 原 SItemTips 非正字段拒绝 | 2例按预期拒绝 |
| 完整原非空/空详情 parser | 8例，顺序/清空/聚合/score 均通过 |
| 评分表 getter / 真实调用函数 | 全映像 direct-call 静态扫描7处；完整函数1626条指令，未执行评分全函数 |

未验证：原服务器权限及扣费、材料消耗、source 对其他容器的允许范围、服务端替换位序、宝石评分原式、完整UI交互与配置对象生命周期、真实角色/断线重连/服务事务、根人物属性投影、实际可玩性。本批没有修改生产、共享入口、冻结 inventory/equipment_detail/currency、其他研究报告或设计政策。

架构接线建议沿既有约束：领域命令保存明确的 bag/equipped 目标类型，进入当前角色所有者；在同一租约/资产版本事务中复核定位与消耗。客户端 wire source 是请求意图，不是资产所有权证明。本文只交原证据和接缝，不替集成方选择运行时入口或宣称共享投影已经接通。
