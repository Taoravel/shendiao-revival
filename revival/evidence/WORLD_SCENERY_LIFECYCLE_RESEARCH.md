# 场景景物的原生创建、日期与回收

2026-10-23。结论：7592条 `CSceneNPCConfig` 是客户端原生景物管理器的本地配置来源，按地图选表、按主角附近范围创建/回收，**不应补造成普通 NpcBasic 入屏**。临安1328条中1293条还受原2012–2016年日期控制；当前日期下看不到这些历史节日景物，可以符合原逻辑，不构成服务器漏发它们的证据。

本批严格部署冻结，仅新增本文。没有新增或修改脚本、Module、配置、存档；没有启动客户端、GUI或服务，没有操作在线进程。下文分开原包扫描与静态原指令，不声称已执行这些景物函数或完成现场可见验收。

## 方法、来源与本批验证

采用已读 `research`：本窗口作为受委派研究者，从原包、RTTI、配置getter及实际调用者逐项追溯，不用字段名字或既有说明互相推导业务。已读根 AGENTS、ARCHITECTURE、DESIGN_AUTHORITY，复核 [recover_scene_content.py](../recover_scene_content.py)、[WORLD_FULL_RECOVERY.md](WORLD_FULL_RECOVERY.md) 和既有景物catalog，避免重复导出。保持研究与集成的Seam：这里交付原行为，不给服务器增加景物状态所有者或默认生成规则。

