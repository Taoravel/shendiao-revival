# CMapConfig 四个位置字段的原生消费者

2026-10-24，World委派的一手客户端研究。采用 `research`，先读 [原出口研究](WORLD_PORTAL_EXIT_SOURCE_RESEARCH.md) 和 [原场景落地研究](WORLD_SCENE_LANDING_RESEARCH.md)，随后从原PFS字段名追到映像加载偏移及实际读取指令。没有重跑或重写先前落地试验，没有修改生产/shared/冻结资料/政策，没有启动服务、GUI或正式DB。

**已查到 `playerPosX/Y` 的世界地图UI矩形用途；`xjPos/yjPos` 已查到原配置加载和以其字段名构造整数属性的消费者。四字段均未确立为原服出生或传送落点权威，不得用来替换九组原goto目的点。** 本批为静态数据流核验，未仿真执行这些原函数，也不声称已穷尽所有间接调用。

## 可复核来源

- [research_world_map_position_fields.py](../research_world_map_position_fields.py)，本批新增，只读取原资源/映像并写新研究JSON。
- [world-map-position-fields-research.json](world-map-position-fields-research.json)，包含原字段名、16张相关地图的完整原属性、各加载偏移、原指令字节/反汇编和范围SHA256。
- 主映像 SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`，BASE `0x400000`，实际重算匹配。
- fresh `artres/config.pfs/autoconfig/knight.gsp.map.cmapconfig.xml`：PFS长度/CRC校验，304行；entry SHA256 `374d400f933a74e83d402c8da948fef47823e7f92344ccb660414edfb87a1814`。原表还含地图名、资源目录、尺寸、世界地图图标边界、介绍、显示开关、动态标志等完整字段，未裁出四列后猜含义。

本批实际执行：

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/research_world_map_position_fields.py
```

退出0，`all_static_assertions_passed=true, configured_maps=304, fields=4, worldmap_rectangle_delta=25.0, spawn_authority_established=false`。这里“assertions通过”是已指明静态指令和字段数据一致，不是玩法通过。

## 原加载布局与表访问

原整数属性读取器 `0x409ce0` 返回EAX，CMapConfig行加载器 `0x879e30` 将各字段写到EDI指向的记录。每项原字符串地址、读取call及写入指令均在脚本中逐条断言：

| 字段 | 原UTF16名字地址 | 记录偏移 | 原写入指令地址 |
|---|---|---|---|
| xjPos | 0x2259960 | +0xb0 | 0x87a1b9 |
| yjPos | 0x2259954 | +0xb4 | 0x87a1f2 |
| playerPosX | 0x2259878 | +0x120 | 0x87a409 |
| playerPosY | 0x2259860 | +0x124 | 0x87a442 |

表注册 `0xd42bd4..0xd42be9` 调用CMapConfig对应实现构造并将wrapper vt `0x2259a28` 写入manager+0x8c8；原getter `0x89dd50` 返回 `[0x2945aec]+0x8c8`。getter结果vt+8取按mapID选定的记录。例如原Scene入口 `0x11e255e..0x11e2576` 按传入地图查记录，然后由 `0x11c5960` 复制到Scene+0x110。复制全部字段并不意味着字段全部参与主角落地；原落地actor setter是否使用这些值应按具体数据流另判。

## playerPosX/Y：Worldmap.layout 的UI矩形

原 `0x15f3320` 初始化的布局字符串是ASCII `Worldmap.layout`（`0x22c17e4`）。`0x15f339a..0x15f33c3` 获取当前Scene+0x110的mapID，经上述CMapConfig getter和vt+8取记录，再由 `0xc34710` 复制到调用者ESP+0x144的局部记录。

因此局部+0x264/+0x268恰是记录的+0x120/+0x124。原代码先检查二者非负，`0x15f346b`、`0x15f3476` 以 `fild` 将其读为X/Y；`0x15f3485` 从 `0x2474118` 读到的原double实际为 **25.0**，给二者各加25形成另一角。随后 `0x15f34ad..0x15f34df` 以原ASCII属性名 **`UnifiedAreaRect`**（`0x24465c0`）向界面控件设置矩形；`0x15f2830` 格式化四个float坐标。另一分支先经 `0x15f1900` 的矩形转换，再设置同一属性。

这条可追踪的数据流支持“世界地图布局中的位置/矩形显示”用途，没有通向Scene角色位置setter或发送传送坐标的操作。原属性 `Image`（`0x2453b9c`）也在同界面函数中使用。未执行整套CEGUI渲染，所以不把它写成已目测箭头效果，也不声称完全排除了其他读者。

原表还有一致的辅助观察：同门派外景和对应内景共用 `playerPosX/Y`；例如1103/1304均459,134，1105/1306均401,597，而1393/94/95均0,0。该观察本身不构成语义证据，语义依据是上述原指令UI链。

## xjPos/yjPos：已证属性构造，最终导航用途尚未闭合

原 `0x160102c..0x160103c` 也通过CMapConfig表按mapID取行。`0x160103e` 开始构造 `MapName` 属性；`0x1601086` 用原字符串 `xjPos`，`0x1601098` 读取记录+0xb0；`0x16010d4` 用 `yjPos`，`0x16010e6` 读取+0xb4。数值与原UTF16格式串 `%d` 一起交 `0x809e90`，其内部格式化再传 `0x809ce0`。多个同类构造点的原字段名引用地址在JSON中列出。

已证明的是“原行的两个值以MapName/xjPos/yjPos具名整数属性参与文字/属性对象构造”。**本批没有沿该对象追到最终点击解析或导航命令，因此还不能把xj/yj展开为某种缩写、确定其单位、断言它是默认寻路点，更不能当作角色出生/出门落点。** 相同+b0/+b4位移也存在于其它对象，不能仅以数值位移搜索命中就归为此记录消费者；例如Scene入口中的主角vt+b4是虚函数槽，并非CMapConfig的yjPos。

| 地图ID | xjPos,yjPos | playerPosX,playerPosY |
|---|---|---|
| 1007 | 211,170 | 592,511 |
| 1103 / 1304 | 149,184 / 19,69 | 459,134（两者相同） |
| 1105 / 1306 | 83,167 / 19,69 | 401,597（两者相同） |
| 1107 / 1308 | 20,145 / 19,69 | 136,295（两者相同） |
| 1108 / 1309 | 83,16 / 19,69 | 192,181（两者相同） |
| 1393 | 66,82 | 0,0 |
| 1394 | 19,41 | 0,0 |
| 1395 | 31,53 | 0,0 |

保留原值；没有乘16后测试哪个更近或更容易通过，也没有把室内共同19,69解释为外景的替代位置。

## 对出口恢复的影响与边界

`playerPosX/Y` 已观察消费者是世界地图UI，不能仅凭“playerPos”名字用于出生；`xjPos/yjPos` 仍缺最终命令消费者。结合 [原落地研究](WORLD_SCENE_LANDING_RESEARCH.md) 已证主角普通落地接受Scene包坐标且不做maze纠正，四字段都没有提供新的原服落点authority。

下一项可证伪来源是具名属性的最终解析/点击处理：是否产生含mapID与坐标的导航命令，其单位、场景前提及原服务端如何选择目的地。即使客户端存在默认导航点，也须另证它与室内返回合同相同；否则补全仍由主策划显式设计。本文不制坐标政策，不改变九组未完成状态。

已验：fresh原表、四字段原加载偏移、指定copy/accessor与Worldmap UI/属性构造静态链。未验：完整callgraph、原函数动态执行、最终xj/yj导航消费者、原服务器坐标/消息、真实GUI与任何部署。
