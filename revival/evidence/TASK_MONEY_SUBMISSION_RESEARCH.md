# 原 MissionType11 交钱提交研究

本批只读原配置与映像；来源状态与实现、部署、GUI 验收分开。结论为 `client_verified` 的范围仅为下列原指令、原配置与离线编码行为，不代表原服务端规则已恢复。

## 可以直接使用的结论

- 五条原任务都走 MissionType11 的统一 GiveDialog、`submitType=3`。确认上行是 **CSubmit2Npc `0xc2340`**，不是普通 CCommitScenarioQuest，也不是另一个带币种字段的已证专用包。
- 正常 UI 生成一个 SubmitUnit，**两个 i32 字段都写入交钱金额**：`units=[(amount, amount)]`。type12 的 `(item_key, count)` 解释不能套用到 mode3。
- body 为 `BE i32 taskID | BE u64 npcKey | BE i32 3 | compact_uint 1 | BE i32 amount | BE i32 amount`，此形状为 **25 字节**，无币种标志。npcKey 保留完整 64 位。
- mode3 的输入上限确实读取钱包 **+0xb0/+0xb4**（现金槽），并将输入截到该余额；原 GiveMoney 与 CurMoney 图标均为 `MainControl/Xianjin`。这不仅是“显示了现金”的间接推断，原输入限制本身也使用该槽。该链未使用 +0xc8/+0xcc 的绑银作相加或回退。
- 以上是原客户端的现金显示、输入约束与提交意图证据。**未取得原服务端扣款实现**，不能据此声称扣款优先级、绑定银可消费、任意币种互换或恢复项目已有用途策略自动获批。CurrencyRules 新用途仍应由对应所有者明确批准。

## 一手来源和哈希

本批直接重读 PFS 成员，PfsArchive 完成长度/CRC 检查，再 BXML 解码；未仅信任派生 JSON。

| 来源 | SHA256 |
|---|---|
| `revival/evidence/native-image.bin`，映射基址 `0x400000` | 2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791 |
| `artres/config.pfs` → `autoconfig/knight.gsp.task.cmainmissioninfo.xml` 原成员 | ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706 |
| `artres/ui.pfs` → `layouts/givedialog.layout` 原成员 | 62835a25cbcd8f0677deed64928ced59c0a024c0a62c519b65f38b05d01aa3c4 |

所有 VA 都针对上述映像，不能直接当其他客户端版本地址。现金/绑银槽的独立主背包及下行追踪见 [CURRENCY_UI_BRIDGE_RESEARCH.md](CURRENCY_UI_BRIDGE_RESEARCH.md)；本批重新追 GiveDialog 自己的现金读法，并执行该金额比较片段。

## 五条任务原表

| ID / 名称 | ActiveInfoNpcID / MapID | ActiveInfoGiveBackMoney | 唯一 PostMissionList | Start/Finish 行数 | 原奖励物品 |
|---|---|---:|---:|---|---|
| 205707 蜕变 | 10857 / 1007 | 500000 | 205708 | 4 / 1 | 无 |
| 230307 化境 | 10381 / 1007 | 2000000 | 230308 | 5 / 1 | 50397 ×1，bind1 |
| 233307 寻找火鸡 | 13874 / 1011 | 100000 | 233318 | 0 / 3 | 无 |
| 233309 寻找火鸡 | 13874 / 1011 | 50000 | 233310 | 0 / 2 | 无 |
| 233906【劳动节】奖章风波 | 10381 / 1007 | 1 | 233907 | 0 / 1 | 50417 ×1，bind1 |

共同字段：MissionType=11；MinLevel/MaxLevel/TransMinLevel/TransMaxLevel/TransformID 全0；ExpReward/MoneyReward/PetExpReward/ShengWang/SMoney 全0；RewardMapJumpType/RewardMapID/XPos/YPos 全0；ProcessBarTime=0；ActiveInfo 四矩形坐标、TargetID/Num、MiniStep/StepProbability/MaxStep、TimeLimit/IsRestartTimer、GiveBackPetID、UseItemID、OtherType、QuestionInfoNpcID 全0；ActiveInfoTeamState=1；AIID=0、BattleResult=1、DeathPunish=0、AITeamSteate=1；BattleMapType=1，其余 BattleInfo 数值全0；AnimationID/BranchNpcID=0。不存在额外 ReqMissionList、问题列表或分支选项。

