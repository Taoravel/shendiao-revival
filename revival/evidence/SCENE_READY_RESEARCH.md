# 普通跨图加载完成确认调查

2026-10-23（Asia/Shanghai）。目标：本地端游1.6.1 / 网络601的现有原生映像。只读研究，未启动游戏、注入、发包或操作当前现场；仅写本文件。

## 可交接结论

**本轮尚未找到可以绑定 `scene_ready` 的通用客户端消息。** 原生确认了普通换图的本地加载成功判断与延时回调，但尚未证明这些回调向服务器发送通用ready。不能把首入世界 `CAfterEnterWorld(0xc003d)`、普通移动、固定500ms延时或特定任务/地图消息改称普通跨图确认。

本结论是本轮有范围的未确认，不宣称客户端绝不存在其他间接发送或独立ready。接线阻塞仍然成立；可以交付精确下一步入口，但不能交付已验证通用ack。

## 当前服务器公开接入状态

读取 `revival/game_runtime.py`、`verify_transfer_runtime.py`、`world_protocol.py` 及 `evidence/NPC_TASK_RUNTIME_INTEGRATION.md`、`WORLD_RUNTIME_HANDOFF.md`、`ROLE_PROTOCOL.md`。

- 传送完成持久化、清源后发送 `scene_entry(...,reason=0)`，角色保留transfer，目标loading期间拒绝普通移动。
- `scene_ready` 是角色所有者可信host hook，调用目标地图ready、checkpoint、retire_receipt后清transfer，随后重入在线/社交索引并spawn。
- `verify_transfer_runtime.py` 明确用 `owner.mailbox.call('scene_ready')` 测状态机，并断言 loading时移动与 `0xc003d` 不会解锁；产物状态 `native_general_scene_ready_verified=False`。本轮仅阅读，未运行该脚本、未更新测试产物。
- 目前不能称真实客户端普通跨图已完成。将可信host hook绑定到客户端输入仍需可辨识、可关联当前交接的原生证据。

## 一手来源与复查方式

