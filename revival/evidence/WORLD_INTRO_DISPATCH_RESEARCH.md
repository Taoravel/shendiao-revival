# 原开场下行、资源解析、Start 与受控跳过的可达性

2026-10-23；本地 1.6.1 原映像。方法为 Matt Pocock `research` 的后台第一方追溯，以及 `diagnosing-bugs` 的有界反馈、单变量反事实。已读取根 AGENTS、ARCHITECTURE、DESIGN_AUTHORITY，研究与角色/地图 Owner、连接、持久化保持隔离；本批只新增独占 verifier、结果及本文，没有修改生产、共享入口、旧 verifier、配置或存档，没有启动客户端、GUI、服务或网络。

原映像 SHA-256：`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。

产物：[独立 verifier](../verify_world_intro_dispatch_native.py)、[全部结果](world-intro-dispatch-native.json)、[原指令](world-intro-dispatch-native-disassembly.txt)。旧 [WORLD_INTRO_BLACK_NATIVE](WORLD_INTRO_BLACK_NATIVE.md) 证明了黑色贴图、五分钟超时和清理方法；本文补上真实下行至原 parser/队列的连接，不能将两种验证范围混写。

## 可直接用于接线的结论

1. **新角开场包可被原 decoder/Process 接受并自然到达 `Start`。** 对 43 条自然路线对应的 10 个不同 intro 资源，保留完整原文本，执行原管理器 constructor、decoder、Process、路径构建、逐行解析、命令查找、factory 和 queue tick。均由原队列执行至 `CStartSetion`，清应用 `+0x3d8` 和 Scene `+0x39c`。没有 host 直接调用 Section、Start factory 或清理函数。
2. **首 Start 不等于电影结束，也不恢复普通移动。** 首 Start 后 MovieManager `+0x3c` 仍为 1；同一实例执行原 `0x1211db0` 均返回 AL=0。它在 `0x1211e09..0x1211e0d` 独立检查电影播放位。因此“去黑幕”和“可走路”应分别验收。
3. **已有原生跳过入口可自然产生 CEnd。** 冷 UI 的 11001 正例继续执行原事件分发 `0x123f160(event=0x7b8a4)`，自然进入 `0x12c2f50`，原方法把队列换成 Return/End；两次原 queue tick 后原结束方法构造并投递 `CEndPlayCG`。捕获对象后再执行其原 marshal，得到 type **`0xc0018`**、movie ID **11001**、body **`00002af9`**。随后 manager `+0x3c=0`，同一实例原普通输入判定 AL=1。网络投递、GUI 和场景资源是下述明确 Adapters。
4. **这不覆盖无章节旧角漏发开场。** 本文所有正例都有明确的有效 SStartPlayCG 输入。父任务另已发现的 [WORLD_LEGACY_INTRO_ENTRY_BLOCKER](WORLD_LEGACY_INTRO_ENTRY_BLOCKER.md) 属于服务器没有发包的路径，不能由“给定发包后可达”替它作验收。

## 实际执行的下行至 Start 链

| 原地址 | 原行为 | 本批证据 |
|---|---|---|
| `0xd57540` | 从 stream 读取 BE i32，要求 movie ID >0，保存 packet+8 | 每个正例消费恰好 4 字节，decoded ID 与输入相同 |
| `0x12c43b0` | manager global `0x2945620` 存在时调用 `0x12c4140(packet+8)` | 原 Process 执行；manager 缺失反例不加载文件、不去锁 |
| `0x12c3f70` | 原 MovieManager constructor，建立命令表和辅助表 | constructor 和原命令注册均执行；未人工安装 Start 函数指针 |
| `0x12c4140` | 准备界面，保存 movie ID 到+38，置+3c=1，调用播放加载 | 普通正例用已存在 panel；冷 UI 例从+48=0执行原创建分支 |
| `0x12c3be0` | 组成 `/config/movie/<ID>.txt`，逐行读取、normalize、dispatch | 实际请求路径保存在结果；逐行器仅由资源流 Adapter 提供原文本 |
| `0x12bb280` / `0x12bec50` | 原空白处理、命令表遍历和匹配、调用相应 factory | 全文件而非 host 截出前缀；BOM/CR 保留给原代码 |
| `0x12c2d90` | Start factory 分配16字节，经 `0x12b8f00(1500)` 构造并入队 | 全部正例各执行一次，vt=`0x229ed80` |
| `0x12c3f10` | 解析成功后选首项，写+60，经 vt+4开始 | 首项是 Setmap，未直接跳至 Start |
| `0x12c0b00` | tick 当前项，经+c判断完成，原 erase 后开始下一项 | 七次 tick(delta=16)到达 Start；实际墙钟延迟未测 |
| `0x12b9a10 → 0x12bc870 → 0x11d3a10` | Start 清 intro flag，移除开场 effect 并清 Scene+39c | 原写入和分支执行；Start 的原调用返回地址记录为 `0x12c0b4c`，证明来自队列推进 |

`world_newbie.py` 的启动消息类型 `0xc0017`、body `struct.pack('>i', route.intro_movie_id)` 与这里实际执行的原 decoder 契约一致。**本 verifier 从 body decoder 开始，不覆盖加密 Peer、消息工厂路由、服务器授权、部署后是否真的发送**；父任务的 Peer/Owner 验证应保留独立证据。

## 十个原资源与 43 路线

每次从原 `artres/config.pfs` 读取、完成 PFS CRC 检查。另重读原 `autoconfig/knight.gsp.task.cmainmissioninfo.xml`，逐一核对 43 条路线的 intro_task_id 均为 MissionType=50，且 ScenarioInfoAnimationID 与路线 movie 相同；路线自身不是本批重新推导的门派可选关系。原表/资源和路线 catalog 的完整哈希在 JSON。

| movie ID | 对应路线数 | 原字节数 | 原解析生成 section 数 |
|---|---:|---:|---:|
|11001|4|46710|688|
|11002|5|46720|688|
|11003|5|46448|685|
|11004|4|46750|688|
|11005|4|46728|688|
|11006|4|46672|687|
|11007|4|46730|688|
|11008|4|46654|687|
|11009|4|46738|688|
|11032|5|46720|688|

十部电影的首 Start 都在原文本第 **12 行**。共同顺序为 Setmap(1009, cell15,137)、MoveCam(15,137)、四个 CreateNpc(id94..97，model5101..5104)、PlaySound(id1,res=杀阵,repeat0)、Start。实际队列前八项 vt 为 `229ed48,229edd4,229edf0×4,229eed0,229ed80`；第九项为 Wait(2000)。

原 Setmap section `0x12b9980` 将 cell 位置左移4，真实传给 Scene `0x11e0c70` 的参数为 **[1009,1100,240,2192]**，这里1100是 fixture 初始 Scene+110。MoveCam 的原计算传给 world 的目标为 **[360,2192]**，包含原横向1.5比例。四个 actor 创建请求也保留原参数，未把它们注册为服务端 NPC 或改服务器地图。

原辅助表记录 `CEffectPath id=2004, Name=杀阵, Patn=/sound/music/huashanzhidian.ogg` 经原 `0x12c13d0` 构建 alias；测试只枚举此真实前缀需要的一条配置。PlaySound 的原 alias 解析和调用链实际向 engine audio 接口提交了这个路径，随后由无声 Adapter 返回0。不是根据字符串猜测声音名，也没有实际播放音频。

## 冷 UI 和合法结束入口

冷 UI 例保留原 constructor 的 manager+48=0。原 `0x12c4140` 调 GUI 加载 `SceneAniBack.layout`，随后原指令把返回 panel 写到+48，再查 `SceneAniBack/TopPanel` 与 `SceneAniBack/BottomPanel`。因此普通正例预装 panel 的前提另有冷分支验证；这不是实际 CEGUI 布局/字体渲染验收。

直接读取原 `ui.pfs` 得到：

- `layouts/sceneaniback.layout`，SHA-256 `95fd8ca98e68806c94962cf186a0c2f9dd4ad39b19a0bcdefc2a88db8e95f804`，含这两个 panel 及原文字“按ESC可退出剧情动画”。
- `layouts/scenemovieexitconfirmdlg.layout`，SHA-256 `6b5e060197436592774bee9dc43fa51e37aaa44a6ce7b3577bafbfec561a5e43`，含 `ScenMovieExitConfirm/Ok` 与原拼写 `ScenMovieExitConfirm/Canel`。

原确认框初始化 `0x12baff0` 查找上述 Ok；`0x12bb11f..0x12bb15e` 把原成员回调 **`0x12baec0`** 放入 delegate，并向该按钮事件注册。该回调直接调用 `0x12c2f50`。这是静态绑定证据，本 fixture 未创建真实确认框、未点击 Ok。

实际执行的替代入口为完整原事件分发方法 **`0x123f160`**：输入整数 **`0x7b8a4` (506020)**，其 `0x123f34c..0x123f364` 检查事件 ID、manager 存在及+3c非零后调用相同的 `0x12c2f50`。fixture 提供空事件待处理 vector 与未激活的其他 modal 状态，**没有从 `0x123f364` 中途开始，也没有 host 直接调 skip/Return/End/cleanup**。本批没有证明键盘扫描码 ESC 到这个 event ID 的绑定，故这里只称受控原事件入口；原 UI 文字不能替代键盘绑定证据。

原 `0x12c2f50` 的流程：

1. +3c为0则返回false；为1时原 `0x12bfdb0` 析构旧 sections、清当前项。
2. 经原 constructor 生成 Return(duration500,vt=`0x229ed64`) 和 End(duration1500,vt=`0x229ed9c`)，按顺序入原队列并开始 Return。
3. Return start `0x12b99d0 → 0x12c0bf0` 调 Scene `0x11e0a80`。本 fixture 捕获到参数1009；此处是资源恢复 Adapter，**没有执行整个 Scene 恢复，不能宣称已证明还原地图/位置，更不能按该值修改服务端地图**。
4. 原 queue tick(delta500)完成 Return并自然启动 End；原 tick(delta1500)执行 End完成和 UI 色彩提交，再由空队列自然进入 `0x12c0970`。
5. `0x12c0997..0x12c09b9` 保留原+3c检查，真实建立 stack 上 CEnd对象(vt=`0x226fab8`)、type=`0xc0018`、movie ID=manager+38；`0x12c0a24..0x12c0a3e` 经原 connection getter与vt+3c提交。
6. 唯一网络 Adapter 把这次原 send 参数对象复制出来。随后执行其真实 serializer **`0xe3fd70 → 0x770960 → 0x770440`** 得到四字节body；不是测试代码直接把匹配 ID 打包成“捕获结果”。原结束代码再清 manager+3c/+38，输入 predicate 可通过。

该受控路径结果为 `movie_id=11001, actual_end_type=786456(0xc0018), actual_end_body_hex=00002af9, manager_3c_after=0, ordinary_input_allowed=true`。父任务可用这一实际捕获 body 接 Owner 的授权匹配校验；**不能据此授权任意 CEnd 完成其他任务**。其他九部 intro 的首 Start 路径已执行；受控跳过/自然 CEnd 序列本批只对11001执行。

## 反馈与反事实

此前缺少的反馈是“真实下行及原解析是否能进入清锁 Section”；本批用原入口和明确字段判据替代只看不崩溃。排名候选及判定：有效包未被接受→decoder/Process hit应缺失；Start未解析→factory/section hit应缺失；前置队列不能推进→Start不出现。给定可工作的外部资源/GUI边界，十个正例均不支持这些内部链断裂。真实进程的图形失败和服务器未发包不在这个反事实里。

| case | App intro flag | Scene+39c | manager+3c | 原普通输入 |
|---|---:|---:|---:|---|
|有效下行解析完成，首Setmap开始|1|marker|1|未在此点额外判定|
|十部原资源经7次tick达到Start|0|0|1|false|
|只从fixture文本移除首条Start，其他原代码不变|1|marker|1|false|
|只将manager global设0，保持相同有效body|1|marker|0|false|
|11001冷UI＋原事件→Return/End→原send|0|0|0|true，其他门控为中立fixture状态|

移除Start的修改仅在离线输入副本，原 PFS 没有改写。manager缺失反例不会加载文件。正例同时要求 `section_start/clear_intro/clear_scene_effect` hit，避免把 UI 失败触发的共用结束清理当作 Start 成功。

## Adapters、接口和验收界限

独立 Interface 为 `run_case(movie_id, raw, sound_alias, remove_start=False, manager_present=True, cold_ui=False, event_skip=False)`，返回 decoder消费、请求路径、原队列、状态、原入口 hit、受控结束捕获。它是离线研究 Seam，不导入或修改生产 Module。

- 原 MSVC wstring、比较/查找/子串、堆分配、memcpy_s等库导入使用host语义适配；CEGUI字符串/整数转换边界适配。命令 token、参数名/值查找、factory选择及成员字段赋值由原指令执行。
- 原 custom stream constructor `0x12c3580` 与 getline/stream状态是资源 I/O Adapter：从已经 CRC 验证的原 PFS 文本按LF提供UTF16行，保留BOM和CR；没有执行完整 PFS虚拟文件系统、filebuf/locale/Windows I/O。路径由原loader形成并核对，没有host伪造Start命令。
- GUI context/layout/window lookup、panel生命周期、颜色提交是外部 Adapter；scene准备 `11d8910`、换图 `11e0c70`、actor创建 `11daa10`、恢复 `11e0a80/11d3620` 是明确场景服务边界；world camera、renderer、audio是外部虚表。其调用被记录后返回，**未证明这些真实资源服务成功完成**。
- 应用/Scene/MovieManager是独立模拟对象；mainchar global在这批设0，执行原可选分支，不覆盖真实角色存在时的取消移动/动画准备。普通输入判定用单独零态角色对象，未从GUI投递点击。不会把这个中立fixture当真实角色所有状态默认。
- effect使用marker `0x12345678`，只在 `11d37d0` 外部dispose边界记录请求；本批保留原清指针及flag写入。真实贴图停止绘制/释放的独立原生证据见旧黑幕报告，本文没有重复声称完整执行该容器删除。
- 连接vt+3c是send捕获边界；原构包和原body marshal执行，没有真实socket、加密封装或服务端回包。没有模拟整部电影数百个动画/对话section，也没有将确认结束当作所有任务奖励授权。

执行命令（使用本机捆绑 Python）：

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' revival/verify_world_intro_dispatch_native.py
```

默认10个原资源正例、2个单变量反例、1个11001冷UI/受控结束例；限定11001可用 `--movie-id 11001`。结果只证明上述离线契约与内部可达性，仍需合法部署后实际客户端验证世界可见、完整演出/用户结束、地图恢复与移动表现。当前禁止打开游戏，未以离线绿色宣称用户黑屏/移动问题已实机修复。

本批最终实际执行：上述默认命令 exit=0，`positive_cases=10, controls=2, cold_ui_and_skip=1, passed=true`；Python编译通过；结果后二次审计确认13例、43路线覆盖、原send对象body和首Start后的独立移动门控。verifier SHA-256 为 `dbe914b50cc6fedb0f757ca5841a5ad896c52724482604daf68a5c01d750682f`。
