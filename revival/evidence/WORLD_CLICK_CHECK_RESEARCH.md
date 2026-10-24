# 原完整主角更新自然发送定时 CHECK

2026-10-23。来源 `client_verified`。本批离线执行原映像，不启动游戏/GUI/服务，不改生产、共享入口、政策或已有 verifier。

## 可交接结果

`verify_world_click_check_native.py` 已执行通过两个 CHECK 场景及一个窄 MOVE→STOP 对照：真实出生入口采用的 map1100 原 maze 上，原点地输入建立路径并发 MOVE，原 actor tick 推进到中点，然后**完整 Main12179a0 和 base120c830 正常运行返回，由原控制流程自然调用 CHECK builder/sender**。没有 host 直接调用12171d0/12160b0，没有 host 写 current/history/future，没有把 base 更新换成 ret Adapter。

`world-click-check-native.json` 的稳定字段如下：

| 字段 | 结果 |
|---|---|
| `all_passed` / `scenarios` | true / 2 |
| `check_message_type` | 0xc0fa3 |
| `original_check_body_hex` | `05d804800105d00480000000000000044c` |
| `original_move_body_hex` | `05d0048005e00480000000000000044c` |
| `original_repeat_check_body_hex` | `05d8048000000000000000044c` |
| `reported_current` | `[1496,1152]` |
| `check_scene_u64` | 1100，取自当时 Scene+30/+34 |
| `normal.original_sender_messages[1].history` | `[[1488,1152]]` |
| `normal.original_sender_messages[1].sender_return` | `0x12172b1` |
| `native_decoder_verified` | true，包括原 decoder 构造的历史链表/current/q64及消耗全部 body |

父任务可用 `original_move_body_hex`→`original_check_body_hex`→`original_repeat_check_body_hex` 验证实际连接 codec/RoleOwner。该 JSON 只提供原客户端上行；本批没有把服务器位置、DB或重连结果称为已验证。

## 上一批停点的准确原因

原映像 `native-image.bin` SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。

最初新 verifier 重现失败：完整 base120c830→120cd5a→11e9db0，后者在11e9dce调1039380，ECX=`role+c8`。旧 fixture 的该树 head=0；1039380 读取 head+4 后在10393a0..10393b2永不遇到 sentinel，达到原 harness 指令预算，未到 CHECK。

原构造链 `Main1219800→121982d call120a330→120a359 call11f0e30` 明确拥有此字段。原 `11f0e9b..11f0ec6` 为+c8树分配 head（8001e0）、设 head+15=1、三向自指及 size0。新 verifier **实际执行这一原构造片段**，ESI=role、BL=1、EBP=0，与原构造11f0e60/11f0e82一致；CRT分配仍是宿主 Adapter，host 不手造 head。

只修树后继续暴露第二个 fixture 问题：此前 ClickMoveProbe 为执行原 mask-selector 片段，把 role+26c 指向了主 actor。完整 base 的120ceba..120d3cb会把这个可选 actor 作为附属对象跟随/播放 `stand1`，因此进入未初始化的显示资源接口。角色主移动 actor 位于+48，不应把两个字段的测试别名当成真实对象关系。

本批在任何点地规划前，执行原 Character 构造 `120a449..120a44f` 的单条写入（ESI=role，EBX=0；120a367原设EBX0），恢复**本 fixture 可选+26c为空**。原 base 自己的120ceba/120cec2空判断跳过可选显示分支，主actor+48和真实运动数据保持。之后完整 base/Main 均正常返回。此结论只是前批 fixture 的构造补齐，不是服务器应当清玩家附属 actor，也不说明所有实际角色+26c恒为空；旧 verifier 未修改。

**旧 MOVE/STOP 的执行范围保持原记录，不因本批补齐字段而被扩大。**旧 mask-selector fixture 的+26c别名不是已证实的真实默认；旧 MOVE/STOP 捕获运行了输入、actor tick和到达回调，没有完整 Main timer/base update，因此当时没有进入后来暴露的可选显示逻辑。其报文与自然发送观察仍是当时明确fixture下的结果，不能据此声称完整主角每帧更新已验证。

为排除+26c别名改变旧报文的可能，本批新增一个低成本对照：在正确默认+26c=0、主移动actor+48保留的同一对象上，原输入→原actor预算16+1→原自然到达回调，不调用Main timer、不触发CHECK，最终得到MOVE `05d0048005e00480000000000000044c`、STOP `0105d0048005e00480000000000000044c`，与旧body逐字节相同；STOP history仍只有源点，current仍为目标。JSON `auxiliary_default_move_stop_control` 保存全部发送对象、两个actor快照与trace，`main_timer_entered:false`、`old_move_and_stop_bodies_unchanged:true`。此对照仅覆盖这一原clear短段，不重跑原8例或505路径，也不把timer范围加到旧证据上。

## 自然 producer、时序与原 codec

