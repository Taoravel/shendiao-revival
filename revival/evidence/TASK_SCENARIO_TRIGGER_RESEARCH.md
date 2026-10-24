# type50空表现/轻功Note：NPC提交、查询与自动触发缺口

2026-10-23，本地端游1.6.1、网络版本601。本批采用 `research` 技能：当前本身为后台委派研究，沿用已读取的 `D:/User/Documents/Codex/.codex/skills/research/SKILL.md` 全文、`ARCHITECTURE.md` 与 `DESIGN_AUTHORITY.md`，只追原PFS/原指令并写单文件；不递归委派，不用客户端事实替代原服务端授权。唯一写入为本文；未修改.py、catalog、policy、shared，未操作在线服/当前客户端/战斗/角色存档。

## 可用结论

1. **42条空表现中，203601/205701/233701可以走已经确认的真实NPC菜单提交意图。** 原Start/Finish/Note/Branch/Animation/Process均空或0；在可信任务ready3与对应NPC菜单中点击时，原Start函数立即返回false，默认type50分支直接发送 `CCommitScenarioQuest=0xc4a44 + BE(task_id,npc_key,option0)`。本批对三条分别执行了原指令小探针。[S1、N1、P1]
2. **其余空表现不能由这条NPC路径自动开放。** 42条中38条ActiveNpc0，231001为999999；这些数值不授权任意NPC。前置/福利/名人轶事等名称及PostMissionList只证明原资料关联，不能证明领取/自动完成触发。[S1]
3. **Note20的已证实显示顺序是收到state1完成处理之后。** `0x125c020`先移除active bean，再按Finish→Note→fallback顺序；这20条Finish为空，故直接将NoteInfo送原提示UI。其“恭喜获得…修炼任务”措辞不能反推SAccept时自动显示或服务器自动完成。重复state1、即使无bean，也会再次显示Note。[N2、P1]
4. **20个Note节点的唯一后继全是type56。** 原ID为221201..223101（步长100），每个PostMissionList=[本ID+1]；这20个后继均为原轻功到区任务。原表支持“轻功修炼入口提示节点→到区节点”的数据结构，触发这个入口的学习/领取事件和原服资格仍未知。[S1]
5. **CRequestQuestCanAccept/回列表/SAccept不能充当已证实的自动完成授权。** 查询上行空体、可接列表回包仅ID集合；已查原handler更新可接集合和标记，SAccept插入active bean。没有从这些handler闭合到type50无NPC的自动CCommit或state1；观察者/UI间接调用未被全面证明，不能把“未找到”写成全程序绝无入口。[N3]
6. **SNotifyStart0xc4a9c是时间/倒计时通知，不是通用剧情启动包。** 它只有一个64位时间值；原Process计算 `(包时间-当前clock)/1000` 并钳非负，更新StandAlone/Time界面。没有taskID，不能用其名字替无NPC节点造启动包。[N4]

## 原始来源与方法

