# NPC方向：field_48原协议、首条placement回退与actor向量

本批沿用本会话完整读取的 Matt Pocock research/diagnosing-bugs、根AGENTS、ARCHITECTURE、DESIGN_AUTHORITY。实际方法：先以原映像追字段数据流，再让原codec、handler局部、原NpcInfo copier、原模型选择分支及原actor setter形成可执行纵切；只改单一wire方向或XML dir作反事实。不按相邻字段名猜含义，不将资料提取或原向量写入说成GUI恢复。后台研究由本代理完成；没有继续委派。

只新增本文与 `../verify_world_npc_direction_native.py`。没有改NPC所属 `world_npcs`、菜单/权限规则、生产/shared/政策/旧审计及冻结35/28例；没有启动客户端、GUI、服务、真实库或真人玩法。

## 交NPC所属窗口的精确事实

**NpcBasic原对象+0x48，即现有纯codec的 `field_48`，确实到达CNpc+0x120并被方向选择分支消费。** 本批已执行其非零1..7的原指令纵切到actor方向向量，能够交接此字段而无须猜field_38。取值0在已测模型分支是“去查本地图npc.xml方向并按分支回退”，不是“所有模型朝枚举0”。

当前 `NpcScene.spawn` 约84行只构造 `NpcBasic(key,npc_id,name,x,y)`，未显式传placement.direction，所以field_48为默认0。这是投递来源的真实缺口；并不表示所有默认0都会朝错，因为原客户端存在本地图dir回退及其他模型分支。把placement.dir投到该字段是一个可由NPC窗口采用的候选，**本批不擅自改投递，也不把受测+98分支覆盖当全模型保证**。

