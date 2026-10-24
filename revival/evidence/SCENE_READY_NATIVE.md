# 普通跨图完成确认的原生证据

日期：2026-10-23。范围：只读本项目已保存的原生解包映像；未访问当前客户端进程、GUI、网络或账号，未更改运行时或部署代码。

## 结论

1. 普通 `SRoleEnterScene(reason=0)` **不会发送**首次进入世界的 `CAfterEnterWorld`。原生发送分支明确要求 `reason=516015`；不能将该包复用于普通传送的 ready。
2. 在已追踪的普通加载主路径及相关类型表中，**没有确证通用的“地图加载完成”上行 ACK**。这不是对所有间接调用、脚本与其他模块作出的全称否定。现有证据不能创建或接受凭名称猜测的 `CEnterSceneDone` / `CRoleMapLoaded`，也不能把移动、心跳或经过固定时间解释为加载成功。
3. 确有原生服务端查询 `SRelocateRolePos(0xc0fbb, 空 body)`，客户端直接返回 `CRelocateRolePos(0xc0faf, 13字节 body)`。它报告客户端的当前 scene 与角色位置，**不是资源加载或渲染 ACK**。scene 在实际资源读取前已切换；加载失败后仍可能存在可响应查询的主角对象。
4. 当前裁定采用服务器发送／提交屏障而不是原生加载 ACK，依据 [场景切换设计裁定](../design/scene-transition-v1.json)。本研究未实现、部署或验证该服务器接线，不将其称为客户端加载确认。

## 第一方材料与复现产物

