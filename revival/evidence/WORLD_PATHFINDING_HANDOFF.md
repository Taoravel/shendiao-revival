# 世界寻路：原网格核与有界像素路径

2026-10-23。`world_pathfinding.py` 提供纯规划 Module：原6212f0网格搜索，以及原6138d0在第3/6/7参数均0、非负整数逻辑像素输入下的DDA捷径与完整顺序压缩。当前没有生产调用者、共享接线或发布；它给出规划结果，不推进角色、不证明客户端已走过路径。

## 调用 Interface

```python
find_grid_path(grid, start_cell, end_cell, *, mask, max_expansions, max_nodes)
find_pixel_path(grid, start_pixel, end_pixel, *, mask,
                max_expansions, max_nodes, max_samples)
```

grid必须是启动加载的不可变完整SceneGrid，bytes长度为width×height，无稀疏present，两个维度1..1920。mask显式byte；预算显式正整数，bool不当整数接受。点为两个int组成的tuple；网格入口在格边界内，像素入口非负且小于width×16、height×16。输入不合法抛ValueError。原maze格边长16，X使用乘1.5之前的逻辑像素；这里不读取客户端actor或把报文integer伪装成原float。

| 输出 | 内容与语义 |
|---|---|
| GridPathResult | 冻结的status、path、expanded_nodes、discovered_nodes。found的path排除源格、包含目标格；same_cell、blocked_goal、not_found、budget均无路径。budget只代表资源不足，不是不可达 |
| PixelPathResult | 冻结的status、native_result、points、expanded_nodes、discovered_nodes、sample_budget_used。原返回0为found、1为搜索失败、2为无输出、3为same_point；预算不足status=budget、native_result=None、points为空，不伪装原失败码 |

像素入口先做原有向DDA。若直达，输出精确请求的end_pixel且不展开网格；同点返回3且不查该点阻挡。需要网格搜索时，输出节点取格中心 `(16*x+8,16*y+8)`，终点可能与请求像素不同。例如墙图请求(89,41)最终节点是(88,40)，而相同请求在清图直达仍为(89,41)。调用者需检查最终点是否满足业务距离，不把“目标格可达”写成“已抵精确请求点”。

像素输出只投影原节点的XY；没有把6-float里的高度/delta、actor速度/动画/客户端队列接线也称恢复。原fractional起点、其它第3参数、正第6参数、第7参数非0、局部查询矩形仍不属于此Interface的原生等价合同。

原码2为空输出分支；本批有效整数/参数0案例未触发它，不把保留该返回码写成已有动态覆盖。

## 原行为与工作预算

原核的八邻居顺序NW,N,NE,W,E,SW,S,SE，直/斜代价5/7，启发式`5*floor(sqrt(dx²+dy²))`。f-only heap保留等f不升、等f子节点选右；open只在g更小时原地上浮并做f差量更新，closed不重开。完整一轮八邻居结束才在目标state为open时回溯，目标通常尚未pop。该行为不等同通用A*的最优性承诺。

原网格核的对角邻居要求两旁正交格清；原像素wrapper的DDA捷径在某些角点仍能直达。实现分别保留两层，不加统一“禁止切角”。压缩从source作anchor，顺序检查后继格中心；原DDA遇阻才输出previous并更换anchor，最后输出末点，不是从路径末端向前找最远可见点。原长路径≥25在本合同的参数0下也处理完整路径，未截成24格兼容子集。

预算是调用方设计的保护，不是原版服务器数值，也没有生产默认：

- max_nodes限制存储的已发现节点总数，包括source；达到后不分配下一节点。
- max_expansions限制实际pop/展开次数；达到后不再开始下一轮。
- max_samples在每次DDA前预留整段主轴长度。即便墙可让实际查询提前结束，也计入全长，所以它是实际采样数的保守上界，不是测量出的真实采样数。余额不足时不执行该段、不输出已经压缩出的半条路径。

内存随max_nodes有界；搜索工作由展开/节点预算限制，DDA由采样预算限制，另有对最多max_nodes个路径节点的线性整理。没有I/O、全服队列、全局可变缓存或等待其它所有者。这里没有测商业容量或硬实时截止；生产预算、调度和满载响应仍由主策划/共享入口明确。

## 地图接入与所有权

