# 梦醒前驱凭据：公开只读接缝与诚实fixture边界

2026-10-24。按research技能直接核正式policy及现有任务源码；codebase-design用于把前驱证明收敛在各自任务Module的公开Interface。已读ARCHITECTURE、DESIGN_AUTHORITY。唯一新增本文；没有执行战斗、数据库、客户端或线上，也没有改源码、政策、共享入口。

## 结论

1. 正式`newbie-dream-return.1`要求第一族的**本路线原AI8002前驱通过可信任务战斗结算路径完成**；第二族要求**批准的画卷结算完成**。两者仅有journal completed均不够。
2. 当前两族都**缺公开的纯只读completed-proof查询**。战斗`_read`是私有且不检查完整终局证据；公开`acknowledge_task_battle_transaction`会进入公共奖励恢复，不能用来做只读前置。画卷`complete_puzzle_transaction`的paid分支同样不是只读；`resume_puzzle_messages`只投影bean，不提供完成来源。
3. 最小补齐应分别放在`task_battle.py`与`task_prologue_puzzle.py`，只读各自任务记录并返回冻结凭据；梦醒Resolver组合这些公开Interface，不借用battle_owner存储SQL，不重放旧奖励。
4. 正式PVE仍暂停时，可用显式Participant/BattleFinished **契约fixture**经真实任务admit/settle路径生成测试记录，验证任务侧接缝；它不是原AI8002实际战斗、不是合法生产胜利来源。按照当前政策“没有实战胜利时第一族继续不可达”，不能将这种fixture结果发布为第一族实际可达。这里的生产前置与测试替身口径需root保留明确区分，本审计不放宽政策。
5. 第二族可复用已存在正式policy画卷检查，在同一临时AccountStore保留它真实产生的画卷receipt/effect、后继active及私有目录，再接梦醒。此前故事与接近位置依然是明确fixture；不补造type40胜利。

## 正式来源与本轮源码身份

主策划policy：`design/newbie-dream-return-v1.json`：

- first.predecessor：`the exact original completed type40/AI8002 on this route, accepted through the trusted task battle-settlement path; this policy never manufactures victory`。
- second.predecessor：`the exact original completed type59 on this route through the approved puzzle settlement`。
- admission：旧RawDreamReturnIntent仍`settlement_authorized=false`，由新受政策约束Resolver准入。
- activation只授权隔离任务结算/临时存储换图验证，不授权改写真实角色或战斗。

`evidence/NEWBIE_DREAM_RETURN_DECISION.md`明确“没有实战胜利时第一族继续不可达”，并要求两族有效结算、各自独立缺前驱/缺active负例，不将late-story fixture当成自然完成前置战斗。

本轮只读时字节SHA256：

| 文件 | SHA256 |
|---|---|
| design/newbie-dream-return-v1.json | fd369d20ba847764eb6436f83819628b52f7f8bc54c743669c708d22edf304f4 |
| evidence/NEWBIE_DREAM_RETURN_DECISION.md | e9f29a133785c2f08b6b8d4da6ef0882092abd8f3b0870bc27735ed73dc1294b |
| task_battle.py | 7e8ebf2be8c7f94fca18d7a3eb9b49d5b841c254a049bbc3b13c59fdbb85ba93 |
| verify_task_battle_binding.py | 067bcad547ff544dc25cda38163f6a9a7d5ec187f0d8ffbf85abae7c0077e885 |
| task_prologue_puzzle.py | acf9714352c732ac9f8b8796f127f2c7c474c72a9c58637be6a8a2d369849a9a |
| verify_task_prologue_puzzle.py | 596ce6efd30b60c31492c670500ec7b9d3f91b806c26a7929f73f1f8a506a4aa |
| task_prologue_return_dialogue.py | c4de1011fd87760253091c30e080748eeb6fbbf71d88f752f368d589fa9935f8 |
| verify_task_prologue_return_dialogue.py | dd9dcf202041780ba4b91e8b6c528f0fff1253e93580614d4fd58c4b8f7cf7af |

## 精确原前驱域

已复核原边的完整资料见[PROLOGUE_DREAM_RETURN_RESEARCH.md](PROLOGUE_DREAM_RETURN_RESEARCH.md)；本轮不再次修改或扩张原域。

| 门派 | 第一族AI8002前驱→梦醒 | 第二族画卷前驱→梦醒 |
|---|---|---|
| 11 | 100110→100111 | 100120→100121 |
| 12 | 100209→100210 | 100219→100220 |
| 13 | 100309→100310 | 100319→100320 |
| 14 | 100409→100410 | 100419→100420 |
| 15 | 100509→100510 | 100519→100520 |
| 16 | 100609→100610 | 100619→100620 |
| 17 | 100709→100710 | 100719→100720 |
| 18 | 100809→100810 | 100819→100820 |
| 19 | 100909→100910 | 100919→100920 |
| 111 | 103210→103211 | 103220→103221 |

当前只读对白`task_prologue_return_dialogue._scope`（139行起）只检查前驱ID在completed集合，不检查其战斗/画卷来源；它原来仅返回raw意图，这与旧scope相符。**新正式结算Resolver必须另查可信前驱凭据**，不能由旧_scope通过推出新政策已满足。

