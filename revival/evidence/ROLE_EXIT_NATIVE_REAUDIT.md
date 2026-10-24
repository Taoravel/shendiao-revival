# 原窗口X无确认：本地退出初始化门禁复核

2026-10-23；端游1.6.1 / 网络601。用户最新真人反馈为：点X“完全没有反应，也没有确认窗口”，游戏内退出也无效；不再开游戏、助手不做GUI，战斗暂停。**该反馈仍有效，服务器内存Peer绿色不能反证。** 本轮重读research/codebase-design及ARCHITECTURE，后台只读原映像/原包；经root追加授权新增离线原指令检查，全部开窗端点只记录，未启动/控制任何客户端或服务、未发在线包、未访问真实角色/数据库。

## 核心发现

**缺失SFirstDayExitGame初始化可精确重现“X无任何确认窗”的原分支。** 主窗口WM_CLOSE在游戏状态2时会消费关闭消息，调用本地退出菜单选择器；全局退出模式是-1时，选择器直接返回，无确认窗、无CRoleOffline。原 `SFirstDayExitGame=0xc0039` 的单个BE signed32字段，经原Process才把模式变成0或1。[N1–N3、P1]

- wire字段**负数→本地模式0→普通ExitGameDialog**。
- wire字段**非负→模式1→首日退出窗**，所以不能发送0就称普通窗口初始化。
- 应用原重置函数把本地模式设-1；这是“未知/未初始化”门禁，不是退出拒绝下行。
- 本轮当前workspace的game_runtime/world_protocol/gateway/serve/role_protocol定向检索没有0xc0039或FirstDayExit接线。实际发布包/连接投递仍由集成方核对，不能从workspace缺失就声称现场已采证根因。

root/集成若采用wire -1打开普通窗，应登记为**显式本地Adapter选择**；原字段业务名、官方首日玩法条件/奖励仍未知。原下行handler和符号分流是client_verified，采用负值的恢复策略不能顺带称已还原首日系统。

另一关键更正：**SRoleOffline的0x2244c30导入是DefWindowProcW，不是PostMessageW。** 该handler直接默认处理WM_CLOSE，不经过已安装自定义WndProc重新弹确认；本轮之前对“投递WM_CLOSE”的表述被原Import Descriptor/OFT/FT链反证，本文更正。空确认包本身没有新增字段可修复尚未出现退出窗的本地门禁。[N4]

## 一手证据与来源

原 [native-image.bin](native-image.bin)，BASE0x400000，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。由 [native_inspect.py](../native_inspect.py) 只读反汇编/RTTI/导入表，不采新dump、不附加进程。

本轮直接PFS read核对目录/本地头、长度、CRC后解码，未以目录存在推断GUI已成功加载：

| 原包/条目 | 行/字节 / CRC32 | SHA256 |
|---|---|---|
| config.pfs/autoconfig/knight.gsp.login.cexitgame.xml | 284行 / 10255 / 12690a0a | 23dd5ab0067e7c42e59a87a6f1e0c04e616b06ee39ff48a7ced909d1b03ca1c4 |
| config.pfs/autoconfig/knight.gsp.login.cexittask.xml | 5行 / 305 / 080c84eb | 3df2716986fe10d40e31e802289e143925693050836468892d4a089ea5cbebe3 |
| ui.pfs/layouts/exitgamedialog.layout | 38640 / 1241390b | b2f9fbecad87f158f52d88619f1aadbc2ea6509ceb337a6d25b44d118f28f158 |
| ui.pfs/layouts/scenemovieexitconfirmdlg.layout | 2115 / 5cedfa27 | 6b5e060197436592774bee9dc43fa51e37aaa44a6ce7b3577bafbfec561a5e43 |

cexitgame原属性包含levela/levelb/area，cexittask包含levela/levelb/msgid（五行msgid141742..141746），是退出窗内容配置，不是名为CExitGame/CExitTask的网络退出请求；不能据名字推测“发这两张表就退出”。[EXIT_DELETE_PROTOCOL_RESEARCH.md](EXIT_DELETE_PROTOCOL_RESEARCH.md)原空体退出codec证据沿用，本轮重点补此前未检查的窗口创建前提。

