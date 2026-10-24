# 首师父Start读尽与武器卡触发审计

2026-10-23。本批针对人类实际反馈“师父对话完没有武器”，只读原PFS/映像、NEWBIE_FIRST_MASTER_RESEARCH、TASK_SCENARIO_START_RESEARCH及既有Probe。沿用已完整读取research/diagnosing-bugs、AGENTS、ARCHITECTURE与DESIGN_AUTHORITY。仅新增本报告和独占`../research_first_master_dialogue_end.py`；不改生产、共享、已有验证或政策，不碰在线库/客户端/进程/战斗。

## 确定的客户端行为

**任务100186的三句Start对白结束后，原phase2继续事件发送CCommitScenarioQuest0xc4a44，未发送CQuestDialogEnd0xc4a52。** 现有“CCommit只ack，等DialogEnd才发武器选择卡”的握手依赖客户端在这一步不会自然发的包。原文献关于DialogEnd的指令证据本身存在，但其最前提是**Finish/清理phase3**；把它外推为首师父Start三句耗尽的上行，导致了错误接线方向。

这不是只从字符串/配置猜测：本批原native反馈已执行Start列表数量分支、原句号推进、下一次phase2继续→原Start耗尽返回→原type10提交构包、清理phase门禁。输出只有CCommit，UI phase保留2。人为改为phase3的对照才输出DialogEnd，并进入20006的Scene effect边界。

本结论证明客户端正常意图与当前握手不相容，不证明修复已部署、人类已看到卡片或物品已入包。服务器在合法CCommit后授权并发送SPlayCardEffect、选择提交时发物/完成任务的事务政策仍属于明确本地设计，应由主任务/主策划修正，不能把客户端包本身说成读取文字完成的权威证明。

## 第一方数据与原指令链

映像SHA256：`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`，BASE0x400000。

probe直接通过PfsArchive.read重读 `artres/config.pfs → autoconfig/knight.gsp.task.cmainmissioninfo.xml`，由该reader核验本地/中央目录一致、长度与CRC，再BXML解析，实际选择100186并断言：MissionType10，ProcessBarTime0，Start句数3，无FinishConversation、BranchNote，ScenarioInfoAnimationID20006。原任务整表展开SHA256此前独立核验为`ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706`。

关键链如下：

| 原位置 | 对100186的实际意义 |
| --- | --- |
| 0x164d865..0x164d873 | 可交付UI分类3的NPC菜单，设主UI+0x64=2，进入Start。wire state3和UIphase2是不同枚举 |
| 0x164b581..0x164b5b8 | 读取原config Start vector数量；index2<3时进入最后一句的渲染入口0x164baad |
| 0x164be0f | 原后显示步骤将UI+0x50的index加1，2→3；显示最后一句本身不立即提交 |
| 0x164c3d6..0x164c3ef | 下一次继续事件检查phase2，完整调用0x164b530；Start耗尽且BranchNote空，AL0后调0x1643360 |
| 0x164b5dc→0x164bb51 | 原BranchNote为空，返回AL0，未切phase5，未切phase3 |
| 0x16433a0..0x16433e9 | MissionType==10；ProcessBarTime0直接进入普通提交分支。本分支没有检查Animation20006并等待其完成 |
| 0x16433e9..0x164342a | 构造并发送CCommitScenarioQuest0xc4a44，填当前task_id、当前完整NPCkey、option0 |
| 0x1643832..0x164383b | 提交后调用原UI关闭虚槽；本Probe只捕获UI副作用，不替代提交构包 |
| 0x1644c1d..0x1644c21 | 关闭/清理片段首先要求phase3。此处this偏移+4，`[esi+0x60]`对应主UI+0x64；Start的phase2直接跳0x1644cf8，越过DialogEnd构造 |

只有通过phase3时，后面的AnimationID>0条件才让`0x1644cb6..0x1644cf2`调用后置表现并发DialogEnd。这不能被“任务含AnimationID20006”绕过最前面的phase门禁。

原100186没有Finish列表。普通完成state1如何移除/播放后置表现另有既有TASK_PROTOCOL研究；本批不以提前完成任务、补发state1或强造phase3来凑出DialogEnd并授权领物。

## 可复用原native反馈

运行：

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/research_first_master_dialogue_end.py
```

本批实际结果：

```text
Start末句分支：index2→进入原最后句渲染边界
原index递增：2→3
下一次phase2继续：CCommitScenarioQuest 0xc4a44(task100186,NPCkey4724464025644,option0)
UI close phase：2
原phase2 cleanup：无CQuestDialogEnd、无Scene effect