`D:/神雕侠侣/revival/evidence/native-image.bin`，BASE `0x400000`，已知SHA-256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`（本轮沿用同一映像，未重新采集或重做哈希）。用已有 `native_inspect.py` 的RTTI、refs、vtables和Capstone离线反汇编检查。地址均为该映像虚拟地址；未以服务器模拟结果替代原客户端行为。

### SRoleEnterScene 接收与加载路径

`SRoleEnterScene@move@gsp@knight` type `0xc0fa9`，原生process `0x11e3140`；原布局见 `ROLE_PROTOCOL.md`：wstring@8、Pos@0x24（坐标在+0x28/+0x2a）、u8@0x2c、i32 reason@0x30、u64 scene@0x38、u8@0x40、wstring@0x44。本轮没有新增布局猜测。

1. `0x11e3145..0x11e315c`：取得全局对象；相关对象+0x20字节为非0或场景管理器`[0x2944564]`为空时跳到返回，不保证任何消息都必然进入加载。
2. `0x11e3162..0x11e3199`：取reason、标签、坐标和scene，调用场景函数 `0x11e21f0`。`+0x2c==1`转成布尔入参；其完整产品语义未确认。
3. 场景函数在 `0x11e25fc..0x11e2600` 以目标坐标调用 `0x11e0310`；`0x11e260c`保存返回AL；`0x11e269b..0x11e26a5`检查成功，失败直接跳到收尾，不进入后续正常初始化。
4. `0x11e0310` 设置本地加载标记，按地图配置resdir读`maze.dat`及其他地图资源；`0x11e0411`引擎加载调用后检查返回值；成功尾部`0x11e07b3`令AL=1，失败路径AL=0。加载调用完成并不等同屏幕首帧或所有异步资源完成。
5. 成功后 `0x11e26ab..0x11e2765`做人物定位/显示等初始化。部分分支排除reason`0x7dfb7`或地图`0x57c`，不能把所有场景视为相同流程。
6. `0x11e2771`按reason分首入世界和普通分支。reason0走`0x11e2842`起的普通路径。

接收handler `0x11e3199`之后继续地图相关UI等处理；未在本轮读取的handler尾部发现一个无条件的ready消息构造。该handler未将场景函数返回AL直接上传服务器。

### 普通路径的定时器与本地回调

`CGameSceneTimer` vtable `0x228c850`，回调入口`0x11e3a00`，对象+4为case编号，jump表`0x11e3cc4`。

| 注册证据 | case与入口 | 实际看到的动作 | 边界 |
| --- | --- | --- | --- |
| `0x11e2842..0x11e285e` 普通分支对scene+0x10，写case2，调度参数0x1f4 | 2 → `0x11e3a58` | 清场景管理器+0x58；调用`0x1141f90`、`0x11ca340`；`0x1082860`取消/结束定时器 | 500为原调度值，不证明ready时限；`0x1141f90`跳入保护/混淆路径，本轮未完整追通 |
| `0x11e2889`仅地图ID发生变化时，分配定时器并在`0x11e28aa..b6`用case7、0x1f4 | 7 → `0x11e3bda` | 选择当前/替代地图参数后调用`0x11ca5a0` | 地图条件且调用未完整递归追通，不能称通用ready |
| `0x11e28e3..0x11e291f`普通分支创建scene+0x378定时器，case8、0x1f4 | 8 → `0x11e3a89` | 条件调用`0x11ca410`，再调用`0x11c6140`清scene+0x378定时器 | `0x11c6140`本身只看到定时器清理，不发网络包；其条件前置调用未穷尽 |

`0x11ca340`本轮完整读取至return，所见为条件检测和消息提示调用，没有通用ready协议构造。以上证明存在本地加载/定时恢复过程，不足以把任何定时器case当成服务器确认。

### 已定位发包：均不通用

在场景函数 `0x11e21f0..0x11e2eca` 范围定位直接取网络对象`0x813860`及协议构造点：

| 条件 | 消息 | 构造/发送点 | 结论 |
| --- | --- | --- | --- |
| reason=`0x7dfaf`（516015） | `CAfterEnterWorld` `0xc003d`，空body | `0x11e2d00`比较，`0x11e2d0d`虚表`0x226f97c`，`0x11e2d15`type，`0x11e2d33`发送 | 首入世界特有；reason0绕过，不能绑定普通跨图 |
| reason=`0x7dfb2`（516018） | `CQuestReachScene@task` `0xc4a54` | `0x11e2b38`比较，`0x11e2b4b`虚表`0x227dac4`，`0x11e2b71`发送 | 特定任务进入原因；原函数中未构造附加业务字段，不等于通用ready |
| reason=`0x7dfbd`（516029） | `0xc1f49`，本处+8字节设0 | `0x11e2b80`比较，`0x11e2b87..0x11e2bb1`构造并发 | 本轮未命名，因特定reason直接排除作为通用ready，无需猜名 |
| 目标地图`0x455`（1109） | `0xc2428` | `0x11e2dfa`起检查，`0x11e2e23..0x11e2e49`构造并发送 | 特定地图流程；不得为解锁而主动伪造该地图消息 |

`CAfterEnterWorld`原构造/编解码为空body证据沿用 `ROLE_PROTOCOL.md`（构造0xd4e530、marshal0xd4e550、unmarshal0xd4e560）。本轮重新核对reason分支，不将其推广成普通ready。

### 候选排除与未追通范围

RTTI枚举所见move客户端请求包括：CBeginStall、CEnterDangerConfirm、CGMGetAroundRoles、CHomeResetPosition、CPickUpItem、CRelocateRolePos、CReqSeeEachOther、CRequestXiaoquMapInfo、CRoleJumpStop、CRoleMove、CRolePlayAction、CRoleTurn、CCheckMove、CRoleJump、CRoleStop，另有task的CQuestReachScene。

没有找到命名为普通场景加载完成的明显RTTI。名称不存在不证明无确认协议；可能存在命名不直观、间接虚调用或其他命名空间。`CCheckMove`发送虚表引用落在`0x12160de`，`CRelocateRolePos`也有多处发送引用；本轮没有建立其与加载完成的因果链，不能选一个看似接近的名字接线。普通移动包也没有交接ID/场景世代证据，不能用它默认解除loading。

尚未穷尽：`0x1141f90`保护跳转链、`0x11ca5a0`、`0x11ca410`及其他普通初始化的间接虚调用；引擎异步加载通知；是否原协议本来就没有通用ready而原服采用不同可见性流程。因此当前应把缺口称为“尚未确认原生通用加载确认”，不是“确定客户端不发任何包”。

## 接线建议与下一步证据门槛

当前没有安全的原生消息绑定交付。保留可信`scene_ready`接口，并明确尚未通过真实客户端跨图；不要把verify脚本里的host hook当原生协议测试。

若后续找到候选消息，绑定前至少确认：它在普通reason0加载成功后可达，失败路径不发；精确type/body；是否包含目标scene或世代；同连接当前transfer及login_epoch如何匹配；重复/迟到/旧场景包不能释放新transfer。若原版确实无通用确认，需要主策划和集成方显式设计另一种可验证的服务器交接/可见性策略并标`designed`，不能静默把定时等待或普通移动改叫`client_verified`加载完成。

## 方法、决定、产物与验证记录

- 方法：沿用全文仍在上下文的 [research SKILL.md](D:/User/Documents/Codex/.codex/skills/research/SKILL.md)，根任务委派后台一手研究；重读 `ARCHITECTURE.md` 并遵循世界/连接/角色所有权与版本隔离。本轮是离线原生研究，未查网络攻略，因为协议触发顺序应由此版本原生代码确认。
- 影响决定：继续排除0xc003d普通ready误用；将本地成功AL、500调度和特殊条件消息与服务器可验证确认分开；没有越过证据缺口提供假绑定。
- 产物：仅 `revival/evidence/SCENE_READY_RESEARCH.md`。
- 验证：静态读取实际transfer hook与验证脚本；原生handler→场景函数→加载成功检查→普通定时器→直接发包条件的反汇编；RTTI/虚表引用核对。没有执行codec或运行时测试。
- 未验证：保护/间接调用的完整链、真实网络加载顺序、异步资源完成、通用ready消息存在性、场景世代防迟到机制与真实玩家跨图。未启动/注入/发包/重启任何游戏或服务进程。