233307/233309 的 DisPlayNPCID=[13874]；233906 为 [13944,13945,13946,13947]。DisPlayNPCID、对白 speaker 与 ActiveInfoNpcID 是不同字段，不能互换，也不证明该活动 NPC 已有可交互场景实例。

原文字将 205707 的500000称为“两银子”、230307称“200万”、233307/233309称十万/五万银两、233906称“一银两”。数字与输入/包金额均未发现倍率换算；已证数字字段一对一传递的范围，不据文案另造货币标识。所有原属性与子列表完整保存于文末，保留原零值、拼写和字符串。

配置解析器：字段 UTF16 名地址 `0x226c1ac`；`0xbb619d..0xbb61d1` 查询 `ActiveInfoGiveBackMoney`，`0xbb61c2` 调 `0x409db0` 取64位数，存 config+0x1a0/+0x1a4。配置金额是64位，不等于线包支持任意64位金额。

## type11 → mode3 → 确认上行的原调用

1. `0x164369d cmp eax,0xb` 是 type11 分支；`0x16436a2` 先调用 `0x10831b0`，返回为真才继续。该前置函数的完整 UI/业务语义本批未进一步归名，不能把它当服务器余额授权。
2. `0x16436ab push 3`；`0x16436ad` 取原对话 UI+0x48 的任务ID，`0x16436b0/+b3` 取 +0x3c/+0x38 的 NPCkey 两半，`0x16436bf` 调 `0x168a1e0`。该函数保存 GiveDialog+0x58/+0x5c NPCkey、+0x60 taskID、+0x64 submitType。mode3 在 `0x168a43b..0x168a448` 显示 UI+0x9c 的 GiveMoney 编辑框。
3. 确认回调 `0x1688990` 读 UI+0x64；`0x16889bf..0x16889c4` 的 mode3 调 `0x1684a20`。物品/宠物等其他 mode 走其他函数，不能拿它们的 unit 构造解释交钱。
4. `0x1684a46..0x1684a58` 检查 UI+0xa8/+0xac 的有符号64位输入大于0；否则走提示ID `0x22f97`、显示函数 `0x156d130` 并返回。本批未解此提示正文。
5. `0x1684a95` 准备 SubmitUnit vtable `0x2284ab8`；`0x1684a9d` 仅加载输入低32位，`0x1684aaf` 与 `0x1684ab3` 把同一 EAX 分别写到 unit+4、unit+8。**不是 (amount,1)**。
6. `0x1684ab7` 调 CSubmit2Npc 构造 `0xf15850`；`0x1684abc..0x1684ae6` 复制 taskID、NPCkey、mode 并追加该一个 unit；`0x1684aeb..0x1684afc` 经网络对象虚调用提交。`0x1684b07` 关闭本地 UI。真实网络边界未执行。

确认函数没有拿原 config+0x1a0/+0x1a4 比较输入、检查恰好等于任务要求金额。输入框初值归零，不能宣称客户端自动代填所需原金额或在该函数内严格锁定金额。恢复服务端应独立核对当前任务、真实 NPC、准确金额和授权，不把原客户端 UI 校验当安全边界。

### 原 marshal 与校验约束

| 原方法 | 地址 / 已证事实 |
|---|---|
| CSubmit2Npc ctor | `0xf15850`；`0xf15884` 写 type `0xc2340`；vtable `0x2284a94` |
| marshal | `0xf16270`；先 `0xf161f0` 校验，再依次写 taskID、u64 NPCkey、submitType、unit vector |
| decode | `0xf16320` |
| vector marshal | `0xf16440`；compact count 后每个 unit |
| SubmitUnit marshal / decode | `0xf16160` / `0xf15b80`；两个 BE i32 |
| generic validator | `0xf161f0..0xf16264`；taskID>=0，NPCkey 的有符号64位>=0，submitType>=0，各 unit 两字段均>0 |

generic validator 不强制 mode=3、不强制 vector 长1、不强制 unit 两字段相等、不核任务要求金额。空列表也不会在该 validator 中被拒绝；这是通用包形状检查，不能解释为服务器允许空交钱。UI 源输入64位，但只将低32位写入 unit，后续两字段又要求正 signed32；因此正常可编码金额范围应收窄到 `1..2147483647`，不能因为钱包/原表是64位就放宽线包。五原金额均在该范围。

## mode3 的现金约束与界面证据

