# 原客户端路径规划与阻挡终点：离线研究

2026-10-23。结论：已直接执行原 `0x6212f0` 网格搜索及原 `0x6138d0` 的直线捷径、搜索、短路径压缩，得到可重复的绕墙节点。没有使用宿主 A* 替代算法。阻挡终点在这两层明确失败；普通角色输入上层另有邻域修正，尚未执行其完整分支，不能据底层失败擅改原传送落点。

## 方法、来源及边界

按 research 从第一方指令追到查询对象、地图安装、搜索、heap 和路径压缩；本任务本身是已委派的后台研究。参考既有 [SCENE_GRID_PROTOCOL.md](SCENE_GRID_PROTOCOL.md) 与 [WORLD_MOVEMENT_RECONCILIATION_RESEARCH.md](WORLD_MOVEMENT_RECONCILIATION_RESEARCH.md)，不重做既有角色 mask、移动报告或位置纠正规则。用单变量反事实分别区分“端点阻挡”“中途绕墙”“完全隔断”“换 mask”“DDA 与搜索分支”。这是原行为研究，不声称已修复某个在线移动故障。

唯一算法来源 [native-image.bin](native-image.bin)，映像基址 `0x400000`，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。可复跑 [verify_world_native_pathfinding.py](../verify_world_native_pathfinding.py)，机器结果 [world-native-pathfinding.json](world-native-pathfinding.json)，原指令 [world-native-pathfinding-disassembly.txt](world-native-pathfinding-disassembly.txt)。18 个案例通过。

Unicorn 只执行这份映像。Host Adapters 仅提供原分配/释放调用、security-cookie、memset、memcpy；分配器为隔离内存中的递增分配，free 不回收。STL invalid-iterator 入口直接报错。碰撞、邻居生成、代价、heuristic、heap、父链回溯、路径压缩均执行原指令，无宿主算法替代。每次原调用有宿主 2,000,000 指令停止上限，它是测试保护，不是原生预算。没有启动客户端、GUI 或服务，没有访问运行进程/存档，没有修改生产 Module 或接线。

## 原地图查询对象的实际来源

既有原 maze loader `0x672490` 产出 Maze 对象：`+8=width, +c=height, +10=cells`，按行 `cells[y*width+x]` 存一字节 flags；原包 maze.dat 头部及合法性已见网格研究。

本轮定位并执行了此前缺少的安装环节：

1. 引擎初始化 `0x5a785a` 分配 `0x24` 字节，`0x5aed50` 将前八个 dword 清零，再分配并构造 `0xe118` 字节 workspace，保存到 query `+0x20`。引擎本体 `+0x164` 保存 query（写入 `0x5a788a`）。
2. 引擎本体 `0x29a4a70` 的次接口是 `+4`，原次虚表 `0x2460594`。其 `+0x88=0x5a63c0` 返回接口相对 `+0x160`，即本体 `+0x164` 的 query；不是另造默认网格。
3. 地图加载 `0x5fd1cc..0x5fd1d8` 取 `World+0x298` 所载 Map 的 `+0x84` Maze，调用 `0x672410`。该函数由传入 World 的 `+4` 取 factory，经真实虚表 `+0x88` 获取 query；从 Maze 复制 width/height/cells、min/max，保留 workspace。
4. 原 `0x672410` 对非正 width/height 写0；正常地图安装结果如下。mask 此时确实是0，后续 actor 根据实例状态写入，不可把0误当普通步行默认。

|query 偏移|类型/含义|原安装值|
|---|---|---|
|+00,+04|i32 width,height|Maze 的尺寸，非正变0|
|+08|u32 cells pointer|Maze+10|
|+0c|u32 mask|0；actor 随后安装|
|+10,+14|i32 min_x,min_y|0,0|
|+18,+1c|i32 max_x,max_y|width,height，排他上界|
|+20|u32 workspace|原 constructor 创建的0xe118对象|

第14案例实际执行 `5aed50 → 672410 → 原次接口getter → 6212f0`，断言全部9个 dword，再得到清图路径。fixture 使用合成 Maze 与原引擎次接口，未执行文件系统/整个地图加载器；不能将此称为全包各地图寻路压力验证。

## 可以调用的离线 Interface 与精确 ABI

