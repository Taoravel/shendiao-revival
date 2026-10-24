# 新角色自然开场：任务、电影与结束回传

2026-10-23；仅适用本地端游1.6.1 / 网络版本601。本轮按 research 与 codebase-design，已读 [ARCHITECTURE.md](../ARCHITECTURE.md)、[DESIGN_AUTHORITY.md](../DESIGN_AUTHORITY.md)、[story-opening-native-evidence.json](story-opening-native-evidence.json)、[TASK_DESIGN_GAPS.md](TASK_DESIGN_GAPS.md)、[NPC_TASK_RUNTIME_INTEGRATION.md](NPC_TASK_RUNTIME_INTEGRATION.md)，并补读当前更完整的 [NEWBIE_ORIGIN_RESEARCH.md](NEWBIE_ORIGIN_RESEARCH.md)。只写本报告，不修改实现/配置，不启动或操作客户端、不注入/发包、不跑战斗或大回归。

## 结论与接线边界

1. `client_verified`：存在独立原生下行 **SStartPlayCG `0xc0017`**，payload是一个正的BE i32 **movie_id**；它进入电影管理器加载并播放相应原脚本。普通入世界确认、空对话和任务接取消息都不能替代这条已确认的播放通路。
2. `client_verified`：电影播放结束流程发送 **CEndPlayCG `0xc0018`**，payload也是一个正的BE i32 **movie_id**，来自管理器保存的当前电影ID；不带任务号、roleid、版本、结束原因或成功标志。自然末Section完成且队列空会走该发送路径，但它属于共用结束清理，不能从包本身证明玩家完整观看了所有镜头。
3. `client_verified`：10个门派各有自己的type50序章root与intro电影，已有43条角色×门派路线。**100101/11001只对应古墓，100192不是自然主线起点，1501是后续梦境，不是通用出生图。**
4. `unknown`：客户端不能提供原服务器“创建成功后何时登记/接取root、何时发CG、重连如何恢复”的程序。可以明确设计一份持久化开场状态与预期movie，等匹配的真实结束回传才生成受围栏约束的剧情完成事件；该状态机与重试规则须标 `designed`，不能宣称已经完整还原原服。

## 原包核验与已有路线

本轮使用 [pfs.py](../pfs.py) 直接读取原 `D:/神雕侠侣/artres/config.pfs`，检查目录/本地头、解压长度与CRC后BXML解码。任务表 `autoconfig/knight.gsp.task.cmainmissioninfo.xml`：2460行，2026233字节，CRC32 `3f7ab7b3`，SHA-256 `ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706`。本轮复查100101及关键后继、100112与100192；没有运行会覆盖旧产物的研究程序。

原100101为 `[主线]序章缘起`，MissionType=50，ScenarioInfoAnimationID=11001，PostMissionList为100184/185/186/187，无incoming；其 ActiveInfoNpcID/MapID、RewardMapID等字段都是**0**。这证明该root不是等一个NPC空对白来交付，也不能把ActiveInfoMapID的0解释成“出生地图0”或“任意图均合法”。门派映射来自后继任务、建角门派限制、schoolinfo与电影最后Setmap联查。

原路线已在 [catalogs/newbie-routes.json](../catalogs/newbie-routes.json) 给出43条唯一组合，详情和原值见 [newbie-origin-client.json](newbie-origin-client.json)。应沿用该只读目录，不能把以下10条root依次派给一个角色：

| 门派ID | 门派地图 | root / intro movie |
|---:|---:|---|
| 11 古墓派 | 1100 | 100101 / 11001 |
| 12 丐帮 | 1102 | 100201 / 11002 |
| 13 西域密宗 | 1103 | 100301 / 11003 |
| 14 白驼山庄 | 1108 | 100401 / 11004 |
| 15 大理段氏 | 1105 | 100501 / 11005 |
| 16 全真教 | 1101 | 100601 / 11006 |
| 17 桃花岛 | 1106 | 100701 / 11007 |
| 18 绝情谷 | 1107 | 100801 / 11008 |
| 19 百花谷 | 1104 | 100901 / 11009 |
| 111 少林 | 1110 | 103201 / 11032 |

古墓root结束后，RequestRoleIDList唯一选择：角色2→100184/movie20025，5→100185/movie20037，9→100186/movie20006，10→100187/movie20001；这四条都是type10，目标map1100/NPC10014陆无双，之后汇入type59的100188穿武器节点。角色ID须由原建角配置及形象映射取得，不能拿shape色号直接当角色行ID。后继中的animation字段也不能据此宣布全部已能自动完成。

