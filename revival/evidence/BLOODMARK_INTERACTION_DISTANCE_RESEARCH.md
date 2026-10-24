# 血手印交互距离与原NPC导航坐标

2026-10-23；本地端游1.6.1/网络601。研究结论：**原通用NPC点击/自动接近停靠距离仍unknown；没有原证据证明32或48是原版交互半径。** 血手印原placement与配置导航坐标属于不同数据流，不能通过替换坐标消除恢复服距离约束。本批仅写本文，无生产/他窗脚本/政策/真实库变更，无客户端、GUI、服务、发包或战斗。

## 反馈基线与可判定范围

root已实际运行`verify_prologue_touch_runtime.py`，自然intro→师父→武器→装备→车夫→嘉兴100160后失败：source `(1006,360,2264)`，目标placement13/NPC10498 `(1668,970)`，state0、mask1、radius32、max_visited100000，`BirthSiteCheck(status='no_witness', visited=44928)`。本批读取该真实调用，不再运行整条玩法回归。

随后root最小原mask查询见[bloodmark-approach-radius-probe.json](bloodmark-approach-radius-probe.json)：32内无clear整数像素；最近clear `(1668,1008)`距离38。radius48可得原DDA见证，末点`(1656,1016)`距NPC约47.54；半径32/48/64/96的结果已独立保存。该新增证据排除“只换成格内其他整数像素，就能在32范围通过mask1”的解释；**不是原客户端交互条件证明**。

[world_newbie.py](../world_newbie.py) `check_birth_site`原注释/返回说明已明确：这是恢复服离线见证检查，起点后采样格中心并用DDA校验边，失败只说明此采样图上无见证，不是原A*或原界面不可达证明。root的整数像素检查更强地约束了本NPC的32范围，但仍不能宣布原交互玩法不可用。实际运行服[NpcScene.interact](../world_npcs.py)则另按当前绑定实体placement执行平方距离≤radius²，32是恢复服显式设计，不来自CVisitNpc线包。

## 本轮原包直接核验

使用[pfs.py](../pfs.py)读取时校验目录/本地头、解压长度及CRC，再BXML解码；并非仅引用派生catalog。

| 原条目 | 字节 / CRC32 | SHA256 |
|---|---|---|
| config.pfs / autoconfig/knight.gsp.npc.cnpcconfig.xml | 619832 / cc437e13 | b4fc5d440380fb535a36b8e5315c5a1bf10a99f550f5bfde55bd156fca864f85 |
| map.pfs / map_1006_jiaxing/npc.xml | 3571 / 51217023 | 72b66cc70e41d78997fb8369c74c5f21a69f500e790797718a41d56ff857752c |
| config.pfs / autoconfig/knight.gsp.task.cmainmissioninfo.xml | 2026233 / 3f7ab7b3 | ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706 |

`cnpcconfig[10498]`原行：血手印，npctype4，modelID5028，bodytype0，mapid1006，xPos104/yPos60，hide1，actionname0；没有本条交互radius字段。场景npc.xml第13条：`id10498 posx1668 posy970 dir4`。任务100106的原目的/追踪富文本有`<G t="血手印" npcid="10498">`；ActiveInfoMapID1006、ActiveInfoNpcID10498，type10、ProcessBarTime3、AI0。该目标不是NPC13模板，也不是Jump目标1501/63/79；奖励跳转与源交互距离无关。

npctype4/hide1的原可见性证据沿用[PROLOGUE_NPC_VISIBILITY_RESEARCH.md](PROLOGUE_NPC_VISIBILITY_RESEARCH.md)：任务NPC mark参与显示，但本批未找到它改变点击半径或免距离校验的consumer。不能把血手印是墙上物件或隐藏任务NPC当作豁免交互距离的已证事实。

## 配置104/60到导航入口：已执行原指令

原映像[native-image.bin](native-image.bin)，BASE0x400000，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。以下VA经本轮[native_inspect.py](../native_inspect.py)独立反汇编。

1. 原NPC parser `0xbaec4d..0xbaec79`以UTF16字段xPos(`0x226b284`)读取整数，存config+0x100；`0xbaec8c..0xbaecb8`以yPos(`0x226b278`)读取整数，存config+0x104。mapid在config+0xfc。并未在parser乘16。
2. 通用UI中按NPC ID处理的一条导航分派，`0x15725e7..0x15725f6`查CNpcConfig getter`0x89df90`，输入NPC ID取`[ebx]`。配置缺失(id=-1)退出；有场景模式/跨图条件，不能忽略这些条件泛化所有导航。
3. `0x157262a`只有模板0x2a9a进入特殊坐标分支；10498=0x2902不命中。普通分支`0x157264e..0x157265a`取config+fc/100/104为map/x/y。`0x1572660`检查Ctrl键(0x11)；按下时进入另一函数`0x1567ad0`，不是本轮路径。
4. Ctrl未按下时，`0x1572685..0x1572694`在原指令中对x/y分别左移4位，并经`0x15721c9..0x15721d5`调用主角色+0x378的`0x1142620`。此入口本身有原移动许可等门控，不等于已经规划、到达或发出CVisitNpc。
5. 另一分派类别100(`0x1572144`，NPC ID来自原`0x1129460`角色配置查询)同样读取config+100/+104并各乘16进入上述导航入口；**不把该类别100直接命名为血手印tracker**。本批原probe使用的是上面显式NPC ID的分派。

