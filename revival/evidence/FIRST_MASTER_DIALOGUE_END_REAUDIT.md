# 首师父真实尾句提交复核

2026-10-23；本地端游1.6.1，网络版本601。原资源/映像和生产源码只读，未操作客户端、服务、真实角色或数据库，未进行战斗。针对真人“对话完没有武器”，沿原UI调用执行，不能用服务器Peer手工补两包否定真人反馈。root追加要求独立复跑后，本批除本文新增离线验证脚本及其结构化证据，未改运行时。

## 结论与旧证据纠正

**43条首师父任务的Start三句耗尽后，原客户端发送一次CCommitScenarioQuest `0xc4a44`，随后关闭Start对白；不会追加CQuestDialogEnd `0xc4a52`。** 等待后者才发武器卡，会使真实客户端停在对白已关闭、没有选择卡的状态。本批独立离线执行了原尾句分派、原耗尽判断、原提交和原关闭指令，43条均仅捕获一包CCommit。

[NEWBIE_FIRST_MASTER_RESEARCH.md](NEWBIE_FIRST_MASTER_RESEARCH.md)首要结论把仅适用于**Finish局部phase3**的CQuestDialogEnd概括为首师父对白后上行，这是本代理先前研究中的错误；其中列出的phase3原地址本身正确，但不能用于本批Start局部phase2。本文明确替代这一概括。旧[NEWBIE_MASTER_CARD_DECISION.md](NEWBIE_MASTER_CARD_DECISION.md)及DESIGN_AUTHORITY中“CQuestDialogEnd→发卡”的契约须由root纠正，不能继续作为权威前置。此前人工CCommit→CQuestDialogEnd的Peer绿例只能证明服务器接受那两包，不能证明原UI会产生两包。

**受当前NPC/任务/位置/租约凭据约束的真实CCommit，是本批可用的首师父尾句上行。** 发卡与结算时点仍是恢复服Interface设计：客户端只证明它发什么及怎样收卡，没有原服代码证明事务顺序。收到该提交后可由root裁定并持久授权SPlayCardEffect；不能把任意无凭据CCommit当成已合法交谈。客户端包本身也不能证明真人确实逐句阅读。

## 本轮一手来源

- 原包：`D:/神雕侠侣/artres/config.pfs` 的 `autoconfig/knight.gsp.task.cmainmissioninfo.xml`；通过[pfs.py](../pfs.py)校验目录/本地头、解压长度和CRC后直接BXML解码，2460行，2026233字节，CRC32 `3f7ab7b3`，SHA256 `ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706`。
- 原映像：[native-image.bin](native-image.bin)，BASE `0x400000`，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。下列地址均VA，用[native_inspect.py](../native_inspect.py)复查指令。
- 路线索引：[newbie-master-cards.json](../catalogs/newbie-master-cards.json)43条实际角色/门派route，用每条master_task_id回查原任务，非按ID步长推测。
- 离线解释器复用[research_task_jiaxing_scenario.py](../research_task_jiaxing_scenario.py)的Probe；本批先通过终端内联执行，不修改该既有脚本；随后按root要求落为[verify_first_master_dialogue_tail_native.py](../verify_first_master_dialogue_tail_native.py)，结果见[first-master-dialogue-tail-native.json](first-master-dialogue-tail-native.json)。十车夫菜单既有原字段及parser对应见[TASK_CART_BRANCH_RESEARCH.md](TASK_CART_BRANCH_RESEARCH.md)，本轮重新读原行和相关原指令。

## 原Start入口、最后一句和关闭的完整因果链

这里“phase”始终指本地对白UI阶段，不是线包任务state。主UI指针为P；关闭函数接收其子对象P+4，因此关闭函数中的`[this+0x60]`就是主对象`[P+0x64]`，不是两个独立状态。

