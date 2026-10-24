# 主角 +218 后续状态转换：原 JumpStop 与保留边界

本批使用 research 的第一方映像追溯、diagnosing-bugs 的单变量可变红反馈。已读根 AGENTS、ARCHITECTURE、DESIGN_AUTHORITY 与本批适用 SKILL；本代理作为后台研究者完成限定任务，没有继续委派。只新增本文及 `../verify_world_movement_state_transitions_native.py`，未改生产 Module、shared、政策、旧研究、存档；未打开客户端、GUI、服务或真实战斗。原表与原指令优先，没有自行制定状态默认值。

## 可以直接交接的事实

普通成功 `SRoleEnterScene` 的 A==1 归一赋值仍按 [WORLD_SCENE_MOVEMENT_STATE_RESEARCH.md](WORLD_SCENE_MOVEMENT_STATE_RESEARCH.md) 的37例与适用条件执行。**该状态不是永久值：原主角跳跃结束会根据结束位置的地图 flags 再选择 +218，也可能保留原值。** 这提供一个必须纳入后续生命周期的客户端消费者，不授权服务器无条件接收任意状态声明或把所有地图强行设0。

原 `1205c80` 是主角 vt+8，getter `1209d10` 为 vt+4；主角 vt=`2299344`，基类 vt=`2298bcc`，两者 +8 均指该 setter。它在 `1205c88` 比较旧 byte 与参数低byte，变化时 `1205c9d` 原样写入；**setter自身不归一为 bool**。原生测试直接传2/255即保留2/255；它们经原 mask selector `12028f7..120291b` 均选mask8，0选mask1。网络包的 A==1/flag==1 是各自 handler 的归一规则，不能移植为 setter 全局语义。

## 新执行的原 JumpStop 链

RTTI 原 vt=`2278fac` 的 COL/type descriptor 指向 `.?AVCRoleJumpStop@move@gsp@knight@@`。原主角函数 `12126d0`：

1. `12126f7..121270c` 经原位置 getter取当前位置，保存 role+3d6 到 BL。
2. role+284==0 时，`1212717..1212765` 在栈上构造 type=`0xc0fcf`，Pos对象+8（x/y在+0c/+0e），报告byte在+10，值为 **role+3d6!=0**，调用原发送虚槽。role+284!=0跳过这一报文构造；本批执行用+284=0。
3. `121276f..121279c` 更新主角目标+328/+32c；`121279d..12127a3` 调 Scene `11c5c00(x,y,8)`。
4. mask8检查返回0时，`12127ae..12127b5` 调主角 setter(1)。返回非0则 `12127b9..12127c9` 再查 mask1；mask1返回0时 `12127d2..12127db` setter(0)；两次均非0则不写 +218。
5. `12127dd` 清 role+3d6，正常返回。

Scene `11c5c00` 保留原体执行：engine getter→engine vt+48取得World→World vt+28取当前位置 byte flags，`11c5c21` 与请求mask按位AND，`11c5c25..29` 归一为是否非0。这里是 **flags & mask !=0** 的测试；本批不将其命名成地面/水面/可走或阻挡的最终玩法枚举。

| World原接口返回flags | 先查mask8 | 再查mask1 | 原最终 +218 |
|---:|---:|---:|---|
|0|0|不查|1|
|1|0|不查|1|
|8|1|0|0|
|9|1|1|保留先前值|

每行分别以 prior=0/1/2执行，共12例。所有分支均产生相同位置(8,8)、报告byte1（fixture +3d6=2）且随后清3d6，而最终 +218 可为0/1/2。因此 **CRoleJumpStop.byte并不直接报告该函数最终选择的 +218**。不能把byte1直接当作后续state1的服务端依据。该状态转换自身使用当前位置的原World flags，并与当前输入状态有关。

另外3例真实原 ctor=`daaab0`、marshal=`e507f0`、decoder=`daab70` 验证 CRoleJumpStop：body为 BE signed16 x、BE signed16 y、原byte，5字节；byte0/1/255逐字节往返通过。Pos(8,8)/byte1体为 `0008000801`。这只证明原客户端报告布局，未恢复服务器的受理/校验规则。生产接入需单独恢复跳跃授权与状态转换，不可凭该报告给客户端任意mask选择权。

### 可达上游与尚未执行的部分

对原映像 E8相对call扫描，`12126d0` 的直接调用位于 `120c2e0`。原 `120c2d0` 比较当前对象是否全局主角 `294454c`；主角走 `12126d0`，其他对象走自己的位置mask8判断和setter。它后续还清动画/动作状态；本批没有把后半清理适配成整函数已恢复。

