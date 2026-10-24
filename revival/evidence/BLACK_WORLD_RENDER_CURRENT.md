# 当前黑色世界：原生渲染调查

## 最新结论：开场遮罩与移动门禁共用一条生命周期

后续原生回放已找到此前未采集的第二种遮罩：SEnterWorld对象+0x48/+0x4c的intro判别值<=0会同时设置App+0x3d8移动门禁，并创建Scene+0x39c的全屏movieblack.tga效果。原贴图全像素不透明黑色；效果300000 tick-ms后自行销毁，但该超时不清移动门禁。真实CStartSetion/CG清理链同时清两者。这能解释“几分钟后出图仍不能移动”；尚无当时黑态Scene+39c的同步现场读数，不能把离线机制写成已完成现场修复。详见[WORLD_INTRO_BLACK_NATIVE.md](WORLD_INTRO_BLACK_NATIVE.md)与[MOVEMENT_INPUT_GATES.md](MOVEMENT_INPUT_GATES.md)。

同时修正了入场字段：真正EXP位于对象+0xf8/+0xfc；world_protocol原先错误写到intro判别槽。verify_world_snapshot_experience_native已先失败后通过，EXP0/150/4886718345分别进入真实XP槽，intro保持独立。补齐开场播放/结束与持久章节由任务及共享入口接线；仅修正EXP字段不能消除默认intro0的门禁。原服务器intro字段业务名称/原始完成值仍未知，采用0/1本地投影须按NEWBIE_OPENING_DECISION执行。

世界侧已交付43条角色/门派路线、10个设计出生候选和首NPC可达性检查。运行时/真实GUI未在本批部署或验收；本文下方“尚无根因”等措辞属于此前调查记录，以本节及原生专题证据为最新状态。

2026-10-23，适用原1.6.1映像，现场最初PID39536。采用diagnosing-bugs，先建立视觉红绿反馈，再列三项可证伪候选，按research只读取第一方原映像和指定进程状态。未写客户端内存、注入、发包或修改生产。根AGENTS/ARCHITECTURE/DESIGN_AUTHORITY沿用本批已读版本；未发现GLOSSARY或相关ADR。

## 实际反馈环

`research_black_world_render.py --image C:/Users/11950/AppData/Local/Temp/codex-clipboard-6d3d1a5a-bcc4-4bce-98cf-655cf5fce6d4.png` 已运行，中心世界视口黑像素比例 **1.0**，结果 `BLACK_WORLD`，退出2。

同脚本读旧正常截图 `codex-clipboard-7b5c888f-5838-4d7b-bb4c-e869ce8fbb58.png`，黑比 **0.0024734766**，结果 `WORLD_HAS_PIXELS`，退出0。裁剪区域为整张游戏截图相对x25%–70%、y25%–65%，避开HUD。固定快照重放确定且秒级；正常画面不等于NPC或加载完成验收。

当前只读画面/状态由父任务捕获：HUD正常、临安、坐标530,436；CGameScene/mainchar存在、scene1007、逻辑Pos8480,6976。对象存在不等于进入绘制。旧自愈黑场的内存采样没有同步截图，不可当作严格正常态内存基线。

## 测试前列出的三项候选与predictions

1. 场景/世界激活门控未开。如果是原因，应找到明确渲染入口早退条件，现场该门控阻止工作而正常场景不阻止。
2. World加载图或camera未就绪。如果是原因，map为空、rect不合法/离角色过远、viewport或zoom不合法；世界正常后相关字段恢复。仅HUD正确不能排除此项。
3. 世界层全屏黑色过渡遮罩。如果是原因，负责该覆盖的visible/资源/alpha路径实际激活；正常后覆盖退出。地图初始化成功也不能排除此项。

候选在读原代码验证前已报父任务，未将任何一项当根因。

## 原生已证实的观测点

原映像 [native-image.bin](native-image.bin) SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。反汇编可重跑 `research_black_world_render.py --disasm`，产物 [black-world-render-native.txt](black-world-render-native.txt)。

