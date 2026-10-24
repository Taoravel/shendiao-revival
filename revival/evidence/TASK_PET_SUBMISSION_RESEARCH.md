# 原 MissionType13 交宠任务研究

本批为 research Skill 委派的后台只读研究。客户端证据、服务端业务策略与实际运行验收分开。以下 `client_verified` 指原资源、原指令及隔离执行结果；不表示原服消耗规则已取得，也不表示恢复服已经接线/部署或GUI完成。

## 最短已证协议和限制

1. **type13 → GiveDialog mode2** 已由原指令闭合；确认发送 **CSubmit2Npc `0xc2340`**，正常单元为 **`[(pet_key_i32, 1)]`**。body：`BE i32 taskID | BE u64 npcKey | BE i32 2 | compact_uint 1 | BE i32 petKey | BE i32 1`，一宠为25字节。没有宠模板、宠类型或绑定字段随包。
2. 此客户端的被选宠 key 从携带宠对象首字段、列表项+0xc0、GiveDialog+0xf8直到 SubmitUnit 都为32位。NPCkey另为完整64位。未发现本链“先有64位宠key再截断”的读法；原通用包校验将该unit首字段限制为正signed32，不能静默截取恢复库中的大宠key。
3. 原客户端拒绝参战宠、展示宠、加锁宠、宝宝(kind byte=2)、未选择/找不到的携带宠；自动选中仅优先第一个模板匹配且kind=1的对象。锁与绑定分开，本链检查锁，**未发现绑定检查**；这不能自动证明原服务端允许任意绑定宠交付。
4. 宠属性490显示为级；小于50直接构包，50及以上多一次交付确认。**50是防误交的确认门槛，不是任务宠等级要求**。
5. 发送 CSubmit2Npc 后关闭提交界面，不在这里直接播放任务 Finish，也没有发现本地删除宠物指令。Finish由任务完成 state1 的原 handler读取本地 FinishConversation 触发；只有服务器真正验证并结算后才能投影完成，不能把发包或关窗当完成授权。

## 一手来源

| 原来源 | SHA256 |
|---|---|
| `revival/evidence/native-image.bin`，VA基址0x400000 | 2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791 |
| `artres/config.pfs` → `autoconfig/knight.gsp.task.cmainmissioninfo.xml` | ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706 |
| 同PFS → `autoconfig/knight.gsp.pet.cpetattr.xml` | 89d947b24d2e61cfe38f8e0ff24ea8ae6ad12410e8ae73e95256a1f1de9b00c8 |
| 同PFS → `autoconfig/knight.gsp.message.cmessagetip.xml` | d0cfc9cb4613442be0bb8ec9262bf6db7f2c7fcb5ad28df05e150c4b0503fa20 |

本批直接读取原PFS成员，经长度/CRC检查后BXML解码；末尾保留14行全部属性和子列表，不只引用派生catalog。本文VA均绑定上述映像哈希。

## 14条原任务

| ID / 原名 | NPC / Map | GiveBackPetID / 原宠名 | 等级范围 / Transform | EXP / PetEXP / SMoney | Start / Finish | Post |
|---|---|---|---|---|---|---|
| 102508 [主线]君心我见 | 10632 / 1553 | 500023 剑之影 | 0–0 / 6028 | 0 / 0 / 0 | 0 / 4 | 102509 |
| 208404 [支线]老顽童的请求 | 10568 / 1007 | 500009 玉蜂 | 53–155 / 0 | 50000 / 30000 / 15000 | 1 / 2 | 208499 |
| 229304 老顽童的情人节 | 13644 / 1013 | 500009 玉蜂 | 0–0 / 0 | 0 / 0 / 0 | 1 / 8 | 229305 |
| 229712 生死茫茫 | 13662 / 1627 | 500009 玉蜂 | 0–0 / 0 | 0 / 0 / 0 | 0 / 4 | 229713 |
| 229718 生死茫茫 | 13662 / 1627 | 500009 玉蜂 | 0–0 / 0 | 0 / 0 / 0 | 0 / 4 | 229719 |
| 230503 [520]烦恼的青年 | 13786 / 1210 | 500009 玉蜂 | 0–0 / 0 | 0 / 0 / 0 | 1 / 5 | 230504 |
| 230803 五环任务 | 13794 / 1108 | 500011 山貂 | 0–0 / 0 | 0 / 0 / 0 | 1 / 2 | 230804 |
| 232103 锦书谁寄 | 10161 / 1104 | 500009 玉蜂 | 0–0 / 0 | 0 / 0 / 0 | 0 / 2 | 232199 |
| 310302 名动江湖·自创秘术($round$/3) | 10218 / 1007 | 500002 小花猫 | 0–0 / 0 | 0 / 0 / 0 | 0 / 2 | 310399 |
| 310402 名动江湖·自创秘术($round$/3) | 10218 / 1007 | 500001 小灰狗 | 0–0 / 0 | 0 / 0 / 0 | 0 / 2 | 310499 |
| 310502 名动江湖·自创秘术($round$/3) | 10218 / 1007 | 500003 野猪 | 0–0 / 0 | 0 / 0 / 0 | 0 / 2 | 310599 |
| 314102 名动江湖·慈悲为怀($round$/3) | 10218 / 1007 | 500002 小花猫 | 0–0 / 0 | 0 / 0 / 0 | 0 / 1 | 314199 |
| 314202 名动江湖·慈悲为怀($round$/3) | 10218 / 1007 | 500001 小灰狗 | 0–0 / 0 | 0 / 0 / 0 | 0 / 1 | 314299 |
| 314302 名动江湖·慈悲为怀($round$/3) | 10218 / 1007 | 500003 野猪 | 0–0 / 0 | 0 / 0 / 0 | 0 / 1 | 314399 |