## 第一族：真实已存在的任务战斗接口

`task_battle.py`：

- `load_task_battle_resources`（72）默认enabled_task_ids为空；原AI/元数据分类不是战斗准入。只有明确启用某ID及engine_revision才能开任务战斗。
- `open_task_battle_dialogue`（168）核当前active、实际NPC/Location、连接generation和期限；`admit_task_battle_transaction`（206）在开战前保存原taskID/AI、role/epoch、battle/settlement ID、engine_revision、definition fingerprint、完整ticket与Participant快照（237..254）。
- `settle_task_battle_transaction`（290）只收合格BattleFinished：task scope、eligible、role/epoch、settlement前缀、胜负字段一致、无自带物品/货币奖励、snapshot/engine版本匹配。胜利才创建`battle_won` TaskEvidence（335..340），同调用方事务完成任务/公共奖励并保存phase=won、result_fingerprint及终局receipt（341..345）。
- 私有`_read`（197）只读task_id/phase/fingerprint/plan，并校验plan散列；**没有校验terminal receipt、result_fingerprint、journal/effect source**。不应从梦醒调用私有函数，也不应只封装其返回值就称completed proof。
- 公开`acknowledge_task_battle_transaction`（281）→`_ack`（263）→`replay_completed_task_transaction`，可能走公共渠道恢复/更新effect；它是既有终局恢复，不是前驱纯查询。

### 建议新增的最小公开只读Interface（提案，当前不存在）

`read_completed_task_battle_proof(db, account_id, role_id, current_epoch, resources, registry, task_id)`。

由task_battle内部完成全部存储细节：

1. 当前角色所有权/有效租约、调用方事务；task_id精确属于传入原定义，AI与fingerprint一致。梦醒调用方再把返回taskID/AI8002与本路线唯一incoming对应。
2. 原任务journal确completed，task_effects存在；从其精确`source_event=task-battle:<battle_id>`定位本Module `(role_id,battle_id)`主键，避免扫描全部战斗历史或让调用方猜battle ID。
3. 校验admission plan散列及内部role/task/battle/scope/settlement身份、原定义/AI/engine revision；phase必须won，result_fingerprint有效，终局receipt的battle/task/settlement/phase/outcome一致且为victory。
4. effect.source_event与终局settlement ID一致；必要时通过公开`task_persistence.get_task_receipt`确认该request的TaskReceipt.effect_id正是本role/task的effect。它单独也不足以替代战斗终局证明。
5. 返回冻结小对象：taskID、AI、battle/settlement ID、definition/plan/result fingerprints、engine revision、原admission epoch、effect身份。只读，不ack、不补渠道、不完成后继、不更新状态。

历史胜利的admission epoch可以是旧租约；**读取须当前有效租约，但不能要求历史admission epoch==当前epoch**，否则合法完成后重登会失去前置。相反旧BattleFinished不能用新租约重新结算，这是不同Interface的约束。

现存记录保存了完整plan和result的散列，但没有完整BattleFinished正文。因此查询能核“任务Module已接纳的终局记录及其关联”，不能从散列反推出原敌方数值、回合过程或实际引擎执行。正式AI8002引擎授权/历史engine revision的可信来源仍应由任务战斗能力契约提供；当前任意非空engine字符串不等于原AI实现已批准。暂停新增admission可以保持enabled集合为空；若将来允许读历史真实终局，需保留经批准历史revision的核验依据，而不是为查询重新开放战斗。

## 第一族fixture：能验证什么，不能伪装什么

现有`verify_task_battle_binding.py`明确为task-only binding/receipt fixture。它启用的是**100107/AI8001**、engine=`offline_binding_fixture_v1`；Participant使用显式Fighter数值，`terminal()`直接构造BattleFinished，报告写enemy_ai_tested=false、combat_simulated=false。它没有运行原AI8002或任何原敌人AI，不能拿其已有胜利receipt当100110等前驱。

可复用的诚实测试层次：

| 层次 | 未来临时fixture方法 | 可声称的反馈 |
|---|---|---|
| 原定义与负例 | 按原路线加载精确AI8002/task；正式registry仍disabled；分别构造缺active、缺终局receipt、仅journal完成、错AI/定义/role/effect关联等受控负例 | 来源/准入检查的静态与隔离拒绝；不代表战斗完成 |
| 任务结算契约正例 | 仅临时库、显式fixture registry启用精确原AI8002 taskID；原章节/目录/入册/接近与Participant/结果均标fixture；调用公开open→admit→settle，再调新增readonly proof | 原AI8002**元数据**绑定、真实任务/奖励/receipt事务及readonly接缝接受一份可信调用方输入；没有执行AI8002战斗 |
| 实际正式AI8002 | 已批准实现的战斗Owner产生真实BattleFinished，连同其权威终局/资源结算接入同一事务 | 才能称本路线实际AI8002胜利前驱；当前PVE暂停且本轮禁止运行，未具备此反馈 |