`NativePath(width, height, cells, mask)` 每例新建隔离引擎内存和完整 flags 网格。输入需合法且大小一致；当前研究工具不是生产不可信输入校验器。

`NativePath.kernel((sx,sy),(gx,gy))` 执行原 `0x6212f0`：

- 输入是**格坐标**。寄存器 `EAX=gy`，入栈六参数依次为 `workspace, query, sx, sy, gx, output_list`；原函数 `ret 0x18`。
- 输出取 `AL`，1成功、0失败。原 STL list 对象三 dword 为 allocator、sentinel、size；节点 `next,prev,i32 x,i32 y`。成功路径不含起点，含目标，按前进方向排列；不能把整个 EAX 当布尔 ABI。
- 查询中宽或高超过 `0x780=1920` 被拒绝；目标须在 min/max 内且 `(flags & mask)==0`。同起终格返回0。未发现同样的起点阻挡前置拒绝，单独案例证实阻挡起点仍可向清邻格出发。因此调用方仍需独立校验权威起点，不能把“kernel成功”当起点合法性证明。

`NativePath.wrapper((start_x_float,start_y_float),(goal_x_int,goal_y_int),mode=0)` 执行原 `0x6138d0`：

- 输入是**逻辑像素**，网格边长16。`ECX=goal_x, EDX=query`，栈七参数依次为 `start_vec, goal_y, mode, grid_list, float_list, 0, 0`；原 `ret 0x1c`。start_vec 为原6-float布局，fixture只需首两项位置。末两个参数业务含义尚未确定，工具显式固定0，未对其它值给出合同。
- mode0先调用原DDA `0x626b40`；直达即生成单个目标 float 节点，不进入 kernel。mode1跳过此捷径，原指令实际进入 kernel；其它 mode 尚未作业务映射。
- 搜索成功后的短路径分支调用原 `0x61bc60` 压缩、`0x61b7d0` 复制；float节点原payload为6 floats，本工具公开首两项位置。grid list会被原流程消费，不能在 wrapper返回后仍用它当完整路径。
- 已执行 EAX=0成功、1搜索失败、3相同点。静态还见2分支，未构造出覆盖案例。长度至少25节点时另有分段处理分支，未执行验证。

这两个公开接口允许父窗口独立复跑原规划。它们只存在研究脚本，不暴露为生产世界 API，不改变 recovery 接口、状态所有权或网络投递。

## 最小绕墙反事实与18例结果

固定8×6 flags网格，mask1；起点格(1,2)，目标格(5,2)。墙为 `x=3,y=0..3`，底部留两行缺口。

|案例|原结果|
|---|---|
|清图 kernel|AL1；[(2,2),(3,2),(4,2),(5,2)]；pop4个节点|
|同图加局部墙 kernel|AL1；[(2,3),(2,4),(3,4),(4,4),(4,3),(5,2)]；pop16个节点|
|墙封至全部6行|AL0，空；pop18个节点后耗尽open heap|
|仅目标格阻挡|AL0，空；pop0个节点|
|起终同格|AL0，空；pop0个节点|
|仅起点格阻挡|AL1，仍能离开起点|
|wrapper清图：(24,40)→(88,40)|EAX0；[(88,40)]；kernel调用0次|
|wrapper同样局部墙|EAX0；[(56,72),(88,40)]；kernel调用1次|
|wrapper阻挡目标|EAX1，空；kernel调用1次，pop0个节点|
|全等f heap|插入label0,1,2，实际弹出0,2,1|
|等f左右子节点 heap|f=[0,10,10,20,30]，实际弹出label0,2,1,3,4|
|width1921|AL0，pop0个节点|
|相同局部墙换mask8|墙flags1不命中mask8，得到清图直行节点|
|原query constructor/map installer|9字段一致，安装后kernel清图路径一致|
|2×2斜对角，两侧正交格均阻挡，kernel|AL0，不能跨角|
|完全相同角点图，wrapper mode0|EAX0，DDA捷径通过，不调用kernel|
|wrapper相同逻辑点|EAX3，空|
|wrapper清图mode1|EAX0，确实调用kernel|

后两种角点结果并不冲突：原搜索的对角邻居检查旁边两格，但原像素DDA不是supercover，原wrapper保留了该捷径。因此不能把“所有移动一律禁止切角”当已证实原规则，也不能因DDA有捷径就删除kernel的正交邻居检查。