14条中6条名字含`$round$`；这是原循环元数据，不可按一次性任务自动结算。102508有TransformID6028，不能略去其变身机制；其文案明确要求“非宝宝的野生剑之影”。8条非round仍不等于8条已能在真实场景交付；活动开放、NPC placement、前置和实例授权由其他所有者负责。

全14的ActiveInfoTargetID/Num均0；交宠模板用 **ActiveInfoGiveBackPetID**，不是把TargetNum0解释为交0只。全14的MoneyReward、ShengWang、GiveBackMoney、UseItemID、OtherType、AIID、ProcessBarTime、AnimationID、BranchNpcID及RewardMapJumpType/目标地图坐标全0；完整零值与其他字段按附录保留。实际正常UI每包选一只并写数量1，不能由通用vector能力推定原服支持批量交宠。

原解析字段名 UTF16 `ActiveInfoGiveBackPetID` 在 `0x226c17c`；`0xbb61e4..0xbb6210` 调 `0x409ce0` 并把值写 config+0x1a8。原宠物表确认500001小灰狗、500002小花猫、500003野猪、500009玉蜂、500011山貂、500023剑之影；表中模板`kind=1`不等于每只实例的宝宝/野生状态，不能只拿模板kind替代实例byte检查。

## 原入口与选中规则

### type13入口

- `0x164368b cmp eax,0xd` 命中MissionType13；`0x1643690` 先调用 `0x10831b0` 并要求非零，此前置函数本批不完整归名，不当服务器授权。
- `0x1643699 push2` → `0x164369b` 跳 `0x16436ad`；后者把原对话UI+0x48 taskID、+0x38/+0x3c NPCkey与mode传入 `0x168a1e0`。
- GiveDialog保存+0x58/+0x5c NPCkey、+0x60 taskID、+0x64 mode。`0x168a454` 判断mode2，调用 `0x1682c20` 构建宠列表；这段遍历携带宠容器(manager+0x278)，将每只宠的32位key放入列表项，不在列表构造中按任务模板/绑定/锁做过滤。
- 原任务配置查找链在 `0x168a5f0..0x168a698`；普通Scenario配置找到后，`0x168a6e2..0x168a6f4` 读 config+0x1a8 并调用 `0x168a090` 自动选中。

### 自动选择不是最终资格检查

`0x168a090..0x168a117` 顺序遍历UI+0xfc列表：`0x168a0cb` 取列表项+0xc0的key；通过 `0x112ffd0(key,1)` 查携带宠；`0x168a0e3` 要求 pet+0x29==1；`0x168a0ed` 要求 pet+4==所需模板；第一条匹配在 `0x168a102` 保存pet首字段到UI+0xf8并选中列表，然后刷新详情。

自动选择片段不检查是否参战/展示/锁定/绑定，所以“已自动选中”不等于可交付；若首只匹配宠不合格，不证明它会继续自动寻找下一只。手动选择 `0x1689bb0..0x1689bd8` 直接把当前列表项+0xc0写入UI+0xf8，并刷新详情；这里也没有按任务模板再次限制手动对象。

`0x112ffd0` 的kind1分支在 `0x112ffdd..0x113002b` 遍历manager+0x278容器，对 node+8 的32位字段作key比较，并返回宠对象node+8；非携带对象不可仅凭某个外部key当作列表内宠。

## 原确认检查与包构造

确认事件 `0x1688990` 在 `0x16889b0..0x16889b5` 的mode2调用 `0x1687ac0`。

| 原VA | 条件 / 原行为 |
|---|---|
| `0x1687aff..0x1687b32` | UI金额+a8/+ac若>0先走另一通用提示路径；不是交宠金额字段。正常交宠不输入金额 |
| `0x1687b37..0x1687b77` | selected key==manager+0x190，提示0x2267a，拒绝 |
| `0x1687b7c..0x1687b94` | selected key==manager+0x194，提示0x2267b，拒绝 |
| `0x1687b96..0x1687baa` | selected key==0，提示0x229a1，拒绝 |
| `0x1687bac..0x1687d0a` | 少数800xxx任务专用检查；见下述范围，不能套给本14条 |
| `0x1687d0f..0x1687d27` | `0x112ffd0(key,1)` 找不到当前携带宠则返回 |
| `0x1687d2d..0x1687d6a` | pet+0x68非零，提示0x22ea5，关提交窗并返回 |
| `0x1687d6f..0x1687db4` | pet+0x29==2，提示0x22dbb，显示NPC提示并关提交窗返回 |
| `0x1687db9..0x1687dd3` | 读取pet属性map+0x34内的490(0x1ea)，与50比较，>=50进防误交确认 |
| `0x1687dd9..0x1687e5b` | <50直接构造单unit=(UI+0xf8,1)，CSubmit2Npc type/mode2/任务/NPCkey，发送 |
| `0x1687e83..0x16880d4` | >=50组装名字/级/颜色提示0x22a84，并注册确认回调0x1684930 |
| `0x1684930..0x16849d2` | 肯定回调再次构造同一包和单unit=(UI+0xf8,1)，发送；没有改成数量/模板ID |

原提示正文直接读取自cmessagetip：