| 原执行步骤 | 实际观察 |
|---|---|
| 原1214bd0输入→12143b0规划→120f9a0 MOVE | 起点 `(1488,1152)`、目标 `(1504,1152)`；初始history只有起点，future保留目标；Scene q64=1100。 |
| 原6529b0 speed setter，测试乘数1.0；原655c80 actor更新，参数8 | 原 actor projected `(2244.,1152.)`，原current `(1496,1152)`；无到达消费，无STOP；future仍为目标。 |
| 原Main12179a0输入 `(1499,499)` | 原120c830完整执行并返回12179b7；原1217a47调用12171d0。构造默认role+338=500自然变为1；没有CHECK。 |
| 原Main12179a0输入 `(1500,1)` | 原base再次正常返回；原倒计时到0，发CHECK并复位500。当前点与future不变；原角色history从源点变为空。 |
| 再次原Main12179a0输入 `(2000,500)` | 角色仍moving，原121721f..121722d允许空history；自然再发CHECK，current相同、history为空，future仍未消费。 |

**全部 clock/tick/speed 参数均为确定的离线测试输入，不命名为毫秒、真实速度或实际经过时间。**Actor tick 与 Main tick 在此分开调度；没有执行完整 App frame，也不宣称这个调度复现真实帧耗时。timer构造值500来自12198d2，重置500来自1217215，只证明原计数逻辑。

CHECK真实来源：

- Main1217a47自然调用12171d0，hook观测的返回地址1217a4c；host从未直接调用该函数。
- 原1217251调角色虚方法+d0，落到原current getter12061a0，读取上述原actor已推进坐标。
- 原121727c取role+34c的真实history，121726f..121727b读取**当前**Scene+30/+34。原1217294调用12160b0（返回1217299），原builder12160e9..12160fd写current，121611b/121611e写q64，1216121写type0xc0fa3。
- 原12172af虚sender调用返回12172b1；sender Adapter在该实时对象的原链表仍存活时调用原serializer e9cd00，抓取OctetsStream，随后返回原调用者。原12172b3清空角色history，原后续析构临时报文。没有拷贝已析构的链表冒充原报文。
- 独立原完整构造器e9c770、decoder e9cda0读取捕获 body，原decoder消耗全部字节，observer只读取其构造出的链表，确认history/current/q64均与实时sender对象相同。空history重复CHECK也独立核验。

q64单变量反事实：第二个场景与第一场景输入、actor、倒计时一致，MOVE已发送且q64=1100。仅在499更新返回后、下一1更新前，将fixture Scene+30/+34输入改为 `0x1122334455667788`。自然 CHECK body变为 `05d804800105d004801122334455667788`，current/history完全相同；原decoder还原该值。由此证实CHECK取发送时Scene字段，并非MOVE缓存q64或host clock参数。不扩张该字段的业务含义，也不将该非地图值用于真实服务器。

## Adapters与范围

继承上一批 ClickArrivalProbe 的原输入、真实maze/path、actor、App→Scene→Main分发和sender/CRT Adapter，完整说明见 `WORLD_CLICK_ARRIVAL_RESEARCH.md` 与 `WORLD_CLICK_MOVE_RESEARCH.md`。新 verifier 没有新增逻辑短路 Adapter，只补上两处构造片段和只读跟踪。

- 输入仍从原持续点地tick进入；虚鼠标设备、camera和latched/throttle是已明示fixture。OS鼠标/UI hit-test未运行。
- 同一个对象的主actor由原tick推进，current/history/future在规划后仅由原指令写入。新增+c8空树与+26c空可选对象均在输入前初始化。
- inherited resource/UI Adapter仍存在，main完整更新不等于完整渲染。具体接口不参与坐标/队列/CHECK builder替代；原120c830、12171d0、12160b0均执行原body。`normal.full_update_trace`有三次完整base返回，q64对照有两次。
- 真实 map.pfs 的maze/RMP本批重新读取并CRC验证，entry SHA保留在JSON；map1100与电影端点作恢复入口仍是既有政策采用，不是原服精确出生证明。
- 未验证非空状态树、可选附属actor真实生命周期、其他模式、完整App调度、真实服务器速度/时间单位、生产codec/owner和GUI。这些不由当前两例推广。

本批采用 research 的后台一手追源；diagnosing-bugs先重现预算耗尽信号，再逐项检验“空树哨兵/对象指针/后续容器”三假设，单变量修复fixture并保持完整base；codebase-design用于记录Seam及Adapter归属。只新增独占verifier/本MD/结果JSON，不改变ARCHITECTURE中状态所有权和移动Interface。

## 重现命令与验证

```powershell
& C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -B revival/verify_world_click_check_native.py
```

实际输出 `all_passed:true`、`scenarios:2`（CHECK场景数）、稳定 `original_check_body_hex`；另有一个上述MOVE→STOP对照，合计约1秒。旧MOVE/STOP批量和505路径差分未重跑，未触碰旧文件。原映像执行及codec验证完成；真实联网客户端实测仍未完成。