## N1：原主窗口WM_CLOSE入口

原应用 `0x831d72–0x831d7a`将函数`0x822490`、索引-4交原SetWindowLongW，将旧WndProc返回值保存在应用`+0x18`。因此下述不是从相邻函数猜出的退出回调。

`0x822490`取第二参数uMsg；`0x822499–0x82249c`命中0x10即WM_CLOSE，跳`0x8224be`：

1. `[0x2945540]`存在且其`+4==2`时进入游戏态退出分支。
2. `[0x2944798]`存在且`0x806ba0`返回真，会尝试关闭`[0x29455b8]`所指UI；该对象存在就调用后返回0，不开普通退出窗。`0x806ba0`原判定为该管理器`+0x54!=0`，或应用`+0x1ed!=0`。本轮不把两个状态完整命名为原服战斗枚举，也不运行战斗验证。
3. 其他游戏态路径 `0x8224f9`调用`0x15f6210`，然后返回0。**此处不自行发CRoleOffline，也不默认销毁窗口。**
4. 不满足游戏状态2时，`0x822503–0x822508`调用应用`0x81f590`，该函数建立通用确认框；它与游戏态退出窗口不同。

WM_CLOSE一旦命中上述分支，**不会再调旧WndProc**；非WM_CLOSE/非激活消息通过`0x8224b5`的CallWindowProcW链转交旧处理。未发现该函数检查intro discriminator或MovieManager+3c，因此不能笼统说“intro直接禁止X”。实际当前状态未采样，本报告不宣称真人必处于哪条分支。

### 原系统关闭菜单范围

此安装函数没有独立SC_CLOSE=0xf060禁用代码；原镜像中精确常量引用搜索没有闭合“禁用系统菜单导致X无效”的消费者。**未找到不等于不存在**，特别其他虚化/引擎路径不能仅靠字节检索排除。本轮已找到直接WM_CLOSE门禁且原指令可重现，停止扩大菜单/API分析；不以猜测添加EnableMenuItem补丁。

## N2：窗口选择器为什么无声返回

`0x15f6210`：

```text
mode = [0x28e6bc8]
if mode == 1: return 0x15f6190()  # 首日窗实例295595c
if mode == 0: return 0x15f5410()  # 普通ExitGameDialog实例2955960
return                         # -1及其他值，没有开窗
```

`0x15f5410`仅实例不存在时分配并调用构造`0x15f8d00`、初始化`0x15f9260`；实例已存在则返回该实例。`0x15f6190`同样是另一首日窗工厂，构造/初始化为`0x15f5510/0x15f5ac0`。此处初始化会建UI，离线检查在这两个工厂**入口即hook记录并返回**，未执行渲染/Windows函数。

模式设置原证据：

- `0x15f5230`写`[0x28e6bc8]=0xffffffff`，应用重置`0x834318`实际调用它。
- 只读引用还存在写1的`0x15f5210`及写0的`0x15f5220`，本轮没有找到它们的直接调用，不将其当当前服务能触发的初始化。
- 核心原网络handler是`0x15f5500`，见N3。

游戏系统菜单退出按钮 `0x165f6a0–0x165f6b6`先调用`0x15f6230`再关闭菜单；`0x15f6230`也读取同一mode：**mode<0在`0x15f6256–0x15f6291`直接返回**；合法模式根据实例是否已存在创建/切换普通或首日窗。此链说明“X和游戏内退出同时没窗”可能共享未初始化前提，而不是两个无关wire缺路由。

## N3：SFirstDayExitGame原布局与初始化

RTTI `.?AVSFirstDayExitGame@gsp@knight@@`，虚表`0x22702f4`；type和原函数如下：

| 项目 | 原VA/布局 |
|---|---|
| constructor | `0xd53a00`：vtable22702f4、type`0xc0039`、object+8默认0 |
| marshal | `0xe40a00`，取object+8调用原BE32 writer`0x770960` |
| unmarshal | `0xd53a90`，读4字节、`0xd53ac8 bswap`，写object+8；没有额外业务范围检查 |
| 原常规约束 | `0xd53a20`直接true；不限制字段非负 |
| Process | `0x15f5500–0x15f550d`：cmp signed object+8,0；setge得到0/1，写全局mode |