| 提示ID | 原正文 |
|---|---|
| 0x2267a / 140922 | 这是你的参战宠啊，可别给错啦。（若确定给予该宠物请取消参战吧） |
| 0x2267b / 140923 | 这是你展示的宠物啊，可别给错啦。（若确定给予该宠物请取消展示吧） |
| 0x229a1 / 141729 | 请先选择一个宠物。 |
| 0x22ea5 / 143013 | 这只宠物已经加锁了，请先解锁！ |
| 0x22dbb / 142779 | <T t="少侠看清楚了哦，这个是"></T><T t="宝宝" c="FFFF3333"></T><T t="，我是不收的，请给我一只"></T><T t="野生" c="FFFF3333"></T><T t="的宠物吧。"></T> |
| 0x22a84 / 141956 | [colour='ffffffff'][border='00']你确定要将[colour='$parameter3$'][border='ffff3333'] $parameter1$[colour='ffffffff'][border='00']（[colour='ffffff33'][border='00']$parameter2$[colour='ffffffff'][border='00']级）拿来交付任务吗？千万别把自己常用的参战宝宝交了哦！ |

原level支路用490作提示参数2“级”，`0x1135089..0x113509d` 的刷新也把消息+0x30写入该属性。这里按原指令和提示归名，不把50当需要交给任务的最小宠等级。

### 模板检查的实际范围

`0x1687bb6` 调 `0x1253440`，该函数仅对六个显式任务值返回真；准确原十六进制为`0xc38e8,0xc3cd0,0xc44a0,0xc4c70,0xc4504,0xc5058`。**本14任务无一命中**。只有命中该特殊列表、mode2且任务bean存在，才在 `0x1687c3c..0x1687c42` 对 pet+4 和该bean+0x40检查模板。

普通14条确认链直接进 `0x1687d0f`，所以不能声称“客户端确认已严格检查任务模板”。模板仅自动选中的来源已确认；恢复服务端仍必须核当前任务原GiveBackPetID与所交真实实例模板，不能由客户端所选或UI当前显示推定。

### 锁与绑定必须分开

原实例flag投影 `0x10c2bc7..0x10c2be7`：

```text
pet+0x6a = raw flag
pet+0x68 = bool(raw flag & 0x05)       // 本交宠提示明确称加锁
pet+0x69 = (raw flag >> 1) & 1       // 原绑定查询读取的独立位
```

原绑定查询 `0x11308c0` 在 `0x1130916..0x113091a` 检查pet+0x69。mode2本次确认函数没有调用该查询，也没有直接检查+0x69；pet+0x68不是绑定的同义词。raw flag2在原片段得到lock0/binding1，raw flag1/4分别得到lock1/binding0。能够证明客户端不以绑定字段作此处拒绝条件，**不能证明原服真实消费规则允许绑定宠、已培养宠或任何特殊保护状态**。

kind字段也同理：自动选择要求1；确认显式拒绝2。某其他kind值穿过这个局部分支，不等于它已获业务授权，不能将`!=2`扩大成所有种类都允许。普通kind1/宝宝kind2的来源与原“非宝宝野生”提示相互支持，未知实例类别仍应保留未知。

## wire精确形状与范围

CSubmit2Npc vtable `0x2284a94`；原ctor `0xf15850`，type写入`0xf15884`；marshal `0xf16270`，decode `0xf16320`；vector marshal `0xf16440`；SubmitUnit vtable `0x2284ab8`，marshal `0xf16160`，decode `0xf15b80`。

```text
taskID        BE signed32
npcKey        BE 64位；原validator要求按signed64非负
submitType    BE signed32 = 2
unitCount     compact_uint = 1
unit[0].key   BE signed32 = 当前携带宠实例key
unit[0].num   BE signed32 = 1
```

通用validator `0xf161f0..0xf16264` 要求taskID>=0、NPCkey>=0、mode>=0、每个unit两字段>0；它不强制mode2、单宠、数量1、模板匹配、宠归属或野生/锁等。实际服务端接入要比通用validator更严格。包无客户端重试ID、宠版本和宠状态快照，所需幂等/事务/租约不能由wire自行提供。

此链从列表→实例→UI→unit都是32位宠key。不能先截一个64位恢复库ID再查宠，也不能把模板500009塞到实例key槽伪造宠物。宽NPCkey与宠key是两个独立字段。

## Finish何时出现

CSubmit2Npc直接路径在 `0x1687e5d..0x1687e68` 关窗；>=50确认回调在 `0x16849ed..0x16849f6` 关窗。二者均不调用Finish renderer，不显示“已结算”或本地删除宠。不能以本地关窗当作原服已收宠。

任务状态handler `0x125c020`：已接bean分支 `0x125c0ee..0x125c105` 写收到state并在state==1时移除记录；`0x125c168..0x125c19b` 检查 config+0x304/+0x308 即FinishConversation，非空则以taskID调用 `0x164beb0`。所有14条Finish非空。renderer `0x164bf00..0x164bf10` 保存taskID并设phase3，随后从本地Finish列表逐句绘制。没有服务器逐句下发此本地对白的需求证据。

无bean的重复state1分支 `0x125c04d..0x125c09e` 也检查Finish并调同一renderer；所以客户端删除bean不保证重复完成包不重播Finish。服务端应保证资产幂等并明确通知重试策略，但本报告不替代接入方制定投递规则。

phase3结束后 `0x1644c1d..0x1644cf2` 的CQuestDialogEnd仅在AnimationID>0、JumpType>0或本地task值>300000等条件走发送分支。前8条非round任务ID<300000且Animation/Jump均0，不能额外要求它们以CQuestDialogEnd授权交宠完成。6条round ID>300000可能走该phase3后置包；这是原本地Finish后的通知，不反向证明任务/周期结算已可跳过。无原证要求交宠走CEndPlayCG。

