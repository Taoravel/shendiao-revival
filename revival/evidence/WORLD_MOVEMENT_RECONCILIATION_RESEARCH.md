# 本地主角位置纠正与重同步：原客户端1.6.1离线研究

2026-10-23。采用research逐项追溯第一方原映像，diagnosing-bugs以相同对象/报文的单变量门控、真实位置写入和队列快照构成确定反馈。实现保留只读研究Seam，没有改world_movement、world_owner、任何共享入口或玩家状态，没有启动/操作客户端、GUI或服务。

**没有找到一个可以无条件“纠正主角坐标并清空所有本地规划/历史”的已验证消息。SRoleMove会纠正后尝试继续旧目标；SSetRoleLocation会重设主角目标并清引擎未来队列，但没有清角色侧旧history；SRelocateRolePos只要求客户端报告位置；SRoleStop在本映像是空处理器。** 不能将其中任一项直接命名为完整服务器重同步屏障。

复现入口 [verify_world_movement_reconciliation_native.py](../verify_world_movement_reconciliation_native.py)，结果 [world-movement-reconciliation-native.json](world-movement-reconciliation-native.json)，[原指令摘录](world-movement-reconciliation-native-disassembly.txt)。本批23个handler/状态案例与5个原codec案例通过；原映像SHA256=`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。

## 下行消息、原布局与实际用途

|原消息|type|原body|原Process|本地主角行为|
|---|---|---|---|---|
|SRoleMove|0xc0fa2|BE q64 roleID + BE signed16 x,y|0x11d7fc0|经过模式/角色flags门控；写位置后调用继续旧目标流程|
|SSetRoleLocation|0xc0fa4|BE q64 roleID + BE signed16 x,y + byte|0x11d7a20|主角专用vt+184重设位置/目标及状态；byte仅值1转true|
|SRelocateRolePos|0xc0fbb|空body|0x11c9f90|请求主角回报CRelocateRolePos；不直接提供或改写坐标|
|SRoleStop|0xc0fab|BE q64 roleID + BE signed16 x,y|0x11c56c0|原字节c2 08 00，仅ret8|

SRoleMove/Stop既有编码来源见 [WORLD_ROLE_PROTOCOL.md](WORLD_ROLE_PROTOCOL.md)。本批新增SSetRoleLocation原构造0xdad6d0、marshal0xe50f60、decoder0xdad780；flag0/1/2逐一原编码和解码通过，13字节布局分别保留原flag。它的byte不是场景世代、位置版本、允许忽略碰撞或“强制纠正”标志：原handler只比较是否等于1，再把布尔值传入角色状态setter。

## SRoleMove：本地额外门控，纠正后可能继续旧目标

Process0x11d7fc0首先要求Scene global0x2944564和主角global0x294454c存在，再按包中roleID调用0x11d5330查Scene玩家表。非主角走既有vt+0xb0目标移动分支；本地主角另外执行：

1. 0x11d8035调用0x806ba0：世界对象global0x2944798的+0x54非0，或App0x2945060的byte+0x1ed非0，均忽略消息。
2. 三次0x1202bd0分别检查角色+0x214是否包含0x10、4、8；任一存在即忽略。该函数就是按位AND后转布尔，不能把所有非0flags都拒绝。本批单改flag1仍执行纠正。
3. 通过后0x11d8135调用0x1212080(x,y)，随后0x11d8140调用0x1217460。

0x1212080先以角色vt+0x134读取角色+0x50作为maze mask，与Scene原0x11c5c00查目标flag。如果目标被该mask命中，会遍历原邻域偏移调用位置setter；函数结尾仍会调用vt+0xc8设请求点。本批只执行清目标分支，没有把该邻域循环解释为可用于服务器的容差或安全寻点算法。

vt+0xc8=0x11f6480，将逻辑X×1.5按原±0.5转整数，再经vt+0xcc=0x11f6120设置actor。后者另有角色vt+0x158/+0x15c状态门控和渲染范围处理；actor+0x34函数0x6526f0会清引擎+0x38、+0x20、+0x2c队列，再写投影float位置。该链的坐标转换、原队列清理和位置写入均执行原指令，本批没有用宿主代码代写“纠正成功”。

0x1217460并不等同取消移动：它检查角色+0x3e6、+0x36c、+0x3a0和当前点对+0x328/+0x32c目标的关系；满足继续条件时调用0x12143b0重新规划旧目标。fixture把当前/规划起点设(8,8)、旧目标(56,56)，收到纠正(100,100)后原current getter返回(100,100)，而原继续分支确实请求`12143b0(56,56,0)`。本批在A*入口捕获该请求并返回成功，**没有执行这次A*或声称用户再次点击**。

九组单变量案例涵盖正常、Scene缺失、主角缺失、世界+54、App+1ed、角色flags0x10/4/8/1。正常和flag1会改坐标且请求继续旧目标；其余七种忽略。由此不能用“向自己广播SRoleMove”作为无条件取消本地输入/规划的方案。

## SSetRoleLocation：重设目标，但不保证清全部本地历史

Process0x11d7a20只先要求Scene存在、按roleID查角色成功，然后对本地主角虚调vt+0x184=0x1213b80。与SRoleMove不同，没有直接调用0x806ba0或检查+0x214的0x10/4/8；本批分别改变这些模式，依然进入位置重设。

0x1213b80实际行为：

- 两次经vt+0xc8执行位置设置，继而把`packet.byte==1`交给vt+8=0x1205c80。该原setter写角色byte+0x218。本批flag0/1/2分别得0/1/0；byte+0x218与原mask选择有关（0→1、非0→8），所以发送方必须提供已知权威状态，不能把未知字段随便填0来“强制落地”。外观/速度辅助更新在fixture中适配，不把该部位的显示结果当成已实测。
- 更新+0x328/+0x32c旧终点、+0x358/+0x35c前瞻、+0x364/+0x368及+0x1b8/+0x1bc到请求坐标，避免SRoleMove那样直接继续旧目标。
- 调用0x1203470、0x120b6f0重设角色字段，其中后者清+0x13c及相关临时坐标/状态；随后有动作/地图UI/镜头辅助更新。
- 真正actor位置setter清空**引擎**未来+0x2c队列；这与主角自身的+0x340未来拷贝和+0x34c待上报历史是不同对象。

fixture在纠正前放入引擎未来[(56,8),(56,56)]、角色+340同序列、+34c历史[(8,8)]。纠正到(100,100)后，原引擎未来为空，原current及+328/+358为(100,100)，**角色+340仍保留旧未来拷贝，+34c仍保留[(8,8)]**。再执行原完整CHECK builder，实际发送history[(8,8)]、current(100,100)，发送后才清history。本批没有另发包、手动清列表或按坐标猜测该history已经失效。

因此，服务端收到纠正后的报告时，不能默认history全部发生在新权威坐标之后。原消息没有新增correction epoch或ack字段；本研究不制定丢弃、冻结、宽限等反作弊政策，也不建议靠重算连接旧history到纠正点拒绝客户端。若要恢复专门的重同步生命周期，需要独立的版本/Owner设计和更多原业务证据，不能只因这个位置包已发出就宣称客户端清理完成。

**还有更深的状态限制。** 即使SSetRoleLocation Process没有上述广播门控，内部位置setter仍会在vt+0x158或+0x15c返回true时不写actor。原vt+158=0x1203da0（依赖+2c0/+2c4、+1e8等），vt+15c=0x1203e30（依赖+2cc、+1d0）。单改+2c0=1或+2cc=1的原fixture中，actor仍在(8,8)，但主角目标字段已经改成(100,100)。这些状态的完整玩法枚举未证实；不能将“Process命中主角”当成实际位置已纠正。

## SRelocateRolePos：服务器请求位置回报，不是下发坐标

RTTI vt0x2279170，原ctor0xdabe80写type0xc0fbb，marshal0xdabea0和decoder0xdabeb0都是空body。Process0x11c9f90仅在主角存在时调用0x1212890。

该函数原构造发送 **CRelocateRolePos 0xc0faf**，vt0x2278f20，原ctor0xdaa6b0、marshal0xe50770、decoder0xdaa7a0，body为 **BE u64字段 + BE signed16 x,y + byte**。首字段从Scene+0x30/+0x34复制；本批只称该原u64字段，不推定单位、单调性或可作为请求ID。

原回报分支已执行：

|主角+0x13c|位置来源|状态byte来源|本批fixture输出|
|---|---|---|---|
|0|原current getter|主角vt+4 getter转布尔（关联+218）|(8,8)，byte0|
|1|角色+0x150/+0x154|+0x3d6转布尔|(31,32)，byte1|
|2|角色+0x158/+0x15c|+0x3d6转布尔|(41,42)，byte1|
|3|无匹配分支|不发送|无回报|

这说明它可能适合恢复“请求客户端报告当前状态”的原协议入口，但请求本身不会清引擎、本地规划或history，也不会使客户端服从服务器指定坐标。特殊分支报告的是保存坐标，不一定是此刻渲染actor的位置；不能把所有0xc0faf都按普通current处理。

## 实现边界、证据和未验证范围

23个handler/状态案例与5个原codec案例通过，均使用本地映像离线执行。原角色/消息虚表、广播模式门控、flag判定、逻辑与投影转换、actor setter及引擎队列清理、主角目标字段更新、原current getter、真实CHECK与CRelocateRolePos构造执行原指令。

Adapter范围完整列于JSON：内存和安全cookie；Scene角色ID/同伴查找；固定渲染范围与空地图flag；文字/日志；UI地图提示；动画资源/动作和镜头偏移；速度/外观辅助；重寻路入口捕获；网络发送捕获。fixture未证明这些外部系统的真实画面或原A*重新规划成功；保留原+340/+34c的数据观察不能扩大成“所有复杂动作中永远不清理”。

本批未接入任何生产协议、Owner或数据库，没有定容差、放一格墙、发布速度/反作弊政策。尚未验证：真实服务器纠正触发规则、纠正与报文在途顺序、复杂骑乘/跟随/跳跃状态、阻挡目标邻域搜索、真实GUI/相机/输入释放、跨图旧包和客户端确认。原量化误拒的既有反例仍有效，见 [SCENE_GRID_PROTOCOL第五批](SCENE_GRID_PROTOCOL.md)；本报告没有重新启用已撤回的严格整数段拒绝。
