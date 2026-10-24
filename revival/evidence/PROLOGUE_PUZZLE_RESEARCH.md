# 序章画卷拼图原生消费者与服务器接缝

2026-10-23。本批采用research技能的一手来源追踪：重读原PFS/BXML、原映像静态指令及局部离线执行；采用codebase-design把菜单授权、客户端声明与任务事务收敛成一个小Interface。已读ARCHITECTURE.md、DESIGN_AUTHORITY.md及两项SKILL.md。本任务本身为后台研究，不再递归委派。唯一新增产物为本文；未改生产、共享入口或主策划政策，未运行当前客户端、在线服、真实库或战斗。

## 直接结论

1. `client_verified`：43条原角色门派路线合并为十个画卷任务。它们是type59、ActiveNpc=0、Map1501、DisPlayNPCID=[11106]，各有一句Start、一句Finish；不能套用装备或参战宠type59的完成判定。
2. `client_verified`：原菜单服务553“进行拼图”的本地分支取得当前主线任务ID，打开专用CJigsawPuzzleForQuestDlg，并把taskID传入dlg+0x80。当前NPCkey保存到+0x88/+0x8c，但最终提交不使用它。
3. `client_verified`：本族固定2×2、初始棋盘[3,2,1,0]，通过两次选格交换，所有格满足tile[index]==index才进入phase3。离线执行原点击、交换、计数与成功分支已自然得到phase3，未手写phase3。
4. `client_verified`：成功状态本身不立即发包；点击原完成按钮的0x1711af0在phase3才发CCommitScenarioQuest(taskID,NPCkey0,option0)，然后清taskID。原棋盘交换链未发棋盘、选择格、步数或随机种子上行。**这是一项客户端成功声明；服务器无法由16字节请求重新验证棋盘。**
5. `client_verified`：本族与通用CJigsawPuzzleDlg、CRefreshJigsawPic、SMiniGameStart为不同对象和调用链。不能用通用MiniGame的消息补造本族启动握手。
6. 11106是原地图静态摆放、npctype4/hide1，不是npctype10生成的本地type7。SVisitNpc服务菜单确可打开553，但首次人类点击11106是否必经CVisitNpc仍未闭合；不将普通SVisit消费者当作该首次点击的完整自然证明。
7. 下一批可由主策划直接制定`designed`的client-assertion接受政策：章节激活资格、可信11106菜单许可、重连与过期处理、提交时重新地图核验、幂等任务结算。无需等待额外人类确认；本文不授权奖励或把离线phase3当作服务器已掌握的解题证据。

## 一手来源与完整性