| 位置/方法 | 原生证据与用途 |
|---|---|
| CGameScene global0x2944564 | RTTI固定对象入口；虚表只有析构，不能把后续UTF16文本当额外render方法 |
| Engine0x29a4a70 +0x40 | 父任务实读World@XiaoPang；engine虚表+0x48取World |
| World+0x298 | map对象。World虚表+8=`0x5fd420` 在 `0x5fd431` 判断为空直接跳到尾段，跳过该函数大段世界更新；不是单凭此处就证实所有绘制入口 |
| map+0xc/+0x10 | `0x5fcd00` 返回两个地图尺寸字段（map为空返回false） |
| World+0x2a0 | 内嵌camera对象；`0x5f9920/30`转调其虚方法 |
| camera+0x1c8/+0x1cc | camera模式与跟随对象槽：`0x5fdb00`按entity查对象并写+1cc，模式4调用`0x687800` |
| camera+0x1e8/+0x1ec/+0x1f0/+0x1f4 | 可见矩形left/top/right/bottom。`0x603480`按地图尺寸重定位并写这四项 |
| camera+0x200/+0x204/+0x208 | viewport两维和zoom。`0x6876d0`记录zoom并以viewport/zoom算rect宽高；zero/NaN必须单独判别，原始u32也保留 |
| World+0x488..0x494 | 同一camera rect（0x2a0+0x1e8）；`0x5fdbd0`复制四值 |
| CGameScene byte+0x334、ptr+0x330 | `0x11c5e20`覆盖绘制必须两者均非0才调用renderer虚表+0xf8画全视口资源，并计算alpha；这是明确的覆盖候选路径 |
| CGameScene+0x338/+0x340 | 上述覆盖路径alpha/阶段计算参数，业务单位未证实 |

## 本批只读采样结果与现场变化

新增 `research_black_world_render.py --pid 39536`，权限仅 `PROCESS_QUERY_INFORMATION|PROCESS_VM_READ`，仅读固定已知对象及字段。执行时OpenProcess成功但读取global0x2944564失败；随后进程列表已无knightclient。故没有本批完整camera/map/overlay现场快照，也不能据此说map不存在或候选已排除。父任务较早的World+24/+28等原始头部不覆盖这里刚确认的关键map+298和camera字段。

新客户端启动后父任务可用新PID运行同脚本，产生 `black-world-render-PID.json`，与同秒截图一同记录；若重新显示世界，务必先保留一份同秒绿态采样。不要通过写门控字节猜修复。

## 本批结论与未验证

已建立黑世界视觉可重复判据，新增只读探针和两组明确的map/camera与overlay条件。尚无根因结论；未做反事实修改、没有实施修复。进程结束中断现场读取，候选仍待同画面状态采样。没有把场景文件加载成功、对象存在或FPS当作世界可见验收。

## PID26680继续现场（后续）

父任务以新现场26680继续并保留会话。before与visible快照分别为 `black-world-render-26680-before.json` 和 `black-world-render-26680-visible.json`。用户随后报告正常地图；两者相隔约384秒。map指针非零，尺寸13056×7424；camera rect12032,6592,13056,7360，viewport1024×768，zoom1；已识别遮罩+334=0/+330=0，两阶段相同。

补充只读探针 `black-world-render-extra-26680.json` 读取camera跟随对象：vt+0x38=`0x6528d0`，从target+0x1a8姿态指针读取floatXY，实际为 **12720,6976**。wire x8480经过原场景×1.5变换后为12720，恰在可见rect内；不能拿wire8480直接和renderer矩形比较。本批曾提出坐标错位候选，现以此读数撤回。

世界更新也有直接推进证据：`0x5fe290` 每次增加q64全局counter `0x29b7810`，3次只读采样7313→7320→7326，world+0x27c为2839120→2842320→2845060；原循环 `0x600d50` byte+0x66c门控已经进入。此证据仅表明世界更新链推进，不证明GPU提交或地表实际画出。

