# xjPos/yjPos 到原 G 链接点击与导航命令

2026-10-24，独立 World 后台来源研究。采用 `research`，沿用已完整读取技能，并重读 ARCHITECTURE / DESIGN_AUTHORITY / GLOSSARY；在 [上一批四字段研究](WORLD_MAP_POSITION_FIELDS_RESEARCH.md) 的具体止点继续。仅新增本研究脚本、JSON及本文，没有修改既有证据、生产/shared/政策，也未操作客户端/服务/正式库。全量地图、场景、怪物恢复目标仍未完成。

**已闭合一个实际用途：`xjPos/yjPos` 是原任务 G 链接可使用的默认导航点，正常点击在调用导航入口前各乘16，地图模板ID保持原值。** 这不是原服务器出生或门户返回落点的证据，不授权移动九组原goto目的地。导航处理在 `0x1142620` 入口被捕获，未执行该函数、后续路径或网络。

## 来源、脚本及实际结果

- [research_world_map_navigation_fields.py](../research_world_map_navigation_fields.py)，SHA256 `5da7c3b72f9c08a25fc34dc64ee497d8e4b106ff54100c750ac6a1210e1db2f3`。
- [world-map-navigation-fields-research.json](world-map-navigation-fields-research.json)，SHA256 `7bb289babe3009375f7db0656e3730d8b45c0b60c720821907adf604f86a0ce5`。保存7例输入、原赋值结果、实际导航参数、执行地址轨迹、静态原字节及范围SHA；依赖的PFS/BXML/映像工具/原生夹具源码哈希也在JSON内。
- 原映像 BASE `0x400000`，重算 SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。
- fresh `config.pfs/autoconfig/knight.gsp.map.cmapconfig.xml`：PFS长度/CRC校验，SHA256 `374d400f933a74e83d402c8da948fef47823e7f92344ccb660414edfb87a1814`。
- fresh `config.pfs/autoconfig/knight.gsp.specialquest.cspecialquestconfig.xml`：PFS长度/CRC校验，SHA256 `f182e296282ee8dc3bbf37beaf1c0b7bba9103c82886e46afc38bc2d0cd75d80`。