原布局 `GiveDialog/TC/FW1/GiveMoney` 被保存为 UI+0x9c：`0x168b791..0x168b7cc`。`0x168b871` 将 `0x1681cd0` 作为输入回调，`0x168b8a2..0x168b8bf` 绑定到同一 +0x9c 编辑框。mode3 又在 `0x168a440..0x168a448` 显示该框，故不是误用了另一用途的编辑回调。

输入回调：`0x1681d61..0x1681d77` 将文本解析入 UI+0xa8/+0xac；随后：

```text
0x1681d7d  ECX = [0x2944628]          // 钱包
0x1681d83  EAX = [ECX+0xb0]           // 当前现金低32位
0x1681d89  ECX = [ECX+0xb4]           // 当前现金高32位
0x1681d8f..0x1681da0                 // signed high / unsigned low 比较输入
0x1681da2..0x1681da4                 // 超上限则把现金余额写回输入
```

`0x1681da7` 后格式化截取结果，`0x1681dfb..0x1681e08` 写回编辑框。空文本在 `0x1681e9f/+ea5` 把金额清零，并走按钮刷新 `0x1681ead→0x1680dd0`；`0x1680dd3..0x1680def` 依金额是否正启用确认。本批未穷举数字解析格式/负数文本；确认自身的非正数拒绝已如上。

余额显示回调 `0x1682260` 在 `0x168228d/+2293` 与 `0x16822af/+22b5` 都读取钱包+b0/+b4，`0x16822bb..0x16822e2` 写 UI+0x98 的 CurMoney。原绑定 `0x168b77f` 保存 CurMoney；`0x168b914..0x168b94c` 注册钱包观察者。

原 `layouts/givedialog.layout` 同时具有：

- `GiveDialog/TC/FW1/CurMoney` 静态余额文本；邻接图片 `GiveDialog/MoneyBack1/Money11` 为 `set:MainControl image:Xianjin`。
- `GiveDialog/TC/FW1/GiveMoney` Editbox；邻接图片 `GiveDialog/MoneyBack1/Money1` 也是 `set:MainControl image:Xianjin`。
- `GiveDialog/TC/FW1/GiveButton` 原文本“给     予”。

在本次有界 GiveDialog 原函数扫描中，直接钱包读取为+b0/+b4；mode3 的已闭合金额比较不包含+c8。不能把这个局部结果扩大为“全客户端绝无绑银消费”，也不能从没有币种tag推定服务器可自行任意选择钱包。

## 少量离线原指令验证

使用现有研究脚本只读载入原映像，在内联 Python `-B` 中构造隔离内存；无文件型 fixture 新增，无原客户端进程附加，无网络/数据库/服务调用。

1. **原完整 serializer**：复用 `research_task_item_submission.py` 的离线 harness，仅在内存替换输入为 task230307、NPCkey=`0x1122334455667788`、submitType3、units=[(2000000,2000000)]；执行原 `0xf16270`。原 generic validator、`0xf16440`、`0xf16160` 均到达。仅 CRT memcpy 与 security-cookie 返回适配，未替换业务字段写入逻辑。结果恰为25字节：

```text
000383a3 1122334455667788 00000003 01 001e8480 001e8480
```

与独立 BE 构造逐字节相同；大于32位 NPCkey 未截断。此项是原 encoder 执行，不是 GUI 确认按钮实测。没有把完整 `0x1684a20` 的 UI 生命周期/析构/网络跑通，UI构造链由原反汇编取证。

2. **原输入现金上限片段**：只执行 `0x1681d7d..0x1681da7`；钱包与输入为隔离内存，结果如下：

| 输入 | wallet+b0 现金 | wallet+c8 绑银 | 回写输入 |
|---:|---:|---:|---:|
| 500000 | 100 | 9999999 | 100 |
| 100 | 500000 | 0 | 100 |
| 500000 | 0 | 9999999 | 0 |

三例均符合原比较结果，现金不足时不会因为此内存中的绑银很多而通过。仅证明已执行片段，不声称覆盖了原服务端资金不足回包、货币变更竞态或GUI自动刷新。

## 未确认与接入边界

