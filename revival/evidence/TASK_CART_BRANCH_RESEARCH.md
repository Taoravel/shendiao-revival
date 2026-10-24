# 新手车夫剧情分支：菜单、提交与传送证据

2026-10-23。范围：10条新手车夫任务的原配置和原生本地对白/菜单调用链。只读 `artres/config.pfs` 与 `evidence/native-image.bin`，运行隔离原指令 fixture；未访问运行中的客户端、在线服、角色数据库或共享运行时。

## 可以用于实现的结论

- **选项使用已有 `CCommitScenarioQuest=0xc4a44`，不是另造一个分支包。** 该包的最后一个 i32 在本地 UI 阶段5被写入选中选项索引。列表从 **0** 开始；这10条唯一的“好的，启程 / 我准备好了”都发送 choice=0。普通无分支提交也默认尾字段0，**不能只看尾字段0就判断客户端走过分支菜单**。[N2、N3、P1]
- 两句本地 `ScenarioInfoNpcConversationList` 播完后，原 UI 直接用 `ScenarioInfoBranchNote`、`ScenarioInfoBranchOptionList` 建菜单；所查调用链没有等待额外 `SNotifyScenarioQuest` 下行。必要的前置是任务进入可交付 UI 分类3（普通type10通常由任务state3得到）、正确NPC菜单和已保存的NPC key。[N1、N2；既有 TASK_DIALOG_PROTOCOL]
- **分支菜单显示判断检查 BranchNote 字符串非空，并非 BranchNpcID 非0。** 原 BranchNpcID 在 config+0x2b0；+0x2c8 是 BranchNote 字符串的长度。后者才是 `0x164b5dc` 检查的字段。[N1]
- 少林103204原表存在不一致：ActiveNpc与两句对白NPC均13290，BranchNpcID却10260。保留此原值；所查菜单构建函数没有读取+0x2b0，不能据此推断UI会自动改成古墓车夫、必须找古墓车夫，或应静默修表。[S1、N1]
- 原任务明确给出 RewardMapJumpType=1、RewardMapID=1006、原X/Y两组36/221和71/242；**本批未证实它们的单位转换。** 提交包不带坐标，所查本地对白/完成路径不读取RewardMapID/X/Y，也没有找到针对此字段的×16消费指令。不能把原数字直接交给接收逻辑像素的传送Interface，更不能将“×16”写成已证实原服事实。[S1、N4]

## 方法与原始来源

已读本批适用 `research/SKILL.md`、`diagnosing-bugs/SKILL.md`，以及项目 `ARCHITECTURE.md`、`DESIGN_AUTHORITY.md`。目录搜索没有找到本项目 GLOSSARY/ADR 文件。当前本身是主线程委派的背景研究，不再递归派代理。

- research：每项跟到原配置/parser/调用处，不从字段名猜 wire；单份报告保存明确已知与未知。
- diagnosing-bugs：采用短小可重复、可捕获错误“第一项从1起”的原指令反馈 loop。默认fixture成功，指定错误预期1会精确失败；只改预期，不改原字节。当前没有授权修复或可运行的原UI症状，因此没有执行技能的线上复现、生产插桩和修复阶段，也不声称该fixture复现了完整真实UI。
- 本批没有新增玩法裁定。协议事实是 `client_verified`；服务端如何授权、事务结算、传送及重试，仍应由角色/地图所有者在已有Seam实现。

S1：`D:/神雕侠侣/artres/config.pfs` → `autoconfig/knight.gsp.task.cmainmissioninfo.xml`，本批直接重读，经原记录长度/CRC和完整BXML解码。原解压字节SHA-256：`ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706`。

N1–N4：`D:/神雕侠侣/revival/evidence/native-image.bin`，SHA-256：`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`，加载基址0x400000；以下地址均VA。使用现有 `native_inspect.py` 和新增独立 `research_task_cart_branch.py`。

## S1：10条原资源的精确差异

