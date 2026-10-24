# 世界实体原生协议（2026-10-23）

本批是离线原生协议核验与纯编码 Module；没有接入网络、世界可变状态、数据库或共享入口。适用本地 1.6.1 解包映像；不是客户端显示或容量验收。

## 方法与可重复证据

按 research 使用本地客户端第一方映像，而非攻略猜字段；本任务本身是父任务委派的后台研究，不再次拆代理。按 codebase-design 将 wire 实现集中在 `world_entity_protocol.py`，Interface 返回不可变 bytes，场景所有权、实体注册与投递留给调用者。遵守根 AGENTS、ARCHITECTURE、DESIGN_AUTHORITY，未改共享文件。

主来源：[native-image.bin](native-image.bin)，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。原地址全文由 [research_world_entities.py](../research_world_entities.py) 重新提取，见 [world-entities-native-disassembly.txt](world-entities-native-disassembly.txt)。

[verify_world_entities_native.py](../verify_world_entities_native.py) 经 Unicorn 执行原 constructor/marshal/unmarshal，fixture 与 Python 输出逐字节比较，原 decoder 必须消费完整载荷并返回。仅替代 CRT 分配、字符串、内存搬运，不替换 wire 例程；非空 vector 需额外 memmove_s host adapter，共用 probe 未修改。结果：[world-entities-native.json](world-entities-native.json)。

9项通过：NpcBasic；SAddUserScreen单NPC；SRemoveUserScreen单NPC；SAddActivityNpc双ID双坐标；SRemoveActivityNpc双ID；NpcBasic非空属性map；CVisitNpc；CNpcService；SVisitNpc双非空vector。属性map仅原 decoder 核验，其他均原 marshal+unmarshal。

## 已证实布局 client_verified

wire 整数为大端，字符串为 compact字节数 + UTF-16LE，容器为 compact元素数。

| 消息 | type | wire |
|---|---|---|
| SAddUserScreen | 0xc0fa5 | RoleBasicOctets list，然后 NpcBasic list |
| SRemoveUserScreen | 0xc0fa6 | role q64 list，然后 NPC q64 list |
| SAddActivityNpc | 0xc0fbf | 配置ID i32 vector，然后 Pos(i16 x,i16 y) vector |
| SRemoveActivityNpc | 0xc0fc0 | 配置ID i32 vector |
| CVisitNpc | 0xc2329 | 非负 signed q64 key（严格8字节） |
| SVisitNpc | 0xc232a | 非负 signed q64 key，然后两份 i32 vector |
| CNpcService | 0xc232b | signed q64 key + i32 service（严格12字节） |

SAddActivityNpc 的两个 vector 必须等长（handler `0x1230b93`），原 wire serializer 自身没有这项等长校验。`0x1230bd8` 调 `0x1228d20` 按配置ID查已有活动项，已存在则跳过。因此此协议不能表示同图同配置的多个独立实例。次 vector 在内存中每元素8字节（包含4字节vptr），wire只有4字节坐标，绝非 u64 实体key。handler `0x1230b20` 到 `0x12295d0` 可确认地图标签路径；不能将活动列表消息当成3D NPC实体快照。

真实实体走 SAddUserScreen：constructor `0xfc5f40`、marshal `0xfc68f0`、unmarshal `0xfc69a0`。第二 std::list 元素在原 decoder 成为 NpcBasic，process `0x11e7015` 分支最终调用 `0x11d9c70`，按完整q64 key查场景实例，缺失则分配 `0x12017f0` NPC对象。配置ID经过 `0x89df90` NPC配置查表。可以以不同key表示相同配置的多份摆放；是否屏显与点击需真实客户端验证。

NpcBasic（vtable `0x2286850`，marshal `0xfc6f70`，unmarshal `0xfc73a0`）：

| 对象offset | wire | 含义与证据 |
|---|---|---|
| +8 | q64 | 实体key；process原样传场景实体索引 |
| +0x10 | i32 | NPC配置ID；process `0x11e7089` 从node+0x18取出并查NPC配置 |
| +0x14 | text | 名称 |
| +0x30 | i16,i16 | 当前Pos，坐标存于+0x34/+0x36 |
| +0x38 | byte | process仅比较==1转内部bool；用途未命名 |
| +0x3c | i16,i16 | 第二Pos，坐标存于+0x40/+0x42；目标位置推定，非已证实朝向 |
| +0x44 | i32 | 传内部info+0x1c，未命名 |
| +0x48 | i32 | 传内部info+0x20，未命名 |
| +0x4c | i32 | model/shape覆盖；0用配置默认形象，见下一节 |
| +0x50 | i32 | 传内部info+0x4c，未命名 |
| +0x54 | map<byte,i32> | compact count及逐项byte key+i32 value；具体属性key用途未证实 |

## 怪物形象接入所需事实

`0x11e71d2` 将node+0x54（bean+0x4c）传内部info+0x40。NPC初始化 `0x1201bd0` 的 `0x1201e01` 读取info+0x40：非0则作为形象ID，0则使用sceneNpc+0x15c（NPC配置默认值）。随后交模型虚函数+0xfc/+0x108，`0x120213f` 经 `0x89e010` 查形象表。由此可在保留有效NPC配置的前提下，用field_4c覆盖形象；这只恢复模型候选通道，不赋予monster模板战斗规则。不存在证据证明 monster模板ID == NPC配置ID，禁止混用。

## 调用与未验证范围

`npc_screen((NpcBasic(server_key, 10000, name, 1680, 5311),))` 提供临安NPC10000的候选快照；名称/摆放取原catalog，key需地图所有者分配并关联摆放ID。此处坐标由父任务原摆放解析确认，不是NPC配置格坐标直接发送。

`read_visit_npc`/`read_npc_service` 只做wire读取；角色epoch、地图版本、距离、NPC服务白名单与任务事件由地图/角色所有者校验。客户端传key不是可信静态配置ID。NPC3D显示、点击返回key、交互菜单、非空角色list、模型覆盖真实视觉及各属性枚举尚未实机验证。没有商业并发或全量恢复完成结论。

SVisitNpc constructor `0xe70050`、marshal `0xe701b0`、unmarshal `0xe700f0`；process `0x1214250` 查完整key对应场景对象，再把两个vector交 `0x120f4e0` 对话描述和 `0x1635f10` UI入口。`visit_npc_reply` 已可输出非空菜单候选，两个vector业务含义未核实，暂用offset命名，不能把任意任务ID或服务ID批量塞入。最小空vector回复可作为实机探针，不宣称已恢复对话菜单。
