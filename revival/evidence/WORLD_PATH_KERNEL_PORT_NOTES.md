# 原生寻路移植核对：距离、节点更新、终止和压缩

2026-10-23。本批按 research 直接追原映像，作为已委派的后台研究执行；重读根约束、ARCHITECTURE、DESIGN_AUTHORITY。方法对实际决定的影响是：不以常见 A*、math.isqrt 或通用平滑算法作为原规则，先执行相应原分支，区分可等价替换域和未知选项。本批不改生产 `world_pathfinding`，不改冻结的18例 verifier，不操作游戏、GUI、服务、运行进程或存档。

第一方映像 [native-image.bin](native-image.bin) SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。独占复现 [verify_world_path_kernel_port_native.py](../verify_world_path_kernel_port_native.py)，[机器结果](world-path-kernel-port-native.json)，[原指令摘录](world-path-kernel-port-disassembly.txt)。前一批完整ABI和18例见 [WORLD_NATIVE_PATHFINDING_RESEARCH.md](WORLD_NATIVE_PATHFINDING_RESEARCH.md)。

## 0x5f87e0：普通网格域内等于floor sqrt，已穷举

原kernel要求 width、height 不超过1920。在完整地图合法格坐标0..1919内，任意两点的 `n=dx²+dy²` 在 **0..7,365,122**。本批逐一向未修改的原 `0x5f87e0` 传入该区间的所有 **7,365,123** 个整数，不仅测试可由平方和组成的子集。

原函数返回值与 `math.isqrt(n)` **差异0**，与下述查表公式亦差异0。原结果按顺序打包little-endian u32所得SHA256为 `8ade27d20a692e5e61fbe6013554a1377bf30ec2dbc6505f1ecb82c42e9e8614`。因此，端口在上述合法坐标域内可使用整数平方根向下取整等价替换；不是任意u32输入全域证明，也没有允许越界/负查询矩形。

原表 `T` 是映像 `0x2461268` 起256个byte，完整hex保留在JSON。原普通域公式为：

```python
if n < 0x3fd:
    guess = T[(n + 3) >> 2] >> 3
elif n < 0x3fe4:
    guess = T[(n + 0x1c) >> 6] >> 1
elif n < 0x10000:
    guess = T[n >> 8]
elif n < 0x100000:
    seed = T[n >> 12]
    guess = ((n // seed) >> 3) + 2 * seed
else:  # 本合同 n <= 7365122，低于下一原生分支阈值0x1000000
    seed = T[n >> 16]
    guess = ((n // seed) >> 5) + 8 * seed
result = guess - int(n < guess * guess)
```

`0x5f8ac0` 和四个直邻居内联段使用 `f=g+5*result`。原启发式是欧几里得整数距离，不是曼哈顿/八方向代价公式。本批不据此保证最短路；原算法还有提前终止及closed不重开，不能为追求“标准A*”而替换。

距离验证无库函数 Adapter。仅有明确公开的14字节x86批量调用driver：加载ECX，call原函数，保存EAX，推进输入输出指针。driver本身不计算距离。每批65536项，断言全部调用完成；原函数仍读取原映像查表。JSON保留driver bytes。

## 8方向节点处理：40个原分支反事实

沿用原节点 `parent+4, g+8, f+c, state+10, heap_index+14`。在八个方向的真实邻居已通过碰撞且取得node之后，分别执行到该邻居处理结束边界。每个方向分别设置 unseen、open更小g、open等g、open更大g、closed更小g，合计40例。不是宿主重写分支，也不是仅观察原helper：八份内联代码均实际执行。

|方向/代价|原执行slice，终点前停止|
|---|---|
|NW / 7|6214e9 → 62153f|
|N / 5|621598 → 621628|
|NE / 7|62170c → 621768|
|W / 5|6217bd → 62184d|
|E / 5|6218a2 → 621932|
|SW / 7|621a12 → 621a6e|
|S / 5|621ac3 → 621b53|
|SE / 7|621c51 → 621ca7|

八份一致的精确规则：

