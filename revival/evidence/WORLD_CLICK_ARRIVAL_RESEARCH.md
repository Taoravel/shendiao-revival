# 原点击规划到自然到达 STOP

2026-10-23。来源状态 `client_verified`；本批仅离线原指令验证，无游戏、GUI、服务、生产或共享源码变更。

## 结果与交接

同一个 `ClickArrivalProbe`（继承已冻结的 `ClickMoveProbe`）由原点地输入建立路径、发送 ROLE_MOVE，再执行原 actor 更新及完整主角到达回调，自然发送 `CRoleStop 0xc0faa`。host 没有调用报文 builder，没有在规划后写 current、future、history，没有构造 STOP 对象或 wire body。

交接文件 `world-click-arrival-native.json` 的稳定字段：

| 字段 | 实际结果 |
|---|---|
| `all_passed` | true |
| `move_message_type` / `original_move_body_hex` | 0xc0fa1 / `05d0048005e00480000000000000044c` |
| `stop_message_type` / `original_stop_body_hex` | 0xc0faa / `0105d0048005e00480000000000000044c` |
| `original_sender_messages[1].history` | `[[1488,1152]]` |
| `original_sender_messages[1].current` | `[1504,1152]` |
| `original_sender_messages[1].scene_u64` | 1100（确切拷贝 Scene+30/+34；不扩张字段语义） |
| `original_sender_messages[1].sender_return` | `0x1217fce` |
| `stop_native_decoder_verified` | true；原完整构造器 e9d5e0、decoder e9d780 消耗全部 body |
| `native_decoded_stop_history` | `[[1488,1152]]`，原 decoder 构造出的链表，非 host wire 解析 |

父窗口可把这一 MOVE→STOP 次序及原 body 交给真实 RoleOwner/连接 codec 隔离验证。本批不声称已经完成该所有者接线、持久化或重连；父窗口独立产物拥有这些结果。

## 原指令链与单变量时序

原映像 SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。调用地址均来自该 `native-image.bin`，跟踪结果在 JSON `trace`/`engine_events`/`events`。

1. `App+3d8=1` 时原 1214bd0 输入 tick 不读取鼠标、不规划、不发送。原 12b9a10→12bc870→11d3a10 清理 intro，之后原输入 tick 真正规划并发 MOVE；与前批的 Seam 相同。
2. 原 12143b0→11f8800→652a40→6bc2f0→6138d0 建立 16 逻辑像素的 clear 路径。真实 map.pfs `map_1100_gumupai/maze.dat` 与 RMP 新读、CRC 验证；两端格 byte8，普通 mask1 clear。原 DDA 样点仍保留于 JSON。
3. 原 120f9a0 由原控制流程调用，sender 返回 1214aa9；此时 actor 仍在源点 `(1488,1152)`，future 两份均为 `[(1504.,1152.)]`，history 为源点。MOVE 是意图。
4. host 只调用原 actor 入口 `655c80`，EAX=actor、EBX=确定的 clock 参数、栈中给 tick 参数。原 `655d51..655d67` 依次调用 actor 虚方法+1a4（原 655500 动画更新也运行）和原 path tick `6bc7a0`。speed 由原 setter `6529b0` 设置为固定乘数 1.0。
5. 首次参数16，原 actor projected 从 `(2232.,1152.)` 到 `(2256.,1152.)`，原 current getter 12061a0 返回 `(1504,1152)`；future 节点仍在、只有一个 MOVE，无到达 STOP。原 `6bc8e7..6bc932` 的剩余预算比较要求严格大于剩余距离才消费；相等仅插值到点。
6. 下一次参数1，原引擎消费节点并产生 event1。原 Engine event receiver 连接到 App 后，`81c670→11d57f0→1217580→120c350→11f8930` 全部真实执行，没有沿用旧报告 probe 对 base callback 的 ret Adapter。
7. `11f8b5f..11f8b9f` 拷贝原 actor future；已为空，于 `11f8b9f` 调角色虚方法+b4，即 `1218000`。该原方法检查真实 moving getter 后，在 `121801a` 调 `1217f00`。**host 未进入或直接调用 1218000 / 1217f00。**
8. 原 `1217f71` 调真实 current getter，`1217f77` 调完整 STOP 构造器 e9d5e0，`1217fa3` 拷贝真实角色 history，`1217fa8..1217fb7` 拷贝 Scene q64，`1217fcc` 调 sender。原 STOP serializer `e9d6d0` 在该实时对象仍存活时执行，捕获上述 body，随后回到 `1217fce`。
9. 原 `1217fd0` 清 history，`1217fdb` 清角色 future，最后完整回调与 actor tick 均正常返回 fixture sentinel。`consumed` 记录 actor 已到点、引擎/角色 future 与 history 都为空。