全部 MissionType=10、ScenarioInfoAnimationID=0、RewardMapJumpType=1、RewardMapID=1006。每条恰好两句 NpcConversation、两个对应 NpcID、一个 BranchOption；BranchNote均为“嘉兴是一个美丽的江南小镇，现在我就要送你去嘉兴了，你准备好了吗？”的原富文本。下表坐标原样列出，**尚未换单位**。

| task ID | 原车夫 | ActiveMap/Npc | BranchNpcID | 唯一选项（索引0） | 原Reward X/Y | PostMissionList |
|---:|---|---|---:|---|---|---:|
| 100104 | 古墓派车夫 | 1100/10260 | 10260 | 好的，启程 | 36/221 | 100105 |
| 100203 | 丐帮车夫 | 1102/10262 | 10262 | 我准备好了 | 71/242 | 100204 |
| 100303 | 西域密宗车夫 | 1103/10263 | 10263 | 我准备好了 | 71/242 | 100304 |
| 100403 | 白驼山庄车夫 | 1108/10268 | 10268 | 我准备好了 | 36/221 | 100404 |
| 100503 | 大理段氏车夫 | 1105/10264 | 10264 | 我准备好了 | 71/242 | 100504 |
| 100603 | 全真教车夫 | 1101/10261 | 10261 | 好的，启程 | 36/221 | 100604 |
| 100703 | 桃花岛车夫 | 1106/10266 | 10266 | 好的，启程 | 71/242 | 100704 |
| 100803 | 绝情谷车夫 | 1107/10267 | 10267 | 我准备好了 | 36/221 | 100804 |
| 100903 | 百花谷车夫 | 1104/10265 | 10265 | 好的，启程 | 36/221 | 100904 |
| 103204 | 少林车夫 | 1110/13290 | **10260** | 好的，启程 | 36/221 | 103205 |

103204 两句 ScenarioInfoNpcID 都是13290。100803 Description 还写“传送到临安”，但Purpose/Trace/BranchNote均写嘉兴，RewardMapID为1006；这是原文字间的不一致，不能用单句描述覆盖原目标地图。

## N1：原字段位置与本地对白转分支

原 parser 直接对应：

| 字段 | 名字字符串 VA | parser / config对象位置 |
|---|---:|---|
| ScenarioInfoBranchNpcID | 0x226bde0 | 0xbb6790推字段；0xbb67b3解析；0xbb67bc写config+0x2b0 |
| ScenarioInfoBranchNote | 0x226bdb0 | 0xbb67cf–0xbb6803，std::wstring位于+0x2b4，长度+0x2c8 |
| ScenarioInfoBranchOptionList | 0x226bbe8 | 0xbb6a36–0xbb6a55，vector位于+0x2d0，begin+0x2d4/end+0x2d8 |
| ScenarioInfoNpcConversationList | 0x226bba8 | 0xbb6a66–0xbb6a85，vector位于+0x2e0，begin+0x2e4/end+0x2e8 |

原入口已在 `TASK_DIALOG_PROTOCOL.md` 确认：`SVisitNpc`第二列表列出任务ID；`0x1257b20` 把普通type10的任务state3分类成UI3；NPC任务点击后 `0x164d865–0x164d873` 设置对白UI阶段 `+0x64=2` 并调 `0x164b530`。state2分类为进行中UI2，不会直接进入该完成对白路径。该事实不意味着服务端可未经任务/NPC/位置校验就给任意任务发state3。

`0x164b530`：

1. `0x164b56d` 查原任务配置；`0x164b581–0x164b5b8` 算 NpcConversation 数量，与UI当前对白序号 `+0x50` 比较。
2. 仍有对白时走 `0x164baad`；读取相应NpcID，渲染本地富文本。`0x164be0f` 把对白序号加1。10条原配置有两句，因而通常先显示第一句，再第二句。
3. 用户继续对白的回调 `0x164c350` 在UI阶段2时 `0x164c3de–0x164c3e0` 再调同一个 `0x164b530`。已无剩余对白后，回到该函数的 `0x164b5be` 后半段。
4. `0x164b5dc` 检查 config+0x2c8，即 **BranchNote.length**。若0，返回没有分支内容；若非0，`0x164b5eb` 改UI阶段为5，`0x164b5f2` 设置可点菜单标志，`0x164b5fc` 起渲染本地BranchNote，`0x164b6b0` 起遍历本地BranchOptionList。