后续关键边本轮直接复查：100104古墓车夫（目标1100/NPC10260）奖励传到1006格(36,221)；100106血手印（目标1006/NPC10498）奖励传到1501格(63,79)；100112目标1006/NPC10082，唯一后继100192；100192的incoming只有100112，目标1006/NPC10899。故可信测试offer100192不能升级成所有新角色的默认开场。

## 原电影脚本与地图含义

本轮重读并CRC检查10部intro原脚本。11001为 `movie/11001.txt`，UTF-16带BOM，46710字节，CRC `f2723192`，SHA-256 `f63fa3eb18d2b7a789cdb85e472f5d4aebc1ac91145327af1e6882d5426d8528`。原文可在 [newbie-source/11001.txt](newbie-source/11001.txt) 对照：

- 第1行 `Setmap id=1009 pos=15,137`；第12行 `Start`。
- 第812行 `Setmap id=1100 pos=22,55`；后段演员最终走到格(93,72)。
- 第846行 **`Return time=100`**，第847行 **`End`**；后面的动作说明注释不是额外剧情完成条件。

另外9部脚本的CRC依次为11002=`7341ec28`、11003=`a015ed3e`、11004=`ad3a199c`、11005=`94df0380`、11006=`287f7d32`、11007=`5e73d120`、11008=`7bd9f443`、11009=`4dd26542`、11032=`32a4284a`；本轮逐项原包读取通过。各movie完整SHA与本门派Setmap证据已保存在newbie-origin-client，不重复生成。

**1009是intro电影中的场景，不等于服务器应把持久出生位置设为1009。** 原movie的Setmap/演员MoveNPC坐标属于客户端电影播放；Return恢复电影前的场景上下文。精确原服出生格坐标仍未由客户端证实，43路线中的cinematic_endpoint均明确 `server_spawn_confirmed=false`。合法恢复位置若选门派可走候选，需要主策划设计并持久化，不能把电影演员终点称为原服务端出生坐标。CG播放期间也不能把电影镜头换图当作服务器跨图结算或普通位置提交。

## 原生启动消息及消费者

