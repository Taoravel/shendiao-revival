# 玩家同屏元数据：朝向、扩展属性与未确认低位

2026-10-23。本批只读原客户端映像并离线执行原指令；不启动游戏、GUI、服务，不读取在线进程、不改存档或共享接线。冻结后仅补本文，源码保持主集成已复跑的44项版本。本文不把协议通过称作真实双客户端同屏验收。

## 方法与一手来源

采用已读 `research`：从原指令、RTTI 与配置对象拥有者追溯字段，不用既有文档的业务名称互证。采用已读 `diagnosing-bugs` 的窄反馈环和单变量反事实：在同一个原 `0x11dd8a0` handler 中只改变 packed byte 或一个 map entry，检查传给真正角色创建入口 `0x11da180` 的 RoleInfo；另执行原角色→引擎方向路径和原整数 map 分发。这里的可判定症状是“字段被投影到错误槽/错误消费者”，不是已重现游戏画面的完整反馈环，因此不宣称修复视觉故障。已读根 AGENTS、ARCHITECTURE、DESIGN_AUTHORITY；无现存 GLOSSARY/ADR 文件。本批是父任务委派的独立研究，没有再委派或改其他所有者模块。

唯一指令源：[native-image.bin](native-image.bin)，BASE `0x400000`，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。复核入口：[verify_world_role_metadata_native.py](../verify_world_role_metadata_native.py)。结果：[world-role-metadata-native.json](world-role-metadata-native.json)；指令摘录：[world-role-metadata-native-disassembly.txt](world-role-metadata-native-disassembly.txt)。前一批原 codec、shape 转换和 RoleInfo→角色复制路径见 [WORLD_ROLE_PROTOCOL.md](WORLD_ROLE_PROTOCOL.md)，本批没有改该 codec。