1. `state==2` 立即跳过，**不重开closed**，即使候选g更小也不改parent/g/f、也不入堆。
2. `state==1` 计算 `candidate_g=parent.g+cost`。原signed比较 `candidate_g >= old_g` 则跳过，等g不改parent。
3. 仅open且更小时，写 `f += candidate_g-old_g`、`g=candidate_g`、`parent=current`。**不重算h、不删除重插、不增加重复堆项**，直接调用原 `0x5f8e50` decrease-key。
4. 其它state进入初次发现路径，写parent/g/f、state1，然后原heap push。正常数据该状态为0；不把异常枚举也作为生产可接受输入。

fixture把已有root f48、child f50/g20放进真实原heap。新g为15/17后，child f45/47，通过原decrease-key移到根；child.heap_index由1变0、旧root由0变1，heap size仍2。等g、更大g不调sift；closed保持不在heap中。unseen使用真实helper/内联公式得到g15/17、f55/57并正常插入。

`0x5f8e50` 从node+14的旧索引向上走：父索引 `(i-1)//2`；父f<=当前f就停止（`5f8e90..93`），否则将父指针移入子槽并更新父index，最后安装当前指针及新index。不能用remove+append来替代，因为等f不再保持同一heap形状。原pop的等f左右子选择仍见前一报告，不能改成常见的 `(f,g,x,y)` 排序。

这些fixture只隔离“已取得合法邻居后的更新段”，没有用合成node坐标重复证明邻居碰撞。本批继承18例工具的allocation/free、cookie、memset、memcpy Adapters；原heap、heuristic、状态写入和上浮均未替代。边界观察hook只在下一段入口停止，不代写结果。

## 终止：处理完本轮八邻居后，goal.state恰为1即回溯

`0x621ca7..0x621caf` 取保存的goal指针，比较 `goal.state==1`；否则跳回 `6213b0`。对state0/1/2的三个原slice测试分别进入继续搜索/回溯成功/继续搜索。

完整清图kernel额外执行确认：最后pop是(4,2)，g15/f20；goal(5,2)已push但从未pop；在goal push之后原代码仍push了(5,3)，g22/f27，然后才进入回溯。因此准确移植应当在**完整一轮邻居更新结束后**判定目标open，不能“目标第一次被发现就break邻居循环”，更不能改成“pop到goal才成功”。后者会改变预算与展开数，即使最终路径偶尔相同。

原 `62139d` 显式设置起点g0后入heap。新fixture首pop观察f0，但原初始化段没有同样显式写起点f；起点是heap唯一节点并立即pop，不能因隔离分配器初值0而额外声称真实池内起点f总为0。有效搜索中的其它新节点f均按上述公式写入。

本段合计4例，未覆盖分配失败或最大地图搜索性能。原无请求budget结论与宿主保护的区别保持前一报告：父模块显式 `max_nodes/max_expansions` 属有界实现的设计约束，不能写成原版数值。

## 61bc60短路径压缩：顺序DDA前缀，不是反向最远可见

原ABI：`ESI=grid_list, EDI=float_list, EBX=最多处理的grid节点数`；栈参数 `query,start_6float`，ret8。`61bc60` 在grid非空且float输出仍为空时调用 `623c00`。`623c14..21` 对EBX<=0或超过剩余size时改取整个剩余list，否则只取指定前缀。

`623c00` 的可移植步骤：

1. anchor取start的位置；previous取首grid节点中心 `(16*x+8,16*y+8,0)`。遍历从第二grid节点开始，至所选前缀末尾。
2. candidate取下一个grid中心。若anchor与previous的(x,y)二元组不相等（任一分量不同），调用原 `626b40(anchor,candidate)`；float转点前加原常数 `0x243d95c=0.5f` 再cvttss2si。对于普通正整数中心不改变值；其它float取整域本批未全扫。
3. **只有DDA返回1**时，emit previous，输出六float `previous.xyz, previous.xyz-anchor.xyz`，再令anchor=previous。不把delta归一化；不从表尾回扫寻找更远点，也不在更新anchor后重新检查当前candidate。
4. 无论是否emit，previous=candidate继续。结束时，若anchor与previous的(x,y)二元组不相等，再emit previous及delta。原调用随后移除已处理的grid前缀；未处理后缀保留。