## 少量离线原指令验证

无在线进程或原客户端启动/附加。内联Python `-B` 使用现有原映像与离线harness，仅在隔离内存给定输入，未新增研究.py。

1. **真实mode2构造片段**：执行 `0x1687dd9..0x1687e5d`，含原CSubmit2Npc ctor `0xf15850`；仅vector追加作内存适配、网络虚调用捕获不发送。task208404、NPCkey `0x1122334455667788`、宠key `0x12345678` 得 type0xc2340 / mode2 / one unit(305419896,1)。不是仅手写期望包。
2. **真实完整marshal**：同fixture执行原 `0xf16270`，原validator、vector `0xf16440`、unit `0xf16160`到达；仅CRT memcpy/security-cookie返回适配。得到25字节，并与独立BE构造完全一致：

```text
00032e14 1122334455667788 00000002 01 12345678 00000001
```

3. **原拒绝条件片段**：执行 `0x1687d25` 起：lock1/kind1到0x1687d33锁提示；lock0/kind2到0x1687d74宝宝提示；lock0/kind1与kind3均到0x1687db9。kind3只作局部分支对照，不授予业务可交资格。
4. **原flag投影片段** `0x10c2bc7..0x10c2bea`，raw0/1/2/4/6分别得到(lock,binding)=(0,0)/(1,0)/(0,1)/(1,0)/(1,1)，原指令证明锁与绑定独立。
5. **原完成表现分支**：执行 `0x125c168..0x125c1cd`，合成非空Finish与task208404，捕获原 `0x164beb0(task208404)` 调用；UI singleton/renderer边界适配，不执行GPU/GUI。此项证明state1委托Finish renderer，未证明真实现场出现。

未完整跑原按钮事件生命周期、>=50弹窗点击、真实宠删除下行或NPC场景，不把这些探针称为GUI验收。

## 服务端仍未知，不能用其他能力代替

- 原服是否实际收走宠、何时收走、失败恢复、重试去重、后继/奖励与宠消耗的事务顺序，均不在该客户端提交函数中。本报告不编原服宠消耗规则。
- 当前恢复项目可借公开、被授权的同角色事务宠交付Interface接入；free_pet是放生业务，私有SQL是实现细节，二者都不能仅凭本报告当作已获交宠授权。接口/资源owner决定必须独立记录。
- 宠实例kind、锁、绑定、参战、展示、归属与版本应来自当前可信快照；缺某字段时不能填零伪造“可交”。模板匹配和数量1必须在服务器核验。
- 原自动选择不核所有最终限制；参战/展示/锁/绑定可能在打开UI之后改变，不能永久信任旧列表或仅做前置UI检查。
- 任务激活/ready投影、临时NPC实例、循环六条、Transform6028、原绑定奖励兑现与缺失字段的设计裁定不由本研究批准。

## 方法与本批范围

实际使用research Skill的主要决定：直接追原PFS/native所属来源；当前窗口已是主线程委派后台研究，不递归开代理；把“原客户端确认链”与“原服实际消耗/恢复服接口授权”拆开记录。重新读取项目ARCHITECTURE和DESIGN_AUTHORITY，据其单一状态所有权约束，不写生产/公共入口，不越过宠物和资产事务所有者。

唯一写入文件：`revival/evidence/TASK_PET_SUBMISSION_RESEARCH.md`；写入时间 2026-10-23T18:10:03+08:00。仅执行离线配置读取、反汇编及以上有界原指令探针；无.py、policy、catalog、shared修改，无服务/在线服/当前客户端操作，无持久宠实例变化。未测GUI、正式扣宠/奖励事务、部署、并发、实际NPC placement或活动开放。原关键链已足够提供接口约束，本批不扩展大量其他宠玩法或攻略。

## 附录：14原行全字段与列表

每项node/attrs/text/children直接取本批原BXML，保留原字符串、零值、speaker及列表顺序。

### 102508

```json
{"node":"record","attrs":{"id":"102508","MissionName":"[主线]君心我见","MissionTypeString":"主线剧情","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"6028","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"13","ActiveInfoNpcID":"10632","ActiveInfoMapID":"1553","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"500023","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"呜哇！什么东西！竟然敢吓到我姑姑，看我不抓住你好好教训一顿！\" c=\"ff12c4ff\" ></T><T t=\"【提示：剑之影在古墓地宫五、六层及宠物迷城中有几率出现，完成任务需要捕捉非宝宝的野生剑之影】\" c=\"ffe9f231\"></T>","TaskInfoPurposeListA":"<T t=\"将\"></T><G t=\"剑之影\" m=\"1224\" x=\"21\" y=\"107\" j=\"4\"></G><T t=\"抓回来让\"></T><G t=\"小龙女\" npcid=\"10632\"></G><T t=\"处置。\"></T>","TaskInfoTraceListA":"<T t=\"将\"></T><G t=\"剑之影\" m=\"1224\" x=\"21\" y=\"107\" j=\"4\"></G><T t=\"抓回来让\"></T><G t=\"小龙女\" npcid=\"10632\"></G><T t=\"处置\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"102509"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10632"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"这位神仙姐姐饶命啊，小的知错了，以后在也不敢吓人了……"},{"node":"string","attrs":{},"text":"你又没吓到我，求什么饶。"},{"node":"string","attrs":{},"text":"咳咳……好了，既然我姑姑都不追究了，你就赶快消失吧！别在我面前出现了！"},{"node":"string","attrs":{},"text":"好了，闹也闹够了，下面我要你去帮我办件事。"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"11286"},{"node":"int","attrs":{},"text":"10632"},{"node":"int","attrs":{},"text":"10683"},{"node":"int","attrs":{},"text":"10632"}]}]}
```