原map+0x98 block指针vector含36项；前6项若干头字段为0，未识别具体ground texture字段，不将0当作纹理丢失。后续world资源容器计数+0x688=109、+0x694=5、+0x6a0/+0x6ac=0，加载计数+0x65c/+0x660=0，byte+0x66d=0。原 `0x5fcb2d` 用+66d和65c/660等值判断该加载回调完成，再设+66c=1/+66d=0；当前读数不支持这一批加载仍挂起。需要进一步定位实际ground draw或设备状态才能确诊。

### byte+0x24c的实际含义限制

before的world+0x24c整字为65792，visible为65793，但不能称低byte为“世界可见开关”。原 `0x5fe1c0` **按world+0x27c日内时间切换**，若map+0xe4的6位未置位：755000 < time < 6745000时设低byte=1，区间外设0；`0x600d50` time按7200000取模。0→1还传递changed标记至 `0x5fdfe0/0x5fde10`。它们遍历map block+0x150起的资源项，每项+0x88记录处理代次，changed时调用 `0x692330` 刷新。当前只证实昼夜时间区间相关资源刷新通路，不证明是黑场根因。

我在用户报可见前的只读采样已经读到24c=1，但没有同秒黑图；这个时间差不能证明或排除此状态对显示的因果。不能将用户置前窗口、时间跨区间、异步资源完成任一候选当作已实施修复。当前进程正常后仍原样保留，未重启、注入、写内存或发包。

## 总World draw与后台状态：进一步原生核验

真正世界绘制入口为 `0x606860`，由Engine context虚表+0x44（`0x5a9e40`，this是engine+4）在`0x5a9f18`调用。入口首先判断World byte+0x66c，为0直接跳到尾部；正常进入后`0x6068cb..0x606903`将当前engine tickStamp写全局 **0x29b8e58**。世界update `0x5fe1c0`写 **0x29b8e48**。值源自context虚表+0x40（`0x5a63e0`取context+0xdc，即engine+0xe0），因此称tickStamp，不能称GPU frame编号或提交成功计数。

好态26680只读三次updateStamp/drawStamp均相等且同步推进：175287903→175288181→175288508。它证明真实世界draw入口已经调用，仍不保证GPU呈现或每个地表tile非空。下一次黑态若updateStamp推进而drawStamp不变，才支持末端绘制被跳过的候选。

原总draw分支`0x5a8f75..0x5a8f9f`要求：Engine+0x9c不等于2、Device虚表+0x154返回4、当前timer结果为true。context入口还要求engine+0x44(device)和engine+0xa4非空。Device状态原方法`0x6d3c70`在device byte+0x1bd=0时直接返回4；非0时检查D3D cooperative状态。未向运行客户端调用该函数。

WndProc `0x5a8fe0` 的WM_ACTIVATE(6)分支把Engine+0x9c写0（active）或1（inactive）；WM_SIZE(5) wParam=1或4写2。**普通失焦状态1不直接禁止worlddraw；状态2才经过这个总门控跳过。** 好态实读Engine+0x9c=1，仍有上述drawStamp推进，因此“后台总是不画世界”与当前事实冲突。不能把先前black→visible归因于置前。

### 离线反事实与持续只读观察

`research_black_world_render.py --replay-gates` 直接执行原始`0x5a8f75`分支，在离线Unicorn中仅以fixture替代外部device查询结果与draw回调。5组已通过，结果见 [black-world-draw-gate-replay.json](black-world-draw-gate-replay.json)：active0/inactive1均允许draw；模式2跳过；device返回2跳过；timerfalse跳过。没有写在线进程或操作UI；这只是原门控的反事实验证，不是故障已修复证明。

可有限时观察同一明确PID：

```text
python revival/research_black_world_render.py --pid <明确客户端PID> --watch-seconds 60 --interval 0.5
```