- 原服务端真正扣款币种、顺序、失败时机、金额不符的响应、是否容许多付/分次付、包重放处理均未取得；本批不设计这些规则。
- 原客户端的输入现金上限有证，但确认函数发送前没有重新读取钱包余额，输入后余额改变仍须服务器验证。
- 任务金额数值原样保留；未发现倍率转换，不能自行把金额乘100或按元宝/绑银解释。
- 五条任务的静态字段不代表全部已可接、活动已开放或全部地图已有实际NPC placement；DisPlayNPCID 不构成现场NPC实例。真实 NPCkey 应来自世界权威交互。
- 本批不为 type11 设计状态枚举、任务开始/后继发放时序，不把 CSubmit2Npc 当结算完成通知，也没有证明任何下行能替代原服务器资金事务。
- provider recipe/purpose 的明确配置授权属于货币所有者；本报告只给出可核对的现金槽证据，不修改 CurrencyRules、不沿用其他费用用途、不授权绑银消费。

## 方法、产物、验证与未验范围

采用 research Skill：当前窗口本身为主线程委派的后台研究，直接从拥有事实的原 PFS/BXML 和原映像逐项追踪，不重复委派。重新读取 ARCHITECTURE、DESIGN_AUTHORITY；因此将客户端字段校验和服务器资产事务分开，不碰角色/地图/货币的权威写入边界。

唯一写入产物为本文件 `revival/evidence/TASK_MONEY_SUBMISSION_RESEARCH.md`；写入时间：2026-10-23T17:54:25+08:00。本批未创建/修改任何 .py、catalog、policy、共享入口、原客户端或运行存档。验证限于原成员长度/CRC/哈希、五原任务完整读取、少量原 marshal 与金额比较指令；未做在线、当前客户端 GUI、NPC实例、服务器扣款、部署或并发验收。未进行攻略扩搜，原生币种槽/输入比较已可闭合，但原服扣款与恢复项目用途规则仍分别保留未知/裁定边界。

## 附录：五原配置完整字段和子列表

以下直接来自本批 PFS 解码，属性字符串不改写；node/attrs/text/children 保留字段结构，避免未显示字段被误当成不存在。

### 205707

```json
{"node":"record","attrs":{"id":"205707","MissionName":"蜕变","MissionTypeString":"换装任务","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"11","ActiveInfoNpcID":"10857","ActiveInfoMapID":"1007","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"500000","ActiveInfoGiveBackPetID":"0","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"我杨彪对天发誓，以后决不再赌，做一个堂堂正正的汉子，也不罔师父对我的一番教导。少侠肯替我去还赌债，那就是对我有再造之恩，我杨彪永世难忘！\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"找到临安的\"></T><G t=\"李百万\" npcid=\"10857\"></G><T t=\"替杨彪偿还\"></T><T t=\"500000两银子\" c=\"ffff3333\"></T><T t=\"的赌债。\"></T>","TaskInfoTraceListA":"<T t=\"找到\"></T><G t=\"李百万\" npcid=\"10857\"></G><T t=\"代还赌债\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"205708"}]},{"node":"ScenarioInfoNpcConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"这位客官，找我有什么买卖做吗？"},{"node":"string","attrs":{},"text":"我是来替杨彪偿还赌债的，一共多少钱？"},{"node":"string","attrs":{},"text":"啊，太好了，那个杨彪真是打也打不过，说也说不得，真是头疼死了。"},{"node":"string","attrs":{},"text":"<T t=\"你能替他还真是再好不过了！一共是\"></T><T t=\"500000银两\" c=\"ffff3333\"></T><T t=\"，客官可带够了吗？\"></T>"}]},{"node":"ScenarioInfoNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10857"},{"node":"int","attrs":{},"text":"1"},{"node":"int","attrs":{},"text":"10857"},{"node":"int","attrs":{},"text":"10857"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"呵呵，这位客官真是豪爽啊，我就喜欢这样的人，以后有什么生意记得来找我啊。"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10857"}]}]}
```

### 230307

