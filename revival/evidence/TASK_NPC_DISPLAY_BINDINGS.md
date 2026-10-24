# 原生NPC任务菜单与对白绑定

2026-10-23；第一方来源为当前`native-image.bin`（BASE0x400000，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`）及原配置。沿用已读research的一手来源链；用diagnosing-bugs的窄反馈环验证实际原生分类代码的正反例，不将协议编解码通过当作UI实测。已读ARCHITECTURE.md、DESIGN_AUTHORITY.md；未改共享runtime、serve、gateway、任务代码或角色。

## 可直接接线的结论

1. SVisitNpc `0xc232a` 的两组i32 vector依次为**普通服务ID**、**任务ID**。主线任务放第二组；普通服务取原`npc.cnpcserverconfig.id`，不能把任务ID塞第一组。
2. 主线任务菜单项不通过CNpcService打开对白：未接分类发CCommitScenarioQuest，已接分类3在本地调用对白UI。
3. 对普通type10任务，wire state2被分类为进行中2；state3被分类为可交付3，后者进入本地任务对白。不能将state3作为所有任务通用的接取初始状态。
4. SAcceptScenarioQuest `0xc4a45` 本身建立本地bean，不是通用“打开对白”下行。已有合法任务且目标就绪时，可先同步state3，再SVisitNpc第二组放任务ID；玩家点击该项后才进入原对白。

## 双vector的直接数据流

SVisitNpc decode `e700f0` / marshal `e701b0`；对象+8是u64 NPC key，+0x10是第一vector，+0x20是第二vector。vector为compact数量+定长BE i32元素（已有WORLD_ENTITY_PROTOCOL原生codec验证）。

`1214388..121439a` 按NPC key、第一vector、第二vector、0调用NPC UI `1635f10`。后者先保存NPC key至UI+d0/d4，第二vector参数在 `1635fba..1635fc7` 复制到UI+a8。`162f36b..162f3c6` 遍历UI+a8，对每个元素直接调用 `1257b20` 查询任务分类。

第一vector则进入菜单服务列表及 `1631980` 普通服务构建路径。点击路径 `1636bab..1636bbc` 使用服务ID查配置factory `89e000`；服务配置中的childservice形成子菜单。原表`knight.gsp.npc.cnpcserverconfig.json`的完整字段为id、icon、severStr、servicedescribe、webaddress，唯一list为childservice；没有questID字段。

## CNpcService与任务的关系

CNpcService type `0xc232b`，body为BE u64 NPC key + BE i32 serviceID（构造837400、marshal83b5a0、decode8392d0）。它没有任务ID字段，因此无法仅靠wire serviceID指定任意主线任务。

原服务表例：70“领取任务”，89/90“天尊任务”，130“领取厢房任务”，135“我要领取家族特产任务”，174“完成特产任务”，178“完成特产任务”。这些名字不证明一个通用主线映射；服务的后端行为依NPC和玩法上下文而定。不能拿service70替代SVisitNpc任务列表。

**主线的确切分支：** `1636ad8` 检查菜单项kind==4，随后任务ID从菜单项+1e0/+1e4取出；`1636b08` 调1257b20。分类1在 `1636b19..1636b61` 构造CCommitScenarioQuest（dd4780，type0xc4a44），填任务ID与当前NPC key并发送；其余在 `1636b66..1636b81` 调164d780。此分支没有构造CNpcService。

## 状态分类与本地对白

原生分类函数1257b20：先1257ac0查ScenarioQuest bean；有bean时查任务原配置+164。type40直接分类3；否则仅bean.state==3分类3，其余分类2。无ScenarioQuest时还会检查另一类任务；本探针把这类lookup固定为空，不外推其业务。

| 条件 | 原生UI分类 | 后续 |
|---|---:|---|
| 无bean | 1 | 菜单点击发CCommit，接取意图 |
| type10，state2 | 2 | 164d84b调用164b2a0，进行中提示 |
| type10，state3 | 3 | 164d86c设对白UI+64=2，164d873调用164b530 |
| type40，state2 | 3 | 特殊类型例外，不应按type10规则处理 |

`164b530` 以UI保存的任务ID查原任务配置，在 `164b581..164b5b8` 访问配置+2e0的ScenarioInfoNpcConversationList和本地对白序号。文本来自客户端，不需要把TaskConversation.lines发为自定义网络对白。若164b530没有内容可播而返回false，`164d87e` 会直接调用1643360提交；因此**必须确认任务本身确有对应对白，不能把“出现后续CCommit”当成对白已显示的证明。**

## SAccept与可用消息顺序

SAccept handler125d5c0先查已有bean；不存在才加8跳过协议头调用125d070，插入、刷新NPC标记和任务观察者。这里没有直接调用164d780。

普通对话任务候选接线：

1. 玩家点击未接菜单项，客户端发CCommit；服务端校验NPC范围、角色、任务接取条件并提交。
2. 以SAccept(state2)同步合法接取。它不会保证对白立即显示。
3. 当该任务目标确实满足、服务端准备接受对白提交时，同步SRefreshScenarioQuestState(state3)，再发SVisitNpc(real NPC key, services空或合法服务, quest_ids=[任务ID])。
4. 玩家点击任务项，原客户端分类3并读本地对白；之后的CCommit/CQuestDialogEnd必须再按服务端ticket和已提交状态校验。

如果服务端有证据在初次同步时任务已处于ready，可直接SAccept(state3)建立可交付bean；这与先state2再Refresh3在本分类函数的最终结果一致，但不是全部任务的原作接取规则。wire state1在RefreshState路径有移除/完成效果；不要因SAccept bean state1也分类2就把1当接取语义。

## 最小原生判据、产物与验证

执行 `../research_task_display.py`：隔离Unicorn直接运行原1257b20，用可控lookup Adapter提供bean和任务配置，原比较与返回代码完整执行。7项通过，见`task-display-native-predicates.json`：无bean→1；type10 state0/1/2/4→2，state3→3；type40 state2→3。

可复查原代码：`../research_task_display.py --disasm quest_menu_click`、`--disasm dialogue_class_dispatch`、`--disasm accept_process`、`--disasm dialogue_resource`。这将输出实际原映像指令，避免把本地Python重写的状态表当原生验证。

本批产物为本报告、上述探针和JSON证据；未改生产接线。未验证：真实UI弹窗/任务点击、服务表全部条目的后端玩法、每类任务的原服初态、奖励结算和剧情自动续接。现有TASK_DIALOG_PROTOCOL.md与本次独立追踪一致；WORLD_ENTITY_PROTOCOL.md中“两vector语义未知”是早期范围说明，本报告提供其后续语义证据。