输出独立 `black-world-render-watch-PID-时间戳.jsonl`。每次含UTC与elapsed、成功snapshot或未初始化/读不可用/退出状态；限定≤600秒，interval 0.1–10秒。每次先以同一进程句柄核exe为knightclient.exe及创建时间，PID复用立即停止，不扫描/读取其他应用内存。snapshot已含engine_mode、device状态字、render_aux、update/draw tickStamp、加载与camera字段。

本次watch测试26680时（11:49:28 Asia/Shanghai）原进程已不可访问，随后系统进程查询已无knightclient；记录exited_or_inaccessible并立即停止。旧39536同样记录退出路径。用当前Python自进程验证wrong_process拒绝，未读取游戏地址。进程已退出使本次连续成功采样未实测；此前单次snapshot及三点只读marker采样已有真实好态证据。未为完成测试启动或重启客户端。

## SGameTime先于场景导致首轮材质漏更新：离线证伪范围

按父任务提出的具体候选继续原生执行，而非只保留假设。新增 [verify_world_time_material_native.py](../verify_world_time_material_native.py)，结果 [world-time-material-native.json](world-time-material-native.json)，**11项原生fixture通过**：

1. 原`0x692330`以不同rand fixture运行两次，effect对象0x100字节sentinel仅+0x64..+0x6b改变，值为6745000+rand%10000与745000+rand%10000；effect+0x30 bit1=0时完全无写入。该函数随机化昼夜触发时间，不是“刷新全部tile及角色颜色/alpha”。函数无材质调用；本次将此前宽泛的“刷新”措辞缩窄为具体写集。
2. 执行原SGameTime入口`0x81b3e0`，scene不存在/已注册两个fixture均写network时间并触发ActivityManager创建，World与Scene各0x700字节sentinel不变。fixture为noon、其他可选manager缺席，保留CRT日历和活动创建为host adapter；不是完整运行服消息重放。静态代码中scene仅在特定时辰提示分支读+0x364，不调用World或renderer。
3. 原worlddraw `0x60692c..0x606933`每次都调用`0x604b80`计算8个全局绘制参数。它读取map+0xcc时间keyframe树（head+0xd0、count+0xd4），按World+0x27c在7200000周期内插值，之后renderer虚表+0x118/+0x11c应用。计算不依赖SGameTime事件，也不依赖24c changed。
4. 直接执行原`0x604b80`，无keyframe、time=0/755001/6745001三组都在本次调用计算并提交默认8floats `[0,0,0,0,1,0,-10000,-10000]`（配置+0x14启用、+0x15直接路径）。有两份真实std::map布局fixture、time=0/1800000/5400000三组也都本次计算提交，正向与跨日反向插值符合预期。**8float各分量尚未命名，不把其中0直接叫black RGB或alpha0。**

因此，不支持“重发SGameTime补首轮全局颜色”以及“等第一次24c切换经692330才初始化全部tile/role材质”这条具体因果链。保持SGameTime在场景前创建ActivityManager的已有安全顺序，不以此证据增加重复消息或改包顺序。仍不能排除其他原生设备/材质首次初始化缺陷，也未证明根因。

### 已落到具体可观测/可重放的下一修复判据

renderer+0x118通过`0x6e29c0`选pixel shader：Device+0x188是selected，+0x18c是applied，+0x174起5个program槽。选择时检查`program+4+backend`可用byte及`program+0xc+backend*4`原生shader handle；backend全局`0x29235d4`。若所需shader不可用，selector直接false（`0x6e29f2`）；这比再次补时间通知更直接地约束GPU提交候选。renderer+0x11c=`0x6d3a00`先调program虚表+0x10存8参数，若正选中再调+0xc应用。

snapshot已增加这些只读shader槽/可用byte/handle/selected/applied与map时间参数count，未编译shader、未执行在线方法、未写状态。新增shader字段因现场进程已结束，尚未进行真实读数验证。所有模拟值仅用于离线函数差分，未改玩法数值。available含义已在以下原生反事实进一步限定，不能解释为异步编译完成。

## 原HLSL与shader反事实：下一处明确门控