第二层仍是**人工构造结果事件的契约fixture**，不是“真实打赢AI8002”。与直接SQL写journal='completed'/phase='won'、手工插入receipt或伪造battle_won TaskEvidence的差别，是它确实测试了公开admission/终局校验及真实任务事务；但二者都不能被宣传为原AI实战胜利。fixture registry/数值/结果不得进入生产能力表或被正式Resolver无条件认作actual original AI8002证明。

因此可诚实验证“第一族任务结算接缝的有效契约输入”，不可在当前暂停前提下声称“生产第一族实际有效前驱已验证”。若root希望将第二层作为正式梦醒隔离验收的正例，需保留明确fixture标识和验收限制；不能通过本审计暗改政策的“没有实战胜利第一族不可达”。本轮不执行任何一层测试。

## 第二族：已批准画卷完成的公开查询缺口

`task_prologue_puzzle.py:281`的complete流程已经同事务生成：

- task_journal completed与task_effect；source_event=`portrait-claim:<hash>`（303..305、329..333）。
- 原唯一梦醒后继active0（334..341）。
- effect.portrait_claim含admission、正式policy revision、operation_id、server_verified_board=false（342..350）。
- `task_prologue_puzzles`存role/task、operation_id、fingerprint、完整ticket JSON及source_event（351）。

这些来源已超出仅state.completed。新只读接口提案（当前不存在）：

`read_completed_puzzle_proof(db, account_id, role_id, current_epoch, resources, puzzles, task_id)`。

应在任务所属Module内核当前角色/创建路线，journal/effect/专用receipt三者一致；按批准的puzzles资源fingerprint重新核ticket与receipt hash、operation_id、source_event，effect.portrait_claim policy/admission/operation一致且server_verified_board严格false；ticket冻结chapter/directory须对应本角色当前原创建来源。返回冻结task/operation/policy/fingerprint/chapter/directory/effect证明，不恢复奖励、不发Finish、不调用complete的paid分支。正式Resolver须注入`load_puzzle_policy()`的批准资源，不能把`isolated-unapproved-puzzle-fixture`资源当政策前驱。

这里同样允许历史完成ticket的source.login_epoch与当前读取epoch不同：新租约只读取历史完成，不重用旧未付菜单许可。现`complete_puzzle_transaction`的paid分支需要精确旧ticket、会执行奖励恢复；`resume_puzzle_messages`没有返回receipt，因此二者都不能直接代替该只读接口。

## 第二族接同一临时调用方的最短真实路径

可沿现有`verify_task_prologue_puzzle.check_role(store,puzzles,...)`和`verify_task_prologue_return_dialogue.py:36..81`保留以下事实，不另写完成态：

1. 同一临时AccountStore调用正式puzzle policy/resource及公开检查。创建/intro为实际公开流程；后期入册、历史师父journal、程英对白前置与NPC接近均有明确fixture标注（check_role 65..88）。不把这些当自然故事或胜利。
2. check_role通过公开`open_puzzle_menu_transaction`、原native close字段、`complete_puzzle_transaction`，实际结算画卷360/360或100719的360/350，并生成receipt/effect及梦醒active0（174..186）。原native phase3是受控fixture；此处合法依据是已批准的authorized_client_assertion政策，不声称服务器解棋盘。
3. **继续使用同一store、同一role的持久记录**。check_role会换租约并测试完成恢复，返回值仅task/pet摘要，不能把其返回dict当权限凭据。后续获取当前租约/公开角色加载，使用`load_map_instance_transaction`取保留的真实私有地址，不新造公开1501或另分配目录。
4. 当前return对白检查已采用public save_checkpoint→bind_map_instance_transaction确认同一私有地址，显式接近10140/placement6/5464,1993为fixture，再由MapOwner/NpcScene产生新的当前证明和generation。没有冒称导航。
5. 在同一当前角色调用方事务中，先用新增readonly puzzle proof核真实完成来源，再用原return对白/真实key CCommit取得raw意图；新正式Resolver随后按梦醒policy处理。世界等待仍在SQL事务外，正式换图/资产/后继/编码按新政策同事务。不能直接拿raw对象当TaskEvidence。

需要单独保持的负例：仅journal completed没有receipt/effect、receipt policy/fingerprint/operation/source不符、其他路线画卷或旧目录、原画卷未完成但return active；与return本身缺active负例分别隔离，不把组合缺前提误报为单条件已验证。

## 决定、产物与未验范围

决定：新增查询归任务Module，历史证明与当前准入分开，公共paid恢复不伪装只读；正式前驱与契约fixture分开，第二族沿已有公开结算保存来源，不重写历史。

产物仅本文。验证仅为逐函数/字段/调用顺序和当前字节SHA静态核对；没有导入运行模块、执行DB/DDL、创建临时角色、执行战斗或运行verifier。本轮不声称新增查询已存在、第一族AI8002已实战或梦醒结算已完成。第一族实际战斗来源、公开readonly查询实现及正式梦醒同事务纵切仍是缺口；政策/验收口径冲突交root统一裁定，不另询问用户或修改中央政策。
