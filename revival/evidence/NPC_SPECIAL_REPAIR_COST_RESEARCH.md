# 原 tag6..11 特殊修理报价：原字段到公式

2026-10-24；本地原端游1.6.1/网络版本601。新增独立研究，不改原96例、鉴定/冻结查询、任何生产/shared/政策/真实库/客户端/服务。**656个新原生费用样例通过**；此前96例只保留哈希，未重跑或重新计入。

原 `0x10dbb20` 的 tag6..11 分支现在已执行到最终 signed64 报价。它不读普通 `cequiprepairconfig`，也不按 method0/1/2 选择费率。公式使用原配置 `CItemAttr.level`、原解析得到的颜色标量与条件字段；不是普通修理公式。服务855原入口 method2仍仅是旧证据，本批不因此授权Inventory接纳特殊装备。

产物：[research_npc_special_repair_cost.py](../research_npc_special_repair_cost.py)、[JSON结果](npc-special-repair-cost-native.json)、[原字节/反汇编](npc-special-repair-cost-native-disassembly.txt)。项目根可复跑：

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/research_npc_special_repair_cost.py
```

## 方法和实际决定

本批读取并使用 research、codebase-design、ARCHITECTURE、DESIGN_AUTHORITY。已经委派的研究子任务直接追第一方本地映像/PFS，不递归委派、不搜web。research方法要求每个计算输入可追到原 getter/赋值，不能 Adapter 待证 getter或最终报价；本批实际执行原完整 EquipObject构造/详情解析、原 CItemAttr整数复制、所有报价getter、原整数幂、x87计算及最终取整。codebase-design用于把报价 Module 的 Interface 与资产资格/扣款 Seam 分开：证明公式不代表已有合法特殊实例模型，更不授权普通六槽condition或NPC服务扩权。

实际决定：以真实原配置12个模板覆盖6种tag；q、current、maximum来自明确wire fixture，走原parser赋值，不把标准最大耐久100当原特殊装备事实。读取原PFS后逐项核对复用解析器Adapter所用catalog，防止把缓存来源当第一方原数据。原96例文件在执行前后校验哈希，禁止写入。

## 第一方源与旧证据冻结

原 `native-image.bin` SHA-256：`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。以下地址属于该离线映像，不是在线客户端读取。本批重新读取 `artres/config.pfs`、核对解压长度/CRC并BXML解码：

| 条目（autoconfig/knight.gsp.item.） | 字节数 | CRC32 | SHA-256 |
|---|---:|---|---|
| citemattr.xml | 4096369 | a3add081 | 974a3b38049c5f5f7cdae418718ffadd2741d373a5846a40fb71289af25e726f |
| cequipeffect.xml | 467441 | e354a76d | 8ef1aacae8d016f875a37a8cf907b16a077b89fa522a87e349dd54d320572fe8 |
| cequipprefixconfig.xml | 291 | c8592725 | 3b36fed5bf4e62e41ceec422d902f8479bdcc487e82351750168ba130805e7ae |
| cgodweapon.xml | 3704 | 65746fc2 | 295fbe76d7deaef3bb4c17733f329ce41384c5724b6aef713b93a7a6abfa86a2 |

保留旧96例的 SHA-256（脚本前后assert，JSON `historical_96_files_sha256`）：

| 旧文件 | SHA-256 |
|---|---|
| research_npc_special_repairs.py | 88bb5258c17a9db8d1dd28324f2528d98b79b16097edb14d5b54b43368452023 |
| npc-special-repairs-native.json | 8ecc806aab098d8d0e2edac192f57517c1e05f66746e3919ac809f927e8d83dc |
| NPC_SPECIAL_REPAIRS_NATIVE_RESEARCH.md | 10a418afe9175882a7dc9712ad126287dd951a77eef88087428e8162cd7044a3 |
| npc-special-repairs-native-disassembly.txt | d8c1b02d345911c1e2e5cd74155a827270e3e197e8271780b6051d89402053ed |

## 原类型与等级来源已闭合到本公式