### 208404

```json
{"node":"record","attrs":{"id":"208404","MissionName":"[支线]老顽童的请求","MissionTypeString":"支线剧情","MinLevel":"53","MaxLevel":"155","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"50000","MoneyReward":"0","PetExpReward":"30000","ShengWang":"0","SMoney":"15000","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"13","ActiveInfoNpcID":"10568","ActiveInfoMapID":"1007","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"500009","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"周老前辈所做的一切都只是为了好玩，为了开心，看着他即快乐又逍遥，叹服他的境界超然呀。答应了周老前辈，捉玉蜂交给他。\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"捕捉\"></T><G t=\"玉蜂\" m=\"1010\" x=\"100\" y=\"100\"></G><T t=\"交给\"></T><G t=\"周伯通\" npcid=\"10568\"></G><T t=\"。\"></T>","TaskInfoTraceListA":"<T t=\"捕捉\"></T><G t=\"玉蜂\" m=\"1010\" x=\"100\" y=\"100\"></G><T t=\"交给\"></T><G t=\"周伯通\" npcid=\"10568\"></G>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"208499"}]},{"node":"ScenarioInfoNpcConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"前辈，你要的玉峰也给你抓回来了。"}]},{"node":"ScenarioInfoNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"1"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"做的不错呀，既然这样我就把这个惊天的秘密告诉你吧。我准备拿这蝴蝶泉水来养这些玉峰，锻炼它们的水性。你觉得这个是不是很好玩？这个秘密可千万不要告诉别人啊。"},{"node":"string","attrs":{},"text":"啊，原来这就是那个惊天的秘密呀。前辈果然是境界超然。"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10568"},{"node":"int","attrs":{},"text":"1"}]}]}
```

### 229304

```json
{"node":"record","attrs":{"id":"229304","MissionName":"老顽童的情人节","MissionTypeString":"节日活动","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"13","ActiveInfoNpcID":"13644","ActiveInfoMapID":"1013","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"0","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"500009","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"小孩果然还是要用哄的，去捉只玉蜂哄老顽童开心。\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"为\"></T><G t=\"周伯通\" npcid=\"13644\"></G><T t=\"捉来\"></T><G t=\"一只玉蜂\" m=\"1010\" x=\"165\" y=\"13\"></G><T t=\"。\"></T>","TaskInfoTraceListA":"<T t=\"为\"></T><G t=\"周伯通\" npcid=\"13644\"></G><T t=\"捉来\"></T><G t=\"一只玉蜂\" m=\"1010\" x=\"165\" y=\"13\"></G><T t=\"。\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"0","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"229305"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"13643"},{"node":"int","attrs":{},"text":"13644"}]},{"node":"ScenarioInfoNpcConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"周大哥，你看这是何物啊！"}]},{"node":"ScenarioInfoNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"1"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"玉蜂！这只玉蜂好漂亮啊！小兄弟，谢啦！"},{"node":"string","attrs":{},"text":"哎？这玉蜂可是我千里迢迢从终南山捉来的，本想与周兄弟一同耍玩，不想周大哥整日闷闷不乐的，好没意思，周大哥要不给我解释解释原委，这玉蜂我可要收回啦！"},{"node":"string","attrs":{},"text":"别呀...哎呀！就和兄弟你说好啦，我在想一个人..."},{"node":"string","attrs":{},"text":"瑛姑前辈，对吧。"},{"node":"string","attrs":{},"text":"兄弟果然料事如神啊，就是她没错..."},{"node":"string","attrs":{},"text":"听闻瑛姑前辈此时正在百花谷野外赏花，周大哥何不去与她相会呢？"},{"node":"string","attrs":{},"text":"还是不去了好吧，当年年轻时曾给过瑛姑一枚飞镖作为信物，拜托兄弟你去瑛姑那取来可好，看见此物就如见她一般，我也就心满意足了..."},{"node":"string","attrs":{},"text":"周兄弟既有所求，我定然不负期望，我去去就来！"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"13644"},{"node":"int","attrs":{},"text":"1"},{"node":"int","attrs":{},"text":"13644"},{"node":"int","attrs":{},"text":"1"},{"node":"int","attrs":{},"text":"13644"},{"node":"int","attrs":{},"text":"1"},{"node":"int","attrs":{},"text":"13644"},{"node":"int","attrs":{},"text":"1"}]}]}
```

### 229712