新增 [verify_world_pixel_shader_native.py](../verify_world_pixel_shader_native.py)，[world-pixel-shader-native.json](world-pixel-shader-native.json) 含 **7项原生x86 fixture**及**3项原源码数学反事实**；两种方法分开记录，未冒充GPU执行。

- `0x711770`以PixelShaderVersion token是否≥`0xffff0300`设置program+4..+0xb共8个可用byte。PS2与PS3两个原生fixture核验通过；这是最低PS3能力门控，**不是异步编译完成位**。若同一设备、同一backend未改变，它不会因等待几分钟自然从不支持变为支持。
- 原`0x711c50`constructor的8float默认是 `[0.2,0,0,0,1,0,500,400]`；原`0x7117b0`setter完整复制8float。初始并非全0，也没有只写部分参数的证据。
- 直接执行selector `0x6e29c0`：unavailable返回false不bind；available且D3D BindShader成功才更新selected；BindShader失败保留旧selected并false；selected已等于requested时直接true不bind。这是缓存信任分支，测试证实行为，不表示现场缓存错误。原初始化 `0x6e286f/72` 将selected/applied均置-1，反对“正常constructor误以为0已绑定”的猜测。

原shader源码就在映像内：header `0x246e970`，主体 `0x246e2b8`，8份backend片段表 `0x2923588`。`--disasm`现在一并提取 [world-colour-native.hlsl](world-colour-native.hlsl)（backend0完整拼接）及 [world-colour-shader-sources.json](world-colour-shader-sources.json)（全部片段/地址）。

由原HLSL现在能命名参数：p0/p1/p2分别对R/G/B增强并交叉抑制其他两通道；p3统一RGB偏移；最后 `RGB = p4 * RGB + p5`；p6/p7是局部渐变中心（X差除1.5，距离250范围）。**604b80提交的默认 `[0,0,0,0,1,0,-10000,-10000]` 是中性效果，绝非黑色或alpha=0。** 这进一步否定首帧默认shader参数造成必然黑场的候选。此前8floats未命名的限制已由源码证据解除。

backend0片段做 `fResult *= input.c0`；backend1先设 `input.c0.xyz = 1` 再相乘。以非黑texel `[.4,.6,.8,1]` 作数学反事实：默认中性参数+白色vertex COLOR0得到原texel；同参数+不透明黑色COLOR0在backend0得到不透明黑；backend1得到原texel。因此下一可验证点是 **实际地表/角色提交quad的COLOR0与shader backend是否匹配**，不是再发时间包。当前没有黑态vertex buffer或shader槽快照，不能宣称此项为根因或直接改颜色。

可测试修复点：如果后续离线重放真实黑态quad证实COLOR0=不透明黑但原材质默认应白，并且白色COLOR0只改变这一项就恢复texel，则在原quad构造/颜色缓存初始化处修复；如COLOR0正确却BindShader失败，定位设备重建后shader handle/selected/applied恢复顺序。当前只有原生门控与源码反事实，尚不具备实施以上任一修复的现场证据。根任务并行检查地表批次，避免重复改其范围；本窗口继续shader/时间常量研究。

本批严格遵守用户新限制：**不打开游戏、不做GUI操作、不自动登录、不重启客户端或服务**；新增验证全部离线原映像/已保存快照。

## 背景图块提交与颜色默认值：离线补充

verify_world_ground_native.py直接执行原0x605110背景层裁剪、0x6d3940的descriptor转换，以及0x6d28ac..0x6d290a的默认/显式颜色选择。5项提交fixture和3项颜色fixture通过，结果world-ground-native.json。正常1024×768 fixture提交12块256×256；空layer vector、空texture槽、camera或layer不相交均提交0。fixture的layer+0/+4是中心位置，未把它当左上角。