本批两例直接调用原61bc60，不经wrapper捷径：

- 清图4格路径得到六float `(88,40,0,64,0,0)`。依次DDA至(56,40)、(72,40)、(88,40)，均0。
- 原绕墙6格路径：DDA由(24,40)依次至(40,72)、(56,72)通过，至(72,72)返回1，emit `(56,72,0,32,32,0)`；随后以(56,72)为anchor，检查(72,56)、(88,40)通过，最终emit `(88,40,0,32,-32,0)`。输入grid全部被原流程消费。

若使用宿主已有原DDA等价实现作压缩port，也必须保留其方向、定点偏置和角点捷径，不能额外换成supercover或统一禁止切角。本结论没有把任意不合法手工路径压缩解释成安全检查；首grid点到起点不会被这个循环重新独立验证。

## wrapper ≥25节点：第3参数兼作前缀上限；第6/7参数须保留边界

原6138d0在 `6139fe..613a03` 对搜索结果size>=25走另一分支。对原32×6墙图，起点逻辑(24,40)、目标(456,40)，搜索有27个grid节点，两次完整原wrapper执行均pop93个节点：

|第3栈参数|第6参数|61bc60实际输入|原wrapper输出|
|---|---|---|---|
|0|0|size27, EBX0→全部|float[(312,72),(456,40)]，grid空，EAX0|
|1|0|size27, EBX1→首1节点|float[(40,40)]，保留余下26个grid节点，EAX0|

第3参数为1还会跳过最初DDA（`613903..61390a`）；<=0和>1会尝试初始DDA。因此前一报告的研究工具参数名 `mode` **仅是临时接口标签，不能作为它是纯枚举的证据**。长路径使用它作为grid前缀数量限制；短于25时原代码强制EBX=-1，不采用这一上限。未执行第3参数2及其它正值的完整wrapper，只能按静态分支解释其限制，不能声称业务意义全明。

≥25分支先 `613ac0..ca` 调 `61b8f0`，EAX=第6栈参数。第6参数0时 `61b8fd` 直接结束，不改grid；这是本批两例已执行的精确合同。第6参数>0的静态代码从list**尾部**取中心并删除（`61b91a`,`61b96b..73`），比较相邻方向、计算段长度、减去浮点余量，必要时插入反向修剪后的点，最后涉及start 6float（`61bbdc..bc2d`）。该分支没有本批执行覆盖；不能仅因有sqrt就认定它是搜索节点预算或自选成普通前向截断。

短于25分支在61bc60之后还调用 `61b7d0`，EAX同样来自第6参数；<=0立即返回。这修正了前报告把61b7d0简述为“复制”的不准确标签：实际list转交使用后面的sentinel/size交换；61b7d0本体是有条件的进一步路径处理。第6参数>0时会从输出尾部处理距离及终点，未执行验证；第7参数非0还会在搜索后走 `615490`，本批未赋业务名或测试该选项。

因此可评审的最小wrapper移植范围是：明确限定第6、第7参数均0；区分初始DDA、<25完整压缩、>=25前缀压缩及剩余grid后缀；可先只公开第3参数0，以“未知选项不支持”作显式接口约束。不要为了返回目标就丢掉第3参数1实际产生的短前缀结果，也不声称已覆盖正距离选项或完整角色点击终点修正。具体生产接口由父模块决定，本研究不设置政策默认。

## 验证汇总与未验证

独占脚本通过：7,365,123次原整数距离、40个八方向状态更新分支、4个目标终止/完整kernel案例、2个独立压缩、2个完整长wrapper，共48个结构案例加全域距离扫描。生成证据包含所有数值与指令；未变更冻结的18例脚本或父模块。

尚未验证：第6参数正值、第7参数非0、负/非整数位置全域、完整角色输入终点邻域修正、分配失败、真实客户端整段播放及在线容量。不能将本报告的原算法执行证明写成生产接线或客户端实测完成。
