# 真实玩家同屏与移动下行：原生协议

2026-10-23。采用research追到原映像字段/调用者，codebase-design将wire构造集中在独立纯Module的小Interface，返回body、不处理AOI/状态/网络。已读ARCHITECTURE、DESIGN_AUTHORITY；可变AOI和位置仍属地图所有者，角色形象取角色所有者快照。本批仅新增独立文件，没有改共享入口、world_entity_protocol、角色存档、游戏进程，也未启动客户端、GUI或服务。

第一方来源：`evidence/native-image.bin`，BASE0x400000，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。索引/可复查指令入口 [research_world_roles.py](../research_world_roles.py)，原地址索引 [world-role-native-addresses.json](world-role-native-addresses.json)，原生执行结果 [world-role-native.json](world-role-native.json)，指令 [world-role-native-disassembly.txt](world-role-native-disassembly.txt)。

## 可调用Interface

[world_role_protocol.py](../world_role_protocol.py)提供冻结`RoleBasic`、`role_basic_octets(role)`、`role_basic(role)`、`role_screen(roles)`、`remove_role_screen(role_ids)`、`role_move(role_id,x,y)`及原布局兼容的`role_stop`。调用者将返回body交给连接所有者封包；不能将它当作客户端已可见确认。

```python
from world_role_protocol import RoleBasic, S_ADD_USER_SCREEN, S_ROLE_MOVE, role_screen, role_move

# packed_2c=0x71只是已验证离线fixture值；生产值需来自已确认形象快照/明确政策。
body = role_screen((RoleBasic(123456, '侠客', 9, 1680, 5311, packed_2c=0x71),))
move_body = role_move(123456, 1696, 5311)
```

role ID工作域为正signed64；坐标按原signed16，禁止在body里预先乘渲染X的1.5；名字UTF16LE octets。本地限每批4096角色、每路径4096点、名字512字节、map最多256个唯一byte key。byte-key map按原signed-char比较排序。`role_screen`只装玩家第一容器并明确发送空NPC容器；要合并NPC列表时由集成方按原两容器布局组合，不在本批重写既有实体codec。未知元数据不由codec猜值。

## SAddUserScreen的两层玩家bean

SAddUserScreen `0xc0fa5`顺序是RoleBasic list、NpcBasic list；第一容器**不是直接裸RoleBasicOctets list**。此前早期实体文档把内层名直接写成容器名，本批以原bean补正：每个RoleBasic里先含一个序列化RoleBasicOctets的octets，再跟坐标等外层字段。

RoleBasic：vt`0x228683c`，constructor`0xfc6bf0`、marshal`0xfc6d30`、decoder`0xfc6c80`。

| 对象偏移 | wire顺序/布局 | 已确认用途 |
|---|---|---|
| +4/+8 | compact字节长度+raw octets | 内层RoleBasicOctets序列化数据 |
| +0xc（coords+10/+12） | BE signed16 x,y | 当前逻辑坐标Pos |
| +0x14 | byte | `==1`被handler映射到RoleInfo表现flag；业务枚举未命名 |
| +0x18 | compact数量+每点BE signed16 x,y | Pos list；handler对0/1/2/4点有不同初始移动表现 |

RoleBasicOctets：vt`0x2286424`，constructor`0xfad590`、marshal`0xfad940`、decoder`0xfae280`。

| 对象偏移 | wire顺序/布局 | 已确认用途 |
|---|---|---|
| +8/+0xc | BE q64 | 真实玩家role ID |
| +0x10 | compact字节长度+UTF16LE | 玩家名称 |
| +0x2c | byte | 低4位+10→RoleInfo+48，业务含义仍未确认；高4位→RoleInfo+54→原引擎八方向向量，详见WORLD_ROLE_METADATA_RESEARCH |
| +0x30 | BE i32 | shape来源；handler转换成模型配置ID |
| +0x34 | compact数量，byte key+BE i32 value | 元数据map；各key语义未在本批完整恢复 |
| +0x40 | compact数量，byte key+octets value | 扩展元数据map；保留原blob，不猜子bean |
| +0x4c | byte | 尾字段；本批未确认用途 |

**本布局没有一个已确认独立school标量。** 不把shape当school，也不把打包byte或map的某个零值擅自叫门派；school/等级等属性若在扩展map中，需要继续追key的原消费者。当前最小空map的原codec和创建参数已验证，不表示所有头衔、队伍、门派、装备外观都已恢复。