`120c2d0` 另有原调用点：`120c3f0`、`120c44c`、`120c53c`、`120c97c`、`120ca38`。前几处在 `120c350` 事件消费者内，受事件参数2、角色虚槽+158/+15c、动作+20=26/27及+13c=1/2、终点相等和 `1203520` 分支限制；后两处在后续更新路径中，以 role+134 达到 `0x1194`（4500）为超时分支。这里只记录原比较数值，不认定 tick单位或完整跳跃时序已经执行。本批直接以公开完整 `12126d0` 为 Seam，**未执行整个起跳、动画、每tick推进至此的链**。

## 其他覆盖与保留点

* 原 `SSetRoleLocation` 0xc0fa4→Process `11d7a20`→主角vt+184=`1213b80`→vt+8=`1205c80`，flag严格等1才写1，否则写0，沿用 [WORLD_MOVEMENT_RECONCILIATION_RESEARCH.md](WORLD_MOVEMENT_RECONCILIATION_RESEARCH.md) 的真实23+5例；本批不重复其全部测试。位置setter可能被+158/+15c gate阻止，因此该包并非无条件完整纠正屏障。
* 外观/模型更新附近 `120d5cc` 先取当前byte+218传给虚槽+fc；另一支 `120d66d..120d67c` 读取当前byte再次调用vt+8。本批仅执行后一小切片，prior0/1/2均不发生状态写入，确认此处是保留/重应用，不是从包中建立新的默认0。前一支模型资源尚未重放。
* 基类位置/状态 setter `120c220` 的参数是x/y/state，`120c28f..120c29b` 取第三参数传vt+8；主角vt+184覆盖为1213b80，故不能把基类另一入口误称新下行协议。`120ba35..120ba41` 的另一更新分支也从栈上取旧调用参数传setter；未完成它的上游字段身份与全函数重放，不宣称是SEnterWorld wire状态。
* `SEnterWorld` 既有 Scene `11da3f8` 经创建/复用主角后虚槽+1b8=`120fb30`。本批读原 `120fb30..120fbad`：它设置ID、RoleDataManager getter结果、快照+28到role+1e8，并在actor缺失时经虚槽+fc创建外观，随后操作actor/World。其直接指令无+218赋值；但+fc模型创建会涉及更多虚调，**没有完整执行该链，不能把“直接未写”提升成所有间接消费者均保留**。
* 对1404或reason516023，原 Scene分支跳过本次+184赋值，随后 `11e272d` 调主角vt+b4=`1218000`。原1218000清+3e4，再按vt+b8判断调用1217f00/1206080；没有直接写+218。本批未重放1217f00及全部模型/actor副作用，仍不能为这些特殊分支建立新的可信0。

## 实际执行、Adapter和源码