指令源：[native-image.bin](native-image.bin)，BASE `0x400000`，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`，地址均为该映像VA。使用现有 `native_inspect.disasm/refs/vtables`，只读反汇编、RTTI与直接call索引；没有新增或运行景物原生fixture。

本批另外通过现有 `PfsArchive.read` 重读原 `artres/config.pfs` 两条entry并校验CRC，`bxml.decode` 后核对既有catalog所有 attributes/lists：

| 原entry | 行数 | 展开字节 | CRC32 | 展开SHA256 |
|---|---:|---:|---|---|
| autoconfig/knight.gsp.npc.cscenenpcconfig.xml | 7592 | 500135 | e14d8580 | b7198e7dfab00009aa9f2bc8d2b187d51ada4c7c84e4e68bd2f703a26027d852 |
| autoconfig/knight.gsp.npc.cscenenpcbase.xml | 251 | 15134 | a4e13c65 | 11f7ad3f1b02d073b7c5847ed19356d38cb5a5caa802d9d3dcafc0a6bce7350c |

Config catalog与本轮原解码完整相同；Base catalog attributes/lists全部相同，children中仅既有美化XML产生的缩进 text/tail 与直接BXML解码的null不同，未当作数据差异或覆盖catalog。既有可读原表：[cscenenpcconfig.xml](../decoded/config/autoconfig/knight.gsp.npc.cscenenpcconfig.xml)、[cscenenpcbase.xml](../decoded/config/autoconfig/knight.gsp.npc.cscenenpcbase.xml)。

## 真实类型与表所有者

| 对象 | 原RTTI / 虚表 | 实际访问链 |
|---|---|---|
| 景物基表 | CSceneNPCBaseTable@npc@gsp@knight，vt2250248 | getter89e070返回ConfigManager+a58；原析构c98569→880c60→880ca5复原同vt |
| 景物摆放表 | CSceneNPCConfigTable@npc@gsp@knight，vt2250258 | getter89e080返回ConfigManager+a60；原析构c98559→881100→881145复原同vt |
| 原生景物实体 | CSceneNpc，vt2299cc4 | 构造121ff90，大小0x220；基础对象kind+1c写10 |
| 景物管理器 | CSceneNpcManager，vt2299e3c | singleton指针global29455f4；+4为本地图摆放ID列表，+10为现存对象map |

这些景物类型与网络NPC/玩家各自的原处理链分开。`12213d0` 直接分配 `CSceneNpc` 并以摆放ID初始化，没有先构造、解码或处理 `NpcBasic`；不能因为表名含NPC，就认定它们是服务器下行的普通交互NPC或怪物。

## 地图进入与本地范围生命周期

1. Scene正常加载路径 `11e2ca6..11e2cbe`：若global29455f4存在，取 `Scene+110`（已确认地图配置ID），调用 `CSceneNpcManager::12200c0(mapid)`。
2. `12200c0` 清空旧的地图ID列表；`1220123` 经89e080→表vt+4取全部摆放ID。逐行vt+8查询，`122017a` 排除缺省行id=-1，`122017f..1220186` 仅保留 `row+8 == mapid`。通过的ID插入本地图列表。此阶段不是把全表7592个模型同时创建。
3. 主角更新 `1217a71..1217afd`：角色+33c计时器非负且消耗到期后，重置为0x7d0（2000）并用主角vt+d0取坐标，调用管理器 `12214a0(position)`。这是本地角色更新驱动，不是等待景物网络刷新；准确的首次计时器赋值与所有特殊角色模式未在本批执行验证。
4. `12214a0` 遍历已选地图ID，并以摆放ID查现存map。未存在时，`122152d..1221551` 要求 `abs(row.posx-pos.x)<=0x240` 且 `abs(row.posy-pos.y)<=0x240`，即各轴不超过576，调用 `12213d0(placement_id)`。这是轴对齐矩形，不是半径576的圆；边界等于576仍在范围内。阈值直接针对表+c/+10和主角坐标getter结果，本批没有把它改成“576格”或另乘16。
5. 已存在时，`12215a7..12215eb` 若任一轴差>576，调用 `1220200(placement_id)`，经对象虚析构并从map删除；仍在范围内保留。
6. `12213d0` 去重查map；不存在则 `1221424` 分配0x220，`1221443` 调121ff90，`122145d` 调实体 `1220790(placement_id)`，`1221469` 插入现存对象map。随后还有global2945620+3c的表现状态传播分支，不是额外服务端spawn条件。
7. Scene清理路径 `11d85ba..11d85c4` 调 `121fa40`，清空本地图列表并逐个虚析构现存景物、清空map。单体删除同样走原析构，因此不需要服务器向普通NPC容器重复发送remove。

持续更新也有独立管理器遍历：`11d5c20→121f9c0` 调每个景物vt+5c；`11d5e0f→121f940` 调vt+68；`11d360f→121fb30` 传播vt+30表现状态。不能仅因catalog导出成功，就视作这些客户端生命周期已经在当前现场逐步观察过。

## 摆放与基表字段的原消费者

原 XML→CSceneNPCConfig 读取函数 `880d20` 提供明确字段名/偏移，不是凭内存排列猜名：

| 摆放字段 | 原bean偏移 | CSceneNpc复制后 | 用法 |
|---|---:|---:|---|
| id/baseid/mapid | 0/4/8 | fc/100/104 | ID管理、查基表、选地图 |
| posx/posy | c/10 | 108/10c | 范围筛选；`1221111..1221127` 设置实体位置 |
| dir | 14 | 110 | `122103a..122108f` 朝向；模型配置特殊分支可能覆盖 |
| talkinterval | 18 | 114 | 定时说话阈值，-1禁用 |
| talkintervalsays | 1c字符串 | 118 | 以原分隔符2293774=`;`解析ID至本地候选表 |
| talkdistance | 38 | 134 | 按主角距离触发的说话阈值，-1禁用 |
| talkdistancesays | 3c字符串 | 138 | 对应ID候选表 |
| talkcharnum | 58 | 154 | 周边人数说话阈值，-1禁用 |
| talkcharnumsays | 5c字符串 | 158 | 对应ID候选表 |
| pacing/movespeed | 78/7c | 174/178 | pacing进入原随机游走分支；非0movespeed在1221130..122115c除以原浮点常量后提交模型 |
| mask/transparent | 80/84 | 17c/180 | mask非0影响1221011处模型创建参数；transparent==1在1221098..12210a8传模型vt+78 |

`1220790` 经89e080取摆放并调用原复制121e310；有效摆放的baseid经 `1220f46..1220f59`→89e070取基表。基表XML原读取 `a716de..a718c6` 与复制 `1220f5b..1220fd4` 对应：

| 基表字段 | 原bean偏移 | 实体槽 | 具体行为 |
|---|---:|---:|---|
| id / shapeid | 0 / 4 | 184 / 188 | 1220fed经89e010查CNpcShape；1221020调实体vt+fc创建实际模型 |
| name | 8字符串 | 18c | 原CSceneNpc名字getter121e2e0返回此字符串 |
| type | 24 | 1a8 | 原表仅51/52；12210aa遇52调用实体vt+10(0)，51另有近身表现分支121fc40 |
| scale | 28 | 1ac | 12210be..1221103：1/2/3/4对应0.6/0.7/0.8/0.9；5及缺省走1.0，**5不是放大五倍** |
| npcappear / npcdisappear | 2c / 48字符串 | 1b0 / 1cc | 解析成出现/消失毫秒时间；见下一节 |
| area1colour | 64 | 1e8 | 已确认复制，本批未确认其后完整着色消费者 |
| chatidlist | 68容器 | 1ec | 专用交互/聊天路径；不能替代三个talk*阈值 |
| mask / transparent | 78 / 7c | 1fc / 200 | 已确认复制，本批未定位后续有效消费；不冒称与摆放覆盖/叠加顺序已明确 |

真实行例：摆放1=`baseid19003,mapid1515,posx829,posy7497,dir3`；base19003=`shapeid6139,type51,scale5`，CNpcShape6139引用`weibing`/`3ds_N085_enchouluweibing`。这是本地景物模型来源，不是怪物刷点/战斗模板的证据。base19002=`shapeid5087,type52,scale5`，CNpcShape5087是火盆`huopen`；同一集合确实包括景物。

## 日期控制是模型可见度，不是网络创建/删除

`122115e..122125c` 检查非空npcappear，按原格式字符串与CRT日期函数解析，将秒×1000存实体+210/+214，调用 `813850` 取得当前q64毫秒；尚未出现时向实体vt+14传0，已出现传0xff。`122125e..1221349` 对npcdisappear做同样解析，已过截止后传0。

景物vt+5c=`121f0a0`，由管理器持续更新。`121f11c..121f181` 对非零的两个截止时间重复检查：到出现时间传0xff，到消失时间传0。原vt+14=`11f6c30` 转调模型vt+6c；`Sprite@XiaoPang` 同槽=`652340`，写其byte+161并继续传底层vt+48。由0/255和值通路可确认这是透明度/可见度强度路径，**不是删掉景物对象**。初始化与tick对截止恰好相等的边界有细微差异：初始化消失检查用严格大于，tick用大于等于；本文不抹平这项原指令差异。

`813850` 直接返回global2945088/294508c。它们也是固定App对象2945060的+28/+2c；原SGameTime初始化链 `81b3e0..81b3fe` 写入这两个槽，并以毫秒/1000做日历运算。因此景物日期与原SGameTime的完整日期值相关，不是World昼夜24c的循环范围。当前集成方已另行核对入场发送 `int(time.time()*1000)`；这是集成源码核对结果，本批没有运行服务或观察该值进入客户端。

本批不指定时区、不重算原日历字段、不把历史出现时间改到现在，也不把开始/结束时间忽略。原CRT在不同运行时的时区、无效日期与夏令时处理未通过执行验证，仍应保持原客户端处理。

## 全量原包扫描的约束

本轮原包扫描得到：

- 7592条摆放覆盖50个mapid；251条base中type51=109条、type52=142条。
- 7592条的talkinterval、talkdistance、talkcharnum全部为-1，pacing与movespeed全部为0。表支持说话/游走，不代表这份原配置实际启用。三个talk*says字符串在本份原行中均未出现，不能补造默认语音/动作序列。
- 摆放mask/transparent组合：0/0共6209，1/1共1030，0/1共353。不同值原样保留；未因“全量恢复”强制显示或去遮挡。
- 91个base有npcappear/disappear，全包1293条摆放引用它们。这1293条全部在临安1007。
- 临安1007共有1328条摆放，1293条有上述日期门槛，35条base未填写日期。仍不能从“无日期”直接推导35条在任意位置全部可见，距离/形象/表现状态仍生效。
- 12组日期窗口分布于2012–2016；最晚一组2016-06-09至2016-06-11。不是按年循环的节日定义，原指令解析的是完整日期。

临安可复核行：摆放2801=`base19114,pos3944,2745,dir3,mask1,transparent1`；base19114=`shape5402,type52,scale5,npcappear="2012-09-30 08:00:00",npcdisappear="2012-10-07 23:00:00"`。摆放2802关联base19115，shape5403，同一日期窗口。看到这些配置存在不能要求当前服务器补刷它们；客户端仍可创建对象后将其强度置0。

## 动画、声音与额外condition的证据边界

景物初始化使用公共模型路径：`1220fed..1221020` 按base.shapeid取CNpcShape，再调实体vt+fc=`11fb330`；该函数最终向引擎World vt+60提交原形象资源，保存模型于实体+44/+48，`11fb654..11fb665` 启动原动作1。景物动作通知vt+4c=`121e950` 在特定状态下随机触发游走或动作18→19，`121e3d0`也提交动作18。这是原客户端动作机；本批未执行动作资源加载、未将动作编号擅自翻译成具体表演名称。

两份景物表本轮没有独立sound/animation字段。`chatidlist` 仅base19001有三项609；原 `121ec40..121eca7` 随机选一项，将placement/base/chat ID交专用聊天处理 `1644d90`。这是确认的聊天消费，不等于本批证明了音效播放。原三个talk阈值则经 `121eb90` 查消息资源、调用公共气泡文字路径；原表全部-1，因此不能据此生成自定环境声音。CNpcShape资源、公共动作机与可能的资源内声音事件的完整音效链尚未核验。

没有在这两张原表发现任务/战斗/服务器条件字段；本批已确认的创建筛选是有效配置、mapid、本地矩形距离；日期用于创建后的可见度，另有引擎形象、透明/遮挡和当前表现状态。不能把“未在表中出现任意condition”扩大成整个客户端无其它表现门控，也不能给服务器设计新的全量生成条件。

## 可接线结论与未验证范围

当前服务器对这批静态景物的合理接入点是保持原地图加载、主角位置与真实SGameTime初始化链正常，让原CSceneNpcManager自行创建/更新/销毁；无需新增7592份服务器实体，更不应转成NpcBasic或怪物。若后续现场景物确实缺失，可只读核对global29455f4、管理器本地图列表/现存map计数、主角+33c计时、摆放/shape引用与对象+210/+218日期阈值，然后判断是地图、范围、资源还是原可见度门槛。

这批交付的是 **原表重新校验 + 原生命周期静态证据**。未验证：原函数离线执行、真实景物创建成功率、GPU可见/声音/动作效果、地图全部位置覆盖、每一种特殊角色状态、准确首次调度、area1colour与基表mask/transparent消费、全部公共资源加载失败分支。没有改客户端日期、配置或服务器投递，也没有为缺口制定新默认规则。
