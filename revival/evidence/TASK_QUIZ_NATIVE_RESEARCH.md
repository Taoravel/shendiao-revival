# MissionType17原生答题：静态题、选项代码与提交

2026-10-23；本地端游1.6.1、网络版本601。采用本批已读取的 `D:/User/Documents/Codex/.codex/skills/research/SKILL.md`，当前本身为背景委派研究，不递归委派。沿用 `ARCHITECTURE.md`、`DESIGN_AUTHORITY.md`，按原配置→parser→UI分支→构包追证，只写本文件；未修改.py、policy、catalog、shared，未操作在线服、当前客户端、战斗或角色存档。

## 可以用于恢复的结论

1. **5条静态题使用独立CAnswerQuestion0xc4a48，不是CCommit尾字段判对错。** 正文16字节：BE `i32 task_id | u64 npc_key | i32 answer_code`。原合法任务ID1001..499999，协议code0..5；具体题还应按实际WrongAnswer数量收窄。[N1、N3、P1]
2. **answer_code不是屏幕行号。** QuestionInfoCorrectAnswer显示项固定code0；WrongAnswerList[j]固定code=j+1。随机只改变显示排列；正确项即使显示在第2/3/4行，仍发送0。原客户端知道这组代码，但不会在发送后据此修改任务状态/选择后继。[N2、N3、P1]
3. **230407的CorrectAnswer原值字符串“2”按通用路径作为正确项正文。** 没有将其解析成WrongAnswerList的第2项或答案序号的指令。原3个WrongAnswer都是完整句子；当前恢复应保留字面字符串，不根据常识修题。[S1、N1、N2]
4. **静态题提交后正确/错误都关闭当前对白。** phase4构包不比较code是否0，发送后统一走0x164903f关闭UI。原静态题的错答反馈、任务跳转、重试次数/活动资格是服务器职责；本批没有证实一个可直接通用套用的静态题结果包。[N3、N4]
5. **SSendAnswerResult0xc4a9e确实存在，但不能误用。** 它只有一个字节，Process更新另一个StandAlone/Time小游戏单例，和SNotifyStart/SRefreshQuestion同组；不是本静态题phase4 UI或task/NPC结果同步。[N4]
6. 229103/229110/229112有两个PostMissionList。原客户端题目/选项代码生成与上行**未访问该列表或发送后继索引**；虽然重试任务文字支持剧情关联，不能直接宣布“code0选Post[0]、错答选Post[1]”已被原服证明。[S1、N5]
7. 其余7条round任务缺本地静态题，type17分支会走普通CCommit路径；它不能被当成普通对白完成依据。当前只研究静态5条，未扩大动态题库/其他小游戏恢复。[S1、N1]

## 原始来源与方法

S1：`D:/神雕侠侣/artres/config.pfs` → `autoconfig/knight.gsp.task.cmainmissioninfo.xml`，本批直接PFS长度/CRC检查、完整BXML解码全部type17行。解压字节SHA256 `ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706`。

