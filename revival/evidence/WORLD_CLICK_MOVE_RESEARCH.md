# 原地面输入 tick 到 CRoleMove 的可执行链

2026-10-23。本批第一方离线研究，来源状态 `client_verified`。只新增 `../verify_world_click_move_native.py`、本文及 `world-click-move-native.json`，没有改生产、shared、政策、旧研究、存档或运行服务，没有启动游戏/GUI。

**已从原持续地面输入入口1214bd0实际走到原角色路径创建、原CRoleMove builder及虚拟sender，取得可交给后续上行适配的真实body。** 它不是host直接调用120f9a0的builder样例，也没有用人造STOP替代移动输入。原开场flag=1时，同一输入入口没有读取鼠标、没有规划或发送；执行原CStartSetion清理后，输入链构造并发送了0xc0fa1。

入口Seam须说清：fixture提供**已锁存的持续输入状态**与一个确定节流tick，设备虚接口返回鼠标屏幕坐标。没有执行操作系统WM_LBUTTONDOWN、按钮锁存/UI命中分发或真实窗口投递，故不称“真实鼠标硬件/GUI已经能走”。在这个明确入口之后，predicate、屏幕坐标转换、高层修正、actor路径、原DDA、队列/前瞻、builder及原marshal都真实执行。

## 复现、来源与当前结果

按AGENTS重新读取research，沿用完整已读diagnosing-bugs，以原始来源追溯及确定、可失败的状态前后比较为方法；本窗口是根任务委派的后台研究。先读`MOVEMENT_INPUT_GATES.md`、`WORLD_NATIVE_PATHFINDING_RESEARCH.md`及原verifier、`WORLD_BLOCKED_GOAL_ADJUSTMENT_RESEARCH.md`与已有actor/report probes。沿ARCHITECTURE的研究Seam保持模块隔离，不创建第二份生产角色状态或网络Owner。

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/verify_world_click_move_native.py
```

实际输出：`all_passed=true,sent_count=1,kernel_entered=false`，约0.9秒；body：

`05d0048005e00480000000000000044c`

这是一组完整前后生命周期fixture，包含原拒绝、原清理、原允许/规划/发送、同捕获对象原marshal和原decoder核验。没有重跑505组规划差分，也不将一个短清段扩大成全图点击验收。机器结果：[world-click-move-native.json](world-click-move-native.json)。脚本只写这个新增研究结果文件，不写数据库/游戏或旧证据。

映像BASE0x400000，SHA256=`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。

fresh读取PFS长度/CRC通过：

| 原entry | SHA256 |
|---|---|
|map_1100_gumupai/maze.dat|b33712b6e7faa872890f9c8eb5257716b4974456862153e3131b3f7a675e34a9|
|map_1100_gumupai/map.rmp|d47f190cc1b120ff2f4786c294bc088045a1fcee491cd216fe617d5d82ab9cb3|

地图1100，恢复方案采用的出生点为(1488,1152)，目标选东邻(1504,1152)。脚本与`newbie-routes.json`角色配置9/school11的home map及原电影端点交叉。**采用该端点作服务器出生是既有newbie-opening-v1的designed选择，原服出生未确认**；这里验证该恢复出生点位于真实原maze，不重新把设计选择升级为原服事实。

起终两格(93,72)/(94,72)的原flag都是8，在本例普通mask1下清。原RMP为3072×3584；未修改flags来造清路。

## 真实执行的输入与坐标链

从完整1214bd0函数入口调用，原字段+308=1表示本fixture已经锁存的持续输入，+304=9使原1214c93..4cbb节流在此tick打开。**这两个字段是输入前提，不是host跳过predicate或直接写目标。** 没有执行把OS点击变成这两个状态的上游事件处理。

1. 原1214cc3调用1211db0。flag为1时在1211dbb..1dc2返回false，1214cca走原返回路径；81ae00、12143b0和sender都未触达。
2. 清理后原1214cd5调用81ae00。81ae00继续通过global2945090对象vt+50取得设备，再通过设备vt+40读取屏幕位置。两个设备虚接口由Host Adapter提供，返回原始屏幕点 **(48,48)**，没有返回逻辑目标。
3. 原1214cf2调用Scene11c5b40；该函数通过真实World vt+a8=5fdbd0读取相机原点。fixture相机投影原点为(2208,1104)，原函数执行屏幕加原点，得世界投影(2256,1152)。相机是fixture输入，坐标加法不是host替代。
4. 原1214cf7..4d4a按原整数/float处理投影坐标，水平除1.5，得逻辑目标(1504,1152)。1214d55实际调用主角12143b0(x,y,1)。本入口第三参数实际为1，先前阻挡目标研究固定0的边界由本例覆盖一个真实原调用来源；不据此解释所有参数枚举。

该链说明“predicate可通过”已推进到原入口实际消费设备坐标并调用路径函数；它仍不能证明真实游戏界面会把用户的点击送到这里。

## 真实执行的角色、actor与路径

主角/actor使用原虚表2299344/2462544；current getter与actor-moving getter均执行真实指令，显式绕开父夹具的替代getter。Scene point/mask及区域树查询沿原高层函数保留；两张区域cell表以空原树作为本例明确输入，不声称已加载真实Island/区域资源。