| 标记 | 一手来源及校验 |
|---|---|
| S1 | `artres/config.pfs` → `autoconfig/knight.gsp.task.cmainmissioninfo.xml`；本批直接PFS长度/CRC检查、完整BXML重读。raw SHA256 `ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706` |
| N1–N4 | `revival/evidence/native-image.bin`，base0x400000；文中地址均VA。SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791` |
| P1 | 内联Python `-B`、既有 `research_task_jiaxing_scenario.Probe`，执行局部原指令；网络/UI/资源边界以fixture截获，没有真实发包/渲染 |
| 辅助索引 | 既有 `task-protocol-evidence.json`、`TASK_PROTOCOL.md`、`TASK_SCENARIO_OBJECTIVES_RESEARCH.md`、`TASK_SCENARIO_START_RESEARCH.md`；RTTI/type/Process和关键新分支又从原映像读取，不以JSON作为最终证据 |

本批方法影响：对查询、接取、提示和完成意图分别追调用位置，不把通知名称当协议含义；一次定向扫描原任务/UI发包字面值，再只核对代表性构包与Note分支，不继续穷举整个客户端。没有浏览跨版本手游资料，也未新增服务端设计值。

## S1：42条空表现分组

这42条原Animation0、Process0、JumpType0、ActiveUseItem0、TargetID/Num0、OtherType0、矩形全零，没有Start/Finish/Note/BranchNote。完整其他字段与资格仍保留，不能从“空”推定“无需授权”。

| 原ID/族 | 数量 | ActiveNpc/Map情况 | 原关联的边界 |
|---|---:|---|---|
| 102101,102201,102301,102401,102501,102601,102701,102801,102901,103001,103101 | 11 | NPC全0；前四Map1002/1002/1005/1003，其余Map0 | 章节节点均有RequestMissionList；不是同一入场事件即可完成 |
| 203201 | 1 | 0/0 | 二十级历练；名称不足以替代等级gate证据 |
| 203601,205701,233701 | 3 | 真实NPC，见下表 | 已确认菜单点击的CCommit意图，不等于原服激活规则 |
| 220901,221001,224301,224801 | 4 | 全0/0 | 升级福利；没有从这些字段证明自动领奖/跳过 |
| 231001..231801，步长100 | 9 | 231001 NPC999999；其余NPC0；Map全0 | 名人轶事，999999不替换成任意NPC |
| 231901..233101，步长100 | 13 | 全0/0 | 锦书谁寄；原后继仍保留 |
| 319901 | 1 | 0/0 | 名动江湖（完成）；“完成”标题不是原触发证据 |
| 合计 | 42 | 38个NPC0、1个999999、3个真实NPC；Map非零7条 | — |

三条真实NPC原值：

| task_id / 名称 | ActiveNpc / Map | MinLevel/MaxLevel | 原PostMissionList | XP/Money/PetXP/SMoney |
|---|---|---|---|---|
| 203601 [支线]千军万马来相见 | 10958 / 1007 | 29 / 155 | [203690] | 全0 |
| 205701 蜕变 | 11224 / 1003 | 50 / 155 | [205702] | 全0 |
| 233701 年的传说 | 13914 / 1007 | 40 / 0 | [233702] | 全0 |

三条RequestMissionList为空。MaxLevel0仍保留原值，不在本报告中解释成155；233701的节庆/活动资格不能从普通NPC路径反推已开放。原零奖励不被可接摘要或其他模板金额覆盖。

## N1：空表现NPC点击与state1 fallback

原菜单分类 `0x1257b20` 对type50仅bean.state3→class3；state0和state2都不是class3，且state2为failed，不能用作正常active。NPC菜单点击 `0x1636b81 → 0x164d780` 保存task/NPCkey；`0x164d865–0x164d873` 对class3设置phase2并调用 `0x164b530`。

`0x164b581–0x164b5b8` 计算Start数量，本三条为0；`0x164b5dc` 检查BranchNote长度，也为0，故 `0x164bb51` 返回AL0。首次点击立即在 `0x164d878–0x164d87e` 调 `0x1643360`，不存在可等待的本地对白句子。

type50走默认分支、Process0：`0x16437ce → 0xdd4780` 构造type0xc4a44，option对象+0x18初始化0；`0x16437d3–0x16437ef` 从UI复制taskID和NPCkey，`0x1643804` 发送。原marshal `0xe57530` 对应BE `i32 task_id | u64 npc_key | i32 option`。任务不存在/未获准、NPC/地图不匹配时，客户端能构包不等于服务器应完成；角色租约与可信交互票据仍必须校验。

收到state1：`0x125c105 → 0x125bb30` 移除active；Finish、Note均为空，在 `0x125c1c8 → 0x1255e70` fallback。Animation0写manager+0x70=0，随后按ActiveNpc进行场景对象清理/刷新。本链不会凭空显示对白或启动CG。无Finish就不建立本地phase3；不能增加CQuestDialogEnd完成门槛。

## N2：Note20的显示顺序和后继

20条Note-only原ActiveNpc/Map全0，Start/Finish/Branch空、Animation/Process/JumpType全0。唯一PostMissionList均为ID+1，后继20条全部MissionType56。

| Note task_id | 原轻功名称 | 唯一后继type56 |
|---:|---|---:|
| 221201 | 一段踏波行 | 221202 |
| 221301 | 一段穿云纵 | 221302 |
| 221401 | 一段燕子跳 | 221402 |
| 221501 | 一段雁行功 | 221502 |
| 221601 | 一段醉仙步 | 221602 |
| 221701 | 一段草上飞 | 221702 |
| 221801 | 一段提纵术 | 221802 |
| 221901 | 一段卧波行 | 221902 |
| 222001 | 一段水上漂 | 222002 |
| 222101 | 一段五禽术 | 222102 |
| 222201 | 二段踏水无痕 | 222202 |
| 222301 | 二段扶摇步法 | 222302 |
| 222401 | 二段凌波微步 | 222402 |
| 222501 | 二段神行无踪 | 222502 |
| 222601 | 二段青莲步法 | 222602 |
| 222701 | 二段飘香幻影 | 222702 |
| 222801 | 二段一苇渡江 | 222802 |
| 222901 | 二段彩翼凌空 | 222902 |
| 223001 | 二段天外飞仙 | 223002 |
| 223101 | 二段凤凰展翅 | 223102 |

221201原Note文字为“年轻人，恭喜你获得一级轻功踏波行修炼任务，这是对你智慧和体力的考验，说书人留。”部分二段Note用“二级”，部分用“二段”，保留原措辞；这不是客户端已执行学习/发任务的证明。

`SRefreshScenarioQuestState0xc4a47` Process `0x125ea00 → 0x125e660 → 0x125c020`：

1. 有bean时 `0x125c0f5` 写state，state1在 `0x125c105` 移除active。
2. `0x125c168` 先检查Finish，空。
3. `0x125c1a2` 检查NoteInfo.length（config+0x94），`0x125c1b7–0x125c1be` 调 `0x156d130(config+0x80,1,1,1)`。
4. 然后跳0x125c1cd，不进入本次fallback；没有在这里播放Start或构造任务上行。
5. 无bean重复state1仍在 `0x125c0a1–0x125c0bd` 调同一Note函数。该handler没有视觉去重。

P1在221201捕获原调用参数，确认两个分支均显示Note；没有真实弹窗/GPU验证。提示调用没有显式taskID参数，本次也未追出专用于此Note的确认任务包。不能要求用户关闭Note后再发CQuestDialogEnd，更不能认为Note出现意味着整个后继type56已完成。

这是**已证实的Note显示入口**，不是对全程序所有潜在Note调用者的穷举。SAccept通知观察者等尚未被全部解释，不声称Note只可能从此处显示。原数据/指令仍未给出：谁offer这个type50节点、哪项可信业务事件完成它、state1与type56接取投递顺序及断线恢复。上述服务端事项应保持unknown或另由主策划明确设计。

## N3：可接查询与SAccept——集合更新不是自动完成

| 协议 | 原证据 | 已确认作用 |
|---|---|---|
| CRequestQuestCanAccept0xc4a50 | ctor0xdd6ee0；marshal0xdd6f00与decode0xdd6f10只返回stream，无body读写 | 空体查询，无taskID/位置/触发原因 |
| SRequestQuestCanAccept0xc4a51 | vtable0x2281b04；marshal0xe72810、decode0xe72870；Process0x125cae0 | compact count + BE i32 IDs，可接任务集合 |
| SAcceptScenarioQuest0xc4a45 | vtable0x227df7c；Process0x125d5c0 | 携带ScenarioQuestInfo，插入原客户端active集合 |

UI查询发送处 `0x15fac30` 在 `0x15fac56–0x15fac60` 检查taskmanager+0x6c标志，为真时 `0x15fac62–0x15fac8b` 构造/发送空体0xc4a50；此分支没有具体taskID。

列表Process `0x125cae0–0x125caf0` 将packet+8交 `0x125b720`。后者比较/替换manager+0x3c的可接集合，清+0x6c标志，通知相关UI（如0x16098b0、0x15fecd0、0x1228ed0），并遍历配置关联更新NPC标记（`0x125b7d4–0x125b7fd`）。该函数没有直接调用active插入0x125d070、state1 handler0x125c020、Note函数0x156d130或发CCommit。被通知UI的所有间接行为未穷举，因此只能说“当前原链未闭合自动完成”，不能用列表自动授权这些节点。

SAccept Process `0x125d5c0–0x125d5e6` 按taskID查active，已存在直接返回，不把重复SAccept当状态更新；不存在才 `0x125d5e0 → 0x125d070`。插入路径更新NPC/DisplayNPC标记，`0x125d247–0x125d24d → 0x125cb80` 做通知；`0x125cb80` 在manager+0x48登记task/time，`0x125cc1b–0x125cc2f` 通过观察者投递回调0x1254ab0。本次未将这一观察者链闭合到type50自动提交/Note显示，不把“已接插入/通知”升级成完成证据。

## N4：SNotifyStart的实际时间含义，以及发包扫描边界

原RTTI `.?AVSNotifyStart@task@gsp@knight@@`，vtable0x227e2ec，ctor0xddab00写type0xc4a9c。marshal `0xe57f70–0xe57f87` 以0x7709b0写一个BE64；decode `0xddab90–0xddaba9` 调0x770650读到对象+8/+0xc。没有taskID字段。

Process `0x129dca0` 将这个64位值交 `0x129dc20` 的UI单例与 `0x129d510`：`0x129d544` 取clock，`0x129d549–0x129d55e` 用包值减当前值并除1000，`0x129d563–0x129d56a` 将负数钳0，写UI+0x50再刷新文字。UI创建 `0x129d8f0` 读取原ASCII路径 `StandAlone/Time`、`StandAlone/Time/Text1`、`StandAlone/QuestionBack`（文字地址0x229dd10/0x229dcf8/0x229dce0）。这是倒计时UI证据，不解释成Unix时间或任意任务延时授权。

本批一次定向扫描VA0x1000000–0x1800000的类型字面值：CRequest0xc4a50仅命中上述UI发送点；CQuestDialogEnd0xc4a52命中0x1640f62和0x1644cd5，前者是原构造器0x1640f50的类型写入，不是另一个自动发送点，后者是既有phase3清理。CCommit0xc4a44还在普通菜单/分支、到区与若干其他UI处出现，**这些字面值不证明其调用者属于本42/Note20**；本批没有把尚未关联的UI+task字段当作无NPC自动授权入口。

已有到区检查0x1257d50按MissionType余数6筛选，50余数0不适用；不能借type56的CQuestReachScene或自动CCommit证明type50触发。当前没有确认通用SNotifyScenarioQuest；不使用SNotifyStart/SEnterDialog替代它。

## P1：必要隔离验证与交付边界

| 原指令/样本 | 结果 |
|---|---|
| 203601/205701/233701：0x164b581→0x164bb53 | 空Start/BranchNote，AL0 |
| 同三条type50/Process0：0x16433a0→0x1643806 | 分别捕获原CCommit及对应taskID、synthetic NPCkey0x1122334455667788、option0 |
| 221201：0x125c168→0x125c1cd，Note非空，Finish空 | 原调用0x156d130(task+0x80,1,1,1)，不进fallback，manager+0x70哨兵保持不变 |
| 221201：0x125c058→0x125c0c2，无bean重复state1分支 | 仍调用同Note函数 |

探针退出0。只执行构包/条件分支/调用边界；没有真实网络、完整GUI、NPC对象操作或业务资产写入。没有新增研究脚本/JSON。实际读取原62条及20个后继，未扩大测试范围。

可交主线程继续恢复的原生接缝是：**3条真实NPC空表现的ready3→菜单点击→CCommit→事务成功state1 fallback**。领取前置、活动开放、可接offer、任务/奖励/后继原子性与重试属于服务器所有者和设计范围，本窗口没有实施。

收尾交接：主线程已报告完成3条emptyNPC支持，并以原203601/NpcScene10958执行caller事务必要检查，active0→ready3→CCommit、原零奖励与唯一后继203690同事务、重试/重登及原Start2/Finish122兼容均通过；234条当前范围记为127静态NPC+10intro+97未支持（movie2/start16/finish20/Note20/empty39）。这是主线程提供的实现/离线验证状态，本窗口没有另行复跑，也不代表GUI或线上已验证。Note20及其type56后继、SNotifyStart倒计时均保留本报告上述原生证据与授权边界。

确切未验证：NPC0/999999真实自动入口、轻功学习/试炼领取授权、原服触发/offer/周期规则、Note所有潜在显示路径及UI确认、原网络/断线顺序、真实GUI/点击、生产接线/部署/在线状态。不能用speaker替NPC，也不能把空体查询、列表返回、SAccept、提示弹出或客户端构包直接当完成授权。本文唯一写入时间以交付mtime为准。
