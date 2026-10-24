# 首战100107：Finish、Animation10019与电影结束的原生证据

2026-10-24。P0有界研究，仅新增本文及独立 staging 脚本；未改Task、World、共享入口、政策或原资源，未操作真人DB/客户端/GUI/在线服/战斗。research技能要求后台原始来源调查，本代理承担根任务委派的后台研究；重读 ARCHITECTURE/DESIGN_AUTHORITY，并复读 PROLOGUE_STORY_EFFECT_RESEARCH 定位后直接检查原PFS与原指令。本文不扩展其他CG或轻功。

## 直接结论

`client_verified`：100107完成刷新state1的已执行显示路径先进入两句Finish的phase3；不是直接播放10019。结束Finish时原代码把10019存入**任务manager+70**并发送 **CQuestDialogEnd 0xc4a52 / task100107**。已识别的pending消费者对10019小于20000直接返回，未进入CG播放入口。

`client_verified`：原movie/10019确为说书人演示太祖长拳；如果**另行已经启动**这部电影，原自然结束tick会构造 **CEndPlayCG 0xc0018 / movie10019**。这是两项独立事实，不能合并为“state1会自动播CG并回CEnd”。本批没有闭合Finish/DialogEnd到CG启动的原服务器桥。

原显式SStartPlayCG的decoder/Process可以把10019传入原CG入口，但这只是控制对照。原服是否使用此包、何时发送、是否先等Finish、播放permit与任务/首技的先后，仍unknown。若main决定显式启动并持久化匹配movie10019播放许可，应作为本地designed策略单独批准；本报告不把SStartPlayCG猜作原服必需时序。

## 一手来源

以下资源直接由PfsArchive从 `artres/config.pfs` 读取（长度/CRC检查），未用派生catalog代替原行。地址绑定原映像 VA，BASE400000。

| 来源 | SHA256 |
|---|---|
| evidence/native-image.bin | `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791` |
| autoconfig/knight.gsp.task.cmainmissioninfo.xml，2026233 bytes | `ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706` |
| movie/10019.txt，8836 bytes，原UTF16 | `bc8206989585938d8b411d3bfd635178553f92aaddfc0f79a1cbcefc5563a5bc` |
| autoconfig/knight.gsp.task.cquesteffect.xml | `8fbbda8366389fe8da2635a4f4160717a6c30b25f3d969f163906366243c9e45` |
| [独立probe](../staging/research_prologue_first_battle_10019_native.py) | `63100b9539912a725401df5d91eadf11b848da2bc6709e8dbc85bc4e443e6690` |

原任务100107：MissionType40、AIInfoAIID8001、ActiveInfoNpcID10908、ActiveInfoMapID1501、ScenarioInfoAnimationID **10019**、RewardMapJumpType0（Map/X/Y也0）、PostMissionList唯一100179。原Start三句，Finish两句且说话者均10908。Finish内容为“打得却毫无章法”“这套太祖长拳就传授于你，你先参悟一下吧”。这段文案不构成技能已写入或战斗授权。

movie10019第1物理行实际同时包含 `Setmap id=1501 pos=65,98`，大量空格后又有 `Setmap id=1501 pos=99,40`；本批保留原字节，不修正或猜解析器会采用哪一个。第8行Start，第125行Return time=100，第126行End；中间说书人创建木人、演示太祖长拳，随后创建三只梦魇邪兽供练手。没有从文本取得技能持久化/任务结算命令。cquesteffect表无10019，不能套用60001标题特效分发。

## N1：已执行的state1与Finish结束

1. 原state1显示决策块 `125c168` 读config+304/+308的Finish vector，以原28字节wstring元素计数。100107实际count2，`125c193→1129af0` 获取UI，再 `125c19b→164beb0`。
2. 本probe保留原 `164beb0`，执行至 `164bf53`：`164bf0a/0d` 写当前task ID，`164bf10` 把UI+64设3，随后原Finish vector计数。捕获结果为task100107、phase3、pending0；这时没有发送包、没有到 `12c4140`。
3. 文本渲染边界未执行。以“已显示两句，UI index=2/count2”为明确fixture继续原 `164c3d6..164c584`：phase3在 `164c412` 再调原Finish函数，耗尽返回false，`164c428` 走UI关闭虚槽。
4. UI关闭框架适配为记录边界；再单独执行原phase3关闭决策 `1644c1a..1644cf8`。`1644c39` 看到Animation10019>0，到 `1644cbd→1255e70`，后在 `1644cc5..1644cf2` 构造并发送 CQuestDialogEnd。
5. `1255e75` 取config+2ac=10019，`1255e7b/80/98` 比较20000，进入 `1255ea3` 写任务manager+70=10019。后续NPC查找返回空为fixture；真实NPC存在时还可能调用 `11fcc50`，因此不能把此路径说成没有其他副作用。

实际输出：

```text
state1 -> original Finish entry -> UI phase3/task100107
Finish index2/2 -> original Finish entry -> UI close phase3
send type0xc4a52, body0001870b (BEi32 task100107)
task_manager.pending=10019
CG entry12c4140: no hits
```