```json
{"node":"record","attrs":{"id":"230307","MissionName":"化境","MissionTypeString":"化境任务","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"11","ActiveInfoNpcID":"10381","ActiveInfoMapID":"1007","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"2000000","ActiveInfoGiveBackPetID":"0","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"这蓝天平，居然看着这古董，也罢，只能去找古董商人一趟，看看能不能买下来！\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"找\"></T><G t=\"古董商人\" npcid=\"10381\"></G><T t=\"用200万买玉鸟\"></T>","TaskInfoTraceListA":"<T t=\"找\"></T><G t=\"古董商人\" npcid=\"10381\"></G><T t=\"用200万买玉鸟\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"230308"}]},{"node":"RewardItemIDList","attrs":{},"children":[{"node":"int","attrs":{},"text":"50397"}]},{"node":"RewardItemNumList","attrs":{},"children":[{"node":"int","attrs":{},"text":"1"}]},{"node":"RewardItemIsBindList","attrs":{},"children":[{"node":"int","attrs":{},"text":"1"}]},{"node":"ScenarioInfoNpcConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"这位客官，要不要也买几个洛阳铲来试试手气？"},{"node":"string","attrs":{},"text":"不了，我想问问你的玉鸟能不能便宜一些卖给蓝天平呢？"},{"node":"string","attrs":{},"text":"他？他哪来钱买啊，我都给他打八折了，他还没钱买！"},{"node":"string","attrs":{},"text":"这玉鸟多少钱？这钱我出了！"},{"node":"string","attrs":{},"text":"<T t=\"这可是极其稀有的玉鸟啊，给你算八折\"></T><T t=\"2000000银两\" c=\"ffff3333\"></T><T t=\"，客官可带够了吗？\"></T>"}]},{"node":"ScenarioInfoNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10381"},{"node":"int","attrs":{},"text":"1"},{"node":"int","attrs":{},"text":"10381"},{"node":"int","attrs":{},"text":"1"},{"node":"int","attrs":{},"text":"10381"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"好好好，一手交钱一手交货，这是玉鸟，你拿好，千万别弄丢了！"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10381"}]}]}
```

### 233307

```json
{"node":"record","attrs":{"id":"233307","MissionName":"寻找火鸡","MissionTypeString":"节日活动","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"11","ActiveInfoNpcID":"13874","ActiveInfoMapID":"1011","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"100000","ActiveInfoGiveBackPetID":"0","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"给西域客商十万银两。\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"给\"></T><G t=\"西域商客\" npcid=\"13874\"></G><T t=\"十万银两。\"></T>","TaskInfoTraceListA":"<T t=\"给\"></T><G t=\"西域商客\" npcid=\"13874\"></G><T t=\"十万银两。\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"233318"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"13874"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"看不出来还有点银子嘛！不过可惜的是火鸡已经吃完了，还是哪来的回哪去吧！"},{"node":"string","attrs":{},"text":"（愤怒）黑心商人！还敢赖账！找打！"},{"node":"string","attrs":{},"text":"保镖！"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"13874"},{"node":"int","attrs":{},"text":"1"},{"node":"int","attrs":{},"text":"13874"}]}]}
```

### 233309

```json
{"node":"record","attrs":{"id":"233309","MissionName":"寻找火鸡","MissionTypeString":"节日活动","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"11","ActiveInfoNpcID":"13874","ActiveInfoMapID":"1011","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"50000","ActiveInfoGiveBackPetID":"0","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"给西域客商五万银两。\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"给\"></T><G t=\"西域商客\" npcid=\"13874\"></G><T t=\"五万银两。\"></T>","TaskInfoTraceListA":"<T t=\"给\"></T><G t=\"西域商客\" npcid=\"13874\"></G><T t=\"五万银两。\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"233310"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"13874"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"哎，钱虽少，也是心意嘛，我也不会因为你给的少就吝啬的，我给你说个地方，那里是火鸡窝，你自己去取。"},{"node":"string","attrs":{},"text":"（欣喜）谢谢！"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"13874"},{"node":"int","attrs":{},"text":"1"}]}]}
```

### 233906

```json
{"node":"record","attrs":{"id":"233906","MissionName":"【劳动节】奖章风波","MissionTypeString":"节日任务","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"11","ActiveInfoNpcID":"10381","ActiveInfoMapID":"1007","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"1","ActiveInfoGiveBackPetID":"0","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"给古董商人一银两完成交易。 \" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"给\"></T><G t=\"古董商人\" npcid=\"10381\"></G><T t=\"一银两。\"></T>","TaskInfoTraceListA":"<T t=\"给\"></T><G t=\"古董商人\" npcid=\"10381\"></G><T t=\"一银两。\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"233907"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"13944"},{"node":"int","attrs":{},"text":"13945"},{"node":"int","attrs":{},"text":"13946"},{"node":"int","attrs":{},"text":"13947"}]},{"node":"RewardItemIDList","attrs":{},"children":[{"node":"int","attrs":{},"text":"50417"}]},{"node":"RewardItemNumList","attrs":{},"children":[{"node":"int","attrs":{},"text":"1"}]},{"node":"RewardItemIsBindList","attrs":{},"children":[{"node":"int","attrs":{},"text":"1"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"这便前往楼外楼吧。"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"1"}]}]}
```