本轮通过终端内联Unicorn执行`0x15725e7`起的原查找、分支、整数移位及call，至`0x1142620`入口停止。输入为本轮原表10498/map1006/x104/y60；配置manager/lookup和Ctrl按键getter适配，当前scene mode为非受限fixture，metadata值0。没有替换乘法或手工调用导航入口。

```text
pass=true
original navigation entry = 0x1142620
this = simulated main+0x378
stack arguments = [1664,960,1006,10498,0,0,1]
```

这条**client_verified（原指令离线）**证明104/60存在×16导航消费，且NPC ID10498随请求传给导航逻辑；不是104/60直接作逻辑像素。它不证明普通鼠标点击CNpc必经此分派，不证明导航最终保留该目标或停靠点，更不证明到达条件等于32/48。

原placement `(1668,970)`与导航参数`(1664,960)`差 `(4,10)`，距离约10.77。坐标相近不允许把两者互换；本轮也没有执行此目标的完整原寻路/自动接近生命周期。CNpc初始化`0x1201c44..0x1201c5d`复制配置到entity+0x150，复制器`0x11f30cd..0x11f30df`保留配置x/y，**不等于把该配置坐标写成actor当前位置**；当前位置来自另一份实例info/placement数据。

## NPC访问距离：未知边界及已排除误读

原CVisitNpc `0xc2329`只有非负q64实体key，构造`0x120eea0`，marshal`0xe52020`，不携带距离、配置坐标或任务ID。原任务UI路径`0x1644c8f..0x1644c9e`取CNpc虚槽+0x38的完整key；另一UI路径`0x164936b..0x16493a2`取缓存key。两者都不能证明鼠标访问的原停靠半径。

追构造器直接调用发现普通交互另有`0x29ce1c5 / 0x29d20a4 / 0x29d94be / 0x29dab5f`受保护/混淆区域调用；本轮未把相邻乱序反汇编当成完整流程，没有声称恢复其距离判断。无需为本局部恢复无限扩张受保护代码研究。

既有[FIRST_MASTER_NATIVE_NPC_KEY_AUDIT.md](FIRST_MASTER_NATIVE_NPC_KEY_AUDIT.md)已排除的数值，本轮沿用并保持证据范围：

- `0x1215f40..0x12160a0`的double208用于构造`0xc07e8`另一操作，不是CVisitNpc；不能套普通NPC。
- `0x1212240..0x121237d`的180限临安1007/特定NPC10565/等级条件，不能套10498。
- `0x1217dbd`的48属于另一实体操作/跟随分支，未闭合为CVisitNpc距离；不能因为拟议设计也用48就升级成原版依据。
- `0x12189dc`的整数0xa0属于Windows消息switch，不是160像素半径。

截至本批仍unknown：普通NPC自动接近最终半径/单位/边缘判定；直接点血手印的特殊停靠逻辑是否存在；原服务器允许的交互距离；客户端绕开墙体接近的最终点。原资源有npctype4、hide1、bodytype0，只证明类型/表现字段存在，不能自动生成距离政策。

## 同款官方端游窄检索

2026-10-23仅检索官方`sdxl.wanmei.com`：血手印、血手印+坐标/接近/距离、NPC+交互距离、对话+距离+像素。命中[2012-07-28《剧情任务》](https://sdxl.wanmei.com/info/renwu/script/20120728/133491.shtml)：序章0级、经门派师父/车夫前往嘉兴，任务NPC包括说书人、血手印。页面不提供血手印接近半径或精确互动坐标；官方题库/美图中血手印仅属剧情/原著内容，无此数值。其余精确距离检索无相关结果。**guide_supported仅到NPC/剧情关联，不支持32、38或48为原版交互规则。** 未使用手游、神雕2或后期资料填空。

## 交root的设计输入与验证边界

root提出的候选是**仅1006/placement13/NPC10498使用radius48，其余NPC维持32**。若采用，须明确标designed；依据是固定原placement、原mask1以及同源可达见证足以满足此恢复政策，不是找到了原版48。原placement、配置坐标和角色位置来源保持各自身份；不要移动血手印、改mask、以导航配置坐标替代实例坐标或全局放大半径。

该局部政策应由NPC交互所有者按地图/placement/配置三重身份选择，并让菜单及提交时当前实体/位置复核使用同一Interface事实；不应只改测试checker半径使绿而生产`interact`仍32。这里是接线审查输入，本批没有实现或替root发布政策。真人原UI自动接近能否实际停在该合法48范围仍未验证。

方法记录：diagnosing-bugs以root已运行的`verify_prologue_touch_runtime.py`红例为反馈基线，本窗口不重复自然链；三条可证伪假设为32设计值过严、导航/placement混用、血手印特殊距离。原包/原指令已确认第二项涉及真实两条数据流，却未证明它就是失败原因；第一项由root额外整数像素/48路径证据支持为恢复服政策约束，第三项未查到。research要求第一方查证后明确unknown；codebase-design用于维持NPC所有者的单一距离校验Seam，不在任务/测试端另造权限。

产物仅本文。已验证：三条原PFS CRC/BXML、原10498/placement13/100106字段、导航配置parser与乘16调用、一个明确模拟场景下的原导航参数离线执行、官方窄检索。未验证：原NPC点击完整自动接近、GUI/线上角色、完整原导航目标纠正、原服务器半径、root局部政策实施/部署和原red回归转绿。未重复BFS、repair96套、游戏或战斗。