正文是**单BE32位模式，Process按signed32解释**。消息不含roleID、taskID、电影ID、intro flag或确认按钮。对字段业务名称保持未知，不能称“天数”“布尔是否首日”已证。精确效果：

| wire | 原signed字段 | Process后本地mode | 随后真实WM_CLOSE选择 |
|---|---:|---:|---|
| ffffffff | -1 | 0 | 普通退出窗 |
| 80000000 | INT32_MIN | 0 | 普通退出窗 |
| 00000000 | 0 | 1 | 首日退出窗 |
| 00000001 | 1 | 1 | 首日退出窗 |
| 7fffffff | INT32_MAX | 1 | 首日退出窗 |

恢复方案若只恢复正常退出而不实现未知首日玩法，可由root选择负值并记录政策。发送时机要在客户端原应用重置之后、允许用户退出的world初始化链里；不能只在登录前发一次，随后被`0x834318→15f5230`重置覆盖。原服务器精确包序未采获，时机由集成方用当前入场发布序列和离线原消费者进一步验证，本文不改共享入口。

## N4：SRoleOffline空体确认的真实消费者

空请求CRoleOffline0xc0011→空确认SRoleOffline0xc0031的原ctor/marshal/unmarshal身份沿既有报告；SRoleOffline虚表22706b4、ctor`0xd562e0`、marshal/unmarshal`0xd56300/0xd56310`空体，本轮复读Process`0x8137c0`。

Process没有读消息body或检查intro/world/movie：

1. `[0x2945090]`存在时，调用其虚表+50取窗口对象，再虚表+4取HWND。
2. `0x8137da–0x8137e1`经IAT槽`0x2244c30`调用`DefWindowProcW(hwnd,0x10,0,0)`；管理对象不存在则`0x8137ea–0x8137f1`用HWND0调用同函数。
3. 该IAT准确身份由**映像PE Import Descriptor→OriginalFirstThunk名称→FirstThunk解析地址→原IAT值别名**确认：

| Import名称 | 恢复导入槽 / 当时映像内解析地址 | 原调用IAT别名 |
|---|---|---|
| **DefWindowProcW** | 0x2b79984 / 0x77250880 | **0x2244c30** |
| PostMessageW | 0x2b7998c / 0x76860a40 | 0x2244c38 |
| SendMessageW | 0x2b79a0c / 0x768652b0 | 0x2244cb8 |
| SetWindowLongW | 0x2b79a04 / 0x768647e0 | 0x2244cb0 |

解析后的系统地址仅用于该dump内同值交叉核验，不是跨机器固定地址。**SRoleOffline直接调用DefWindowProcW处理WM_CLOSE，绕过0x822490，不会递归进入mode=-1窗口选择器。** Microsoft [WM_CLOSE文档](https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-close)确认默认DefWindowProc会调用DestroyWindow；[DefWindowProcW契约](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-defwindowprocw)明确其为默认窗口处理。故不能把原空体确认本身改成带roleID/状态码，也不能以任意定时器等待再关闭冒充原协议。

有效HWND、Windows默认处理成功与应用主循环实际退出仍是必要运行条件；本轮没有执行系统API或验证当前窗口句柄。原窗口管理对象为空而传HWND0并不证明真实窗口能关；应由后续合法现场证据确认，不能从本地指令推断全部退出流程必成。

真正普通退出按钮的本地回调仍是 `0x15f62c0`：`0x15f62e3–0x15f630c`构造/发送空CRoleOffline0xc0011，无需额外退出字段；前提是原窗口已创建、按钮能点击。退出窗内容加载请求0xc0022/0xc0024也不是关闭确认。**本次发现的是按钮出现前的初始化，不是证实c0011/c0031消息号错误。**

## N5：场景动画退出与intro门禁的边界

