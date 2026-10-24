# 原客户端任务对话与经验显示

日期：2026-10-23。针对同项目 1.6.1 端游、网络版本601的本地 `native-image.bin`。本批按 research 的一手来源链定位 RTTI → type 构造 → marshal/unmarshal → Process → 本地 UI；按 codebase-design 将纯 wire Interface 保持在独立 `../task_dialog_protocol.py`，不让它授予奖励、修改角色或发送网络包。两份技能全文仍在研究上下文中，沿用其方法；已重读 `../ARCHITECTURE.md` 与 `../DESIGN_AUTHORITY.md`。

只创建/更新本文件和 `../task_dialog_protocol.py`，未改共享实现。沿用 `TASK_PROTOCOL.md` 已确认的主线基础消息，以下增加对显示路径的直接追踪。

## 结论及最小消息组合

- **经验条：** `SRefreshUserExp` type `0xc000d`，body 为8字节 BE u64 **当前经验余额**。奖励事务成功后发送当前资产余额，不是本次增加量；重试时应读取当前权威余额，避免用旧回执覆盖客户端较新的显示。
- **NPC 菜单：** `SVisitNpc` type `0xc232a`，body 为 BE u64 npcKey + compact长度/BE i32服务ID列表 + compact长度/BE i32任务ID列表。它携带菜单入口，不携带任务对白文字。
- **任务对白：** 原 CMainMissionInfo 的对白与选项由客户端根据任务状态本地取出。`TaskConversation.lines` 不需要另发为通用文本消息；仅在服务端返回内部对话模型，并不能让原客户端出现 NPC 对话。需要正确的 SAccept/RefreshState、真实 NPC key 和 NPC 菜单中的任务ID。
- **提交：** 没有找到 `SCommitScenarioQuest` RTTI。原 CCommitScenarioQuest 既用于未接任务的接取，也用于已可提交任务的交付；不能据请求名字把所有此请求直接当成完成。
- **完成显示：** `SRefreshScenarioQuestState(questID,1)` 有本地任务清理/后续表现副作用，可作为已确认完成后的状态通知；不代替服务端原子结算，也不保证每种任务都只是显示文字。

## SRefreshUserExp：已确认可接入

RTTI `.?AVSRefreshUserExp@gsp@knight@@`，虚表 `0x22705c4`。构造 `0xd55190`，`0xd5519a` 写 type `0xc000d`，对象 `+8/+0xc` 是一个64位字段。marshal `0xe40ef0` 直接把这两个 dword 交给原64位 BE writer `0x7709b0`；unmarshal `0xd55220` 调原 reader `0x770650` 后写回 `+8/+0xc`。

Process `0x1138e60` 在人物全局对象存在时把两个 dword 传给 `0x11355b0`。后者在 `0x11355c1 / 0x11355ca` **直接覆盖**人物 `+0x17c/+0x178`，没有相加；随后通过人物观察者 `+0x34` 虚调用 `+0xc` 刷新依赖显示。故消息是绝对余额，无 roleID、奖励差值、任务ID或额外 flag。

同 handler 在 `0x11355f2..0x1135664` 检查等级属性490等于10且经验达门槛，触发引导30002或30007；`0x113566e..0x11356dc` 检查11级且经验达门槛，触发引导31。这比静态文本更进一步证明10/11级有引导分支，但**仍不能推导服务器完整自动升级界限或消费规则**。刷新经验本身不在此函数自动改等级。

模块提供 `S_REFRESH_USER_EXP`、`encode_user_experience(balance)`、`decode_user_experience(body)`。编码器只允许非负 signed64 范围作为人物余额的工作域；原解码本身只是读64位，未证明更大值的合法业务含义。经验条刷新不等于已证明存在“获得XX经验”飘字/聊天通知；该奖励提示消息本轮未定位。

另确认 `SRefreshRoleData@attr` 身份为 `0xc32c8`，Process `0x113f070`。本批未补全其容器 value 布局，不用于替代 SRefreshUserExp，也不通过未经确认的属性map写等级。