CQuestDialogEnd包字段捕获自原发送对象；另执行其原vtable227da98对应marshal，得到同一四字节body。它不是CEndPlayCG，也不证明客户端成功学习技能。

该反馈从已确认的state1显示块开始，不是完整刷新包unmarshal/任务bean移除/GPU/UI交互整链。文本index=2是边界fixture，不称已执行两句真实渲染或人为点击。

## N2：10019 pending dispatcher实际早退

在上例同一隔离任务manager继续执行完整原 `12550c0(0)`：`12550cb` 取pending，`12550d2` 比较20000，`12550d7` 跳 `125511c` 返回。实际pending仍10019、无新消息、无CG入口。

这与既有10001/10002原证相同门槛，但本批确实用10019重新执行，没有只按ID类推。>=20000的场景效果/另一分发分支不适用；本批未重新扫描整个映像或排除所有间接消费者。由已识别此链不能声称原客户端自行启动10019，也不能用等待任意时间补造CEnd。

## N3：显式入口对照与“已在播放”后的实际CEnd

**入口对照**：用body `00002723` 执行原SStartPlayCG unmarshal `d57540`，实际解到10019并消费4字节；再执行原Process `12c43b0`，在 `12c43c0` 调用目标 `12c4140` 前停止，读取原栈参数确为10019。没执行CG入口、资源加载或渲染，也没证明任务应该发此包。

**自然结束纵切**：独立建立CGmanager+38=10019、+3c=1、当前section已完成且队列空的fixture，进入原tick `12c0b00`。保留原判断和调用：`12c0b1f` 检section完成，`12c0b28` 移除section边界，清+60；空队列在 `12c0b52→12c0970`。后者原 `12c09aa` 构造type0xc0018，`12c09b2..b9` 从manager+38写movieID，再在 `12c0a3e` 发对象；执行至 `12c0a43`，实际active已清0。

```text
active10019 + finished section + empty queue
  -> original tick -> original cleanup/send
  -> type0xc0018, movie10019, body00002723, active0
```

CEnd body另经原marshal `e3fd70` 验为BEi32 movie10019。Adapter仅覆盖section tick/移除、UI清理、连接/发送边界；不替代完成/队列判断、CEnd包构造或movie读取。section完成本身是fixture，未播放整部10019。Return恢复原布景是既有通用 `12c0bf0→11e0a80` 的证据，本批未重放该电影的完整Setmap/Return；不能把CG临时1501当服务端权威传送。

## normal_location0是否覆写剧情

main提供的当前顺序为 `BATTLE_END→state1/100179 bean→normal_location0`，且END_PLAY_CG只路由intro_ticket；本批不验共享运行版本。

当前 `game_runtime.normal_location_message` 用SSetRoleLocation0xc0fa4，body为roleID/current x/current y/flag0。直接复读原Process `11d7a20`：场景/角色存在时在 `11d7a4e..64` 将flag严格等1归一，并调用主角vt+184；已核原 `1213b80→1205c80` 可把主角+218写0（也会走位置/移动队列相关操作）。其适用条件、gate与原反馈沿用 [WORLD_MOVEMENT_STATE_TRANSITIONS_NATIVE.md](./WORLD_MOVEMENT_STATE_TRANSITIONS_NATIVE.md)、[WORLD_MOVEMENT_STATE_LIFECYCLE_GATES.md](./WORLD_MOVEMENT_STATE_LIFECYCLE_GATES.md)。

**有证据的覆写**是主角移动状态/位置消费者；**没有本批证据**证明该包会关闭Finish UI、清CGmanager+3c、取消10019或改任务manager+70。未执行normal_location0与10019播放的真实组合，不能把“CG被此包覆盖”当已诊断原因。反过来也不能凭normal_location0的写0，宣布整个Finish/CG期间普通移动永远安全。

当前最直接的缺口是**state1→Finish/DialogEnd→电影启动没有闭合**，不是已证自动CG与normal0冲突。如果main选择新增10019播放许可，应按现有Owner/epoch/位置版本策略使CG开始撤销普通移动声明，匹配10019结束后再恢复；这个接线时序属于待批准设计。CEnd10019不能由只接受开场intro ID的路由误当开场结束，也不能授技能、重付100107奖励或替代正式首技任务。

## 交付与限制

运行独立probe整套通过：原资源核验、state1 Finish phase3选择/耗尽/关闭、原DialogEnd marshal、pending10019早退、显式入口对照、已active10019的自然结束CEnd构造/原marshal。初次CEnd夹具UI getter适配缺callee栈清理导致捕获偏移，修正该已识别外部UI调用的cleanup4后通过；未改原指令或状态判断。

未知：原服发送电影的时机/是否使用SStart、是否需DialogEnd许可、重登/中断规则、10019第一行双Setmap解析结果、完整CG与normal0组合、真实画面/网络/战斗/任务结算。本文没有为上述unknown作授权，也不将CG表现文案升级为100008技能grant原证。