所有VA来自既有 [native-image.bin](native-image.bin)，BASE `0x400000`，SHA-256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`；本轮仅静态读原指令。

| 消息 | 身份、type与codec |
|---|---|
| SStartPlayCG | RTTI `.?AVSStartPlayCG@gsp@knight@@`，`0x2888040`；vtable `0x22708b0`；构造 **`0xd574b0`**，`0xd574b8`写type **`0xc0017`**、object+8默认0；marshal **`0xe410e0`**，unmarshal **`0xd57540`**，validator `0xd574d0` |
| CEndPlayCG | RTTI `.?AVCEndPlayCG@gsp@knight@@`，`0x2885884`；vtable `0x226fab8`；构造 **`0xd4f070`**，`0xd4f078`写type **`0xc0018`**、object+8默认0；marshal **`0xe3fd70`**，unmarshal **`0xd4f110`**，validator `0xd4f090` |

两者payload均为 **BE signed i32 movie_id >0**，固定4字节；原默认0不满足最终合法性检查。既有story-opening-native-evidence已离线执行两decoder并确认11001/`00002af9`与消费4字节；本轮没有重复执行codec。

SStartPlayCG::Process **`0x12c43b0`**：检查电影管理器全局`0x2945620`存在，再取消息object+8，调用 **`0x12c4140(movie_id)`**。

`0x12c4140`准备电影UI：在`0x12c4336`保存movie_id到manager+0x38、`0x12c4339`置manager+0x3c=1，`0x12c4347`保存电影前scene+0x110到manager+0x40，然后`0x12c437a → 0x12c3f10(movie_id)`。该路径使用当前场景对象，所以必须已有有效世界/场景上下文；不能仅在建角成功包后、场景尚未建立时随意发送并称安全。

`0x12c3f10 → 0x12c3be0`按movie_id构造脚本路径并解析，成功后从section队列取首项存manager+0x60，经section虚表+4开始执行。SAcceptScenarioQuest的已知路径`0x125d5c0 → 0x125d070`负责把bean放入任务集合、更新标记与跟踪；本轮未取得“只发该接取bean即可自动播放root11001”的证据，应使用已确认的SStartPlayCG启动链。

原脚本命令 `Start` 对应 **CStartSetion**（原拼写）：vtable`0x229ed80`，方法`0x12b9a10 → 0x12bc870`。后者检查应用`0x2945060+0x3d8 = 0x2945438`，非0则清标记并`0x11d3a10`移除scene+0x39c的intro遮罩。这里是实际Section开始动作，不是网络首次入世界ACK。

## Return、自然结束与CEndPlayCG发送

原 **CReTurnSection** vtable`0x229ed64`；`0x12b99d0`开始时调用 **`0x12c0bf0`**，后者读manager+0x40保存的原场景ID，`0x12c0c17 → 0x11e0a80`恢复场景上下文。另见 [NEWBIE_ORIGIN_RESEARCH.md](NEWBIE_ORIGIN_RESEARCH.md) 的Return与出生点限制。不能删除Return或用发奖传送覆盖原图来掩盖未完成的电影流程。

原 **CEndSetion** vtable`0x229ed9c`；`0x12b9ae0`开始时重置Section计时/完成位，并设manager+0x3d=1；Section tick `0x12b9b00`累计delta，到阈值调用完成方法 **`0x12b9b60`**，置section+0xc=1并清manager+0x3d。

电影管理器tick **`0x12c0b00`** 先要求manager+0x3c非0且当前section(manager+0x60)存在；虚调用section tick。发现当前section+0xc完成后，`0x12c0b28`移除section，清manager+0x60；如果队列仍有项则`0x12c0b47 → 0x12bc6c0`继续，**队列空才`0x12c0b52 → 0x12c0970`**。这是原自然播放完毕路径，而非按固定服务器计时模拟完成。

共用结束 **`0x12c0970`**：manager+0x3c非0才进入；`0x12c09a2`构造CEndPlayCG，`0x12c09aa`写type0xc0018，`0x12c09b2..0x12c09b9`把**manager+0x38当前movie_id**放请求object+8；清理Section/电影UI后，若连接存在则`0x12c0a24..0x12c0a3e`走连接vtable+0x3c发送。随后清播放位，`0x12c0aa7..0x12c0ac4`清intro标记/黑层，`0x12c0ac9`清movie_id。

**证据限制**：结束函数还有`0x12c4383`（电影UI准备失败的清理分支）、`0x1570bfd`、`0x1570f9e`等直接调用者；后两者本轮没有扩展命名。UI失败分支是否发送还受manager+0x3c此前是否已置位约束，不能断言每次加载失败都会发包。可确认的是，同一CEndPlayCG没有“自然End / 跳过 / 其他清理”的区分字段。客户端CEndPlayCG::Process为`0xd4f0c0 ret 8`，因为它是上行；本项目没有原服务器消费者源码，本轮不能伪造其原任务结算实现。

## 新角色入场与type50等待规则的精确缺口

旧story-opening JSON只记录100101和一部电影，不覆盖全部门派。旧BLACK_MOVIE_MASK报告把SEnterWorld对象+0x48/+0x4c叫“经验”，已被NEWBIE_ORIGIN_RESEARCH的后续原生链纠正：这里仅称**intro判别字段**；真实经验经packet对象+0xf8/+0xfc→RoleInfo+0x80→manager+0x178传递。不得因真实EXP=0就自行重播开场，也不得把EXP伪造为1解锁。

SEnterWorld `0xc0006`原process`0x8337c0`的`0x83380a..0x83382b`由intro判别值产生应用+0x3d8；置位时可安装遮罩并阻止普通输入，详情见 [MOVEMENT_INPUT_GATES.md](MOVEMENT_INPUT_GATES.md)。这只证明“客户端进入等待intro状态”，**未证明该标记会自己选择门派root并主动请求SStartPlayCG**。创建响应与普通入服字段也没有替服务器保存持久化剧情进度。

判别的符号/高低字可精确写为：**将该64位值按signed解释，`intro_discriminator <= 0`时BL=1，`>0`时BL=0**。在小端客户端对象内，SEnterWorld **outer+0x48是低32位、outer+0x4c是高32位**，对应RoleDetail inner+0x40/+0x44；这不是网络包固定字节偏移，前面有变长名字，wire仍按BE64先写高字。原指令分别为：

| 高/低字条件 | 原分支 | 写入App+0x3d8 |
|---|---|---:|
| high32按signed >0 | `0x83380a cmp high,0; 0x83380e jg` | 0 |
| high32按signed <0 | `0x833810 jl` | 1 |
| high32==0且low32按unsigned >0 | `0x833812 cmp low,0; 0x833816 ja` | 0 |
| high32==0且low32==0 | `0x833818 mov bl,1` | 1 |

SEnterWorld构造`0xfe4160 → 0xfdfe90`在outer+8建立RoleDetail；`0xfdfeba xor ebx,ebx`清零，**`0xfdfff8 / 0xfdfffb`分别将RoleDetail+0x40/+0x44写0**，故默认判别值0及其进入intro分支的效果有直接证据。构造默认值只证明新对象初始化，不等于原服务器会向每个新角/旧角永远发送0。

由该静态分支直接可得：0→flag1；1→flag0；2^32（high=1、low=0）→flag0；任意signed64负值→flag1。`0x00000000ffffffff`仍是正值，低字虽最高位为1也走flag0，不能把低字按signed32单独判断。本轮遍历整个普通入场process `0x8337c0..0x834200`，对outer+0x48/+0x4c仅见上述两次直接读取；没有找到“值1另有业务用途”的直接消费。此结果只覆盖该处理器的显式成员读取，未穷举全客户端别名、泛型结构拷贝及一切后续用途，不能据此将原64位字段改称已证实bool。

对已完成开场的旧角色，已确认的行为仅是：若入场仍发0，会重新置intro等待flag；若发任一signed64正值，则这处比较不会置该flag。**尚无原服报文或服务端源码证明“已完成角色原值恒为1”、它是布尔值、任务次数、累计进度或别的计数。** 因而“完成后发送某个正值/1”必须由主策划明确标designed；本报告不给1授予client_verified，也不从旧角色当前XP或等级计算该字段。后续CG Start/结束清flag是运行内动作，不能替代重登入场值的持久化政策。

首次入图的 **CAfterEnterWorld `0xc003d`**只表示原首次reason516015路径的确认，见 [SCENE_READY_RESEARCH.md](SCENE_READY_RESEARCH.md)。它不带movie_id，也不经过上述Section结束链，所以不能用它完成type50；普通CCommitScenarioQuest、CQuestDialogEnd、空对话、一次移动也不能代替匹配的CEndPlayCG。

以下可供主策划明确 `designed`，而原message/字段与路线保持 `client_verified`：

- 新创建来源如何原子登记唯一门派root与intro阶段；何时将SAcceptScenarioQuest同步给客户端、root初态/value1/value2如何取值。普通type10使用的state2本地策略不能未经决定直接称type50原始初态。
- 在初次世界/场景上下文建立后启动对应movie的具体服务端时点；首次世界确认可以作为设计调度触发，但不能作为剧情完成证据。原服这两包精确相邻顺序未证实。
- 由角色状态所有者保存`未启动/等待该movie结束/已完成`及学校、角色行、root、expected_movie和登录epoch；匹配预期CEndPlayCG才经剧情所有者生成完成事件并一次性推进合法后继。它是对原生结束意图的服务器验证，不能冒称防篡改的完整观看证明。
- 重复/过期/不匹配movie回传拒绝或返回既有回执；断线重播、跳过是否等同完成、超时与恢复策略需明确。原wire没有version/nonce，同一movie迟到重传不能靠包字段完全消歧，不能虚构“恰好一次网络结束”。
- 原服精确出生坐标、伤势/经验与intro判别字段的全部业务取值未知；旧角色无创建来源不自动重置主线。CG内Setmap不修改持久化权威位置，真正任务传送沿现有地图所有者交接。

这些规则在角色/任务事务中保持阶段、完成凭据与后继一致，提交后才投递逻辑消息；网络连接仍只拥有编解码与发送队列。不得以全局世界锁或把电影时长阻塞在网络循环的方式实现等待。

## 官方端游旁证与验证范围

本轮尝试重开既有两页“序章缘起/第一次做任务”时抓取失败，未伪称重新读到正文。定向查询取得[官方剧情任务资料（路径日期2012-07-28）](https://sdxl.wanmei.com/info/renwu/script/20120728/133491.shtml)：其序章介绍支持玩家醒在门派、见本门师父拿武器后由门派车夫前往嘉兴的方向，并列0级领取条件。该历史网页没有协议、movie ID、出生格坐标或CEnd验证细则，也早于本地含少林的10派内容；不用于覆盖当前包的门派/路线。

research方法实际用于先读已恢复资料，再对原包关键行与10部movie作CRC复核，最后以RTTI→codec→普通网络handler→Section自然结束→网络发送闭合链路；没有从手游借字段或剧情。codebase-design实际用于将电影codec **Adapter**、剧情阶段 **Module** 与角色/地图 **Interface** 分开：电影临时场景、任务完成、权威位置各保持原状态所有者；剧情消息在现有 **Seam** 以不可变ID/预期状态传递。

已验证：原配置与脚本读取/CRC、root和后继原值、两个电影包的静态布局/正值约束、启动消费者、Start/Return/End及自然结束发送链。既有decoder执行结果仅引用已有JSON；本轮未新增执行探针、任务推进或运行时测试。未验证：原服开场调度/初态/断线/跳过策略、完整服务器算法及客户端实测画面；报告不代表新角色自然开场已经接入或可玩。