## SVisitNpc：布局与实际用途

RTTI `.?AVSVisitNpc@npc@gsp@knight@@`，虚表 `0x228191c`；构造 `0xe70050..0xe700a9` 中 `0xe7008d` 写 type `0xc232a`。

marshal `0xe701b0` 顺序：

1. 对象 `+8/+0xc` → `0x7709b0` 输出 BE u64 npcKey。
2. 对象 `+0x10` → 容器 factory `0xe69750` → 虚表 `0x22812d4`。
3. 对象 `+0x20` → 同一 factory、同一容器虚表。

容器 marshal `0xe69830` 在 `0xe69859..0xe69894` 计算 vector元素数（end-begin除4）并写compact count；`0xe698fd..0xe6998a` 逐个取 i32、bswap、写4字节。相应容器 unmarshal 为 `0xf82320`，SVisitNpc 总 unmarshal `0xe700f0`。

Process `0x1214250` 有入世界、非战斗和交互状态检查。允许显示时，`0x1214388..0x121439a` 将 npcKey、第一vector、第二vector和0传入 NPC UI `0x1635f10`。不是任意未进图会话都可无条件弹窗。

`0x1635f10` 保存 npcKey 到 UI `+0xd0/+0xd4`。第二vector在 `0x1635fba..0x1635fc7` 复制到 UI `+0xa8`；`0x162f330` 遍历 `+0xa8`，在 `0x162f3bd..0x162f3c6` 逐ID调用任务状态查询 `0x1257b20`。因此第二vector是任务 ID，而非另一组服务参数。第一vector交菜单构建 `0x1631980`，用于普通NPC服务入口；任务无需伪造相应服务ID混进第一vector。

模块的 `encode_visit_npc(npc_key, first_ids=(), second_ids=())` 保留布局顺序：first_ids=服务ID，second_ids=任务ID。空列表分别是单字节00，空菜单 body 总长10字节；非空每个ID固定4字节BE。

### npc_key=0 的适用范围

`SAcceptScenarioQuest` bean末尾 npcKey=0 **允许建立任务**：接受 handler `0x125d5c0` → `0x125d070` 已先插入已接集合；刷新标记的 `0x125a950` 在key>0时调 `0x11d5260` 查场景实体，在key=0时按任务配置的NPC ID调 `0x11d1870`。所以静态NPC任务的已接信息可以使用0末字段，不因此失去任务列表。

但 **SVisitNpc 的 NPC key 不应因此也置0**。UI `0x162fa70` 首先用 UI保存的key调用 `0x11d5260`；失败时用 UI缓存的NPC配置ID `+0xd8` 调 `0x11d1870` 回退查找。缓存是否已正确设置有前提。最小接入应回显经过位置/角色校验的 CVisitNpc 实际 npcKey。对一个未建立/不存在的NPC仅发送菜单，不证明能显示任务对白。

## 本地任务状态 → 白话/提交链

`0x1257b20` 是 UI分类查询：

- 找不到已接任务时返回1。
- 对 ScenarioQuest 已接bean，state==3或任务类型40时返回3。
- 其他已接bean（包括wire state2）返回2。

故 **wire state2合法且映射进行中分类2**，但不能声称它是全部任务类型唯一的接取初态。`SAcceptScenarioQuest` 原 decoder只要求state非负；不要把UI分类1错当wire accepted state1。

NPC任务点击入口 `0x1636acf..0x1636b86`：取得任务ID，经 `0x1636b08` 调 `0x1257b20`；

