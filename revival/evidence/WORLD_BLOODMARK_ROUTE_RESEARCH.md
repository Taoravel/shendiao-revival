# 嘉兴血手印32像素接近条件：原地图无合法终点

2026-10-23。本批 `client_verified` 地图与原指令研究；实际所有者流程只用临时SQLite库复现失败，不启动GUI/服务/战斗，不改变任务、坐标、半径、mask或任何生产/shared/政策文件。

## 结论

自然前缀得到权威起点 **`(1006,360,2264)`**。原血手印 NPC10498、placement13在 **`(1668,970)`**。普通state0→mask1下，以NPC为圆心、半径32的全部 **3209个整数逻辑像素均阻挡**。因而指定的32条件不存在任何合法整数终点，不能靠增大搜索预算、换采样点、改A*或连通算法恢复这一见证。

全图最近clear像素为 **`(1668,1008)`**，距离严格38（平方1444），格`(104,63)`，属于起点的44928格四向clear分量。该格中心`(1672,1016)`距离平方2132，是源分量距NPC最近的格中心。原客户端kernel+pixel wrapper确实能从起点找到该附近区域，因此也不是源区与附近道路整体断连。

本批不据此修改交互半径或NPC落点。需要另行证实的精确输入缺口是：**原NPC接近/点击/任务交互判定是否允许角色停在距该原placement至少38的合法像素，并如何选择停靠点**。本次32来自调用者明确实验参数，原NPC业务半径尚未在本批核验。

## 红色复现与起点来源

新独占 verifier `verify_world_bloodmark_route.py` 创建全新临时库，按现有 `verify_prologue_touch_runtime.check` 执行自然 intro/master/weapon/equip/cart/Jiaxing/100160 前缀与其显式pending-edge恢复。只在该模块的 `check_birth_site` 调用Seam加入进程内只读捕获并委托原函数；没有改旧脚本或手工推进到血手印。

捕获位置在原集成代码读取 `source=owner.position.value`、断言100106 active之后，实际路线调用参数记录为：

```text
source=(1006,360,2264)
NPC10498 placement13=(1668,970), direction4
state_byte=0, interaction_radius=32, max_visited=100000
BirthSiteCheck(status='no_witness', visited=44928, movement_mask=1)
```

该集成assert确实失败，被新verifier精确捕获为预期红信号；后续研究只分析几何，不执行血手印菜单/提交/传送或战斗。`natural_source_reproduction`保存上述值，`prefix_script_sha256`固定本次读取旧脚本的版本。临时库随退出销毁，不读写真实账号库。

## 新读原地图与穷举

本批重新读取原 `runtime/client/artres/map.pfs`：

- `map_1006_jiaxing/maze.dat`：版本12、384×296字节格，CRC通过；与现只读 `maze_grids()[1006]` 完全相同。
- `map_1006_jiaxing/map.rmp`：CRC通过，原render尺寸9216×4736；逻辑地图6144×4736，与16像素maze覆盖一致。x投影1.5不得把原render宽9216误当逻辑宽。
- 每个entry的SHA256、原映像SHA256均在结果JSON中；本批未改地图文件。

穷举所有113664格中的mask1 clear格，共51277格；计算NPC到每个格的**闭整数像素矩形**`[16x,16x+15]×[16y,16y+15]`的最短平方距离，不使用格中心近似。全图最小值1444即38²，唯一最近像素`(1668,1008)`。这独立证明32²=1024范围内没有clear格矩形的任何整数像素。

同时枚举圆内全部3209整数点，clear数量0。每一个被圆覆盖的格还选取圆内代表点，以原 `6284f0` 查询验证mask1返回阻挡；代表格与实际点及原byte记录在 `circle_native_cell_representatives`。原查询指令`628524..628535`直接读取grid byte并与显式mask按位与，故同格其余圆内点与代表点一致。并核验最近合法像素的原查询为clear；不凭字节频率推定通行。

源格`(22,141)`四向clear分量为44928格，和旧采样搜索访问数相同；分量排序后坐标SHA256在JSON。这不是仅凭计数宣称任意两种搜索visited集合完全相同。这里判定“32内无解”依赖全圆/全图最短距离穷举，与任何搜索visited集合无关。

## 原kernel、pixel wrapper与DDA见证

诊断目标取全图最近clear像素`(1668,1008)`，**明确超出半径32，不是请求条件的成功替代点**。原 `6138d0` mode0、两distance limit0执行真实maze、原kernel6212f0、原顺序压缩61bc60，返回0；展开773节点，调用kernel一次。原输出float路径：

```text
(1032,1560), (1672,1016)
```

当前 `find_pixel_path` 显式预算113664 expansions/nodes、10000000 samples得到相同完整有序points与773展开数。只做这一必要差分，没有重复数百随机例。原wrapper在需绕路时输出终格中心，未自动保留精确请求点，故精确最近像素最后一小段另作原DDA查询，不能冒称原wrapper额外输出。

完整诊断折线：

```text
(360,2264) → (1032,1560) → (1672,1016) → (1668,1008)
```

三段均实际执行原 `626b40`，返回0；每段完整原6284f0采样坐标、code、首尾均保留在 `diagnostic_nearby_witness.original_DDA_segments`，并与当前port的 `maze_segment_result`一致。前三个点包含原wrapper路径；最后一段是明确标注的额外诊断几何见证，不是实走或发送的移动报文。

反事实：从自然起点直接连到最近clear像素，原DDA返回1，`direct_source_to_nearest_DDA`保留完整被阻挡前采样。该区域可绕行，不可将直线或手工瞬移当成已经到达。

此完整见证只证明可到NPC附近的合法区域；`radius32_witness_exists:false`始终保持，未改变实验半径。也不宣称原鼠标点击这一阻挡NPC点时会自动选择同一终点。

## 方法、Adapter与边界

research：本窗口作为后台研究者，只追原PFS/原映像与当前自然流程source，独占Markdown交付。diagnosing-bugs：先用同一临时库prefix复现红，再按“采样假阴性/分量断连/目标圆无clear”三假设逐项验证；结果是第三项。codebase-design：在原诊断函数调用Seam只捕获入参，不改owner/运行时Interface；原指令宿主Adapter与规划证据分开记录。

原执行基于冻结的 `NativePath`，本新verifier仅把maze buffer移到0x5800000，避免完整113664字节地图覆盖旧小fixture的workspace；原query/workspace/heap/codec控制逻辑不改。原查询、kernel、pixel wrapper、DDA均实际执行；宿主Adapter沿用分配/free、memset/memcpy、security cookie，离线指令预算显式提高到20000000以覆盖完整图压缩采样，不是原游戏搜索政策。旧2000000预算初次运行在628500耗尽，未把这一测试预算失败当作原寻路失败。

未覆盖：真实客户端GUI/实走、原NPC点击与接近半径业务、浮点actor起点量化preimage、其他移动状态、战斗与真实库。没有改mask8、扩大半径、挪NPC、伪造传送或推进血手印任务。

## 重现

```powershell
& C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -B revival/verify_world_bloodmark_route.py
```

已实际运行，约11秒：先输出相同自然source与no_witness44928，再输出`all_passed:true`、`radius32_clear_pixels:0`、`nearest_clear_distance:38`及两原wrapper拐点。最终生成独占 `evidence/world-bloodmark-route-verification.json`。`all_passed`指研究断言通过，不表示半径32路线可通或自然剧情已打通。