可直接复现：

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/verify_world_npc_direction_native.py
```

最终实际 `all_passed=true, case_count=19`，约3秒；只stdout JSON，无新结果JSON文件。输出每例原wire、原+120、实际选中值、原actor三维向量、原XML请求路径/属性读取轨迹及源hash。

## wire布局与原数据流

现有 `world_entity_protocol.npc_basic` 的结构是 `>Qi`、compact UTF16 octets、`>hhBhh4i`、property map。该4i依次为field_44、**field_48**、field_4c、field_50，均原signed32。原构造=`fc71e0`、marshal=`fc6f70`、decoder=`fc73a0`。本批每例都执行原构造/编码/解码，字段+48原值与现pure codec逐byte一致；空name fixture内该field位于body[26:30]，**这不是带变长name所有包的固定线偏移**。

原SAddUserScreen NPC列表节点在+8嵌入NpcBasic，所以对象+48对应node+50。`11e71be..11e71c4` 取 `[esi+50]` 放到frame+dc，即局部info+20（局部info从frame+bc起）。本批执行这段原handler指令；节点中的NpcBasic来自独立原decoder快照，host只在两CPU Seam之间复制快照，不伪装同一次完整网络解包/Process。

原 `1201c36..1201c3f` 以 `ecx=CNpc+100` 调 `11fd140(info)`。该原复制器 `11fd176..11fd180` 将info+20复制为CNpc+120。本批执行整个11fd140，wstring为明确空串fixture，经原IAT库ABI Adapter复制；断言+120精确等于decoded+48。

本批从CNpc初始化中的方向选择 `12020e0`开始，fixture CNpc+98=1。该原分支：

* +120非0，`12020ea..12020ff` 原样传CNpc vt+e4=`11f5b00`，不查XML。
* +120为0，`1202106..1202113` 按CNpc+108配置ID调Scene `11db690`。返回1/3/5/7直接使用，其余0/2/4/6通过 `120212c..1202138` 传4。
* 到 `120224c` 停止，避免把后续任务标志/附加模型初始化算作已执行。

field_38的已知handler行为是node+40严格比较1再转bool；它不是本批发现的方向字段，也没有被拿来修补方向。

## 原方向setter真正写了什么

保留CNpc原vt=`22985e4`。`11f5b00`先执行原vt+158/+15c gate；本fixture二者中立，随后actor vt+40=`652750`。原 `652750` 调 `651700(enum)` 生成向量，再 `6519d0` 写actor+1a8所指移动对象的+10/+14/+18。原6519d0、相等检查与旧方向处理均执行；本批没有在setter入口直接返回来伪造终值。

|方向枚举|原651700输出/本批actor存储向量|
|---:|---|
|0|(0,-1,0)，来自静态原jump表；本批wire0走回退，没有直接将enum0传actor|
|1|(1,-1,0)|
|2|(1,0,0)|
|3|(1,1,0)|
|4|(0,1,0)|
|5|(-1,1,0)|
|6|(-1,0,0)|
|7|(-1,-1,0)|

1..7均有独立wire→原actor向量实执行；不依2D屏幕方位给其强命名东南西北。651700对>7的unsigned比较走零向量默认，负数也会进入该default，但本批未执行非法值方向，不提供其作为合法可用值。底层enum0与wire字段0回退语义必须区分。

## 原本地图getter与重复ID的实际反馈

原 `11db690` 整体执行到返回：

1. `11db6c7..11db6ea` 拼原 `/map/` 与当前Scene+168 resdir，再 `11db705..11db71c` 拼 `/npc.xml`。
2. `11db750` 请求Scene原XML加载入口 `11c6030`，后者在本夹具为明示Adapter，供应fresh原包中顺序不变的记录向量。
3. `11db75d..11db7f3` **原指令按8字节记录从前往后遍历**，通过属性ABI读取id，`11db7da` 比较所请求configID，未命中则继续。
4. 首次命中后 `11db7f5..11db820` 读取原字段字符串 `dir`，退出而不考察后面相同ID。它没有接收entity_key或placement位置来区分实例。

XML属性读取 `409ce0` 在夹具由host从相应原row返回int，**并未执行完整原XML parser/DOM属性转换**；但请求字段、迭代顺序、ID比较、首条命中与dir选择由原getter体执行，不是host先挑出“首条结果”交回。资源请求路径由原函数形成，实际捕获为 `/map/map_1002_dashengguan/npc.xml`。

新鲜读取 `runtime/client/artres/map.pfs:map_1002_dashengguan/npc.xml`，PfsArchive核长度/CRC，entry SHA256=`ff846a28ce43322a89af9e2e4c68a0e5469ac88a8cafeace6b2074a3261d9ad4`。原表97条；同config11206：

|原顺序placement|id|原posx,posy|原dir|wire字段为0的原选中值|显式wire采用原dir后的选中值|
|---:|---:|---|---:|---:|---:|
|54|11206|(1286,3455)|7|7|7|
|55|11206|(950,3438)|1|7|1|

4例使用不同key `(1002<<32)|placement`，其他config相同。此处为方便辨别key的fixture，不将其称原服分配方案；关键事实是getter不接收它。dir0的两个实例都实际读取原首条7；显式1绕过fallback，实际actor向量变成(1,-1,0)，显式7为(-1,-1,0)。这证实**当前受测原分支无法靠“同配置ID查本图首条”保留这两处不同方向**，但原CNpc+98是否对该真实11206模型为1未完整构造验证，所以不冒称此具体NPC已经在GUI朝错。

另8例只改变XML返回dir0..7（同ID、wire0），原getter/分支最终选中分别为4/1/4/3/4/5/4/7。首7例非零wire1..7完全不调用本地图getter。总19例：7非零、8零值回退、4真实重复placement对照。

## 未覆盖的模型分支与权限界限

原 `120213f` 在CNpc+98=0支读取shape config+100；等1则默认4。另一actor能力支在 `1202172..1202181` 检查actor虚槽+138；有的零值回退选择原奇数dir，有的rand选择3/5；不支持该能力时 `1202226..120224a` 将零+120改4后应用。部分shape ID6100/6126还有强制3的原比较。以上为静态来源，没有加入19例，也没有用host造shape配置结果冒称全分支完成。

因此可交接字段是field_48，当前有效方向范围原枚举0..7；**wire0在CNpc高层不是简单enum0直通**。1..7对+98=1分支真实可用，其它形状/能力分支可能覆盖。不能在不知道模型分支时承诺所有placement方向100%按wire呈现，也不以此恢复NPC隐藏条件、交互服务/任务权限、模型资源或monster身份。

## Adapter、验证范围与hash

Host Adapter：沿用IntroReplay的CRT分配/释放及wstringABI；外部CRT sqrt以fixture内x87 fsqrt/ret实现，原方向选择/向量构造/存储不改；XML加载/属性值与文档/向量析构为资源ABI边界。首轮缺外部CRT sqrt导致执行在原导入跳转处失败，补该明确Adapter后全部19例重跑通过，没有改原映像字节。fixture只给空名称/中立gate和最小actor/path，未创建实际渲染对象。

|来源|SHA256|
|---|---|
|原native-image.bin BASE400000|`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`|
|本批verifier|`1580ec34fe3c363b41077af71f45334b8d0d75c547ee7ff2ea5ae1aa178582bc`|
|world_entity_protocol.py|`d4977aa707e2e0c3d1cbca6bb11ddafa39f678ef3457128d13f9e5db8d66f964`|
|world_npcs.py|`177f55e34168229665586f9fef6ddee3fcdeef17c3c47fde716ad7353ac7d1c4`|
|native_gameplay_probe.py|`a585adc6522c8162ecaa8c87250eed240a49477ee57322f2950344a92bb7e24c`|
|verify_world_intro_dispatch_native.py|`dbe914b50cc6fedb0f757ca5841a5ad896c52724482604daf68a5c01d750682f`|

未验证：整个SAddUserScreen Process自然创建/注册、全CNpc配置/shape/model构造、完整XML parser与PFS VFS、非中立gate和其它方向选择支、3443个真实模型的适用分支、GPU/视觉效果、运行服投递或policy。当前证据足以让NPC所属窗口按该字段做受范围约束的实现/下一批原构造验证；不把研究完成等同地图NPC恢复全部完成。