本函数所查完整反汇编范围 `0x164b530–0x164bea4` 没有读取 config+0x2b0。故本批只把BranchNpcID记为原存在字段，不给它虚构“必须等于当前NPC”的客户端条件，也不把少林异常当作已证明的报错来源。

## N2：选项数据从0开始，保留额外退出项

`0x164b6a4` 将选项迭代计数 `[esp+0x14]` 清0；每项步长0x1c（原wstring对象），从 OptionList 逐项生成可点击文字：

- `0x164b8b5–0x164b8b9`：取迭代计数，写入新菜单item+0x30。
- `0x164b8bc`：item+0x34置0。
- `0x164b8c7`：迭代计数加1；`0x164b8cc`：字节偏移加0x1c。

遍历后另加一项，文字从原表getter `0x89e000` 的条目10003取得（`0x164b9f0`）；`0x164ba81` 把其item+0x30写成 `0x2713`（10003）。本文把它称为“退出/保留菜单项”，没有在本批独立提取其中文caption。它不是第二个任务分支，也不是PostMissionList序号。

菜单点击回调 `0x164c350` 后半段：阶段5不走“继续下一句”路径，而在 `0x164c483` 起找到被点菜单对象；检查点击对象类型/事件后，`0x164c579` 从item+0x30取值，`0x164c57f` 调 `0x1648d00(choice)`。中间没有加1或减1。

## N3：phase5发送 CCommitScenarioQuest，末字段就是选择值

`0x1648d00` 读取UI阶段+0x64。phase4用另一个协议（0xc4a48），phase5走本次车夫分支：

| VA | 原行为 |
|---:|---|
| 0x1648e88 | 比较UI阶段5 |
| 0x1648e8d | eax = 传入的菜单值 |
| 0x1648e91–0x1648e96 | eax==10003时跳过发送，转退出处理 |
| 0x1648e9c | packet vtable=0x227d670 |
| 0x1648ea4 | packet.type=0xc4a44 |
| 0x1648eac–0x1648eb2 | 从UI+0x48复制当前任务ID |
| 0x1648eaf、0x1648eb6、0x1648ec1–0x1648ec5 | 从UI+0x38/+0x3c复制实际NPC key |
| 0x1648ec9 | 将eax原样写packet末字段（对象+0x18） |
| 0x1648ecd–0x1648ede | 取网络发送Interface并调用其虚函数 |

原 marshal `0xe57530`：任务ID对象+8 → `0x770960`（BE i32），NPC key对象+0x10/+0x14 → `0x7709b0`（BE u64），选项对象+0x18 → `0x770960`（BE i32）。body固定16字节：

```text
i32 task_id | u64 npc_key | i32 choice
```

例如100104、synthetic npcKey `0x1122334455667788`、选择0的body为：

```text
00 01 87 08 11 22 33 44 55 66 77 88 00 00 00 00
```

body没有 BranchNpcID、分支文字、目标地图、目标X/Y、任务版本、租约或交互票据。NPC key来自UI此前保存的互动实体key，不来自BranchNpcID这个配置整数。原 marshal还检查选项非负，不能把-1当作未经确认的取消协议；本地保留项10003根本不发送此包。

**可复用既有codec**：`task_protocol.decode_commit_scenario_quest` 的末字段仍可保留通用 `option` 命名；本次证据仅将它在phase5的含义确认为0-based选项索引，不将所有任务都概括成分支提交。

## 下行和对白结束的区别

本地链为：可信任务已可交付 → 正确 `SVisitNpc` 菜单 → 本地两句对白 → 本地分支菜单 → 选中0后 `CCommitScenarioQuest`。上述菜单生成/选中链未发现中间分支下行。

原映像中未找到精确名称 `SNotifyScenarioQuest` 的RTTI字符串；现有协议索引中的 `SNotifyStart=0xc4a9c` 属另一个原类型，本文没有把它作为车夫前置。不能仅凭“Notify”名字使用它。