原 `CItemAttr` reader `0x86e8e7/0x86e910` 将 itemtypeid 写record+4；`0x86e95a` 引用UTF16 `0x2251a44="level"`，`0x86e983` 写record+0x24。这里是 **level，不是仅凭值相等猜 needLevel**。

本批执行原初始化 `0x1080720` 的lookup调用，按真实template ID返回原配置行；原 `0x1072890` 先复制 id/type，再在 `0x10728af..0x10728b2` 将 record+0x24 复制到目标+0x24。目标原本是wrapper+4，因此精确落到 wrapper+0x28。只将中间wstring复制作为宿主Adapter；在 `0x10728bb` 停止，其余不相关wrapper配置未初始化。原getter `0x1074d10` 在这些完整type104/120/136/152/168/184上实际返回刚复制的wrapper+0x28。没有人工写目标level或替换getter。

| tag | 原type | 原总条数 | 本批真实template（原名） | 配置level |
|---:|---:|---:|---|---|
| 6 | 104 | 79 | 47000 乌纱帽；47001 铜钱乌纱帽 | 10；30 |
| 7 | 120 | 73 | 47036、47037 倾城之恋（30天） | 10；10 |
| 8 | 136 | 38 | 47005 框镜；47006 墨镜（3天） | 50；30 |
| 9 | 152 | 21 | 47007 桃心口罩；47008 麦秆 | 60；65 |
| 10 | 168 | 6 | 47003 花猫面具；47004 脸谱 | 40；40 |
| 11 | 184 | 112 | 48010 王侯将相（3天）；48020 暹罗之恋（3天） | 10；10 |

counts只证明原表分类数量，12例只覆盖这些实际模板的公式输入链。没有根据名称给6..11拟另一套类别定义，也不将30天/3天文案直接解释为本公式的condition单位。完整type1c8/2c8/3c8的动态等级另走 `0x1074d10` 特例，不属于本批这六种type，未扩大其适用范围。

## 原详情解析到三个 getter

复用独立研究类 `NativeEquipmentDetail`，但未运行它的main、未修改该文件。原构造 `0x107cf80` 与完整详情parser `0x107d960` 真正执行；配置、宿主CRT和空字符串为原有Adapter。相关citemattr行、cequipeffect属性/scorecolor、prefix5配置与cgodweapon ID集合均与本次原PFS核对。

1. 原parser按wire固定标量读 current/maximum，写 bean+0xc8/+0xcc。原 `0x1072dd0` 检查低4位为8，读取 bean+0xc8；原 `0x1072e10` 同样检查类型后读+0xcc。报价实际调用两者并相减。这里只证明字段/读取，尚未恢复这些特殊物品的原生成上限、时间含义或衰减规则。
2. wire前缀中空字符串之后有 prefix quality、score、color 三个i32。本批固定 prefix5、score9999，单独改变第三个color标量q=1..6。原 `0x107dce3` 将其写bean+0x5c。
3. `0x107dcf0..0x107dd0e` 从原citemattr读tag；**tag>5直接跳到0x107de4e，保留wire color**，跳过普通scorecolor重算。原 `0x1073090` 读取bean+0x5c，报价调用三次均得到原解析值。因而q不是prefix_quality5，也不是score9999。特殊服务器怎样生成q尚未知，不能用普通 `rules.color` 代算它。

完整详情fixture为116字节、属性容器为空、扩展标记关闭；原parser消费全部字节。每组wire的SHA保存在JSON；完整helper有原高级容器读取指令，但本批没有开启高级特性。当前值/最大值/q是显式线包输入，不是从真实角色或原服务器取得的已存实例。

## 特殊公式与精度

原 `0x10dbb37..0x10dbb4e` 判断 `(wrapper.itemtypeid>>4)&15`：6..11进特殊段 `0x10dbb54..0x10dbc17`；其余普通段不在本批执行。以 `q=原1073090返回值`、`L=原1074d10返回值`、`D=原1072e10−原1072dd0` 表示，q1..6上的计算可写为：

```
factor = q <= 4 ? binary32(0.8) : 1
divisor = 2 - trunc(min(q, 4) / 4)   # q1..3为2，q4..6为1
power = 原1073d70(binary64(1.3), q - 1)，再存binary64
quote = trunc_signed64(L * (2 * factor) * D * power / divisor)
```