| 步骤 | 原指令及可确认含义 |
|---|---|
| 进入Start | `0x164d865..0x164d87e`：输入分类3时写`P+0x64=2`，调用`0x164b530`；其返回AL=0则直接调用`0x1643360`。不能把输入分类3当作Finish phase3。 |
| 查Start剩余句数 | `0x164b56d..0x164b5b8`：查任务配置，读取Start vector begin=`config+0x2e4`、end=`+0x2e8`，元素步长28字节；与UI当前序号`P+0x50`作有符号比较。 |
| 展示尚余句子 | index<count进入`0x164baad`后段；展示后`0x164be0f`将`P+0x50`加1，`0x164be7a`返回AL=1。完整文字绘制不在本轮离线执行范围。 |
| 用户继续尾句 | 回调`0x164c350`的`0x164c3d6..0x164c3ef`检查phase2，再调用原`0x164b530`；AL=0则调用原`0x1643360`。本轮从`0x164c3d6`执行到`0x164c584`，未把上述两个函数替换成固定返回值。 |
| 没有分支菜单 | Start耗尽后，`0x164b5dc`检查`config+0x2c8`即BranchNote.length；首师父此字段为空，跳`0x164bb51`返回AL=0。`P+0x6c`非零时还有局部菜单清理，本轮fixture将其设0。 |
| 原提交 | `0x1643360`查配置；`0x16433a0`确认MissionType=`config+0x164=10`；`0x16433af..0x16433bd`检查ProcessBarTime=`config+0xd8`。本族均0，进入`0x16433e9..0x164342a`构造/发送CCommit。 |
| 原线包数据来源 | 对象+4 type=`0xc4a44`，+8 questID取`P+0x48`，+0x10/+0x14 npcKey取`P+0x38/+0x3c`，+0x18 option=0；已知wire为BE i32 questID、BE u64 npcKey、BE i32 option。不是服务器人工补发的CQuestDialogEnd。 |
| 原关闭调用 | `0x1643832..0x164383b`经P+4子对象虚函数调用`0x1644b50`。`0x1644c1d`仅`[子对象+0x60]==3`才进入CQuestDialogEnd分支；本族仍phase2，直接跳`0x1644cf8`。 |

43条原任务均Start长度3、Finish列表不存在、ProcessBarTime=0、BranchNote不存在，故本次结论不是只看100186的单例。原ID集合：

```text
100184 100185 100186 100187
100283 100284 100285 100286 100287
100383 100384 100385 100386 100387
100484 100485 100486 100487
100584 100585 100586 100587
100683 100685 100686 100687
100784 100785 100786 100787
100883 100885 100886 100887
100984 100985 100986 100987
103283 103284 103285 103286 103287
```

古墓角色9的100186例，第三句原文包含“这件兵器就送给你防身了……之后你去找古墓派车夫，让他送你去嘉兴吧”；这是Start第三句，不是Finish。动画字段20006和卡片物品来自原表，不改变上述phase判断。

## CQuestDialogEnd与卡片是两条不同消费链

`0x1644c1a..0x1644cf8`在**仅phase3**时查配置。若AnimationID>0，`0x1644cbd`先调用本地后置表现`0x1255e70`，随后`0x1644cc2..0x1644cf2`构造/发送CQuestDialogEnd(taskID)。这证明该包在别的阶段存在，不证明本族Start关闭会发它。不能通过服务器先发完成state1、人为切Finish来伪造读完证据，也不能用root开场CEndPlayCG替代。

真正卡片下行仍是SPlayCardEffect `0xc001c`，BE i32 effectID；原Process `0x1744540`查CCardEffect，`0x17444a0→0x1744070`打开并填充200xx武器卡。两个按钮`0x1743990 / 0x1743a10`发送CGetCardItem `0xc041f`(effectID,itemID)，随后关卡。这里没有要求预先收到客户端CQuestDialogEnd的本地条件。本批不重复codec探针；具体原布局和已有边界验证见[WORLD_MASTER_CARD_PROTOCOL.md](WORLD_MASTER_CARD_PROTOCOL.md)及旧研究中仍有效的独立卡片部分。

## 十车夫同判据的窄复核

原任务集合及所有共同字段已本轮直接原包核对：

```text
100104 100203 100303 100403 100503
100603 100703 100803 100903 103204
Start=2；无Finish；ProcessBarTime=0；AnimationID=0；RewardMapJumpType=1
BranchNote非空；ScenarioInfoBranchOptionList仅一个可选项。
```

车夫与首师父的差异是BranchNote非空。Start耗尽进入`0x164b5dc..0x164b5f2`后，原函数改`P+0x64=5`并设置可点标志，不走首师父的AL=0立即普通提交。后续建立本地菜单的原循环和选项index0见TASK_CART_BRANCH_RESEARCH；这是本地菜单，不需伪造Finish phase3。

玩家点唯一选项后，`0x1648e88..0x1648ede`在phase5发送CCommit(taskID,npcKey,option0)，`0x164903f..0x1649048`调用同一个原关闭函数。phase5同样跳过CQuestDialogEnd。十例离线执行原选项发送→原关闭，均仅一包CCommit；本轮没有重新执行菜单文字绘制，不能将该探针称为完整点击GUI。