后续44项原生元数据单变量验证已独立复跑：高4位经player朝向链进入原Sprite八方向，0..7依次为(0,-1)、(1,-1)、(1,0)、(1,1)、(0,1)、(-1,1)、(-1,0)、(-1,-1)，8..15给零向量，不能把这些未定义值作为新增方向。低4位只证实展开为10..25，没有发现school111的直接/取模/扩展覆盖依据。int properties key1..6进入装备/外观消费者；octets key3经原配置lookup进入称号表，不是等级。生产元数据不得据此编造门派/等级，原0x71仍只是离线fixture。详细原地址、Adapter和未证范围由WORLD_ROLE_METADATA_RESEARCH维护。

## 真实玩家创建路径

SAddUserScreen handler`0x11e69f0`在`0x11e6f56..0x11e6fbf`对角色octets调用原constructor/decoder，随后以外层RoleBasic与内层RoleBasicOctets调用Scene `0x11dd8a0`。它拷贝role ID/name/Pos并展开packed byte；shape<=10时转为1010100+shape，10<shape<300时转为2010100+shape%100，>=300保留。不要把这些是原生转换误写成服务器需要发送1010109：原输入shape9已经产生该模型ID。

handler在`0x11de739`调用`0x11da180`；后者以role ID查玩家表（`0x11d5330`），已有则更新，缺失时分配并执行玩家constructor`0x120a330`，vt`0x2298bcc`，之后调用vt+0x188初始化并插入Scene玩家表。它不是NpcBasic的NPC注册路径。

两份原handler执行fixture在到达玩家create调用时捕获实际参数：shape9/packed0x71→model1010109、RoleInfo+48=11/+54=7；shape10/packed0x32→model1010110、RoleInfo+48=12/+54=3。坐标均1680,5311原样保留。fixture执行了整个前置handler和临时bean构造，仅在实际创建引擎角色前停止，未执行GPU或模型加载；没有将“到达创建调用”叫作真机同屏成功。

## 移动、停止与移除

| 消息 | type | body | 原方法 |
|---|---|---|---|
| SRoleMove | 0xc0fa2 | BE q64 roleID + BE signed16 x,y | ctor dacd10；marshal e50d90；decode dacdc0；Process11d7fc0 |
| SRoleStop | 0xc0fab | 相同12字节 | ctor dad130；marshal e50e60；decode dad1e0；Process11c56c0 |
| SRemoveUserScreen | 0xc0fa6 | q64角色list，然后q64 NPC list | ctor e6e9e0；marshal e6ea90；decode e6eb20 |

SRoleMove Process从包中取role ID查Scene玩家表；目标非主角时，`0x11d8147..53`调用该对象vt+0xb0，参数为sign-extended x,y。玩家实际vt+0xb0=`0x1205fd0`设置目标并进入角色移动流程；主角另有校正和状态判断，不能直接把这一广播当本地移动授权。

**本映像SRoleStop Process只有`c2 08 00`（ret8），是空处理器。** 原生fixture执行后没有方法调用或对象写入。所以虽然codec兼容，发它不能保证远端玩家立即停步。SRoleMove是目的坐标下行，不携带速度、路径或场景世代；精确停步/迟到包问题不能靠发SRoleStop或虚构epoch字段宣称解决。普通路径的自然到达与其它校正下行仍需联调。

本地主角纠正、SSetRoleLocation和SRelocateRolePos的23组handler/5组codec证据见WORLD_MOVEMENT_RECONCILIATION_RESEARCH。SRoleMove可能继续旧目标，SSetRoleLocation仍可留下待上报history，且实际位置setter另有状态拒绝；均不能称完整清规划/历史屏障。该研究未接生产codec或制定纠正触发策略。

`remove_role_screen`编码第一list为真实玩家role IDs、第二list为空NPC；不能拿NpcBasic key或NPC集合位置替代。

## 验证与未验证

执行`verify_world_roles_native.py`共13项通过：内层/外层原marshal+decoder、非空玩家入屏及移除、Move/Stop各两组坐标原往返，含负坐标；非空两map与两点path由原decoder验证；两组原handler到创建参数的执行；原remote Move分派及Stop空处理器执行。非空map/path的原serializer未测，报告明确区分。fixture手工构造STL容器壳/树头，仅系统堆、CRT string和对象外部lookup/调用边界用host adapter；原wire与handler分支不重写。

未验证：真实两客户端同屏、角色模型/名字实际渲染、school和各扩展key、packed byte的完整枚举、角色所有元数据组合、带NPC混合入屏批次、移动插值/速度/精确停步、AOI并发和客户端加载时序。未因用户禁止打开游戏而启动新现场，也未修改服务端玩法或持久化。