原query的准备也执行指令：

- 5aed50创建query及workspace，保留原分配/构造；
- 672410从本例Map的Maze字段安装真实128×224 flags网格；
- 原engine次接口2460594通过+88=5a63c0返回query；
- 原12028f7..1202919读取角色state0并安装actor path mask1；6bc33d再把实例mask写query+c。

实际规划链：

```text
12143b0
  →11f8800
  →actor.vt+170=652a40
  →6bc2f0
  →6138d0
  →626b40 / 6284f0
```

本16像素清段走原DDA捷径，**未进入6212f0网格搜索核**；不把它写成“原A*本例执行”。实际16个原点查询为(1489,1152)…(1504,1152)，与原起点排除/目标包含规则相符。路径创建未在11f8800截断，没有host给path返回成功、填未来队列或另写目标。

原11f8800继续返回到12143b0；随后原actor snapshot652a70→6bc6c0复制规划、头插current；原1213f80选前瞻；角色+2f4的空观察者列表也按原103c4d0复制/遍历/清理，没有把该回调替换成成功。完整12143b0和1214bd0均正常返回到fixture caller。

原上行发送时：引擎未来和角色未来都为[(1504,1152)]；发送后角色history为[(1488,1152)]，初始current头已按原消费链从未来移到history。actor仍投影(2232,1152)，原current getter仍是 **(1488,1152)**；没有执行运动tick去到目标。

这仍是移动**意图**，不是已确认到达，不能因为捕获到CRoleMove就把目标1504写为权威已到达点。

## 原上行对象、序列化与后续可消费输入

真实调用点1214a89进入builder120f9a0；之后原虚拟sender收到其栈上对象。捕获时sender返回地址为**1214aa9**，类型字段为**0xc0fa1**，对象原32字节：

`d88f2702a10f0c00548e2702d0058004548e2702e00580044c04000000000000`

Host sender边界复制这个已经由原builder构造的对象并返回1；没有host调用builder、重新填start/end或造STOP。输入函数返回后，对**同一捕获对象副本**执行原marshal e50840，产生16字节body。额外使用完整原ctor **daac40** 与原decoder **daad20**解码该body，核对原start/end/u64及完整消费；daac30仅是类型壳，不能替代daac40初始化内嵌Pos的完整构造。

| 供下一步上行Adapter读取 | 本例值 |
|---|---|
|消息type|`0xc0fa1`（CRoleMove）|
|body hex|`05d0048005e00480000000000000044c`|
|原start|(1488,1152)|
|原end前瞻|(1504,1152)|
|原u64字段（本例来自Scene+30/+34）|1100|
|原角色current，尚未到达目标|(1488,1152)|
|普通实例状态/mask|state0 / mask1|

后续可以用这个实际原上行body代替手工STOP，在一次性RoleOwner/地图实例fixture中检验原入口。该接线必须另行提供其角色租约、连接代次、地图绑定/位置版本；这些不是CRoleMove线包中的字段，本批没有将研究对象直接交给生产Owner或真实账号。机器结果保留type与body，不只是展示字节字符串。

**这不是完整网络密文帧。** sender是明确的发送Seam；原marshal通过后得到协议body，RC4/MPPC、外层封包/真实socket投递尚未在本fixture执行。不能称为原网络栈已连接运行服或服务端已经接受移动。

## 原开场清理前后

同一对象起始App2945060+3d8=1，Scene+39c=12345678。原输入tick实际得到0次鼠标读取/0次路径/0次发送，原predicate确实被调用。再调用原CStartSetion12b9a10→12bc870→11d3a10：原指令清App flag和Scene+39c，外部dispose Adapter收到原效果ID12345678。没有host直接清flag。

随后以同一设备/地图/角色/已锁存输入再执行1214bd0，得到1次鼠标读取、1次实际CRoleMove sender。两阶段只重置用于稳定触发的节流字段，未调用builder来补发。它证明这条输入链确实受原intro门控；不说明原游戏开场的启动/结束、遮罩命中和UI消息已经全部恢复，也不授权生产绕过开场。

## Host Adapter 与未验证范围

Host边界：CRT内存分配/释放、memcpy/memset/cookie及外部sqrt；设备工厂/鼠标坐标虚接口；原sender对象捕获和成功返回；原path开始event0发给fixture接收器；外部黑层dispose；地面点击标记120fe50的渲染副作用，以及继承夹具的UI/动画/无伴随对象边界。120fe50在原路径调用之后，只为避免离线渲染依赖，ret8；没有替代12143b0、11f8800、6138d0、DDA、列表消费、120f9a0、e50840或daad20。Scene11d2b00使用实际原函数，本例+320已为0而直接返回；不再用旧的Scene辅助Adapter。

未验证OS鼠标消息→持续输入锁存、真实设备/窗口/遮罩/相机状态、真实区域表、完整格搜索绕墙点击、后续运动tick/CHECK/STOP、原服接收与角色Owner、密文网络投递、GUI人物移动和动画。出生点选择仍是既有设计，原服出生未确认。本批新增的是可执行上行来源证据，未宣称真实客户端移动故障已经修复或部署完成。