```json
{"node":"record","attrs":{"id":"229712","MissionName":"生死茫茫","MissionTypeString":"节日任务","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"13","ActiveInfoNpcID":"13662","ActiveInfoMapID":"1627","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"0","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"500009","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"蜂翼道破人间，玄机必在深潭。\" c=\"ff12c4ff\" ></T><B></B><T t=\"可以和\"></T><G t=\"黄蓉\" npcid=\"13661\"></G><T t=\"一同下谷。\"></T>_x000D_\n","TaskInfoPurposeListA":"<T t=\"再去附近抓一只玉蜂给\"></T><G t=\"黄蓉\" npcid=\"13662\"></G><T t=\"瞧瞧。\"></T>_x000D_\n","TaskInfoTraceListA":"<T t=\"再去附近抓一只玉蜂给\"></T><G t=\"黄蓉\" npcid=\"13662\"></G><T t=\"瞧瞧。\"></T>_x000D_\n","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"0","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"229713"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"13662"},{"node":"int","attrs":{},"text":"13663"},{"node":"int","attrs":{},"text":"13664"},{"node":"int","attrs":{},"text":"13665"},{"node":"int","attrs":{},"text":"13666"},{"node":"int","attrs":{},"text":"13667"},{"node":"int","attrs":{},"text":"13661"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"情谷底，我在绝。情谷底，我在绝。啊，是了，这里四面都是高逾百丈的峭壁，无路可通，潭边的大树奇形怪状，不知名目，云雾封谷，难见天日。关键必是这碧水寒潭，少侠你内力深厚，又善水性，不知可否去那水中一探？"},{"node":"string","attrs":{},"text":"黄帮主交代，后辈定当竭力而为。"},{"node":"string","attrs":{},"text":"凡事小心，若有古怪之处不要逞强，回来大家再做计量。"},{"node":"string","attrs":{},"text":"谨遵前辈嘱托。"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"13662"},{"node":"int","attrs":{},"text":"1"},{"node":"int","attrs":{},"text":"13662"},{"node":"int","attrs":{},"text":"1"}]}]}
```

### 229718

```json
{"node":"record","attrs":{"id":"229718","MissionName":"生死茫茫","MissionTypeString":"节日任务","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"13","ActiveInfoNpcID":"13662","ActiveInfoMapID":"1627","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"0","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"500009","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"蜂翼道破人间，玄机必在深潭。\" c=\"ff12c4ff\" ></T><B></B><T t=\"可以和\"></T><G t=\"黄蓉\" npcid=\"13661\"></G><T t=\"一同下谷。\"></T>_x000D_\n","TaskInfoPurposeListA":"<T t=\"再去附近抓一只玉蜂给\"></T><G t=\"黄蓉\" npcid=\"13662\"></G><T t=\"瞧瞧。\"></T>_x000D_\n","TaskInfoTraceListA":"<T t=\"再去附近抓一只玉蜂给\"></T><G t=\"黄蓉\" npcid=\"13662\"></G><T t=\"瞧瞧。\"></T>_x000D_\n","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"0","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"229719"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"13661"},{"node":"int","attrs":{},"text":"13662"},{"node":"int","attrs":{},"text":"13663"},{"node":"int","attrs":{},"text":"13664"},{"node":"int","attrs":{},"text":"13665"},{"node":"int","attrs":{},"text":"13666"},{"node":"int","attrs":{},"text":"13667"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"情谷底，我在绝。情谷底，我在绝。啊，是了，这里四面都是高逾百丈的峭壁，无路可通，潭边的大树奇形怪状，不知名目，云雾封谷，难见天日。关键必是这碧水寒潭，少侠你内力深厚，又善水性，不知可否去那水中一探？"},{"node":"string","attrs":{},"text":"黄帮主交代，后辈定当竭力而为。"},{"node":"string","attrs":{},"text":"凡事小心，若有古怪之处不要逞强，回来大家再做计量。"},{"node":"string","attrs":{},"text":"谨遵前辈嘱托。"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"13662"},{"node":"int","attrs":{},"text":"1"},{"node":"int","attrs":{},"text":"13662"},{"node":"int","attrs":{},"text":"1"}]}]}
```

### 230503

```json
{"node":"record","attrs":{"id":"230503","MissionName":"[520]烦恼的青年","MissionTypeString":"节日任务","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"13","ActiveInfoNpcID":"13786","ActiveInfoMapID":"1210","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"0","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"500009","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"捉只玉蜂给青年暗恋的小萍。\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"为青年暗恋的\"></T><G t=\"小萍\" npcid=\"13786\"></G><T t=\"捉\"></T><G t=\"一只玉蜂\" m=\"1010\" x=\"165\" y=\"13\"></G><T t=\"。\"></T>","TaskInfoTraceListA":"<T t=\"为青年暗恋的\"></T><G t=\"小萍\" npcid=\"13786\"></G><T t=\"捉\"></T><G t=\"一只玉蜂\" m=\"1010\" x=\"165\" y=\"13\"></G><T t=\"。\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"0","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"230504"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"13786"},{"node":"int","attrs":{},"text":"13785"}]},{"node":"ScenarioInfoNpcConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"小萍，你好啊，有个朋友托我送你一个小礼物。"}]},{"node":"ScenarioInfoNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"1"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"玉蜂！这只玉蜂好漂亮啊！太感谢了！不知道是谁托你送我的呢？"},{"node":"string","attrs":{},"text":"这只玉蜂是他千里迢迢从终南山捉来的，想托我送给你，其实主要是想告诉你，他暗恋你已经很久了。"},{"node":"string","attrs":{},"text":"..."},{"node":"string","attrs":{},"text":"不知道他是谁呢，能让他来见我吗？"},{"node":"string","attrs":{},"text":"好的，我去去就来。"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"13786"},{"node":"int","attrs":{},"text":"1"},{"node":"int","attrs":{},"text":"13786"},{"node":"int","attrs":{},"text":"13786"},{"node":"int","attrs":{},"text":"1"}]}]}
```

### 230803

