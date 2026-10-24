# 神雕侠侣复原：主策划统一裁定

生效日期：2026-10-23。适用对象：本地 1.6.1 端游客户端，网络版本 601。用户授权主策划统筹各恢复窗口，并在客户端和攻略均无法确认时补全玩法、制定数值。

架构硬约束：实现或接入服务器功能前读取 `ARCHITECTURE.md`。按角色、地图实例和战斗场次划分状态所有者，阻塞I/O退出网络循环；现有同步恢复代码按该文迁移。此约束同样适用于本地设计值功能。

## 每个缺口的处理顺序

1. 客户端验证：查原始资源、配置、文本和原生编解码，记录路径、行 ID、字段与含义。表内存在一个数值，只证明该字段存在；公式顺序、单位和服务端用途另记证据。
2. 攻略核对：优先同款端游官方资料，再看端游攻略。记录链接、文章日期、适用版本与冲突。手游、《神雕侠侣2》资料须单独标注，不直接充当本版本事实。
3. 策划补全：完成有针对性的资料查找仍未知，即采用设计值继续实现。设计值集中登记，写清适用范围、单位、取整、上下限、奖励归属与替换条件。无需因为缺少原服规则重复等待用户确认。
4. 交付：分开报告“资料提取 / 协议核验 / 服务端实现 / 客户端实测”。批量恢复优先；保留解析、基本运行和涉及状态写入的必要检查。

来源状态统一为 `client_verified`（客户端证据）、`guide_supported`（攻略支持）、`inferred`（推定）、`designed`（主策划补全）。来源状态与实现/实测状态分别记录。

## 当前共用依据

- `evidence/design-client-audit.json`：本批直接重读原始 config.pfs，进行长度/CRC、BXML 解码及完整配置行比对；并非仅引用既有 JSON。
- `catalogs/knight.gsp.pet.cpetattr.json`：158 条宠物定义。500001 小灰狗的攻击资质范围为 1040–1220，成长档原始整数为 986/996/1006/1016/1026。倍率换算、抽样概率尚待确认。
- `catalogs/knight.gsp.pet.cpetnextexp.json`：宠物经验表；0/1/2 行 exp 为 50/200/450。等级索引与经验消费流程在调用处明确后采用。
- `catalogs/knight.gsp.role.cattrmoddata.json`：人物属性转换系数；联查属性 ID 定义，避免将系数表当作完整人物成长公式。
- `catalogs/knight.gsp.role.cresmoneyconfig.json`：已有 nextexp，1/2/3 行分别为 89/195/373；优先接入原表，不另造等级经验曲线。resmoney/expreference 不能仅凭字段名直接当作初始货币或任务奖励。
- 药品 `cfooddrugeffectformula` 的 ai/bi、技能 `cskillconsume` 的 numberrand 均有客户端值；参数顺序、单位、概率含义另核验。
- `evidence/DESIGN_SOURCE_RESEARCH.md`：本轮端游来源和适用性记录；有具体系统缺口时继续查对应攻略。

## 第一版设计裁定

`design/recovery-baseline.json` 是主策划补全参数的唯一来源。各模块接入、部署和GUI结果分别记录，不由配置存在推定运行服已生效。明确证实的客户端值优先于补全；已有存档与角色属性不由训练配置覆盖。

训练战斗先用固定攻防模型打通普通攻击、防御、死亡与结算。此模型仅用于本地训练入口，不宣称还原门派技能或原版战斗平衡。敌人 HP=60，攻击=12，防御=4，速度=8；无属性接口时训练人物 HP=100，MP=100，攻击=20，防御=5，速度=10。伤害=max(1,攻击−防御)，防御行动使本回合所受伤害向下取整减半且至少为1。相同速度按战斗位置号升序；训练不启用随机浮动、暴击、闪避。用已有真实人物属性时优先真实值。