运行（从项目根目录）：

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/verify_world_movement_state_transitions_native.py
```

首批实际输出 `all_passed=true, case_count=23`；本次纵切增加12例后最终为 **35例全部通过**，约2秒量级；仅stdout JSON，不写新JSON文件。第一轮 mask helper 缺少fixture role+26c actor绑定导致精确断言红，补齐既有原selector要求的对象关系后重新执行全部通过；没有改原映像指令来取得通过。

5例setter（不同值原写/同值不写）+12例JumpStop（3旧值×4flags）+3例原codec+3例外观保留。记录原mem-write PC，状态写均发生1205c9d；host只初始化prior，不host执行状态选择。单变量 flags 由World vt+28 Adapter返回，原11c5c00的AND/bool、12126d0的分支/发送对象构造、真实setter、mask selector及codec均执行原指令。发送边界只捕获原对象，不称已完成实际网络/加密投递；没有host直接给最终状态赋值。

沿用 Reconciliation Adapter：CRT分配/释放、展示/外观/动画边界、无伴随角色查找、既有actor/Scene最小夹具。World flags为受控fixture，不是完整原maze到World vt+28的资源加载重放；尤其不能拿本表 flags 与maze原byte未经证明直接同名替换。旧37例Scene归一仍另属资源成功切片，不与本批拼成完整首次登录自然链。

| 来源 | SHA256 |
|---|---|
|原 `evidence/native-image.bin`，BASE400000|`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`|
|本批 verifier（35例当前版本）|`914710db7528b7e5811c748ccca8f0c5687a67eb1aadb1a15239ce04c5fccc26`|
|继承 `verify_world_movement_reconciliation_native.py`|`3e8947a9fa6e33b6996503523d7acd20144df57579bec9c6f2d30e9338a1edf7`|

扫描边界：扫描原byte位移218在11c0000..1230000附近并核查候选指令；此范围内确认本对象byte显式写1205c9d，另有基类嵌入构造11d50d9清0。其他相同偏移的dword写属于不同对象/栈，不能合并。E8直调搜索与vt+8附近追踪不能穷尽所有指针别名、内联写、跨范围或间接调用，本文不声称all-writers穷尽。

尚未验证：完整SEnterWorld间接外观构造、特殊1404/516023后的玩法、所有起跳/结束协议、CRoleJumpStop服务器校验授权、World flags从原地图加载的全链、真实客户端运动及服务部署。接线建议仅限已证契约：状态由匹配场景/位置版本的可信生命周期事件建立；普通Scene A正常成功可覆盖，加载失败/特殊分支保留未知；已知JumpStop本地会再转换，未经授权报告不足以建立服务器state。未知分支保持明确未知，不静默套全图0。

## 后续纵切：原 maze loader → World原字节 → JumpStop

本节补足前文的 World flags Adapter 边界；历史12个flags合成case保留，并未把其结果改称资源原加载。新增12例使用 `DenseTransitions`，**不适配6036e0、11c5c00或6284f0的结果**。

原来源链与数据身份：

* 原Scene加载 `11e0310` 拼 `/maze.dat`，经World `5f9770/5fcd50` 走资源加载，既有完整网格报告见 [SCENE_GRID_PROTOCOL.md](SCENE_GRID_PROTOCOL.md)。本批追加静态核实 `5fd0e9..5fd0fc` 将World+298地图对象交672ff0；`672720` 后续分支 `672c0d..672c17` 明确设置 `ESI=map+84` 调 **672490**。
* 672490检查源buffer长度≥12、header≥12、总长度=`header+width*height`。`6724cf..67250d` 给目标buffer reserve并copy，`672510/672519/67252b` 原指令写 Maze+8 width、+c height、+10 cells。因此地图内嵌Maze位于map+84，对应map+8c/+90/+94。目标cells指向已复制buffer+header。
* 原World vt+28=`6036e0` 在 `6036e1` 取World+298；它直接使用该map+8c/+90/+94，对坐标向零除16、验证索引并读 `cells[gy*width+gx]`。这不是另一份特殊jump网格，也没有在该读取函数做mask或字节重映射。`5fd1cc..5fd1d8` 同样以map+84调用原672410建立寻路查询结构，进一步交叉原数据身份。
* 6036e0输入是逻辑pixel x/y，不是引擎投影x。完整12126d0经原主角current getter拿逻辑坐标；fixture将actor path当前float设为 `(x*1.5,y)`，原getter读回后，真实6036e0入口观察到 `(x,y)`。新例360与361分开验证，避免只用原点掩盖投影差异。

`DenseTransitions` 为原672490提供源/目标buffer对象，Adapter只实现源长度/data、目标reserve/data和CRT memcpy ABI；reserve不决定width/height/cells，后者由原loader写出。每例断言loader AL=1、实际目标内存与整个输入raw完全相等，width/height/cells均匹配原写入结果。World+298和vt+28由fixture初始化，实际查询从原6036e0开始。没有执行PFS到整个World/渲染对象的完整创建；这是明确的 **原Maze buffer加载器之后的资源纵切**。

新增用例：8例2×2 dense原loader→World→JumpStop（字节0/1/8/9，另-1、-16、右边界、下边界）；1例World+298=null；3例fresh PFS嘉兴1006。原entry `artres/map.pfs:map_1006_jiaxing/maze.dat`，长度/CRC由PfsArchive.read核验，SHA256=`6f81a7407738d6ce9b7ca167c82c28849dea1db12e7f2aa7fe1285e747698351`。完整dense width384,height296，无裁剪/稀疏替代。每一新例还对同一原loader产出的cells执行原6284f0 mask1与mask8，单独记录clear结果。

|真实1006逻辑坐标|6036e0原byte|6284f0 clear(mask1)|clear(mask8)|JumpStop prior2后|
|---|---:|---|---|---:|
|(360,2264)|8|true|false|0|
|(361,2264)|8|true|false|0|
|(1664,960)|11|false|false|2（保留）|

这直接消除了“可能不是同一maze flags”的来源缺口，但 **11c5c00非零与6284f0 true语义相反**：前者原byte与mask有交集返回1，后者无交集且范围有效才返回true。墙格11不让JumpStop自动归0；它会保留prior2。不能把“JumpStop之后总为0”当成普遍规律，也不能拿本地转换函数替代服务器合法终点检查。

边界：6036e0对负数向零除16，(-1,0)在2×2 fixture读cell0；(-16,0)、x=32或y=32越界均返回 **EAX=ffffffff**。World+298=null同样返回ffffffff。原11c5c00只看AL与mask，因此这两类情况下mask8和mask1都为非零，JumpStop保留旧+218；原6284f0越界则直接false。缺map例的6284f0控制仍基于已加载fixture查询对象，不能将其误称缺map函数返回；缺map行为断言只针对World与JumpStop。服务器必须继续独立检查非负/地图边界，原向零索引特性不是负坐标许可。

本节没有重放原World完整文件系统/异步资源路径、map创建/销毁/动态patch、起跳动画产生和服务端受理；这些仍为前述未证范围。35例当前脚本和两次原23例不是不同状态政策，只是相同公开Seam的递进证据。