[NEWBIE_CART_TRANSFER_DECISION.md](NEWBIE_CART_TRANSFER_DECISION.md)当前已明确“不增加CQuestDialogEnd前置”，此项契约正确，应保留。若旧脚本在车夫后人工发第二包，也不代表原UI产生它。本结论只覆盖这十条Start/BranchNote/Jump1任务，不外推所有Jump3、血手印或其它剧情任务；坐标单位继续按既有inferred/designed记录。

## 本次原指令离线执行记录

执行环境为已有Python/Unicorn x86解释器，加载固定原映像和独立模拟内存；没有连接操作系统GUI或网络。沿用Probe的配置lookup/网络Adapter，额外映射FS:[0]所需独立页，避免使用实际进程状态。fixture：

- P+0x48=各任务ID，P+0x50=原Start句数，P+0x64=2；原任务vector用本次CRC行的真实句数构造begin/end，元素宽28。首师父config+0x164=10、+0xd8=0、+0x2c8=0；UI+0x6c=0。
- P+0x38/+0x3c使用显式假NPC key `0x1122334455667788`；P+4虚表的关闭槽指向原`0x1644b50`，不将其替换为“成功”。
- `0x89ebd0`及其lookup槽返回fixture；`0x813860`及网络发送虚槽只记录消息对象，绝不发包。
- 栈cookie检查`0x1919184`及UI注销端点`0x8015e0 / 0x800980 / 0x1614740`采用返回hook；它们不会实际创建/销毁窗口。原phase检查、原CCommit构造和原CQuestDialogEnd条件没有hook。
- 记录全局`0x29586d4=0`，排除独立的非本任务NPC关闭通知。报告“不产生CQuestDialogEnd”的判断依赖明确phase分支，不依赖此通知标志。

实际结果：

```text
首师父 43/43
start 0x164c3d6 → stop 0x164c584
trace 164b530 → 164bb51 → 1643360 → 1644b50 → 1644c1d → 1644cf8
每例 sent=[{type:0xc4a44, taskID:原ID, npcKey:0x1122334455667788, option:0}]
CQuestDialogEnd数量=0

车夫 10/10
start 0x1648e88 → stop 0x164904a；输入原phase5、option0
trace 1644b50 → 1644c1d → 1644cf8
每例 sent=[{type:0xc4a44, taskID:原ID, npcKey:0x1122334455667788, option:0}]
CQuestDialogEnd数量=0
```

第一次probe因缺独立FS页停止，第二次因fixture误写Start元素宽56而进入“还有对白”分支停止；均未作为通过结果。按原乘法/移位除数及真实容器布局修正为28后，以上原尾句整链43例和原车夫发送/关闭10例均通过。这些是离线指令证据，不是实际GUI验收。

独立复跑（项目根目录，结果仅重写上述研究JSON）：

```powershell
& 'D:/FO/FFO/runtime/python.exe' -B -X utf8 revival/verify_first_master_dialogue_tail_native.py
```

落盘脚本已实际执行，输出`master_passed=43, cart_passed=10, quest_dialog_end_sent=0`。程序断言固定原映像哈希、原配置CRC和所有每例调用轨迹，不接受缺第二包时仍强行把它补发。

## 方法、决定与交付边界

research用于回到原包和原UI因果链，避免只复用旧研究/codec结论；codebase-design用于检查Interface的**真实调用顺序**，使任务Module以一个有凭据的原提交进入卡片授权，复杂校验及幂等留在所属Module，避免调用方补造第二包。重读当前ARCHITECTURE、DESIGN_AUTHORITY并沿用用户来源顺序。

本批产物为本文、追加授权的独立离线脚本及结构化结果。任务窗口源码在本轮只读时已将`authorize_master_card`改为受凭据约束的CCommit发卡；这是工作区Implementation变化，本文没有验证其持久事务、共享接线、不可变发布或真人界面。root须同步纠正旧决定文档并让自然验证只发原UI确会发送的包；当前报告不替root发布奖励/重放政策。

未验证：完整文字绘制/物理点击、当前真人角色的任务状态、原服奖励事务时点、当前线上发布哈希和画面、读完后卡片实际可见及获武器。真人“没有武器”仍是未闭合的现场反馈，不能因本轮离线通过而宣布已修复。