- 原始依据：[native-image.bin](native-image.bin)，VA索引方式为 `VA - 0x400000`。本次探针记录的 SHA-256：`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。
- [离线探针](../research_scene_ready.py)：只读映像，在隔离模拟CPU中执行选定原指令；仅写自己的证据产物。
- [探针结果](scene-ready-native-probe.json)：两种 reason 分支、9组原生查询响应构造与 codec。
- [原生反汇编片段](scene-ready-native-disassembly.txt)：本报告的关键 VA 指令。
- 已有 [角色协议证据](ROLE_PROTOCOL.md) 的 `CAfterEnterWorld与先后顺序` 与本次证据一致。

命令：`python revival/research_scene_ready.py`。输出为 reason0 无发送、reason516015 发送 `0xc003d`，以及9组查询响应 codec 检查通过。没有运行完整客户端，也没有调用渲染器或地图资源加载器。

## 首入与普通切图的不同

`SRoleEnterScene`：type `0xc0fa9`；原构造 `0xdac580`，marshal `0xe50b00`，unmarshal `0xf74260`，Process `0x11e3140`，虚表 `0x227921c`。

Process 在 `0x11e3199` **直接同步调用**场景函数 `0x11e21f0`，调用返回后才继续其后处理。加载函数在 `0x11e2600` 调用资源加载器 `0x11e0310`，将 AL 保存到局部 `+0x17`；`0x11e269b..0x11e26a5` 在加载返回零时跳到 `0x11e2e7a` 的清理／返回路径，不执行随后定位与首次确认分支。这些指令说明该函数的同步控制流；不证明所有渲染资源已经呈现。

成功分支在 `0x11e26d3` 取得主角虚表 `+0x184`，`0x11e26dc` 调用；`CMainCharacter` 虚表 `0x2299344` 对应方法为 `0x1213b80`。该方法设置角色位置、移动与显示相关状态；不能仅凭方法返回宣称画面已显示。

首次确认的原指令：

```text
011e2d00 cmp [esp+0xb0], 0x7dfaf  ; 516015
011e2d0b jne 0x11e2d39
011e2d0d mov [esp+0x20], 0x226f97c
011e2d15 mov [esp+0x24], 0xc003d
011e2d22 call 0x813860
011e2d29 mov edx,[edx+0x3c]
011e2d33 call edx
```

`CAfterEnterWorld` 的原 marshal `0xd4e550` / unmarshal `0xd4e560` 只返回 stream，body为空。离线探针从 `0x11e2d00` 执行到 `0x11e2d39`，以宿主捕获 network send 边界；reason0 发送列表为空，516015 发送列表为 `[0xc003d]`。本探针只验证条件分支，不重放前面完整加载过程。

其他显式消息发送受特定原因／地图限制，例如 reason `0x7dfb2` 的 `0xc4a54`、reason `0x7dfbd` 的 `0xc1f49`、特定map `0x455` 的 `0xc2428`，不能称为普通传送确认。

## 可证实的位置查询响应

`SRelocateRolePos@move@gsp@knight`：

| 项目 | 原生依据 |
|---|---|
| type | `0xc0fbb`，构造 `0xdabe80` |
| body | 空；marshal `0xdabea0` / unmarshal `0xdabeb0` 只返回 stream |
| vtable | `0x2279170` |
| Process | `0x11c9f90`：取全局 `[0x294454c]`，非空即直接调用 `0x1212890`；空则返回 |

`0x1212890` 在 `0x1212a49..0x1212a5a` 直接通过网络 interface `+0x3c` 发送 `CRelocateRolePos`；这里不是根据名称猜测包义，而是原 handler 到原构造和原发送的连续指令。

`CRelocateRolePos@move@gsp@knight`：type `0xc0faf`，vtable `0x2278f20`，marshal `0xe50770`，unmarshal `0xdaa7a0`。body精确布局：

| 字节偏移 | 宽度 | 内容 | 原生字段／指令 |
|---|---:|---|---|
| 0 | 8 | BE u64 scene_id | 对象 `+8/+c`，`0xe50778..0xe50782` 调原 `0x7709b0` |
| 8 | 2 | BE 16位 x | Pos对象 `+4`，原Pos marshal `0xe50690` |
| 10 | 2 | BE 16位 y | Pos对象 `+6`，同上 |
| 12 | 1 | flag，严格0或1 | 对象 `+0x18`，`0xe50792..0xe507b6` 写1字节 |

坐标线宽为16位，没有 scene 字符串、计数、request_id、transfer_id 或位置版本。原 `SRoleEnterScene` 的坐标消费使用 `movsx`（`0x11e3181/0x11e3185`），而响应 marshal 按16位原样写出；解析器可按协议Pos约定解释带符号值，但不得改成32位或compact整数。

响应 scene 源自 `[0x2944564]` 的 `+0x30/+0x34`：闲置分支 `0x12129e5..0x12129f6`；状态1分支 `0x12128f6..0x12128ff`；状态2分支 `0x1212976..0x121297f`。

位置与flag取决于主角 `+0x13c`：

| `+0x13c` | 位置来源 | flag来源 |
|---|---|---|
| 0 | 主角虚表 `+0xd0` 的当前位置 getter，`0x12129aa..0x12129d0` | 主角虚表 `+4` → `0x1209d10` 取 `+0x218`，然后 `setne` |
| 1 | 主角 `+0x150/+0x154` 的低16位 | 主角 `+0x3d6` 是否非零，`setne` |
| 2 | 主角 `+0x158/+0x15c` 的低16位 | 主角 `+0x3d6` 是否非零，`setne` |
| 其他非零 | 本函数不构造发送 | 无 |

flag的业务名称尚未确证，不把它命名为loaded、ready、mounted或alive。原指令仅证明规范输出0/1；不能要求成功加载时必须是1。

离线探针保留原 `SRelocateRolePos.Process`、响应构造、分支、flag规范化及原生 encode/decode；状态0仅以宿主adapter替代与渲染模型耦合的坐标getter。状态1/2的坐标直接读取原字段，无此adapter。输入flag为0/1/2，9组都产生原生13字节；示例scene `0x1122334455667788`、Pos8480,6976、flag0：`112233445566778821201b4000`。这是线格式与构造路径验证，不是完整角色、地图或画面验证。

## 为什么不能将查询当作加载ACK

场景函数开头就在 `0x11e2267/0x11e226a` 将传入scene的低／高32位写入 `CGameScene+0x30/+0x34`。这早于 `0x11e2600` 的资源加载。`SRelocateRolePos.Process` 没有检查加载返回值，仅检查主角指针。因此即使查询返回目标scene，也不能推导资源加载成功。

精确目标Pos比仅scene更有区分力，但不含唯一传送关联值；旧查询响应、同目标scene/Pos的重复传送、客户端其他定位路径仍可能产生相同body。一次仅一个未决查询、绑定connection generation/login epoch、拒绝源scene或非目标Pos，属于服务器策略，不能补成原生渲染确认。

`CCheckMove(0xc0fa3)` 在原方法 `0x12171d0` 中受 `+0x338` 倒计时控制，重置为500（`0x1217215`），并在状态条件允许时发送。它是周期性移动检查候选，而不是本次加载函数末尾直接发送的通用ACK。本报告不允许将其或其他位置包隐式升级为ready。

## 调度次序的证明边界

已追到通用网络解码 `0x77c8b0` 的逐包循环：调用原decoder后 `0x77ca20` 调protocol虚表 `+0x14`，返回后 `0x77ca29` 回到下一包；两种scene/query类的该槽都指向 `0x7710d0`。它转发manager虚表 `+0x1c`。实际manager表 `0x24719c4` 的该槽为 `0x775f30`，后者 `0x775f89..0x775f9b` 转调上层interface `+0x34`。

**本次没有完成上层interface `+0x34` 到最终游戏线程队列的全链路FIFO证明。** 不能仅凭TCP字节顺序宣称两个Process已按发送顺序执行。已经证明的是各自Process内部的同步调用与立即响应路径。若今后采用查询作为位置同步屏障，需另行验证同read batch、分片、延迟、旧查询响应、加载失败以及角色状态1/2对响应的影响。

## 方法、决定与未验证范围

- `research`：使用实际本地原生映像作为第一方材料，每个协议／字段结论落到具体VA；没有借其他游戏协议填字段。
- `diagnosing-bugs`：将“reason0应该发送首入确认”的假设缩成原条件分支CPU重放并证伪；将“查询响应等于加载完成”用scene写入发生在load前的独立指令证伪。没有完整跨图重现场景，因此不声称修复当前黑屏或取得真实渲染ACK。
- `codebase-design`：将wire位置查询事实、世界所有者激活策略、客户端资源／渲染事实保留为不同契约；跨图ready不借用同名或近似消息制造不存在的语义。未修改服务器模块或其状态所有权。
- 验证：2种reason分支、9种响应构造与原codec执行通过；原decoder消耗13字节。未验证真实会话FIFO、运行时query往返、资源失败现场、完整地图渲染与最终设计接线。