原映像[evidence/native-image.bin](native-image.bin)：50675712字节，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`；本文VA基址0x400000。

下表均重读PFS成员并通过原目录长度/CRC检查，SHA为解包后的成员字节。

| 原包 / 成员 | bytes | CRC32 | SHA256 |
|---|---:|---|---|
| config.pfs / autoconfig/knight.gsp.task.cmainmissioninfo.xml | 2026233 | 3f7ab7b3 | ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706 |
| config.pfs / autoconfig/knight.gsp.npc.cnpcconfig.xml | 619832 | cc437e13 | b4fc5d440380fb535a36b8e5315c5a1bf10a99f550f5bfde55bd156fca864f85 |
| config.pfs / autoconfig/knight.gsp.npc.cnpcserverconfig.xml | 420722 | 67481f85 | c6db03275d0d63106623e339742318a38b33d229bc73894d46136e8b9901aa26 |
| config.pfs / autoconfig/knight.gsp.minigame.cspecialquestuselittlegameconfig.xml | 218 | f8d94bcb | d6a95bbdc76daccaaabac470ee66f628af51366201396ecdf9d6189576a7ca48 |
| map.pfs / fubenjiaxing/npc.xml | 888 | 06370594 | 3e96b678f8213459052fcf8c9fccc9c1eb7222ac33672d2a966600513f7b32fa |
| image.pfs / jigsaw/xiaolongnv.jpg | 149418 | 146e05b8 | 42ae841ebfb4fffe175334dfbf8e0a6d88086f95fefde5c32da73fee0eba34c2 |
| ui.pfs / layouts/gamepuzzle.layout | 2051 | b0e83dad | 3eacd0edcfc82baf4aa393940d0d10574ce78b1a2c7a9576dc60e130a5a0255e |

复用根任务已有[research_prologue_puzzle_close.py](../research_prologue_puzzle_close.py)与[prologue-puzzle-native-close.json](prologue-puzzle-native-close.json)：40个受控phase样本没有重跑。本批增加的是同一棋盘从固定初始化、实际选格到成功的局部反馈，不能混称这40例已经覆盖自然解题。

## 十条原任务与实际前后边

从[catalogs/newbie-routes.json](../catalogs/newbie-routes.json)43个原intro沿原任务表PostMissionList遍历，每条路线恰好命中下表一条。未按ID加减猜测。

| 门派/root | 前驱→画卷→后继 | 人物EXP / 宠物EXP |
|---|---|---|
| 11/100101 | 100180→100120→100121 | 360 / 360 |
| 12/100201 | 100280→100219→100220 | 360 / 360 |
| 13/100301 | 100380→100319→100320 | 360 / 360 |
| 14/100401 | 100480→100419→100420 | 360 / 360 |
| 15/100501 | 100580→100519→100520 | 360 / 360 |
| 16/100601 | 100680→100619→100620 | 360 / 360 |
| 17/100701 | 100780→100719→100720 | 360 / **350** |
| 18/100801 | 100880→100819→100820 | 360 / 360 |
| 19/100901 | 100980→100919→100920 | 360 / 360 |
| 111/103201 | 103280→103220→103221 | 360 / 360 |

十条全属性及子列表逐条比较，除taskID、PostMissionList及100719 PetExpReward=350外相同：MissionType59，ActiveInfoNpcID0/Map1501；ProcessBarTime0；ScenarioInfoAnimationID0；JumpType/Map/X/Y均0；MoneyReward/SMoney/ShengWang0；ActiveTargetID/Num、AIInfoAIID、BranchNpcID均0；无奖励物品list、Note/BranchNote。DisPlayNPCID仅11106。

Start一句：“试着将其拼回原样看看是谁的画像吧。”；Finish一句：“好漂亮的姐姐啊，不知道那个道姑为什么会带着这样一幅画像呢？”；两者speaker列表均10139。此为原配置内容，不单凭文案断言自动Start/Finish的所有服务器时点。尤其不能统一把十条宠EXP写为360。

## NPC实体与菜单路径

11106原cnpcconfig：name程英、npctype4、model5004、hide1、map1501、xPos366/yPos96、zaxueid16。1501资源目录fubenjiaxing；原npc.xml**第16条**11106，pos5870,1541、dir5；第15条10139与之同坐标。它有真实原静态摆放，不是依据任务文本临时造出的NPC。

原1132590在0x11325b7明确仅允许config+8 npctype==10才走本地type7创建；11106为4而早退。相关静态NPC可见性框架见[PROLOGUE_NPC_VISIBILITY_RESEARCH.md](PROLOGUE_NPC_VISIBILITY_RESEARCH.md)。本族DisPlay列表命中11106时，原0x1259005..0x1259017有11106特例，将NPC mark设2；0x11fe6d8表的mark2分支0x11fe495在hide>=1时调用vt+0x30(true)。该mark不是Scenario state2（failed）。NPC本地可见与服务器授权仍是不同事实。

原服务553行：icon2、severStr“进行拼图”。确认的下行菜单链：

1. SVisitNpc vtable0x228191c，Process0x1214250；0x1214388..0x121439a将packet+8完整NPCkey、packet+0x10服务vector、packet+0x20任务vector传给0x120f4e0→0x1635f10。
2. 0x1635f5a..0x1635f6b将key保存于NPC UI+0xd0/+0xd4；0x1636042把服务vector交菜单构建器0x1631980。因此服务器若发SVisit(key,[553],...)，原客户端可呈现该本地服务。不是新增专用SStartPuzzle协议。
3. 点击菜单通用分发0x1638ae1减0x20c，byte表0x163f494将service553映成13，目标表0x163f42c的第13项为**0x1638e06**。
4. 0x1638e0c调用taskmanager0x1258050。此getter遍历manager+0x24的已接列表，返回首个100000≤taskID<200000的ID，未在此处校验“它是type59/这十条画卷之一”。恢复实现不能照搬这一宽范围当服务器授权。
5. 返回非0时0x1638e19..0x1638e2f把taskID及NPC UI保存的key传给0x16286e0获取专用拼图对象，再调用**0x1711820**：taskID→dlg+0x80，key两半→+0x88/+0x8c。随后关闭NPC菜单，未见网络发送。

专用对象global0x29560f4，factory0x16286e0，constructor0x17130d0，vtable0x22ce65c，RTTI CJigsawPuzzleForQuestDlg。原0x1713300加载GamePuzzle.layout并注册GamePuzzle/Button回调1711af0、GamePuzzle/Image点击回调1712090及tick1711ba0；0x1713639调用初始化1713270。

本批离线执行原0x1638ae1→0x1638e41：服务553输入、隔离已接list含100120、NPCkey=0x1122334455667788。原getter、跳表、参数传递及1711820均执行；仅factory返回隔离UI、窗口关闭回调被适配，网络入口设异常哨兵。结果taskID=100120、puzzle key仍为该64位值，零网络调用。

**尚未闭合的前链**：首次鼠标点11106是否必经CVisitNpc→SVisitNpc。普通CVisit原构造和SVisit消费者存在，但人类点击的部分前链在受保护29c/29d跳转代码内，本批没有自然click反馈。上述证据只能证明SVisit菜单确能启动553，不能宣称每一种本地打开方式必然给服务器一次启动信号，也不把“553无上行”写成“服务器完全看不到此前NPC访问”。

## 本地棋盘、自然交换与phase3

原1711d50写dlg+0x5c/+0x60=2/2，加载表现资源；原1711990硬编码加载`/artres/image/Jigsaw/xiaolongnv.jpg`，不从当前任务行或服务器随机种子选图。原ui.pfs布局有GamePuzzle/Image与“完      成”按钮。

原1713270在纹理成功后0x1713288..0x17132f0分配四格vector，依次压3、2、1、0，置phase1。此初始排列**固定**；本族查得链没有rand调用，也不使用通用难度表生成棋盘。

- tick1711ba0：phase1时累加+0x6c，超过原浮点阈值1后清它并置phase2（0x1711c02）；phase2交换进行时+0x64为真，累计动画+0x68。这里只记录原阈值，不拟定服务端秒数。
- 点击1712090：要求phase2且未在交换；从图片控件宽/高除2算格坐标，索引为x格×2+y格。已归位格tile[index]==index不进入选择；第一格保存+0x50，第二格保存+0x54，selection+0x58=2。重复同一格清选择，不交换；两格不同则置+0x64并清动画累计。它是**两次点选交换**，没有本族拖动步骤上行证据。
- render/update1712a70在动画比例达到阈值后调用1712960；0x17129e0..0x17129ed实际交换两个vector元素。此前及之后分别调用1711ef0统计tile[index]==index格数。
- 0x1712a35..0x1712a42将正确格数与2×2比较，全部正确才调用1711f40；后者**0x1711f7b写phase3**，随后进行本地成功提示/按钮文字等表现。没有在此处分配任务奖励或发送任务完成请求。

新增离线自然局部反馈，task100120（未手工设phase3）：

```text
原固定初始化: [3,2,1,0], phase1
原预览tick:   [3,2,1,0], phase2
原点击0、3:   selection1→2, swapping1
原动画/交换:  [0,2,1,3], phase2, selection0
原点击1、2:   selection1→2, swapping1
原动画/交换:  [0,1,2,3], phase3, selection0
原成功分支:   1711f7b实际写3；全程零网络调用
```

方法：复用research_battle.NativeBattleDecoder作为通用离线映像执行器（没有执行战斗函数）。纹理/控件由隔离400×400布局适配；执行原1713288..17132f8固定vector构造，原1711ba0计时、完整1712090点击、1712a70的动画完成分支、完整1712960交换和1711ef0计数。只适配控件坐标46c7f0、声音156abb0/156e0e0、显示字符串及CRT分配/cookie；成功函数实际写phase3后，于1711fa8跳到其原epilogue1712075跳过纯成功提示/按钮渲染。网络入口813860为异常哨兵，未触发。成功前状态和格数组由原指令生成，而不是调用方直接赋成已解答案；外部delta为受控测试值，不代表完整真人计时或渲染。

## 最终上行及与通用MiniGame的区别

完成按钮回调1711af0：0x1711b19比较phase==3；成立时0x1711b1f..0x1711b45构造CCommit(type0xc4a44)，taskID取+0x80，NPCkey两半、option均0；0x1711b49..0x1711b5a提交网络。无论phase，0x1711b75清taskID再关闭窗口。**成功判定与按钮关闭是两个步骤，不能把自然phase3直接说成已发提交。**

根已有40例分别把十任务phase置0/1/2/3后运行完整原1711af0，只有phase3得到16字节body `BE i32 taskID | BE u64 0 | BE i32 0`。这批原包构造反馈与本批自然交换分别证明“成功状态如何产生”和“成功后关闭发什么”；它们不是原服务端对棋盘的验证，也不是现场完整鼠标流程。原marshaller未在40例重复执行，捕获字段按已核验CCommit布局编码，见[TASK_PROTOCOL.md](TASK_PROTOCOL.md)。

本族1711900..1713654可见实现中的813860网络调用仅上述close处；已追点击、tick、交换、初始化、成功分支无棋盘/步骤提交。不能据此给最终CCommit凭空添加棋盘、耗时、种子或签名字段。

通用拼图另有：

| 项目 | 本族画卷 | 通用小游戏 |
|---|---|---|
| 对象 | CJigsawPuzzleForQuestDlg | CJigsawPuzzleDlg |
| vtable / global | 22ce65c / 29560f4 | 22ce1f8 / 2958500 |
| factory / constructor | 16286e0 / 17130d0 | 1728400 / 170f480 |
| 启动桥 | NPC服务553→1711820 | SMiniGameStart type3→1729135→1710910 |
| 原刷新图请求 | 本族链未调用 | 1710580构造CRefreshJigsawPic 0xc7921 |
| 本族完成输出 | CCommit(taskID,0,0) | 不能套用到本族 |

SMiniGameStart::Process1729100按packet+8游戏类型分发，type3的0x1729129..0x172913c走通用对象；本族factory唯一找到的直接E8调用为1638e28，1711820唯一直接调用为1638e2f。原specialquestuselittlegameconfig仅102106/207703/311102/314502四行，没有本族十任务。CRefreshJigsawPic/CMiniGameStart(0xc791f)/CEndMiniGame(0xc791c)存在不能证明本族使用它们，未将通用小游戏扩作本族服务器握手。

## 未来Module最小Interface建议（尚未实现，须主策划设计）

采用codebase-design将章节限定、菜单许可及零NPC声明归属隐藏在独立任务Module内，而不令共享分发器按type59统一完成。建议一个Module包含两项操作，名称仅为提案，不冒称现有helper：

- `open_menu(actor, snapshot, chapter, proof, current, now_ms, policy)`：只针对该角色当前路线精确的十条之一、当前active任务、正确1501私有实例，以及地图所有者确认的11106/placement16访问。返回SVisit菜单553和有界服务端许可；本地菜单显示本身不完成任务。许可保存role/epoch、task实例/章节、source_id、实例、实际绑定key与placement、位置版本、政策版本、时限。若原首次click不经过服务器，恢复开窗或菜单授权路径仍须由策略显式建立，不能伪造已收到553启动包。
- `plan_submission(actor, snapshot, intent, ticket, fresh_proof, current, now_ms, policy)`：仅接受CCommit该task、key0、option0；使用**服务端保存**的11106 key/placement16请求当前地图核验，不从zero key找NPC。检查章节、租约、实例及许可/过期后，返回明确标`designed`的“接受客户端画卷完成声明”的任务计划；随后由现有角色所有者任务事务同事务完成/奖励/后继，凭据提交成功后消费许可。拒绝通用任务ID、过期/异实例、重登旧epoch或未授权zeroNPC请求。

这里的`fresh_proof`应来自既有world_npcs.NpcInteraction/当前Location公开Interface；当前task_conversation.open按task.target.npc_id匹配，原任务目标0，不能直接把proof11106塞入普通对白并改目标。需要专用领域准入，并按任务实例唯一结算。现有task_workflow的事务/资源渠道供后续复用，不在本报告授奖或更改共享入口。

尚需主策划明确并集中登记的规则：接受客户端声明的风险范围；菜单许可是否持久化、重连恢复或要求重新访问；过期、最短等待及移动/换图/任务变动如何失效；成功重试与新请求的区分；客户端提前关闭/无包时的恢复方式。这些不能从本地1/动画阈值推得原服数值。即使要求最短等待与就近菜单，也不能宣称已防伪解题；原协议没有供服务器重算棋盘的证据。后继保持原实边，宠物EXP保留100719=350的差异。

## 本批决定、验证与未验证范围

- 方法影响决定：原type59并不提供统一完成语义；按真实UI链和十条原域区分画卷。接口不暴露棋盘验证的虚假承诺，而显式接收/校验客户端声明；地图、角色、持久化分别保持既有所有权。
- 产物：仅本文；复用根已有close研究及JSON，本批自然交换为一次性离线执行，无新增生产模块或共享修改。
- 已验证：原资源CRC/SHA、43路线唯一命中、十行字段和PetExp差异、11106真实静态摆放/npctype4、服务553跳表→原getter/参数传递、固定vector和自然两次交换→phase3、按钮close输出与通用MiniGame对象分离。
- 未验证：首次真人点击11106的CVisit前链、原服服务553绑定与防伪策略、原服持久化/超时/重连规则、完整窗口GPU/鼠标现场、生产接线/部署、正式任务结算或奖励。未把这些缺口转成用户确认或扩大运行范围。