离线验证命令（项目根目录运行）：

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' revival/verify_world_role_metadata_native.py
```

实际结果 `passed: 44`，父集成独立复跑同样44项通过：8项 packed 投影、14项标量 Octets entry 投影、16项真实引擎方向转换、6项整数 map 原分发。原 C++ 字符串、分配、原子引用计数、memcpy 的宿主 ABI 由等价适配提供；没有替换 `11dd8a0` 的分支、标量 decoder、原方向转换和 map 迭代。创建测试停在 `11da180`，未创建GPU实体。整数 map 测试在 `11edd30` 等表现调用边界捕获参数，未执行装备模型装载；不能从其通过推导任意 key/value 都是有效装备组合。

## packed_2c：已确认高位，低位仍不命名

`11dd93e..11dd962` 直接执行：

| wire 来源 | 原处理 | 临时槽 | 角色槽/消费者 | 结论 |
|---|---|---|---|---|
| `packed & 0x0f` | 加10 | RoleInfo+48 | `120c698` 复制至角色+1a8，`1209d80` 返回它 | `client_verified` 数值投影；业务枚举未知 |
| `packed >> 4` | 原值 | RoleInfo+54 | 复制至角色+1b4；`120d6c6` 调角色vt+e4 | `client_verified` 朝向编号 |

低位单变量 `0x70/71/72/79/7f` 得到 +48 的 `10/11/12/19/25`；高位单变量 `0x01/31/71/f1` 得到 +54 的 `0/3/7/15`，其它捕获字段不变。测试值 `0x71` 只用于控制变量，不是生产默认。

高位不再仅凭表现槽猜测：角色vt+e4=`1202db0`→`11f5b00`，正常移动模式下尾调用模型vt+40；`Sprite@XiaoPang` RTTI 对应vt `2462544`，该方法为 `652750`，调用原 `651700` 将编号变为向量，再交 `6519d0`。本批16项用原 `11f5b00→652750→651700` 全链执行，只在最终向量提交边界捕获：

| 高四位/方向 | 原引擎向量 `(x,y,z)` |
|---|---|
| 0 | `(0,-1,0)` |
| 1 | `(1,-1,0)` |
| 2 | `(1,0,0)` |
| 3 | `(1,1,0)` |
| 4 | `(0,1,0)` |
| 5 | `(-1,1,0)` |
| 6 | `(-1,0,0)` |
| 7 | `(-1,-1,0)` |
| 8–15 | `(0,0,0)`，原转换的缺省分支 |

生产若已有明确方向0–7，可确认 `packed=(direction<<4)|opaque_low` 的**高位编码**。没有证据规定新角色应初始朝哪个方向，也没有本批证据把向量编号命名为地图东南西北；不要把固定方向或从移动差值量化方向的算法标成原服规则。原角色特殊移动状态可以跳过设置，fixture明确选取两个模式检查均false的正常分支。

## 门派111与等级：不能从当前证据冒充已恢复

**低位算术只能产生10–25，111不能原样进入 RoleInfo+48。** 如果服务端把 `(111-10)&15` 写低位，原客户端得到15，不是111；把111取模100得到11也没有对应原映像变换证据。低位的11–19恰好与旧门派号重合，只能构成候选，不能证明其业务身份。本批定位到 +48→角色+1a8 的复制与getter，未定位到能为其业务名称背书的原配置/UI消费者；所以保留 `opaque_low_nibble`，不把它命名 school、sex 或 camp。查遍本handler的扩展分支，也没有确认“111专用补位/高位覆盖”链。

原 `SEnterWorld Process 8337c0` 另有明确的 `packet+34=level`、`+38=school`、`+3c=shape`：`833949..833978` 用 +38 查 `SchoolInfoTable`，`833988..833999` 查 `SchoolMasterSkillInfoTable`，属于自身人物资料路径。原 [schoolinfo.xml](../decoded/config/autoconfig/knight.gsp.role.schoolinfo.xml) 中111是少林，11是古墓，不能因同屏未知而改变权威门派。这个明确主角色来源不自动证明同屏另一个 byte 或任一 map key 等价；同样没有确认可把 `server.role.level` 填入此协议某个标量槽。

从本批证据得出的可接线边界：同屏的 school/level 保留在权威角色快照与已确认的其它协议中；在 `RoleBasicOctets` 上没有确认映射时，不随意写扩展 key。若集成为最小同屏指定低位常量和空扩展表，必须集中登记为 `designed` 的最小表现政策，保持未来可替换，不能宣称已原生还原。本文没有选定或修改这个政策。

## properties 是整数表现表，不是通用人物属性表

`11de883..11de88f` 把 inner+34 传 `11f0970`。原循环在 `11f0b50..11f0b82` 对非7/8键调用 `11edd30(player,key,value,0)`；key1另调用 `11ec1c0(value)`、`11eb1b0`、`11eb070`。本批分别只放一个 key1–6、观察原分发，6例通过。用49009只是有辨识度的输入值，并不证明49009适合每个位置。

`11edd30` 在 `11ede92..11edea5` 把 key1–6分至6个表现分支；key1 `11edeac..11edec0` 使用 value 查询 `89d4c0` 返回的配置表。该 getter 返回 ConfigManager+480；原 manager析构 `c99111..c9911c` 对同偏移调用 `86a480`，其 `86a4c5` 将对象虚表复原为 `224f698`，RTTI是 `CEquipEffectTable@item@gsp@knight`。这条表身份链与已有物品装备配置相符，足以排除“key1是school或level”。不是通过看起来像模板ID就下结论。

| int key | 已证行为 | 状态/限制 |
|---|---|---|
| 1–6 | 原 `11edd30` 六个表现分支；1查CEquipEffect | 客户端表现 key；本批没有证明每个编号对应哪个装备槽/数量/实例属性 |
| 7 | `11f098b` 特查并写 player+e8/cache；普通循环跳过 | 仅存储与专用分支确认；业务名未知 |
| 8 | 普通循环跳过，`11f0bd8` 后特查→`11eb290` 等 | 专用表现分支；业务名未知 |
| 其它 | 原循环仍可分发，`11edd30` 不进1–6主模型分支 | 不将可解码视为有效属性含义 |

因此现有角色有持久装备快照也不能仅凭“装备slot0”直接写 properties key0/1；须另由已确认装备→表现映射提供。仅有 shape/school/level/name 时，不能生成可信的非空整数表现表。空表可作为显式最小表现政策，不能称已恢复武器外观。

## octets_properties 的已证 key 矩阵

这是 inner+40 的 `map<byte,Octets>`，和上面的整数 map 是两个容器。`11dda91` 使用 key-1索引 `11de9e4` 的26项跳表。以下14项单变量分别以BE i32 `111`、`37` 输入原 `770ac0`，改变指定RoleInfo槽且保持 packed 的+48/+54不变。

| Octets key | 原 case 地址 | blob格式 | RoleInfo 目的 | 本批业务结论 |
|---|---|---|---|---|
| 3 | 11ddd09 | BE i32 | +24，后复制至角色+184 | **称号配置ID**：`12041c0` 读该槽，经89eee0→ConfigManager+11d8；`c976eb→89b670→89b6b5` 的vt22510d0 RTTI为CTitleConfigTable。不是人物等级 |
| 8 | 11ddf6b | BE i32 | +b4 | 未命名 |
| 19 | 11de48a | BE i32 | +d8，后角色+238 | `12029c0` 专用资源表现链；未命名，不称level |
| 21 | 11ddc9c | BE i32 | +7c，后角色+1dc | 专用表现状态；未命名，不称school |
| 23 | 11de4f0 | BE i32 | +c8 | 未命名 |
| 25 | 11de5c9 | BE i32 | +e0 | 未命名 |
| 26 | 11de62c | BE i32 | +e4 | 未命名 |

其它静态分支保留为后续线索，不混入44项已执行结论：key12也调用770ac0→+b0；key11/13/14调用byte decoder；1/2/15/17/18/22涉及其它bean；4/5涉及字符串；6/7/9/10/16/20走缺省。没有为这些分支补造payload或擅自命名。原 key3称号身份的表链为静态指令/RTTI核验，fixture验证的是decoder和RoleInfo+24投影，没有加载真实称号表或渲染称号。

## 给集成方的字段来源矩阵

| 已有权威资料 | 同屏可确认构造 | 仍需明确来源/政策 |
|---|---|---|
| role_id | inner roleID q64，玩家身份查找；outer列表用真正RoleBasic | 正数范围等使用现有codec约束；不借NPC键替代玩家ID |
| name | UTF16LE名字Octets→原RoleInfo字符串 | 名字校验由角色所有者负责 |
| shape | inner+30；完整合法模型ID如1010109保留；1–10与11–299原转换见上一批 | 不从school生成shape；变身/骑乘等覆盖另行确认 |
| 已校验地图位置 | outer signed16 Pos→RoleInfo+4c/+50 | 有效场景/epoch/位置版本由MapOwner提供，不能用UI格坐标替代 |
| direction0–7（若有） | packed高4位，原引擎八方向已证 | 未存方向时初始方向是设计选择；低位仍独立opaque |
| school，包括111 | 本batch无已证同屏槽 | 不能填整数map或截低4位；不能把111改成11/15 |
| level | 本batch无已证同屏槽 | 不填blob key3；其实际是称号ID |
| 装备、称号等（目前仅基本四项资料） | 不足以生成非空表现扩展 | 由对应所有者提供已确认表示或登记最小空表政策 |

与现有 `world_roles.RoleScene` 的 Seam 保持不变：调用方提供冻结的 `RoleBasic` 快照；研究脚本不读取数据库、不广播、不持有Session。不改 `world_roles.py`、`world_role_protocol.py` 或任何部署配置。此次交付的调用接口仅为独立离线核验 `project(...)`、`direction(number)`、`integer_property_dispatch(key,value)` 和上述证据矩阵；不引入生产默认值。

未验证：低位业务名称/新门派编码、远端等级扩展、完整key枚举、每个整数表现key对应的装备槽、跨状态朝向与移动量化、GPU模型/称号/装备实际显示、两客户端真同屏、正式网络与并发接线。没有把这些未知扩成事实；也没有用“44例通过”覆盖真实画面验收。