`CQuestDialogEnd=0xc4a52` 是另一个阶段的通知。`0x1644c1d` 检查的是完成对白UI阶段3（该函数的this偏移使其读取 `[esi+0x60]`）；满足动画/RewardMapJumpType等条件时 `0x1644cb6–0x1644cf2` 调显示后续并发送 `i32 task_id`。**它不是本次阶段2→阶段5的选项选择协议。** 这10条本次查看的配置没有 FinishConversation，因此不能为了执行车夫传送而任意要求一定先收到CQuestDialogEnd。

普通 `0x1643360` 在type10没有进度条的提交路径也发相同 CCommit且choice默认0；初次接取还使用同一包。服务端需要自己持有任务阶段、可交付授权、NPC/位置/任务版本与连接租约信息，不能由wire中的choice0单独证明“两句对白和菜单真的已播完”。

## N4：RewardMap字段与坐标单位——本批明确未证实

原parser：

| 字段 | UTF-16字段名VA | 原存值位置 |
|---|---:|---|
| RewardMapID | 0x226c4b8 | 0xbb5c88 → config+0xcc |
| RewardMapXPos | 0x226c49c | 0xbb5cc7 → config+0xd0 |
| RewardMapYPos | 0x226c480 | 0xbb5d06 → config+0xd4 |

这些parser只读整数并保存，未在存入前乘16。定向检查 `0x125c020`（state1）、`0x1255e70`（完成fallback）和 `0x164b530`（本地对白/分支）未发现对这三个配置位置的消费。完成fallback确实使用RewardMapJumpType参与电影立即播放/暂存分流，但这不等于已查到执行地图传送。

本次研究因而没有拿到“RewardMapX/Y是cell”或“客户端将它们乘16后形成SRoleEnterScene坐标”的原生指令证据；CCommit也未携带坐标，原服务端如何生成入场消息不在客户端映像中。其他portal配置或地图代码的×16不能自动证明这个任务字段的单位。

集成方若选定×16，应先由世界Module的目标地图/可走格和相同坐标源进一步确认，或由主策划集中记录为 `inferred / designed`。转换后候选值36×16=576、221×16=3536，71×16=1136、242×16=3872，仅是算术候选，不是本报告的原服坐标结论。地图权威迁移仍必须走现有prepare/commit/handoff契约，不能只改显示位置或任务表。

## P1：必要离线fixture与结果

新增独立 `D:/神雕侠侣/revival/research_task_cart_branch.py`：直接执行原菜单索引写入指令 `0x164b8b5–0x164b8bf`，和原phase5构包指令 `0x1648e88–0x1649037/0x164903f`。只替代网络Interface查找/发送回调，观察原对象字段；不连接网络、不打开账户库。Synthetic key用于辨认64位字段是否被原样复制，不是任何在线NPC。

已运行：

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 revival/research_task_cart_branch.py
```

退出0：10条原配置两句/单选结构核对通过；10条第一项均原生写索引0并构造choice0；额外synthetic第二项索引1会原样构造choice1；保留值10003无发送。第二项用例只证明handler保留传入数值，不声称本表有第二个合法选项，服务端仍应严格限制为0。

故意要求第一项为1：

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 revival/research_task_cart_branch.py --expect-first-option 1
```

退出1：`AssertionError: first option is 0, expected 1`。这为错误1-based接线提供了可重复、精确的失败信号；没有篡改原映像来制造失败。

## 交接限制

资料提取、协议含义与局部原指令验证已完成。服务端交互票据/状态授权、选项后原子完成与唯一后继、奖励、地图迁移顺序、断线重试均未实现或验证。原客户端完整UI/真实点击、最末对白到菜单的实际画面、全部取消/关闭事件、真实传送坐标及在线服行为没有实测。

仅产出本文和独立研究fixture，没有修改任务领域、Inventory、任务配置、共享入口或在线状态。原值异常和未证实单位已单独标记，不因原服未知而阻断集成方在统一设计依据下继续恢复。