在地图执行者上，以当前MapAddress/role_id/login_epoch/Location.version及可信原生移动状态选择grid/mask，先核world_catalog实际RMP边界和源节点，再调用规划。原查询grid可覆盖RMP边界之外的padding，因此也需核每个输出点/业务区域。若把纯计算移出所有者，传冻结输入，返回后重新核同一位置版本/租约/实例再使用结果；旧规划不能推进新登录。

原kernel允许从阻挡源格向清邻格出发；原DDA不采样起点且同点返回3。本Module保留这两个已验证行为，**调用者必须独立验证权威源点**。规划成功只是空间建议，不能用来授权任意客户端history、ROLE_MOVE两个点之间的直线、速度、到达奖励或NPC任务证据。报文current/初始history/到达history三种producer与量化问题见WORLD_MOVEMENT_QUANTIZATION_INTERVALS，普通CHECK不能靠此直接开启严格整数重连线拒绝。

地图位置/view仍统一走WORLD_MAP_VIEW_HANDOFF的配套命令。规划结果没有地图状态副作用、SQL或投递；其冻结节点能交给可信AI/导航调用者，但不会替调用者提交位置。第3/6/7为0是已验证的原算法分支合同，不给全部特殊玩法暗设默认；实例/角色模式和生产容量需明确来源。

## 已执行验证

| 入口 | 实际证据 |
|---|---|
| verify_world_pathfinding.py | 11组公共行为。网格方法缺Module先红→实现绿；像素方法缺导出先红→实现绿。随后追加清/墙/无路、原blocked-start、目标阻挡/同点、mask、角点层次、节点/展开/采样预算、无半路/重试、非法输入和无文件访问 |
| verify_world_pathfinding_native.py | 固定seed601的320组真实原核随机完整maze。逐项比成功/失败、完整顺序路径、展开节点数，全部一致 |
| verify_world_pixel_path_native.py | seed1601的180组随机像素，加长墙/交替长墙/DDA角点/同点/非中心直达共185组。与原wrapper比返回码、全部压缩XY、展开数，全部一致，包含≥25节点的长路径分支 |
| verify_world_birth_pathfinding.py | 对真实PFS maze、43角色/门派组合的10处设计出生点，规划到先前独立验证的师父接近点；每条原DDA段/节点清、最终点在现行设计32像素半径内。不是原完整地图emulator或真实客户端行走 |

原依据另见WORLD_NATIVE_PATHFINDING_RESEARCH与WORLD_PATH_KERNEL_PORT_NOTES。研究后台实际原函数全扫7,365,123个距离值，普通0..1919格域内isqrt差异0；父读取执行源/机器摘要，并另独立跑66个边界/随机原距离、40更新/4终止/2压缩/2长wrapper案例，没有声称父又重复全扫736万次。所有原算法/heap/DDA执行原指令，Host Adapters仅为内存/CRT和明确观察边界。

当前文件：world-pathfinding-verification、world-pathfinding-native-verification、world-pixel-path-native-verification、world-birth-pathfinding-verification。没有改已有MapOwner/传送/新手政策/共享入口或运行服；本批新增独立Module与验证、文档，不将新模块未接线状态藏在离线通过之后。

## 上层阻挡目标与剩余完成条件

WORLD_BLOCKED_GOAL_ADJUSTMENT_RESEARCH新增23例原12143b0入口研究，父独立复跑通过：阻挡目标使用16像素象限半环候选，当前点阻挡使用1..8像素八方向局部source，区域byte同值是第三阶段。局部source变化不写actor，11f8800只收到goal；到达这个入口不证明路径可达。未将该上层角色/Scene上下文或区域表接入本Module，也未自动改9组原阻挡portal或家园/同图入口。

后续仍需：原高层条件与实际actor/规划缓存衔接、可信规划/量化轨迹和特殊移动状态、共享运行时/连接发送前围栏、预算政策、特殊图/传送、两缺资源、NPC/怪物导航与真客户端输入/显示/跨图验收。完整世界目标继续active。

方法：codebase-design用两条纯Interface隐藏原heap/搜索/压缩；tdd在上述两个新方法实际红→绿，差分与真实资源为补充验证；research后台追原公式、内联更新/结束分支及上层修正，直接改变实现中的等序/压缩/目标中心语义；writing-for-agents把调用、预算、所有权和未完成条件放在一处。