```json
{"node":"record","attrs":{"id":"230803","MissionName":"五环任务","MissionTypeString":"节日活动","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"13","ActiveInfoNpcID":"13794","ActiveInfoMapID":"1108","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"0","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"500011","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"抓一只山貂送给欧阳峰，求他帮助解救中毒的士兵\" c=\"ff12c4ff\" ></T>_x000D_\n","TaskInfoPurposeListA":"<T t=\"找\"></T><G t=\"欧阳峰\" npcid=\"13794\"></G><T t=\"帮忙。\"></T>","TaskInfoTraceListA":"<T t=\"为\"></T><G t=\"欧阳峰\" npcid=\"13794\"></G><T t=\"捉来\"></T><G t=\"一只山貂\" m=\"1011\" x=\"157\" y=\"43\"></G><T t=\"。\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"0","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"230804"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"13794"}]},{"node":"ScenarioInfoNpcConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"有人中毒管我什么事！！！"}]},{"node":"ScenarioInfoNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"13794"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"看在山貂的面子上，就勉为其难的帮你小娃娃一把，这不可是黄老邪的面子大！！"},{"node":"string","attrs":{},"text":"晚辈知晓，晚辈还要去探望一灯大师，就不与欧阳前辈同去襄阳了，晚辈告辞。"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"13794"},{"node":"int","attrs":{},"text":"1"}]}]}
```

### 232103

```json
{"node":"record","attrs":{"id":"232103","MissionName":"锦书谁寄","MissionTypeString":"日常任务","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"13","ActiveInfoNpcID":"10161","ActiveInfoMapID":"1104","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"500009","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"周伯通托你给瑛姑送去玉蜂。\"></T>_x000D_\n","TaskInfoPurposeListA":"<T t=\"去把玉蜂送给\"></T><G t=\"瑛姑\" npcid=\"10161\"></G>_x000D_\n","TaskInfoTraceListA":"<T t=\"去把玉蜂送给\"></T><G t=\"瑛姑\" npcid=\"10161\"></G>_x000D_\n","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"232199"}]},{"node":"RewardItemIDList","attrs":{},"children":[{"node":"int","attrs":{},"text":"64378"}]},{"node":"RewardItemNumList","attrs":{},"children":[{"node":"int","attrs":{},"text":"1"}]},{"node":"RewardItemIsBindList","attrs":{},"children":[{"node":"int","attrs":{},"text":"1"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"瑛姑，这是周大哥让我送来的。"},{"node":"string","attrs":{},"text":"哎，这么大把年纪还是不改脾性。少侠，多谢你奔波操劳，这点不成谢意。"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"1"},{"node":"int","attrs":{},"text":"10161"}]}]}
```

### 310302

```json
{"node":"record","attrs":{"id":"310302","MissionName":"名动江湖·自创秘术($round$/3)","MissionTypeString":"单人任务","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"13","ActiveInfoNpcID":"10218","ActiveInfoMapID":"1007","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"0","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"500002","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"黄药师真不愧是精通百术之人，那个宠物的斗转星移之术真是闻所未闻，如果不是亲眼见过真是不会相信啊。少侠你如果想见识一下的话就请替我抓一只小花猫来吧。\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"去抓一只\"></T><G t=\"小花猫\" m=\"1014\" x=\"100\" y=\"100\"></G><T t=\"给\"></T><G t=\"宠物加强师\" npcid=\"10218\"></G><T t=\"。\"></T><T t=\"(当前第$round$/3环)\" c=\"ffffff33\"></T>","TaskInfoTraceListA":"<T t=\"抓\"></T><G t=\"小花猫\" m=\"1014\" x=\"100\" y=\"100\"></G><T t=\"给\"></T><G t=\"宠物加强师\" npcid=\"10218\"></G><T t=\"($number$/1)\" c=\"ffffff33\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"0","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"310399"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"少侠真是好快的身手，来来，我先试试，成功了之后再演示给你看。"},{"node":"string","attrs":{},"text":"那是什么眼神，别那么看着我，我也没说一定就成功啊……"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10218"},{"node":"int","attrs":{},"text":"10218"}]}]}
```

### 310402

```json
{"node":"record","attrs":{"id":"310402","MissionName":"名动江湖·自创秘术($round$/3)","MissionTypeString":"单人任务","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"13","ActiveInfoNpcID":"10218","ActiveInfoMapID":"1007","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"0","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"500001","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"黄药师真不愧是精通百术之人，那个宠物的斗转星移之术真是闻所未闻，如果不是亲眼见过真是不会相信啊。少侠你如果想见识一下的话就请替我抓一只小灰狗来吧。\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"去抓一只\"></T><G t=\"小灰狗\" m=\"1014\" x=\"100\" y=\"100\"></G><T t=\"给\"></T><G t=\"宠物加强师\" npcid=\"10218\"></G><T t=\"。\"></T><T t=\"(当前第$round$/3环)\" c=\"ffffff33\"></T>","TaskInfoTraceListA":"<T t=\"抓\"></T><G t=\"小灰狗\" m=\"1014\" x=\"100\" y=\"100\"></G><T t=\"给\"></T><G t=\"宠物加强师\" npcid=\"10218\"></G><T t=\"($number$/1)\" c=\"ffffff33\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"0","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"310499"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"少侠真是好快的身手，来来，我先试试，成功了之后再演示给你看。"},{"node":"string","attrs":{},"text":"那是什么眼神，别那么看着我，我也没说一定就成功啊……"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10218"},{"node":"int","attrs":{},"text":"10218"}]}]}
```

### 310502