**16+1 是确定的 native tick / 运动预算实验输入，不是已证实的毫秒、真实网络时钟或原服务器速度公式。**本批不从该乘数制定服务器移动速度、反作弊时限或容差。

一个容易混淆的差别：本次自然 STOP 的 history **只有源点**，目标在独立 current 字段。完整 base callback 先发 STOP 并清角色 future，因此外层 Main callback 不再追加已消费目标到 history。旧 `verify_movement_reports_native.py` 的某些专门 history 消费 fixture 有 base callback Adapter，不可拿其目标历史结果替换本次完整流程。

## Adapters、fixture 与未验证范围

采用 research 的一手追源与单独 Markdown 产物；本窗口已是父任务后台研究。diagnosing-bugs 用同一对象的三个可判定状态形成紧反馈：规划后未到、等预算到点未消费、下一预算消费并发 STOP。真实 actor/回调/原 sender body 是验收信号，getter 或 serializer 单独成功不算自然到达。codebase-design 用于明确下面的 Seam，不修改服务器所有权或政策。

| Seam | host Adapter / fixture；保留的原逻辑 |
|---|---|
| 输入 | 原 1214bd0 持续输入入口；role+308 已 latched、+304 为开节流的9，虚设备返回 `(48,48)`，camera `(2208,1104)`。OS 鼠标事件/UI hit test 未运行。 |
| 世界与角色 | 继承前批 original native World/path/actor vtable、真实 maze/query 安装。构造期初始化空容器及指针、正常 state0。初始地图1100、坐标来自既有政策采用的原电影端点；不是原服出生坐标证明。 |
| 事件接收 | path identity=原 actor；Engine+28=App 2945060，真实 App/Scene/Main 分发。Scene 11d1db0 的 actor→role 查找由 Adapter 返回这一 fixture role；无其他模式接收者/特殊 actor（11d5260 返回0）。 |
| 更新 | 调用原 actor655c80；原 actor 动画655500、路径6bc7a0和完整base回调120c350均真实运行。每次 clock/budget 都显式记录，speed原setter1.0是测试输入。没有调用完整 App frame/主角定时更新来代替 actor tick。 |
| 资源/UI | 沿用前批外观、UI、动画资源查询 Adapter（120fcc0/1212390/12172f0等）；新增 1172740 只接受并删除句柄0，断言实参为0，替代缺失渲染 backend。此 Adapter 发生在 STOP 已发送后的后续附属清理。 |
| sender | 虚sender ABI Adapter 跳入 fixture 保存寄存器 stub，**调用原实时对象 serializer**，在返回点读取 OctetsStream，随后向原调用者返回1。没有 host 序列化/直接 builder。每种消息独立 stub 地址，避免模拟器旧翻译块复用。 |
| CRT | 继承的内存分配、free、memcpy/memset、sqrt等宿主 Adapter；原容器/codec/移动指令保持原样。 |

未验证：完整 App frame、操作系统鼠标入口、真实 render backend、网络发送线程、真实客户端界面及服务器速度单位。也未得到完整定时 CHECK 链：曾在 STOP 完整返回后尝试原 Main update12179a0，进入真实 base120c830 后停在缺失状态树的 `1039380` 查询循环（fixture 未初始化该树），没有声称其自然 CHECK 成功；最终成功 verifier 不纳入该失败尝试，也不直接调用 CHECK builder补齐。STOP 本身由上述原控制链自然产生，满足本次到达证据目标。

## 重现

在项目根目录运行：

```powershell
& C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -B revival/verify_world_click_arrival_native.py
```

实际输出 `all_passed:true`、`messages:2`，包含稳定 `original_stop_body_hex`，生成 `evidence/world-click-arrival-native.json`。约1秒，无客户端进程。`-B` 不产生 pycache。

只新增本 MD、该独占 verifier 与 JSON；旧 click/report probes、生产/shared/政策均未改动。未改动 owner Interface；服务器所有权接入仍按 ARCHITECTURE 的 RoleOwner/MapOwner 与连接 codec Seam 执行。