实际最终执行：

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/research_world_map_navigation_fields.py
```

退出0，约0.75秒，`all_passed=true,cases=7,original_G_callback=true,coordinate_scale=16,scene_spawn_authority=false`。此处通过的是下面明确划定的原消费链与控制例，不是全世界或实际传送完成。

## 资源到 G 属性的连接

原 SpecialQuest 801004“寻找宠物”的 `aim` 明确含地图链接：`<G t="$MapName$" m="$mapid$" x="$xjPos$" y="$yjPos$">`。其描述/跟踪文字也用这两个变量；801024及802002等还有相应引用。因此上一批在 `0x160102c..0x1601122` 观察到的 MapName/xjPos/yjPos具名整数构造，有实际原配置的同名占位符下游，而非按名字推测用途。

本批由host读取并选择801004的这一原G节点，使用原CMapConfig值替换具名字段；**没有执行完整原任务formatter或完整XML语法解析**。这是明确Adapter，不把Python替换冒充原生模板渲染。原模板全文及选中节点原属性均保留在JSON。

## 原 G 解析与点击链

静态原分派 `0x514a31..0x514a65` 对照原CEGUI字符串对象 `0x292c1b8` 的内容“G”，进入 `0x5161d0`。本批执行其数字属性尾段 `0x5165cb..0x5167b9`：保留原存在检查、缺省0分支及组件字段写入；底层CEGUI/STL属性查找和整数词法转换是适配器，只输入规范十进制整数。未声称验证负数/溢出/畸形XML处理。

| G 属性 | 原属性对象 | 原组件字段 |
|---|---|---|
| m | 0x292c6e0 | +0xfc |
| x | 0x292c790 | +0x100 |
| y | 0x292c7e8 | +0x104 |
| npcid | 0x292c840 | +0x108 |
| j | 0x292c738 | +0x10c |
| mapkey | 0x292c8f0 | +0x110 |

实际字段由原 `0x516785..0x5167b3` 写入，host没有把期待结果直接写回这六个字段。字段结果逐项与输入/原缺省值对照。

随后执行原G组件鼠标处理 `0x5665a0`。事件+0x1c为0时，它取上述六字段的地址，调用组件callback或CEGUI manager+0x154的callback。原初始化 `0x1572d67..0x1572d76` 把 `0x1571b50` 注册在该槽；夹具按同一槽布置该真实callback，保留原handler的实际调用。基类鼠标记账和OS按键查询为Adapter。

原 `0x1571b50` 普通分支在有明确x/y时把二者各 `shl 4`，在 `0x15721c9..0x15721d5` 取主角对象+0x378，调用 `0x1142620`。捕获到的参数依次为 `[x×16,y×16,m,npcid,j,0,1]`。`m`始终是原整数地图模板ID，不创建完整MapAddress或实例身份。

当 `m!=0` 且 `x=y=npcid=0` 时，原 `0x1572699..0x157275d` 按m查询CMapConfig，通过原copy constructor `0xc34710` 复制记录，再读取记录+b0/+b4的 `xjPos/yjPos`，各 `shl 4` 后交同一导航入口。这里记录查找由Adapter提供fresh原表值，标量字段复制、默认分支和移位均执行原指令；仅空wstring拷贝/析构被适配。

## 七例真实执行结果

除标出的控制变量外：当前Scene模板1007、npcid/j/mapkey均0，组件原callback槽回退有效，Scene+0x364及前置UI阻止对象为显式空fixture；Shift未按下，Ctrl默认未按下。导航入口截获后返回，未建立真实寻路或移动状态。

| 例 | G 输入 | 原赋值/原callback实际产物 |
|---|---|---|
| 原地图字段1007 | m=1007,x=211,y=170 | 导航 `[3376,2720,1007,0,0,0,1]` |
| 原地图字段1103 | m=1103,x=149,y=184 | 导航 `[2384,2944,1103,0,0,0,1]`，未被当前1007覆盖 |
| 单位控制 | m=1103,x=1,y=2 | 导航 `[16,32,1103,0,0,0,1]` |
| 只给地图1007 | m=1007，其余缺省0 | 原表默认211,170→导航 `[3376,2720,1007,0,0,0,1]` |
| 只给地图1304 | m=1304，其余缺省0 | 原表默认19,69→导航 `[304,1104,1304,0,0,0,1]` |
| 非零鼠标事件控制 | m=1007,x=211,y=170；event+1c=1 | handler返回0，无导航callback产物 |
| Ctrl分支控制 | m=1007,x=211,y=170；Ctrl按下 | 原 `0x1567ad0` 边界得到 `[1007,211,170]`；未调用普通导航入口，坐标未乘16 |

“16”只对应这条普通G点击到导航入口的逻辑坐标单位转换；Ctrl分支继续用途没有在本批执行，不把其原单位参数当作服务器移动像素。1304例只是原默认导航命令证据，未检查其路径、碰撞或可达性，尤其不能用它替代1304→1103的出口坐标。

## j、mapkey、NPC与实例范围

七例均为 **j=0、mapkey=0、npcid=0**。原handler会将j作为指针交callback，普通分支再将其值传给导航参数；本批未执行j非零，不推导其业务含义。原模板中的j=1/2 NPC链接不能由这里的默认地图链接绿灯代替。

原callback在普通导航之前另检查mapkey。静态 `0x1571efa..0x1571fee` 可见非零分支查询对应对象、核查资源并可能构造type `0xc04f4` 请求；该分支本批未执行，也没有核验其业务/消费/权限，不能据此实现付费传送或私有副本入口。NPC非零、m=1的特殊分支及保留NPC编号同样未验。

本批只有地图模板ID的消费证据，没有帮派/住宅/剧情实例目录、成员许可或真实地图归属证明；不能推广为私有地图/实例导航成功。

## 对恢复工作的具体结论

四字段上一批的疑点中，xj/yj的一个最终消费者现在得到实际原指令补齐：**任务地图链接的显式/默认寻路目标**。已观察路径不使用Scene落地setter、不生成SRoleEnterScene，也不让客户端决定服务器传送归属。

未执行 `0x1142620` 的导航门控和后续路径、跨图选择、任何网络发送或服务器回包，故没有证明命令被实际受理、可到达目标、目标可走或门户目的点有误。原G解析的完整XML/STL/整数实现和完整任务替换亦未执行。这些界限与七例的通过一起保留；不改九组阻挡落点的未完成状态，不作新的坐标或实例政策。

方法记录：research以fresh原PFS模板、映像字节、原callback注册和可执行最小fixture互证；影响的决定是将xj/yj归为已证默认导航用途，并保留出生/门户authority未证；产物为本脚本/JSON/本文；验证为7例秒级原消费链和互斥控制；未验范围如上。