## 邻居代价、heuristic 和 heap 顺序

`0x6213de` 在真实 pop后记录节点。节点原布局是：`i16 x,y; parent+4; g+8; f+c; state+10; heap_index+14`。state0未发现、1 open、2 closed；这些数值依据原写入/比较，不额外取玩法名称。

实际首轮 push 顺序为 NW,N,NE,W,E,SW,S,SE；直步 g增5，斜步增7。清图第一轮首8邻居 g依次为7,5,7,5,5,7,5,7，完整真实push/pop轨迹留在JSON。`0x5f8ac0` 写parent和g，按平方距离调 `0x5f87e0` 的整数距离函数，再乘5加入f；不是浮点hypot。没有对该整数函数所有输入作差分，不将其精确取整性质扩展为全域已验证。

`0x5f8bb0` push调用 `0x5f8e50` 上浮；`0x5f8e90..93` 只比较f，父f小于等于子f就停止，等f不额外比较g/h/坐标。`0x5f8c20` pop将末节点移根；当需要在较小左右子中选取时，`0x5f8d0b..12` 对等f选择右侧。两个独立原heap案例直接确认它不是FIFO tie-break。复刻时仅使用常见 `(f,g,x,y)` 堆键会改变相等f时的路径。

目标节点state变1后，在 `0x621ca7` 一带进入回溯，目标通常尚未被pop；故本文不因算法外形像A*就承诺全图最优路径或将pop数当路径长度。

## 预算、失败与接线限制

`0x6212f0` ABI内没有观察到时间/展开节点预算参数，也未见核心调用 GetTickCount。查询1920尺寸约束对应16×16稀疏分块、120×120块指针缓存；heap位于workspace+e108，节点池和块池由原分配器管理。`0x607fe0` 的65536预留不是已证实最大搜索节点数/预算；不能把它改名为原版限额。

失败可由超尺寸、目标越界/阻挡、同格、open heap耗尽产生；本工具对其中尺寸/阻挡/同格/耗尽已执行验证。未覆盖最大图、分配失败、所有局部查询矩形或耗时分布。若生产需要命令预算、超时或路径长度限制，应由Owner独立设计并标注 designed，不能声称来自此原接口。当前脚本的2百万指令保护亦不能直接冒充服务端预算。

## 普通角色输入：静态链与未执行的终点修正

原 `CMainCharacter 0x12143b0` 不是上述两个已执行函数的同义名称。它先处理重复目标及角色状态，以角色虚表+134读mask，再调用Scene `0x11c5c00` 查目标阻挡；目标不合法时的 `0x1214502..0x12145b9` 有朝当前位置方向按16像素候选移动的循环。后续还见当前点检查、原偏移表 `0x28d39e0/0x28d39e4`、环形候选和Scene `0x11deaa0` 条件。完整候选顺序、停止界限和不同mask/状态下的最终点未执行，不能据这些静态片段发布服务端“自动找最近可走格”策略。

通过后 `0x121492c..0x1214930` 调 `0x11f8800`，该函数逻辑x乘 `0x2923784` 的1.5，调用actor虚表+170；原actor表 `0x2462544+170=0x652a40` 再进入 `0x6bc2f0`。该层由path+4 factory获取World和query，把path+48实例mask写query+c；目标投影x除1.5，取得逻辑起点后调用 `0x6138d0`。当前未执行完整 actor/角色/鼠标链，亦没有恢复鼠标输入本身。

原 `0x1212080` 是服务器位置纠正相关的另一套邻域流程，见既有重同步研究；不能拿它替代普通输入修正。父集成当前发现部分原portal目标在状态0的mask1下阻挡，本文只证明kernel/wrapper会失败、上层可能另行修正；没有证明那些portal真实会进入哪条修正分支，不改其原坐标、不以研究结果绕过地图权威。

下一处精确待裁定是：在原 `12143b0` 的正常角色对象及Scene查询条件下，给定阻挡目标，最终传给 `11f8800` 的实际逻辑坐标及失败返回。完成这项前，只能使用现已执行的两层ABI作为离线规划证据，不能宣称完整点击导航已恢复。