该背景路径传给generic textured draw(0x6d2660)的+0x14颜色指针为0，原默认支路写四个0xffffffff白色ARGB，故“背景descriptor没填颜色，默认全黑”不成立。原shader的backend0乘COLOR0事实仍正确，但要支持它是现场原因，必须实际看到提交的黑色顶点；不能拿shader数学fixture代替坏态证据。此处是map+0x68的背景层，不等同全部world/camera分层几何。

只读snapshot增加map+0x68背景vector、world+0x2a4起7组0x24条目与+0x384起2组0x28条目的计数和少量原始字段，以及engine+0x48配置的mode+0x48、合成alpha+0x18、背景分支+0x3b。vector读数先校验begin/end/capacity、stride和16MiB上界；每组最多采2条（背景4条）。这些新增现场字段仅完成语法检查，当前无客户端，尚未取得真实进程新字段样本。

用户经战斗窗口传达最新限制“不要打开游戏”，本批全部离线，未启动客户端、操作GUI、自动登录、重启服务、写入客户端内存。先前一张正常图只证明那一刻有世界像素，不能覆盖用户后续黑屏反馈。根因与原症状回归仍未完成，黑屏反馈判据保持红：用户83cfe图black_ratio=1.0；b1ee正常图=0.001806。

## Render config与RT合成alpha：默认值候选已缩窄

本批沿用research的原始来源追溯和diagnosing-bugs的单变量离线反事实；原映像SHA256仍为`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。新增 [verify_world_render_config_native.py](../verify_world_render_config_native.py)，执行8项原生fixture均通过，结果 [world-render-config-native.json](world-render-config-native.json)，对应原始指令 [world-render-config-native-disassembly.txt](world-render-config-native-disassembly.txt)。这些fixture验证具体默认值与分支行为，不代替黑屏症状回归。

Engine初始化`0x5a760c`分配0x6c字节config；`0x5a7656`保存到engine+0x48，`0x5a7664`调用原默认初始化`0x5ba8b0`。context虚表+0x34方法`0x5a6300`读取context+0x44（context是engine+4），与engine+0x48同址。原初始化直接执行所得：config+0x48为 **1**，config+0x18为 **0.6000000238418579**，config+0x10为1.5。因此“正常constructor将RT合成alpha初始化成0”与实际指令冲突。

World绘制`0x606683`对config+0x48分支：0到`0x6067db`，1到`0x6067c2`，2到`0x6066a4`执行RT路径，其他值到`0x6067e9`。四份fixture保留原比较/跳转指令，仅在分支落点停止记录，分别证实0/1两条直接绘制分支、2的RT分支与3的不绘制分支。**默认mode1不会走这条RT合成alpha路径。** 仍未确定0/1模式业务命名，不将它们叫画质档位。

在mode2分支中，`0x606745..0x606766`把config+0x18乘255、截断为整数，再把低8位写入白色ARGB高字节。原指令三组结果：0→`0x00ffffff`，0.6→`0x99ffffff`，1→`0xffffffff`。这确证某些运行值可使合成alpha为0，但未执行GPU混合、未证明黑态实际mode=2或alpha=0，也未追明RT texture本身有效与否。故不能把此fixture说成已重现当前黑屏。

配置写入点检索仅确认上述constructor写入；在config默认值/相邻helper范围，以及映像内立即数store和浮点store候选中，未取得有engine/config对象来源链的后续+0x18/+0x48写入证据。`decoded/config/autoconfig/knight.gsp.systemsetting.cgameconfigsetting.xml`也未提供这两个偏移与用户选项的映射。该检索范围不涵盖所有间接register赋值、bulk copy或插件调用，**不声称没有其他写入者**，不据此改用户设置。

下次已有且获准读取的黑态，先用已增加的只读snapshot字段区分：若mode仍为1，直接排除这一条mode2合成alpha因果链；若mode为2，再对照alpha和RT对象/texture；若mode落在0/1/2外，原分支会不绘制，应先追config变更来源。当前没有客户端进程且用户禁止打开游戏，新增字段没有真实黑态样本，尚无可实施修复结论。本批不修改共享入口、客户端设置或在线内存。
