# SRoleEnterScene 的主角移动状态与天气字节

本批为离线第一方研究，来源状态 `client_verified`。只新增本文及 `../verify_world_scene_movement_state_native.py`，没有改世界 Module、现有协议 Interface、共享入口、默认 mask、存档或政策；没有启动游戏、GUI、网络服务或真实战斗。

## 可用于接线的结论

`SRoleEnterScene` type `0xc0fa9` 中 Pos 后的第一个 byte（消息对象 `+0x2c`，下称 A）确实控制主角 `+0x218`：原 Process 严格按 **A==1** 归一为 bool，成功普通场景的加载分支把该 bool 交给原主角 setter。A=0 将已有 1/2 覆盖为 0；A=1 写 1；A=2/255 也写 0。随后原 mask selector 读取该 byte，0 选 mask1，非0 选 mask8。这是原消费者赋值证据，足以说明**满足原加载条件时，服务器明确发送 A=0 可以建立该字段的状态0**。

此结论有明确前提：Process 未被 App+0x20 门控、Scene 与主角存在、原地图配置有效、资源加载成功、reason!=516023、配置地图 id!=1404。首次入世界 reason516015 **不会跳过**这里的 state setter；它与特殊 reason516023 不同。

scene/mapID 后第二个 byte（对象 `+0x40`，下称 B）是**有符号天气配置 key**，通过 `CMapWeatherConfig` 消费。它不是第二个移动状态标志。B=255 被 sign extend 成 -1，清旧天气后不查新天气；B=128 传 -128，B=0 传0。原表 key1–11，没有 key0；当前 wire 填0的行为不能重新解释为“正常移动0”或“已恢复晴天”。本批不更改该 wire 值，也不制定天气政策。

状态0只说明这一个移动状态字段。它不证明 intro/input 锁、动画/特殊移动状态、场景交接生命周期和角色租约均已解除；也不是取消原主角所有未来路径/历史的通用指令。参见既有 `MOVEMENT_INPUT_GATES.md`、`WORLD_MOVEMENT_RECONCILIATION_RESEARCH.md` 的独立门控与保留队列限制。

## 原来源及复现

映像 `native-image.bin`，BASE=`0x400000`，SHA256：

`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`

入口 RTTI：`.?AVSRoleEnterScene@move@gsp@knight@@`；vt=`0x227921c`；ctor=`0xdac580`；marshal=`0xe50b00`；unmarshal=`0xf74260`；Process=`0x11e3140`。先读取并沿用 `ROLE_PROTOCOL.md`、`WORLD_ENTITY_PROTOCOL.md`、`SCENE_READY_RESEARCH.md`、`SCENE_READY_NATIVE.md`、`WORLD_MOVEMENT_RECONCILIATION_RESEARCH.md`，没有重新执行既有23+5纠正验证或 Stop noop 研究。