证据：`0x10dbb61` 检查q<=4，载入float32常量 `0x2474050`，实际值 `0.800000011920929`（hex `0x1.99999a0000000p-1`）；`0x10dbb97` 载入double常量 `0x228c2c8`（1.3，hex `0x1.4cccccccccccdp+0`），原 `0x1073d70` 执行整数幂，`0x10dbbaf` 存double；`0x10dbbe0..0x10dbc0a` 计算整数除数并按原顺序乘除。最终 `0x10dbc0c` 调 **0x1919216** 返回EDX:EAX signed64截断，不是普通分支最后的signed32路径。

所有getter、原power和ftol实际执行，未以Python函数代替。脚本只在原指令地址观察已存double、float与分母，再用Decimal核对乘除表达式；这不是对原幂值的独立数学重实现，原幂实现本身由原指令执行。接口若将来重写纯公式，须另以这些原结果作oracle，不可简单用十进制0.8或直接Python pow替换并忽略截断差异。

特殊段 **不读取 method参数，不调用0x89d550、不取npcrepair/familyrepair/skillrepair**；三个方法的实际执行结果逐例相等。method99/-1诊断也同价，只证明函数本身不校验method，不授予这些请求有效性。service93的组织资格和855的实际开放范围仍与纯报价分开。

## 新656例分层与样例

主体648例：12个真实模板 × q1..6 × `(current,maximum)=(0,100)/(80,100)/(100,100)` × method0/1/2。每个模板先走原配置赋值；每个条件/q组合都重新走原完整详情parser，再调用整段报价。最大值100是便于隔离算术的fixture，**没有声称是特殊物品原耐久标准**。

| 实际模板/原L | D=20时q1 | q2 | q3 | q4 | q5 | q6 |
|---|---:|---:|---:|---:|---:|---:|
| 47000 / 10 | 160 | 208 | 270 | 703 | 1142 | 1485 |
| 47005 / 50 | 800 | 1040 | 1352 | 3515 | 5712 | 7425 |
| 47007 / 60 | 960 | 1248 | 1622 | 4218 | 6854 | 8911 |
| 47008 / 65 | 1040 | 1352 | 1757 | 4569 | 7425 | 9653 |

q3→4的突变包含整数分母2→1，不能光用平滑品质幂公式替代。D=0均报0，current0/max100使用相同字段链产生对应100缺口金额；没有硬编码“一件完整装备固定多少钱”。

额外8例为受控诊断：0/0与20/20均0；current101/max100报-8；q0报123、q7报1930；q6/current0/max2147483647报159469129149，确证保留高32位；method99/-1与q4标准测试均报703。后三类是原函数接受度/数值宽度，**不是合法实例或服务器权限**；不能把负报价当奖励、不能据此允许q超范围或任意巨大条件值。真实最大值/状态限制未恢复。

## Adapter、剩余未知与交接

Adapter限于：原parser宿主CRT/空wstring/配置lookup；原初始化copy的wstring赋值；原配置行内存布局、wire fixture和对象连接。实际待证的q/current/max/level getter、幂、特殊公式和signed64取整均未替换。wrapper只初始化本公式需要的真实id/type/level前缀，再连接原完整parser构造的bean，不声称整套原wrapper构造或CEGUI完成。

目前可交付的是独立特殊报价算法/字段来源。仍未知：特殊物品实例的q/条件生成、上限与单位、时限和耐久关系、修理成功/失败及最大值变化、材料和币种、方法对应服务端资格、855真实NPC绑定、原服务器扣费事务/回执、真人GUI。原cequipeffect存在endurecoef（本批例项500或300，JSON保留）不能直接充当最大值或修理材料公式，本批未套用它。

原Inventory仅支持ordinary六槽的边界仍保留；本研究未调用或修改生产模块。下一领域实现必须先有特殊资产状态及合法来源，再由角色所有者在统一事务使用明确政策和NPC授权；不能借已证费用将普通修理兜底扩展到tag6..11。本批到此停止写入，供根任务独立重跑。