N1–N5：`D:/神雕侠侣/revival/evidence/native-image.bin`，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`，base0x400000；以下均为VA。复用 `native_inspect.py` 与已有RTTI索引定位，再重读原指令；内联Python `-B` 复用隔离Probe，网络/字符串/渲染边界截获，不运行客户端进程。

research影响：先区分CCommit（接受/进入其他流程）和CAnswerQuestion（静态选项意图），再分清显示行、原选项代码、任务结果与Post列表；不凭字段名/字符串数字猜网络语义。唯一产物本文，没有另写脚本或证据JSON。

## S1：12条原任务与静态5题

| task_id | 原名称 | ActiveNpc/Map | 正确项原字符串 | WrongCount | Start/Finish句数 | 原PostMissionList |
|---:|---|---|---|---:|---|---|
| 229103 | 新年群英会 | 13168/1006 | 段智兴 | 5 | 0/2 | 229111,229110 |
| 229110 | 新年群英会 | 13168/1006 | 段智兴 | 5 | 1/2 | 229111,229112 |
| 229112 | 新年群英会 | 13168/1006 | 段智兴 | 5 | 1/2 | 229111,229110 |
| 230407 | [劳动节]答题 | 10215/1007 | **2** | 3 | 0/2 | 230408 |
| 232503 | 锦书谁寄 | 10170/1101 | 莫，莫，莫。 | 5 | 0/0 | 232599 |
| 311202 | 名动江湖·上晓天文($round$/3) | 11101/1007 | 无 | 0 | 0/1 | 311299 |
| 311302 | 名动江湖·下知地理($round$/3) | 11101/1007 | 无 | 0 | 0/1 | 311399 |
| 314402 | 名动江湖·止戈为善($round$/3) | 10012/1007 | 无 | 0 | 0/1 | 314499 |
| 318502 | 名动江湖·宝石大盗($round$/3) | 10568/1007 | 无 | 0 | 3/1 | 318503 |
| 321101 | 笑迎新春-拜访长者($round$/10) | 11334/1006 | 无 | 0 | 1/1 | 321102 |
| 321201 | 笑迎新春-拜访长者($round$/10) | 11335/1005 | 无 | 0 | 1/1 | 321202 |
| 321301 | 笑迎新春-拜访长者($round$/10) | 11336/1013 | 无 | 0 | 1/1 | 321302 |

静态5条QuestionInfoNpcID均等于表中ActiveNpc，Animation/Process0、没有BranchNote；四个229xxx/230407有Finish，232503没有。当前原普通Money/PetExp/SMoney/Exp字段均0，230407另奖励64063×1绑定1，232503另奖励64378×1绑定1；没有从题库摘要制造额外数值。

原题和列表：

| 任务 | QuestionInfoConversion | WrongAnswerList原顺序 |
|---|---|---|
| 229103/229110/229112 | 少侠可知道五绝中的南帝一灯大师的俗家名字叫什么啊？ | 段誉；段天德；段正淳；段正明；段延庆 |
| 230407 | 以下哪条关于劳动节的知识有错误？ | 美国政府规定每年9月第一个星期一为劳动节；中国人民庆祝劳动节的活动可追溯至1912年；1889年第二国际宣布将每年5月1日定为国际劳动节 |
| 232503 | 你可知山盟虽在，锦书难托的下一句是： | 错，错，错。；霍，霍，霍。；作，作，作。；懦，懦，懦。；鹅，鹅，鹅。 |

## N1：原字段、NPC入口与phase4

| 原字段 | 字段名字符串/原parser | config对象位置 |
|---|---|---|
| QuestionInfoCorrectAnswer | 字符串0x226c0f8；0xbb62a1–0xbb62d5按字符串读入 | wstring +0x1b4，长度+0x1c8 |
| QuestionInfoWrongAnswerList | 字符串0x226bc50；0xbb69e1–0xbb6a00读取vector | +0x1d0，begin+0x1d4/end+0x1d8，每项0x1c字节 |
| QuestionInfoNpcID | 0xbb62eb–0xbb6317读取整数 | +0x1e0 |
| QuestionInfoConversion | 字符串0x226c0a4；0xbb632a–0xbb635e按字符串读入 | +0x1e4 |

普通NPC task菜单仍依赖当前bean投影与可信NPC交互。type17没有type40的class3特例；正常state0不直接变成可提交菜单，state3才给UIclass3，state2是failed。菜单 `0x164d780` 在class3设phase2，先读Start；读尽（或本来没有）再调 `0x1643360`。

type17在 `0x16436e6` 被识别：

- `0x16436eb–0x16436f8` 通过0x5ba6c0判断WrongAnswerList是否为空；
- `0x16436fa–0x1643701` 检查CorrectAnswer.length是否为0；
- 两者均非空，`0x1643705 → 0x1642670` 本地构题，**这一步不发送CCommit**；
- 任一为空，进入 `0x1643721–0x164375b` 的普通CCommit。7条round恰属该缺静态题路径；当前未闭合它们的原服题库下发/结果链，不能将该CCommit作为完成授权。

`0x1642670` 在 `0x16426a2` 设置UI+0x64=4；`0x16426c8–0x164277a` 读+0x1e4的QuestionInfoConversion渲染题干，再构建选项。229110/229112的一句Start是phase2，之后切phase4；没有Start的三条点击菜单直接进入phase4。无需另发虚构SNotifyScenarioQuest、通用确认对白或服务器题干包来显示这5条本地题。

## N2：随机的是显示顺序，代码保持原身份

`0x1642787` 调原随机整数函数，`0x164278d–0x16427a9` 取模4并跳表0x1642f28。跳表0/1/2/3对应0x16427b0/0x1642950/0x1642b90/0x1642b90。没有对整个答案向量做全排列洗牌。

正确文本始终从config+0x1b4取得：例如0x16427b0、0x16429d6、0x1642ccd；对应菜单项+0x30在0x1642816、0x1642a3c、0x1642d7c写0。Wrong[j]的菜单值始终j+1（如0x1642923–0x164292d、0x1642b62–0x1642b71、0x1642c99–0x1642ca1、0x1642ebc–0x1642ec4）。

记C=CorrectAnswer/code0，Wj=WrongAnswerList[j]/code(j+1)。本批原指令捕获：

| rand模4 | 3个Wrong时的显示顺序 | 5个Wrong时的显示顺序 |
|---:|---|---|
| 0 | C,W0,W1,W2 | C,W0,W1,W2,W3,W4 |
| 1 | W0,C,W1,W2 | W0,C,W1,W2,W3,W4 |
| 2 | W1,W0,C,W2 | W1,W0,C,W4,W3,W2 |
| 3 | W2,W1,W0,C | W2,W1,W0,C,W4,W3 |

因此正确项在5个Wrong的六项题里也只出现在前四个位置；不因这个行为看似不均匀而修算法。原随机分支的边界在P1验证，不是自行实现一个更“合理”的shuffle。

230407的config+0x1b4就是字符串“2”，原UI复制/渲染字符串，所查路径没有atoi、数值索引查WrongList或替换正确文本。**按本地通用路径该选项正文为“2”、提交code0**；屏幕真实渲染未验，配置异常保留。WrongList第二个完整句子原code2，不能被当成0。服务端若要修题须另作明确策划变更，不在本批原恢复中静默修改。

## N3：点击选择、原协议和正确/错误职责

phase4选择走 `0x164c483` 起的菜单点击回调；`0x164c579` 取被点item+0x30，`0x164c57f → 0x1648d00(value)`，没有根据屏幕位置加减索引。

`0x1648e36–0x1648e81` 的phase4分支：

- vtable0x227d594、type0xc4a48；
- UI+0x48复制taskID到packet+8；
- UI+0x38/+0x3c复制完整NPCkey到packet+0x10/+0x14；
- 原传入菜单value原样写packet+0x18；
- 发送后 `0x1648e83` 直接跳 `0x164903f`，通过UI虚函数关闭当前对白。

该路径不比较value是否0，正确/错误都会关闭；不在客户端调用任务state handler、移除任务、发奖励或选择PostMissionList。phase4也不是Finish阶段3，不增加CQuestDialogEnd/CEndPlayCG门槛。

原RTTI `.?AVCAnswerQuestion@task@gsp@knight@@`：ctor0xdd40b0、vtable0x227d594、marshal0xe57440、decode0xdd4170、validator0xdd40d0。正文固定16字节：

```text
BE i32 task_id | BE u64 npc_key | BE i32 answer_code
```

marshal在0xe57443–0xe5745e检查taskID1001..499999、code0..5，然后0xe5747d写BE32任务ID、0xe5748c写BE64 key、0xe57497写BE32 code。decode在0xdd419c–0xdd41ff读同样字段、0xdd4202–0xdd421d施同样范围检查。本段未额外验证NPCkey的业务有效性。230407只有3个Wrong，协议可解码4/5不代表原题有这些合法选项；服务端应拒绝超过该题实际WrongCount的code。

synthetic NPCkey0x1122334455667788，230407/code2的正文为 `00038407112233445566778800000002`。key不是QuestionInfoNpcID配置整数，也不是玩家roleID。

code0来源于客户端标记为CorrectAnswer的显示项，恶意客户端当然可直接填0。有效任务/NPC/位置/版本/租约/未过期题票据可约束请求上下文，不能宣称wire证明玩家真正点击或阅读过正确文字。正确/错误后的服务器任务状态、重试策略、奖励与后继结算必须由权威所有者处理，不能仅凭任意CCommit(option0)授权。

## N4：结果包排除、错答表现与重试

原task协议RTTI索引没有找到名为通用SAnswerQuestion的类型，但确实有其他题型/结果协议，不能因名字相近就使用：

| 原协议 | Process / 已确认消费者 | 本批适用性 |
|---|---|---|
| SSendAnswerResult0xc4a9e | 0x129d870→0x129d7b0，global0x294e910 | 另一StandAlone/Time小游戏UI，非本phase4 |
| SRefreshQuestion0xc4a9d | 0x129e750→0x129dcc0，同global0x294e910 | 与倒计时SNotifyStart同组，未证明用于本静态5题 |
| SQuestion1 0xc4ac6 | 0x1640e40→0x1630b10 | 另一原题目下发入口；不能替代本地静态题构造或据此猜结果 |
| SAnswerXinyoulingxi0xc4a59 | 0x16105f0 | 独立心有灵犀类题，不在本批范围 |

SSendAnswerResult的vtable0x227e648、marshal0xe58550、decode0xddc850，正文**只有1字节**；0x129d872只取global0x294e910存在的对象，再处理该字节。0x129d7b0改变自己的提示/效果对象，未读普通taskID/NPCkey。此前同一单例初始化读取StandAlone/Time、StandAlone/Time/Text1和QuestionBack（见TASK_SCENARIO_TRIGGER_RESEARCH）。它不是一个应随本地CAnswerQuestion发出的通用答对/答错确认。

本phase4已证实的合法错答客户端表现仅是：按原code发包，然后关闭对白；没有本地“错了”弹窗、扣奖励或标任务failed的自动分支。没有原证可指定服务器必须回哪个通用提示/失败包，故本报告不造包、不选提示ID。

若服务器采用“合法错答留active、不奖励、不跳后继；再次经可信NPC菜单重开本地题”的恢复策略：当前bean仍可由服务器投影ready3，再SVisitNpc列出任务，玩家点击会重建phase4并重新随机显示。这与原入口相容，**属于明确本地重试设计，并非原服错答规则已复原**。原是否直接下发229110/229112、切换失败状态、限制次数或付费重答均未确认。state2通用tracker会显示失败，不应无依据用于普通错答。

## N5：PostMissionList与原结果没有闭合索引映射

229103原Post=[229111,229110]，229110原Post=[229111,229112]，229112原Post=[229111,229110]。229110/229112的Description明确说之前答错并重答，且一行Start提醒重试；这支持它们在故事中的错答关联，但**不是code与Post索引的原服务器映射指令**。

所查0x1642670完整构题、0x1648e36发送分支没有访问Post列表（配置+0x6c），也没有将code转换成后继ID或布尔结果。wire里的1..5表示具体Wrong列表项，不是Post[1]..Post[5]。因此不能用“两个Post恰好像成功/失败”认定成功一定选第一项，或者把所有Wrong统一映射为第二项。多后继继续pending、保留原边界与本报告证据一致。

## type11交钱的顺带入口核对

`0x164369d` 匹配type11；0x10831b0通过后，`0x16436ab` 传模式3，`0x16436b6–0x16436bf` 携当前taskID/NPCkey调用0x168a1e0，进入统一提交UI。0x168a43b–0x168a451的mode3分支显示专用UI控件并返回。**此入口不是直接发普通CCommit**。本批没有继续追确认交钱按钮后的上行/金额布局、货币类型或扣款事务，不把既有CSubmit2Npc的其他模式推成已证type11协议。

## P1：最少必要隔离验证

1. 原构题选项段0x1642787→0x1642eee，WrongCount3/5、rand模4=0/1/2/3，共8例。仅替换外部CRT随机、字符串/颜色包装、UI追加/析构边界；保持原分支/循环/菜单值写入。捕获表N2中的源文本标签和实际menu+0x30，Correct全0，Wrong[j]全j+1。
2. 原phase4构包0x1648e36→0x164903f，230407/code0与code2两例；均捕获CAnswerQuestion及完整64位NPCkey，均走相同关闭入口。
3. 原decode0xdd4170，以上述两份16字节body输入；均读出相同task/key/code并精确消费16字节。原marshal布局另由N3直接反汇编核对，没有把host拼接body称为原encoder roundtrip。

均退出0。首次菜单探针因外部CRT IAT指向未映射地址而停止；改为隔离fixture中的调用边界后8例通过，没有修改原指令或生产文件。未执行真实UI绘制、用户点击、随机分布统计、服务器应答或任务/奖励数据库写入；没有扩大测试其他小游戏。

## 交付与未验证范围

本批可交接的原事实：静态5题的原内容/字段位置、本地phase2→phase4条件、原答案代码及显示排列、独立CAnswerQuestion布局/范围、答后关闭行为，以及多后继/错答结果仍未知。主线程可建立当前NPC题票据与code0完成策略，合法错误保留active；其活动资格、错误重试及多Post处理须与原证分开标为恢复设计。本窗口没有接入这些模块。

未验证：完整真实GUI、实际点击/取消全部事件、原服务器正确/错误反馈与次数/活动规则、多Post选择算法、7条round动态题库流程、type11实际交钱上行与扣款、线上投递/重连和奖励结算。唯一产物本文；最终写入mtime另随交接核对。