`layouts/scenemovieexitconfirmdlg.layout`原文是“你确定要退出场景动画吗?”，确定/取消控件为`ScenMovieExitConfirm/Ok`和`.../Canel`。这是本地电影确认框，**不是已发现网络类CSceneMovieExit**；原RTTI/ASCII名字搜索未找到这一消息，不能造type。

原初始化`0x12bb05f`查Ok、`0x12bb11f`绑定回调`0x12baec0`；该回调调用MovieManager`0x12c2f50`，返回false时隐藏本框。后者要求manager`+0x3c!=0`，清本地播放队列并安排退出动作，涉及本地500/1500参数，不是游戏退出wire。之后共用电影收尾是否发CEnd依原电影状态，不能当CRoleOffline替代。

电影输入handler`0x12bd630`在Esc且`+0x3c!=0、+0x3d==0`时调用`0x12bc830`创建/切换此电影确认框；普通应用消息入口`0x832ab6–0x832adf`在MovieManager+3c活动时交给电影输入并消费消息。但**主窗口0x822490已专门先截WM_CLOSE，不能把后面的通用电影输入门禁直接套成X被吞的证据**。intro discriminator控制锁/遮罩的旧证据并没有取代本轮退出mode初始化；未看到该discriminator直接写28e6bc8。

## P1：可重复的离线原指令红绿证据

新增 [verify_role_exit_native.py](../verify_role_exit_native.py)，输出 [role-exit-native-reaudit-check.json](role-exit-native-reaudit-check.json)。该脚本复用公开 `native_gameplay_probe.probe(ctor,marshal,unmarshal,fields,observer=...)`：原codec完成后，observer继续在**同一Unicorn机器**执行原reset、原Process和真正已安装WndProc，不以宿主手写setge替代。

每个signed字段-1、INT32_MIN、0、1、INT32_MAX均执行：

1. 显式离线夹具：游戏状态对象+4=2、战斗管理对象空、模拟HWND0x1234；不模拟真实人物或部署状态。
2. 执行原`0x15f5230`得到mode=-1；真实`0x822490(WM_CLOSE)`自然返回0，UI端点记录为空，形成用户现象的**原分支red**。
3. 执行原constructor→marshal→fresh constructor→unmarshal，精确消费单4字节wire；执行该新对象的原Process`0x15f5500`。
4. 再执行相同WM_CLOSE，分别只命中普通窗工厂15f5410或首日窗工厂15f6190；这两个终端仅记录并返回，不打开GUI。

5例通过，包含符号边界和wire字节一致；**没有实际Windows函数调用，也没有服务器内存Peer冒充客户端分支**。检查未执行UI构造/资源加载、战斗退出分支、API窗口销毁或真实客户端状态，因此仅证明这条原分支及初始化效果。

## 交接与未闭合范围

主集成优先核当前不可变发布源码和实际初始化发送链是否存在c0039，以及其是否在应用重置之后到达。若缺失可按root裁定补普通退出初始化，随后由其所有权/发送顺序契约验收；本代理不改shared、不操作现场。原始生命周期内存测试仅证明直接送入c0011能回c0031，并未执行本地WndProc/窗口选择器，因此旧“剧情中退出绿色”不能覆盖本次真人反馈。[verify_role_lifecycle_runtime.py](../verify_role_lifecycle_runtime.py:35)

当前缺少真实失败时mode、游戏状态、窗口句柄与实际到达消息的采样；即便静态缺包和原red一致，也应称**高相关且已证明机制的候选根因**，不能宣布真人故障已经实测解决。用户禁止再开游戏，继续守约，不以反复询问/自动GUI尝试获得验收。

research实际决定：从用户“完全无窗”前移到WndProc→菜单模式→初始化消费者，发现错误IAT假设后用真正PE进口链纠正；codebase-design实际决定：把客户端本地初始化前提、退出请求、角色持久化和窗口确认消费者分开，绿色服务器Interface不替代UI入口证据。产物为本文、单离线检查脚本及其JSON；未改生产/配置/政策，未启动或控制客户端、服务、战斗、网络或真实角色。原首日业务值/奖励、完整系统菜单禁用路径、窗口销毁后的主循环及真人修复效果保持未验证。