| UI分类 | 原客户端行为 | 关键地址 |
|---|---|---|
| 1（未接） | 构造并发送 CCommitScenarioQuest，任务ID和当前NPC key，末字段保持默认0 | `0x1636b19..0x1636b61` |
| 2（已接进行中） | 本地对话入口 `0x164d780` → `0x164b2a0`，依任务类型显示进行中提示；普通type10走通用提示，不进入完成对白序列 | `0x164d846..0x164d862`、`0x164b4df..0x164b4f8` |
| 3（可交付分类） | `0x164d780` 设置UI `+0x64=2`，调 `0x164b530` 播本地对白/选项；若无要播的内容则直接调用 `0x1643360` 提交 | `0x164d865..0x164d87e` |

本地对白的直接字段对应证据：原解析字符串 `ScenarioInfoNpcConversationList` 地址 `0x226bba8`，parser `0xbb6a66..0xbb6a85` 将其放到 CMainMissionInfo `+0x2e0`；`ScenarioInfoBranchOptionList` 地址 `0x226bbe8`，parser `0xbb6a36..0xbb6a55` 放到 `+0x2d0`；`ScenarioInfoBranchNote` 地址 `0x226bdb0`，parser `0xbb67cf..0xbb6803` 放到 `+0x2b4`。

对白函数 `0x164b530` 在 `0x164b581..0x164b5b8` 读取配置 `+0x2e0` 和当前本地对白序号，后续读取 `+0x2b4` 分支提示、`+0x2d0` 选项。这是 TaskConversation.lines 不需要重新网络发送的直接依据。

普通type10提交函数 `0x1643360` 查本地任务配置 `+0x164==10`；无进度条时 `0x16433e9..0x164342a` 构造 CCommitScenarioQuest `0xc4a44`，放入当前任务ID、NPC key、末字段0并发送。有进度条时先走原UI进度条路径再触发提交。CCommit不是“对白文本上行”，而是本地UI在特定阶段产生的业务请求。

### 完成与 CQuestDialogEnd

`SRefreshScenarioQuestState::Process` `0x125ea00` → `0x125e660` → ScenarioQuest状态更新 `0x125c020`。wire state1在 `0x125c0f2..0x125c105` 写bean状态并调 `0x125bb30` 清理已接任务，随后刷新NPC标记、触发完成剧情/表现路径。该状态已在旧证据中记为完成分支，不是accepted。

对白播完入口 `0x1644c1a` 检查本地UI阶段为3；满足后续电影/表现条件时 `0x1644cb6..0x1644cf2` 构造 **CQuestDialogEnd `0xc4a52` + BE i32任务ID** 并发送。某些任务直接清理NPC表现而不走相同发送分支，因此不能要求所有任务完成必须收到该请求，也不能把任意CQuestDialogEnd当成服务端可信完成凭据。

推荐接线顺序（仍需原客户端实测）：合法接取后 SAccept；位置/NPC交互与目标条件都通过后，若任务已达可提交条件，先 RefreshState=3，再 SVisitNpc把任务放第二列表；客户端完成本地对白后发 CCommit；服务端按已保存交互ticket、版本/epoch/期限等校验并同事务完成/奖励，提交成功后 RefreshState=1及SRefreshUserExp当前余额。此顺序来自原显示路径，不替代跨模块的权威状态检查。

## 验证与未验证

本批必要基本验证只检查 XP8字节BE样例/round-trip、NPC非空服务/任务列表round-trip以及空菜单10字节长度；没有扩大模拟或执行真实客户端UI。

已确认的范围是原消息布局、余额覆盖语义、NPC菜单task列表身份、本地对白资源字段与UI分支。未确认/未实测：整个真实客户端交互、特殊任务类型的完整状态机、原始剧情播放时序、真实地图NPC注册、完成后奖励飘字消息、SRefreshRoleData全部字段、各任务type唯一accepted值。SCommitScenarioQuest未在本次原RTTI枚举中发现，不宣称它在任何其他版本绝不可能存在。

`SEnterDialog` type `0xc2413` 虽有 i32+UTF16LE octets+u64布局，但其 Process `0x811220` 用消息模板 `0x23577`、两个按钮和回调 `0x811090/0x16254e0` 构建通用确认框。**本模块没有实现或使用它冒充任务NPC对白。**