未知任务经验采用任务最低等级对应 nextexp 的比例：纯对话20%，战斗40%；经验=max(1,floor(nextexp×比例))。例如1级对话17、战斗35经验。仅用于缺失奖励且已确认完成的任务，按角色和任务实例唯一结算；周期任务的实例需包含周期。领取等级不改变任务等级奖励。已有原奖励优先。未知任务类型另登记设计，避免所有交互统一判定完成。货币与道具奖励按明确的货币映射、道具 ID 接入，不能凭展示名映射。

上述训练与任务经验在攻略不能确认公式后作为 `designed` 发布；各模块记录自己的检索范围、采用版本和验证结果。宠物随机成长分布、装备强化概率等在实际实现缺口出现时逐项裁定，优先复用已恢复原表。

本轮官方端游资料核对完成，未找到上述三项补全公式的可靠原式，维持设计值。另将[历史官方战斗规则](https://sdxl.wanmei.com/info/qita/fight/20120729/133541.shtml)中的30秒输入窗口、200回合上限作为 `guide_supported` 候选；尚未证明该历史规则与1.6.1完全一致。人物每级潜能和宠物血脉规则按来源报告对照客户端后接入。官方剧情总表含部分明确奖励，先对齐任务 ID，原奖励优先于比例补全。

宠物成长补全：原包与官方端游攻略调查见 `evidence/PET_NUMERIC_RESEARCH.md`。经验表0–150和1001–1150两段均保留原值，不拟合平方曲线；成长1256≈每级12.56总属性点仅有历史攻略支持。仍未知的索引、余数分配和派生属性已由主策划制定 `design/pet-growth-v1.json`，整套标为designed，逐字段保留原值依据。该文件是宠物成长补全的单一来源，与共用baseline分别管理不同参数。事务、原生刷新与任务奖励接入状态查INVENTORY_INTEGRATION及ARCHITECTURE_ACCEPTANCE；人物/宠物完整平衡另验。不覆盖已有宠物实例，不将未知构造零属性当作成长存档。

人物普通升级补全：研究见 `evidence/ROLE_PROGRESSION_RESEARCH.md`，参数单一来源 `design/role-progression-v1.json`。普通1–155逐行nextexp保留，1001–1129特殊段不按减1000猜映射；人物属性ID110是命中，不能替代外攻。设计采用当前级经验消费、10级前奖励后自动升级、10级起手动每请求一级、每级五维各1及自由5的潜能账本。原生请求默认BE32零仅作为本地普通升级入口，字段业务名称仍未确认。现有角色须明确初始化基线且不补发历史潜能；此裁定未修改在线角色。完整派生属性与原生刷新单独核验，不能把只实现等级账本当成完整人物成长完成。

人物普通派生属性：`design/role-attributes-v1.json`及纯计算 `role_attributes.py`，从显式、带版本的属性基线加成长增量计算。原HP/MP、命中、躲闪、外防、速度及内攻内防系数保留，但按成长增量组合是designed；缺失外攻设计为基线外攻+2×力量增量+2×等级差，与命中ID110分开。新角色基线均标设计，InitialRoleProfile仅是纯创建模板，须保存明确新建来源及政策版本后于有效角色租约兑现；旧角色不得静默套用或追补过去潜能。装备、技能、经脉及特殊阶段另作已核验/版本化修正。HP/MP成长保留缺失量、死亡不复活。成长事务、普通属性刷新、入场与重连的当前进度见 `evidence/ROLE_ATTRIBUTES_DECISION.md`；伤势上限640=maxHP仅是未实现伤势系统时的明确设计。该配置未声称原版平衡或完整人物成长已完成。

普通换图接线裁定：原生已查普通同步加载与本地定时器，尚无通用ready回包证据，不能套首次/任务回包。设计文件 `design/scene-transition-v1.json` 允许目标场景包经目标连接精确发送屏障后，由服务器事件激活已提交目标，同时必须隔离旧批次/旧版本输入并继续验证移动连续性与NPC实例。该屏障只是服务器发送完成，不能称客户端加载/可见确认；原移动报文本身无场景世代，无法完美区分字节完全相同的迟到旧/新请求，必须保留协议限制。未接全部输入防护和匹配屏障之前保持loading，不用任意延时伪造确认。仍须真实客户端跨图行走及故障恢复验收。

货币奖励与费用：接入任务MoneyReward/SMoney、钱包基线或组织扣款前，读 `evidence/CURRENCY_DECISION.md`；规则单一来源 `design/currency-v1.json`，事务模块 `currency.py`。字段→现金/绑定银映射为designed，原奖励金额与零值保留；已有角色不隐式建钱包或清pending。四币原生UI槽位已独立追通，`currency_protocol`发送当前绝对余额；元宝须成对且各限非负signed32，未知另一项不得填零。账本、原生布局与真实显示分别验收。

NPC仓库存取同样读CURRENCY_DECISION的追加裁定：`npc_depot_transfer`设计为同角色现金与显式仓库现金等额无费转移，双方余额和账本/命令凭据同租约事务；原64位请求与独立显示槽位已核验，未知旧基线拒绝。该用途不授权跨角色交易、绑定银消费或商会资金业务。

普通商店绑银mode1接入前读`evidence/NPC_SHOP_BOUND_PAYMENT_DECISION.md`和`design/npc-shop-payments-v1.json`。原控件/请求mode已核验，完整结算配方仍为designed；仅当前合法普通服务2、原货架正价，独立npc_shop_bound扣绑银并产binding1，同事务/已付兼容必须验证。库存不推原菜单权限，零价/特殊mode不兜底免费。

人物治疗294接入前读`evidence/NPC_ROLE_HEALING_DECISION.md`和`design/npc-role-healing-v1.json`。原CNpcService/等级×30标签已核验；10380关联、现金费用及HP>0补最终HP/MP为designed，独立npc_heal/npc_role_heal；仅已知无伤势profile和普通等级1..155，满状态新操作不扣、死亡不复活、paid只读当前。家族/其它治疗服务不扩权。

普通任务宠物经验：接入PetExpReward前读 `evidence/TASK_PET_EXPERIENCE_DECISION.md`，规则唯一来源 `design/task-pet-experience-v1.json`。完成前固定当前参战宠与人物等级，原量不均分，+5及无宠/死亡的处理明确designed；旧完成记录无接收者快照保留待核对，重试不切换接收宠物。与成长、人物/货币/道具渠道同事务，原刷新按固定key发送当前绝对XP。

普通升级/加点请求接线：读 `evidence/ROLE_GROWTH_ACTIONS.md`，使用role_growth_protocol按type分别解码，再调用role_growth_actions加入角色租约事务。人物加点wire体/内/力/敏/耐与内部最后两项相反；两种请求都无客户端重试ID，同一受理命令幂等与新的相同线包必须区分。

新角色出生、type50及重连开场：读 `evidence/NEWBIE_OPENING_DECISION.md`，政策唯一来源 `design/newbie-opening-v1.json`。43角色门派原路线与movie端点来自客户端，采用端点作服务器出生位置、章节授权/恢复及intro字段0/1投影均明确designed。独立创建来源授权root，CEnd须匹配当前播放且与后继/奖励同事务；真实EXP不参与intro判定。原电影临时Setmap不改服务器权威位置。

首师父选武器及type59：读 `evidence/NEWBIE_MASTER_CARD_DECISION.md`，政策 `design/newbie-master-card-v1.json`。43首师父200xx是原选择卡，原Start尾句仅发CCommit；合法当前对白提交→获准SPlayCardEffect→CGetCardItem二选一。原phase3的CQuestDialogEnd不适用于本批Start-only任务。物品/完成/后继同事务，绑定1及精确获领实例实际装备slot0判定为designed；原模板/数量已由客户端确认。

新手车夫传送：读 `evidence/NEWBIE_CART_TRANSFER_DECISION.md`及`design/newbie-cart-transfer-v1.json`。原地图/坐标保留，cell解释inferred、采用×16和单事务任务/位置提交为designed；仅正常state0/mask1可走目标，源失败恢复与目标提交后重连按持久交接决定执行。原唯一option0须当前NPC/任务冻结凭据授权，不猜通用ready或提前完成后继。

血手印读条或私有1501实例：先读`evidence/NEWBIE_BLOODMARK_INSTANCE_DECISION.md`，参数为`design/newbie-bloodmark-v1.json`和`design/story-instance-v1.json`。仅十个原节点/43真实章节路线；3000ms/15000ms及独立剧情目录为designed，原坐标×16仍inferred。当前共享模板路由不代表已支持私有地址；原后继仅active，正式战斗继续禁用。

NPC交互距离或原CVisit准入：读`evidence/NPC_INTERACTION_CELL_DECISION.md`，新候选唯一规则`design/npc-interaction-v2.json`。新原公共CNpc访问判据已证：逻辑非负坐标除16的格差平方<169，采用为server规则仍designed，原serverunknown；不是208像素圆。旧32/血手印48仅保留v1显式历史验证，见NPC_INTERACTION_DISTANCE_DECISION。角色当前完整地址/实体/世代/租约/版本及权限复核保持；运行服是否选v2另验。

序章画卷type59/服务553：读`evidence/NEWBIE_PUZZLE_DECISION.md`，规则`design/newbie-puzzle-v1.json`。仅原十任务/43真实章节，接受授权客户端声明而非验证棋盘；最短0/许可300000ms为designed，原360及桃花宠350保留，后继仅active0。前置正式战斗与后继梦醒传送不由该政策完成。

Scenario任务显示枚举：按 `evidence/TASK_TRACKER_FAILURE_RESEARCH.md` 与task_protocol命名常量，active0、完成移除1、failed2、ready3；原x86确认2会显示“任务已失败”。此前设计active2已被现场与原指令反证，禁止继续作为进行中投影。此纠正不改持久active/completed或章节身份；卡片等尚未具备玩法时也应准确恢复已有active bean，不能因不支持普通对白而丢重连追踪。

师承武器人物属性：读 `evidence/ROLE_EQUIPMENT_DECISION.md`，政策 `design/role-equipment-v1.json`。原81/811/1231分别映射总80/810/1230，不是百分比；从当前裸身成长与当前已穿装备重算绝对值，额外加强封印基线必须显式记录。新恢复角色设计0、旧角色已知基线另供；未知装备/高级修饰拒绝。当前纯投影、事务和共享自然链/成长/修理已分别验证，来源、源码接线、部署与GUI结果按决定文档区分，不能将仅穿戴成功称属性已在现场生效。

普通六槽会改生命/真气上限时，先读`evidence/ROLE_RESOURCE_TRANSITION_DECISION.md`、`ROLE_RESOURCE_EQUIPMENT_SEAM_AUDIT.md`及`ROLE_RESOURCE_STORAGE_INTEGRATION.md`。`design/role-resources-v1.json`设计穿脱/损坏/修理保持绝对资源、降低上限时裁剪；成长按同装备最终上限增量保持缺失量，死亡不复活；单记录存储和消费者最新接线/完成条件以交单维护，不把裸身vitals和装备vitals永久双写，也不把读档当治疗。选择普通六槽v2、1240基线或装备policy升级前另读`evidence/ORDINARY_EQUIPMENT_V2_INTEGRATION.md`及其单一政策`design/role-equipment-v2.json`：默认v1保持，未知基线不推0，原套装/百分比等未恢复语义不静默删除；pure/临时事务验证不等于共享激活或现场生效。

新创建资源授权：实现真实建角、首次兑现或激活新profile前读`evidence/ROLE_RESOURCE_CREATION_AUTHORIZATION.md`，单一政策`design/role-resource-creation-v1.json`。许可在同一真实创建事务另存，稳定绑定原creation_id及四policy；历史new_restoration_role/format1不追补，已付加载只读当前。当前仅授权.1规则的实现与隔离验证，自动开关及部署仍关闭。

普通物理战斗终局写人物资源前读`evidence/ROLE_RESOURCE_COMBAT_INTEGRATION.md`：仅可信入场快照对应的consume-only结果，保持同caps/source，由角色事务完整CAS/凭据结算；政策显式combat_causes授权，不能治疗/复活或自动迁移。该数值接缝验证不表示暗雷整体、技能公式或真实战斗已验收。

同库保存不同装备policy时，先读`evidence/EQUIPMENT_POLICY_SELECTION_INTEGRATION.md`。启动可冻结多套规则，当前角色按持久basis精准选择，缺失/未知明确拒绝；加载可用规则不等于全局切v2或自动升级旧None基线。原生退出初始化则读`evidence/ROLE_EXIT_UI_DECISION.md`及`design/role-exit-ui-v1.json`，普通模式值-1为designed，不能把0误作普通窗。

NPC装备鉴定状态查询：读`evidence/NPC_IDENTIFICATION_QUERY_DECISION.md`及单一规则`design/npc-identification-query-v1.json`。仅当前临安10890/p75显式495关联、mode1、128有序vector预算、当前角色已知干净详情只读；重复保序同值，未知/外物/穿戴/仓库/过期不兜底。原495是本地菜单分支，不虚构先行CNpcService包。此查询不授权c4276收费/改flag或随机结果；完整公式待独立政策，官方跨年代及原fixture范围见NPC_IDENTIFICATION_SOURCE_RESEARCH。

序章两次梦醒：读`evidence/NEWBIE_DREAM_RETURN_DECISION.md`和单一政策`design/newbie-dream-return-v1.json`。仅原20节点/43路线、已active和真实前驱完成、当前已采用私有1501及原NPC新证明；raw×16解释inferred、采用public1006两目标/5分钟期限designed。保留125/0、450/450原奖励，同事务handoff/任务/资产/唯一后继与编码；提交后重登目标、不重复奖励。原RawDreamReturnIntent保持未授权，正式许可独立；不造战斗胜利、不提前CG或定义第二次入梦。

NPC固定基础结果鉴定：读`evidence/NPC_EQUIPMENT_IDENTIFICATION_DECISION.md`和`design/npc-equipment-identification-v1.json`。只限可信已持久保存的explicit_known_clean_instance未鉴定普通基础结果，原16精确报价键、现金purpose独立、绑定与其余字段保留为designed；不生成随机附加属性、不补未知档、不改默认identified1。query上下文+新NPC证明/租约/版本，公开Inventory CAS、费用/唯一source/凭据和native编码同事务；收费片与已验只读query分开审验部署。

NPC宠物忠诚新报价：读`evidence/NPC_PET_LOYALTY_V2_DECISION.md`与`design/npc-pet-loyalty-v2.json`。原1140是当前PetBlood.power，逐宠(45+2×power个位)×缺口累加；已知字段按原消费，新server采用designed。未知旧blood且已知合法care明确保留旧45来源，不补blood；畸形known拒绝。原free≤20的-3映射0，保留npc.1/旧paid fingerprint且receipt-first不补扣、不回放；kind4资源项等旧规则不变。此费用片与当前private整批分开审验部署。

家族银箱数值、跨Owner付款恢复及296接线前读 `evidence/FAMILY_DONATION_ROOT_DECISION.md`。执行参数仍唯一位于baseline的organizations.family_donation及family_construction_targets；每箱资金100000、消耗阈值结转及满级处理为designed，原建设1/声望5保留。两个unbound槽各+5投影同一逻辑奖励，不据此授权累计10或分别消费；真实本家族完整实例/NPC证明、选中箱子及current唯一source precommit另验。数值已复核，当前private发布不夹组织闭包。

序章首技能、人物其他技能账本或建角技能授权前读 `evidence/NEWBIE_FIRST_SKILL_DECISION.md` 及单一政策 `design/newbie-first-skill-v1.json`。原100008玩家身份、十节点/43路线/120经验已核；完成教学免费授value1、已有取max保留、最短1000ms为designed。角色所有者持完整known技能基线和版本，原SSendOtherSkills必须发完整当前map；历史缺档不推空。任务窗口单写新ledger/协议/任务域，main单写建角/登录/共享接线；正式AI8001暂停及独立战斗公式保持，不混当前费用或碰撞发布。

## 窗口职责与共用接口

| 现有聊天 | 负责范围 | 跨模块交付 |
|---|---|---|
| 你负责恢复神雕侠侣的战斗系统 | 战斗状态、行动、表现与结算 | 战斗实例 ID、胜负、参与角色、任务事件 |
| 你负责恢复神雕侠侣的任务 | 接取、目标、对话、进度、奖励 | 可信游戏事件入口、奖励请求与唯一键 |
| 你负责恢复召唤兽系统装备道具 | 背包、装备、宠物、道具效果 | 属性快照、物品增减、宠物参战与成长 |
| 你负责恢复地图大世界 | 坐标、移动、传送、NPC交互 | 服务端校验后的位置/NPC交互事件 |
| 你负责恢复社交功能 | 好友、聊天与在线投递 | 在线角色目录和投递入口 |
| 你负责NPC所有的恢复以及功能的接入 | NPC菜单、服务授权及对应领域调用 | 可信NPC服务凭据、调用方事务Interface，统一交原始集成窗口接shared |
| 你恢复神雕侠侣的怪物 暗雷遇怪 这些 | 怪物原数据、区域暗雷与遭遇提议 | 地图/角色版本化触发、稳定遭遇ID与战斗参与快照；正式怪物不套训练数值 |

按 `codebase-design`，各模块通过小接口隐藏数据库、协议和状态细节；客户端输入由所属模块校验后才进入任务事件入口。奖励写入由统一结算操作完成，成功记录与资产变化应在同一事务，重试返回既有结果。现阶段尚未形成这些接口的部分在交付中明示。

各窗口在 `evidence/<系统>_DESIGN_GAPS.md` 或已有对应文档记录待补字段、来源、当前设计值、跨模块依赖。共享文件修改前重读最新版并局部编辑；主策划维护本文及共用补全配置，各系统窗口维护自己的实现和证据。发现与裁定冲突时先保留已知事实，记录差异，由主策划合并修订。

部署时由原始集成窗口宣布短暂源码冻结、保存数据一致性备份并核对最终内容哈希；其确认启动完成后主策划通知各窗口继续。冻结涉及启动将导入的源码/配置，各玩法继续按实体所有权执行；只读研究和交接文档可继续。发布采用已核验的不可变源码副本，保留原项目资源与运行存档路径，后续工作区改动不自动进入运行进程。人类另开NPC、暗雷等窗口也纳入该协作范围，避免旧职责表遗漏写者。当前实际角色在线时由集成窗口集中处理部署/保存提示，其他窗口不同时关闭连接、重启进程或操作人类角色。

## 本批方法与验收记录

- research：后台核对端游来源，限制跨版本外推；来源逐项记入研究报告。
- codebase-design：战斗、任务、资产、世界和社交通过事件、属性快照与结算接口衔接，共用数值集中配置。
- writing-for-agents：将证据检索、补全条件和交付标准写成可执行步骤；职责与来源各有单一记录位置。
- 产物：本文、补全参数、原包抽查记录、来源报告，并已将口径通知五个恢复窗口。
- 验证记录：初批原包CRC/解码、JSON与算例，及后续人物/宠物/货币/章节/按钮的独立事务、Owner与原生codec结果，统一查ARCHITECTURE_ACCEPTANCE和各分支决定文档，不以本页缓存实现进度。
- 当前限制：完整玩法、商业存储与容量、GUI与多系统实际验收尚未完成；来源、源码、部署、现场画面必须分别举证。已部署intro的人工反馈及tracker/按钮修复范围见NEWBIE_OPENING_DECISION，后续源码不自动视为已部署。