从项目根目录执行：

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/verify_world_scene_movement_state_native.py
```

本批实际结果：`all_passed=true, cases=37`，约1.4秒。脚本只向 stdout 输出 JSON；不写 JSON、客户端、账户或服务文件。输出含每例输入、原分支地址、状态、原 mask 及天气查找参数。父窗口随后报告已独立复跑当前37例全部PASS；双方离线结果都不构成 GUI/服务端接入验收。

## 原布局与 A 的消费者

原 codec 的顺序如下；字符串是原 compact 字节长度 + UTF16LE，多字节定长数为大端：

| 顺序 | 对象偏移 | 线类型 | 本批消费者证据 |
|---|---:|---|---|
|场景标签|+8|wstring|复制后传 Scene，现有文档已证资源目录另查原地图配置|
|Pos|对象+24，x+28/y+2a|i16 x/i16 y|11e3181/3185 sign extend 后传逻辑像素|
|A|+2c|u8|11e3162 比较1；11e3169 sete al|
|reason|+30|i32|传 Scene；516015首次与516023特殊须区分|
|scene/mapID|+38/+3c|u64|传 Scene；低32查地图配置|
|B|+40|原样u8编码，消费按i8|11e3209 movsx eax,byte[packet+40]|
|天气文字参数|+44|wstring|复制后与 B 传1219ff0，供显示格式化使用|

原字节 A 并非“任意非零就是1”。Process `11e3162..11e3199`：

```text
cmp byte [packet+2c],1
sete al
push eax                ; bool ABI 使用低byte，高位寄存器值不需要归零
push [packet+30]        ; reason
... copy 1c-byte wstring ...
push sign_extend(y), sign_extend(x), scene_high, scene_low
call 11e21f0
```

脚本执行真实 marshal/unmarshal 和 Process 构造栈参数，并在资源加载边界捕获 A 的实际低byte；再将捕获值送入 Scene 的加载后切片。没有用 Python 的条件式替代原 Process 判断。空字符串 fixture 的线体共20字节，例如 A0/B0/map1007/Pos100,120：

`0000640078000000000000000000000003ef0000`

两个 Process 早退点为 `11e314a..315c`：App getter813830 返回对象 `2945060`，其 byte+20 非零则返回；Scene全局2944564为空也返回。二者均不会调用 Scene 或天气消费者。

Scene `11e21f0` 的相关事实：

1. `11e256d..2576` 把原地图配置复制至 Scene+110。`11e257b..258c` 在主角全局294454c为空、配置 id=-1 时跳 `11e2e95`；尚未执行资源加载或 state setter。脚本用单变量原切片核验这两个 gate 与有效对照。
2. `11e25ee..2600` 取原 x/y 并调用 `11e0310`。`11e260c` 保存其 AL 到当前 frame+17。脚本不虚构资源成功，直接在这一个可观察加载结果 seam 注入成功/失败并明确区分。
3. `11e269b..26a5` 根据该返回 byte 决定是否跳过 setter；此处还清 Scene+32c。失败跳 `11e2e7a`。
4. `11e26ab..26c2` reason==`0x7dfb7`（516023）或 Scene+110==`0x57c`（1404）跳 `11e272d`；后续执行主角 vt+b4=`1218000` 的另一分支，不调用本次 vt+184 位置/状态 setter。脚本在分支处停止，所以本批只证明“不走此赋值链”，不冒称完成特殊分支玩法。
5. 正常分支 `11e26c4..26dc` 取 frame+b4（A的归一bool），依次 push bool/y/x，调用 Main vt+184=`1213b80`。**reason516015不在跳过条件内**，单变量原切片已核验。

`1213b80` 两次调用 vt+c8 位置 setter，然后 `1213bac..3bb6` 取第三参数交给主角 vt+8=`1205c80`；`1205c88..5c9d` 在值改变时真实写入 byte+218。没有适配这两个 setter 或目标byte。原 getter `1209d10` 读取它，原 `12028f7..1202919` 通过 vt+4 getter和 actor vt+184=`652af0` 给移动对象+48安装mask；脚本在每例场景状态结果之后实际执行此选择链，未用 host 计算 mask。

## 构造初始化与 SEnterWorld 的边界

主角构造链是 `11c67c0`（全局主角为空才分配）→`1219800`→`120a330`。`120a3ed..403` 在角色+160构造嵌入状态对象 `11d5020`；其中 `11d50d9` 将其 byte+b8 清0，即角色 `160+b8=218`。两个 poison 旧值1/255的原指令切片均被清0。这只证明该初始化写入，不把零填充内存当作构造依据。

SEnterWorld Process `833f99..833fa9` 将整理后的角色快照交 Scene`11da380`；后者 `11da3f8` 调`11c67c0`创建/复用本地主角，并经 vt+1b8=`120fb30`应用快照。`120fb30` 的直接指令设置角色ID/等级/shape与模型；本批没有完整重放其模型创建及所有间接调用，**不据此声称 SEnterWorld 的所有可能状态写入均已穷尽**。

场景成功 setter 的覆盖关系已独立、可执行地证明：不论先前字段来自构造还是入服/其他玩法，只要当前+218为0/1/2且经过上述正常 Scene 分支，最终值取决于原 Process 归一后的 A。因此无需猜测 SEnterWorld 的某个 byte 可以替代 A；也不能将其入服 intro 判别字段（packet+48/+4c）当作这个移动状态或真实EXP。SEnterWorld intro 与真实经验的既有纠正保持不变。

后来的 `SSetRoleLocation` 等已知消费者仍可能覆盖+218，见既有纠正报告；本批不将这次 Scene 赋值视为永久状态，也不修改任何发送策略。

## B 的天气调用链与原表

Process `11e31f6..3214` 复制 packet+44，再用 `movsx` 将 B 传给 `1219ff0`。后者的直接原调用链：

```text
121a030 call1213180               ; 清已有天气效果/显示
121a035 edi=arg0
121a03c cmp edi,-1
121a03f je121a186                 ; -1不查新天气，销毁文字值参数返回
121a045 call89dd60                ; ConfigRoot2945aec+8d0
121a04a..052 call table.vt+8(key)
```

`89dd60` 的原指令确为 root+8d0；表 vt2259aa8，原 ctor87a8d0/87a8f0赋该vt，getter87a980返回原UTF16类名 `knight.gsp.map.CMapWeatherConfig`（字符串从2259ab8开始）。vt+8=`87a970` 是原配置 wrapper，再调用 provider.vt+8。脚本保留 getter与wrapper，只在数据 provider 的查表 ABI 边界捕获实际 signed key；不伪装自己已执行天气资源创建。

原 parser87a790 的字段对照：row+0=id，+4=weathername（原字段字符串2259a8c），+20=weatherTIPS（2259a74），+3c=magic（2259a68）。`121a056`读取row+3c，经actor+44/vt+108创建效果，把句柄存主角+3dc；`121a0f6`取row+20格式化提示；`121a137`取row+4和提示传显示消费者15d3c80。清理函数1213180在有旧句柄时通过actor vt+114移除并将主角+3dc置0。该直接消费者没有把 B 传给1205c80或写+218。

本批 fresh 读取原 `runtime/client/artres/config.pfs` 的 `autoconfig/knight.gsp.map.cmapweatherconfig.xml`，PfsArchive校验长度/CRC；原entry SHA256=`2d757e3d1154a585c21d5069c4f844f4fdc31888489c8f081925b216fe6d0063`。11行key1..11，例如3=小雨/magic=`geffect/Function/Weather/rain`，5=雪天/`.../snow`，6=大风/`.../wind`。**没有key0。**这些数值/描述不授予本批实现天气战斗加成或随机天气的权限；原服务端规则另查。

## 验证表、方法与未验证范围

| 原生观察批次 | 例数 | 最小变化及实际断言 |
|---|---:|---|
|codec+Process|8|固定Pos/reason/map/空串，只变A或B；断言线体、decode、A归一和B sign extend|
|Process gate|2|只变App+20或Scene指针；两个下游调用均0次|
|正常Scene setter+mask|12|旧state0/1/2分别只变A0/1/2/255；捕获原Process低byte→原Scene切片→原setter→原selector|
|加载后跳过|3|成功对照只变load AL、reason516023、map1404；原分支与旧state2/mask8保留|
|首次原因|1|正常对照只变reason516015；仍写state0并选mask1|
|加载前gate|3|有效对照、主角null、配置id=-1；分支分别2592/2e95/2e95|
|天气原getter/wrapper|5|只变signed B=-1/0/1/127/-128；-1无查询，其余原样到provider|
|构造写|2|只变旧byte1/255；原11d50d9写0|
|原天气配置|1|fresh原entry长度/CRC通过，字段集合与原parser交叉|

方法采用 research 的原始来源追溯，以及 diagnosing-bugs 的可重复、可变红的离线差分循环。脚本用单变量断言区分并否定“A按任意非零解释”“B决定移动状态”“加载失败仍覆盖状态”，验证“A严格等1”的消费者。原 API/表/字节所有权在结论处分别注明，没有因邻近字段名或缺省0推导玩法。已读 ARCHITECTURE 与 DESIGN_AUTHORITY，本批只交研究 seam，没有增加第二份世界可变状态或模块间共享对象。

Host Adapter 仅用于：CRT分配/释放/cookie与空wstring复制，Scene同步资源加载边界捕获参数，已有Reconciliation夹具中的无伴随角色查找、UI/外观/动画与场景尺寸接口。原codec、Process比较/sign extend、加载前/后的原分支、1213b80/1205c80、getter/selector/mask setter及天气root getter/wrapper均执行原指令。加载后切片从11e269b开始，其frame/EBX/ESI/x/y由fixture按原调用栈明确建立；它不是整个Scene加载函数的原资源重放。天气查询在provider边界止步，未执行默认/非法key的真实cache结果与效果/UI资源加载。

未验证：完整首次入世界及重连包顺序的运行服行为、原地图资源实际成功加载、特殊516023/1404后续玩法、完整S_enterWorld模型创建间接写入集合、所有后续状态包和特殊移动转换、intro/input/动画锁释放、真实天气显示或战斗效果、客户端渲染/移动现场。该文件不把native fixture通过提升为上述范围已恢复。
