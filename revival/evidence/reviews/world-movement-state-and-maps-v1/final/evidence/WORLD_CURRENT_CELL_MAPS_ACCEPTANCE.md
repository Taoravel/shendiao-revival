# 原资源302图：显式current-cell逐图校验

2026-10-24。既有Planner／MapOwner公开Interface不变；本批只新增`verify_world_current_cell_maps.py`及研究／验收证据。共享入口、政策、线上服务和真人存档未改。旧302加密运行时报告绑定修改前模块，本页是修改后显式`native_current`领域校验，二者分开。

## 实际执行范围

从项目根执行`python -B revival/verify_world_current_cell_maps.py`，报告`world-current-cell-maps-verification.json`：302个available地图、1208组显式state0/1/2/255夹具、5039次公开MapOwner命令、3656次原`6284f0`点查询通过。每图fresh读取原PFS maze并校验长度／CRC，与启动冻结网格逐字节对照；完整map.pfs和实际加载源码／catalog／原映像前后SHA一致。1302/1307原资源仍缺失。

每个原flags byte选择一个地图范围内、非portal的格心代表点；没有代表点的flags单独记录。原映像`2b49e95d…`在独立模拟器执行真实`6284f0`，完整原dense grid与query布局由夹具安装，没有host替代该函数的clear/blocked返回。不是逐像素穷尽，也不执行原地图引擎加载或渲染。

状态是明确离线夹具，mask0-state→1、非零-state→8沿原getter/selector研究；不根据地图ID或玩家报文建立可信生产状态。地图实际允许的每种flags以原点查询作为oracle，再调用真实MapOwner显式Interface检查：

- 存在合法代表点时，STOP可提交该点，版本前进且没有portal offer。
- 存在阻挡代表点时，STOP与CHECK均拒绝，位置／版本／checkpoint／offer保持；MOVE指向该点仍只是意图，不会到达。
- 人工history含阻挡整数但current在合法格时，只按current判定；这项只验证字段选择，不声称该人工轨迹由原客户端自然产生。
- 负坐标继续被bounds拒绝，包含原查询对负坐标向0截断可能与服务器bounds不同的情形。

## 不能制造不存在的正例

原1012等233张图在本次非portal、范围内的全部原flags类别中，没有mask8合法代表点。保留这个结果：对应state1/2/255只做阻挡和bounds拒绝，以明确的受控初始位置夹具建立Owner，不冒称已建立合法源或自然进入该移动状态。所有302图都有state0合法对照，总合法对照509组、阻挡状态组1180组；9图某些状态没有阻挡代表点，报告明确不计相应负例。

初版脚本错误假设每张图每种state均有合法源，跑到1012触发StopIteration；这是验证夹具错误。修正为如实区分“无合法对照”和拒绝检查，没有修改原图、状态规则或生产逻辑。不能据本页推定任意state适用于任意地图。

## 故障敏感性与接线前提

`--maps 1006 --fault-clear-walls`只在独立Owner依赖中清除对应mask，原oracle仍用未修改PFS；真实墙内STOP错误被提交为version3，安全断言准确exit1，`world-current-cell-maps-fault.json`在异常前保存实际输入／报错。不修改生产、原网格或原映像，不将这次人为故障算作新的游戏缺陷。

生产仍需唯一main按`WORLD_CURRENT_CELL_COLLISION_HANDOFF.md`注入原maze和对应角色／地址／版本的可信状态。后续状态研究见`WORLD_MOVEMENT_STATE_TRANSITIONS_NATIVE.md`：原JumpStop会再次转换状态，报告byte不能直接当最终state；特殊1404／reason516023、未知生命周期仍须分别处理。本页没有把显式state夹具改成共享常量。

方法：diagnosing-bugs用实际拒绝与清墙故障建立可变红反馈；codebase-design继续从公开MapOwner／冻结命令Seam验证，不增加生产Interface；research以原映像函数和fresh原档作独立oracle；writing-for-agents将正例缺失、真实运行时红例和接线条件共置。双轴固定审查另见`WORLD_MOVEMENT_STATE_AND_MAPS_REVIEW.md`。未验运行时新接线、连续轨迹／速度、自然地图资格、真实跳跃授权、特殊传送、NPC隐藏／朝向、完整新手流程、GUI或怪物战斗。