```json
{"node":"record","attrs":{"id":"310502","MissionName":"名动江湖·自创秘术($round$/3)","MissionTypeString":"单人任务","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"13","ActiveInfoNpcID":"10218","ActiveInfoMapID":"1007","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"0","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"500003","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"黄药师真不愧是精通百术之人，那个宠物的斗转星移之术真是闻所未闻，如果不是亲眼见过真是不会相信啊。少侠你如果想见识一下的话就请替我抓一只野猪来吧。\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"去抓一只\"></T><G t=\"野猪\" m=\"1002\" x=\"100\" y=\"100\"></G><T t=\"给\"></T><G t=\"宠物加强师\" npcid=\"10218\"></G><T t=\"。\"></T><T t=\"(当前第$round$/3环)\" c=\"ffffff33\"></T>","TaskInfoTraceListA":"<T t=\"抓一只\"></T><G t=\"野猪\" m=\"1002\" x=\"100\" y=\"100\"></G><T t=\"给\"></T><G t=\"宠物加强师\" npcid=\"10218\"></G><T t=\"($number$/1)\" c=\"ffffff33\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"0","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"310599"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"少侠真是好快的身手，来来，我先试试，成功了之后再演示给你看。"},{"node":"string","attrs":{},"text":"那是什么眼神，别那么看着我，我也没说一定就成功啊……"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10218"},{"node":"int","attrs":{},"text":"10218"}]}]}
```

### 314102

```json
{"node":"record","attrs":{"id":"314102","MissionName":"名动江湖·慈悲为怀($round$/3)","MissionTypeString":"单人任务","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"13","ActiveInfoNpcID":"10218","ActiveInfoMapID":"1007","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"0","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"500002","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"当时一灯大师慈悲为怀，看见我在这摆弄这些宠物就觉得大大不妥，最后说动我放了很多，导致现在我的宠物都没了，不管怎么说我要靠这个吃饭呀，麻烦少侠给我抓一些日常的小宠物回来，我不会虐待它们的。\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"去抓一只\"></T><G t=\"小花猫\" m=\"1014\" x=\"100\" y=\"100\"></G><T t=\"给\"></T><G t=\"宠物加强师\" npcid=\"10218\"></G><T t=\"。\"></T><T t=\"(当前第$round$/3环)\" c=\"ffffff33\"></T>","TaskInfoTraceListA":"<T t=\"抓\"></T><G t=\"小花猫\" m=\"1014\" x=\"100\" y=\"100\"></G><T t=\"给\"></T><G t=\"宠物加强师\" npcid=\"10218\"></G><T t=\"($number$/1)\" c=\"ffffff33\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"0","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"314199"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"一灯大师已经和我说定了，只要我不虐待那些抓来的宠物，或许这是它们最好的归宿，毕竟这世道人都吃不饱……"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10218"}]}]}
```

### 314202

```json
{"node":"record","attrs":{"id":"314202","MissionName":"名动江湖·慈悲为怀($round$/3)","MissionTypeString":"单人任务","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"13","ActiveInfoNpcID":"10218","ActiveInfoMapID":"1007","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"0","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"500001","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"当时一灯大师慈悲为怀，看见我在这摆弄这些宠物就觉得大大不妥，最后说动我放了很多，导致现在我的宠物都没了，不管怎么说我要靠这个吃饭呀，麻烦少侠给我抓一些日常的小宠物回来，我不会虐待它们的。\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"去抓一只\"></T><G t=\"小灰狗\" m=\"1014\" x=\"100\" y=\"100\"></G><T t=\"给\"></T><G t=\"宠物加强师\" npcid=\"10218\"></G><T t=\"。\"></T><T t=\"(当前第$round$/3环)\" c=\"ffffff33\"></T>","TaskInfoTraceListA":"<T t=\"抓\"></T><G t=\"小灰狗\" m=\"1014\" x=\"100\" y=\"100\"></G><T t=\"给\"></T><G t=\"宠物加强师\" npcid=\"10218\"></G><T t=\"($number$/1)\" c=\"ffffff33\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"0","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"314299"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"一灯大师已经和我说定了，只要我不虐待那些抓来的宠物，或许这是它们最好的归宿，毕竟这世道人都吃不饱……"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10218"}]}]}
```

### 314302

```json
{"node":"record","attrs":{"id":"314302","MissionName":"名动江湖·慈悲为怀($round$/3)","MissionTypeString":"单人任务","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"13","ActiveInfoNpcID":"10218","ActiveInfoMapID":"1007","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"0","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"500003","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"当时一灯大师慈悲为怀，看见我在这摆弄这些宠物就觉得大大不妥，最后说动我放了很多，导致现在我的宠物都没了，不管怎么说我要靠这个吃饭呀，麻烦少侠给我抓一些日常的小宠物回来，我不会虐待它们的。\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"去抓一只\"></T><G t=\"野猪\" m=\"1002\" x=\"100\" y=\"100\"></G><T t=\"给\"></T><G t=\"宠物加强师\" npcid=\"10218\"></G><T t=\"。\"></T><T t=\"(当前第$round$/3环)\" c=\"ffffff33\"></T>","TaskInfoTraceListA":"<T t=\"抓一只\"></T><G t=\"野猪\" m=\"1002\" x=\"100\" y=\"100\"></G><T t=\"给\"></T><G t=\"宠物加强师\" npcid=\"10218\"></G><T t=\"($number$/1)\" c=\"ffffff33\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"0","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"314399"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"一灯大师已经和我说定了，只要我不虐待那些抓来的宠物，或许这是它们最好的归宿，毕竟这世道人都吃不饱……"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10218"}]}]}
```