仅人为phase3对照：Scene effect boundary20006 + CQuestDialogEnd0xc4a52(task100186)
```

`native_start_completion(task_id=100186,npc_key=...)`返回：

```python
messages, trace, last_phase = native_start_completion(100186, actual_verified_npc_key)
```

默认key只是fixture，默认返回的唯一逻辑包体为`0001875a0000044c0000002c00000000`（16字节），调用方可给自然场景已验证的真实key。`messages`为`tuple[(kind,body)]`，能直接喂隔离运行时peer；不应在其后手工注入DialogEnd来制造通过。`native_synthetic_finish_cleanup`另提供phase3反例，**不能当真实Start执行序列**。

Probe边界写清：

- 原`0x164b581→0x164baad`保留最后句数量/下标判定；完整renderer、原文字替换及GPU不执行。随后单独执行原`0x164be0f`，模拟已显示最后句之后的确定原index推进，不声称仿真整段文字渲染。
- 下一次事件实际从原`0x164c3d6`开始，运行完整Start耗尽函数及完整type10提交函数到原继续事件收束0x164c584；没有hook掉0x164b530、0x1643360或状态/phase分支。
- 仅外部lookup、编译器cookie检查、网络发送和UI关闭副作用适配；发送边界捕获原实际构造对象字段，再按此前已原生核验布局编码为逻辑body。本脚本未重复执行原marshal或网络加密。
- 在同一UIphase继续执行原清理片段0x1644c1a→0x1644cf8；正常phase2跳过DialogEnd；对照phase3执行原后置分支，Scene effect资源边界只捕获不加载。

因此这个反馈能使“把DialogEnd当作首师父Start必然上行”的假定失败，能使“只在合法CCommit后服务端发卡”的候选握手获得真实客户端正常上行。它不是完整GUI自然点击的替身，也未覆盖其它43条逐句绘制；43条共用type10/time0/三句配置的静态归类和已有领域参数测试可另沿用。

## Animation20006与卡片不是同一触发链

原`0x1255e70`在20006且JumpType0时调用`0x12550c0`；20006不在30000..59999另一分支，在`0x1255105..0x1255110`交Scene `0x11ca790`。本Probe在**人为Finish phase3**下捕获该边界20006；它没有调用CCardEffect卡UI。

实际武器卡的独立原消息仍是 `SPlayCardEffect0xc001c(effectID20006)`，process0x1744540查CCardEffect，经0x17444a0/0x1744070填卡；两个按钮发CGetCardItem0xc041f(effectID,itemID)。原卡20006为49009×1或49006×1，原任务自身奖励列表为空。这些配置与按钮身份继续沿用WORLD_MASTER_CARD_PROTOCOL和NEWBIE_FIRST_MASTER_RESEARCH的已核内容；本次纠正的是**发卡授权触发上行**，不是更换卡片/武器模板或猜CG结束包。

## 旧结论的精确更正范围

NEWBIE_FIRST_MASTER_RESEARCH中“该切片对白后上行是CQuestDialogEnd”与其后“UI+0x60==3”的静态证据并非同一个充分条件：后者只证Finish清理片段，不证三句Start进入该片段的phase3。TASK_SCENARIO_START_RESEARCH早已明确Start用phase2，读尽走CCommit，非phase3不发DialogEnd；此规则同样适用于当前type10/time0/无BranchNote的首师父Start链。

据此应撤销把“先CCommit ack、再等DialogEnd授权”当原客户端必然顺序的外推。最小服务端候选：在当前已授权真实NPC/任务对白票据下接受原CCommit作为卡选择请求，持久卡授权并回SPlayCardEffect；仍由合法CGetCardItem按原二选一执行唯一物品及任务/后继事务。CCommit不携带逐句阅读证明，角色租约、真实NPC/位置、当前任务/effect授权及幂等仍须现有服务端验证，不能放宽为任意taskID即可发卡。

## 方法与未验范围

diagnosing-bugs实际采用“先原客户端正常输入转红”：先验证原phase2输出唯一CCommit，额外手工DialogEnd明确作为反例；主任务可用返回包驱动自然运行时peer，验证该原输入能否得到SPlayCardEffect，再修握手并重跑。research沿原PFS字段、实际调用者phase与原包构造逐段闭合，纠正此前条件外推。

本批原native局部反馈通过；没有修改生产/政策/共享或现有verifier。未验证真实人类卡片显示、点击领物、入包/实际穿戴、生产提交/重连或43条全部GUI。最终“对话完有武器”仍须实际卡片选择和原模板物品入包证据，不能以服务器发了某包代替。
