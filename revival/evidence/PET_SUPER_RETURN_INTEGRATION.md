# 超级还童候选与确认保存

候选/保存与灵石交叉前读[PET_STONES_INTEGRATION](PET_STONES_INTEGRATION.md)：预览/保存保留已知石头来源，baseline含完整版本，最终资质/成长只含一次效果。

进化最新：普通kind1/3宝宝阶段、稀疏跳终阶、50次追加成长及材料/成长同事务、原生刷新与真实加密Owner共享链路已通过；普通/超级还童现保留已知进化成长。接线、原/设计边界、旧档来源及未验范围见PET_EVOLUTION_INTEGRATION.md。神兽蜕变/灵石/宠装、发布与原GUI提示/动画继续恢复，全量active。

年糕最新：五种实际服用、原预测37,920例、总20次、同事务/原生提示及真实加密Owner共享链路已通过；旧四字段审计升级、耗尽重试、故障回滚和重登已验。接线、浮点差异与设计边界见PET_CAKE_CONSUMABLES_INTEGRATION.md。未发布/GUI，进化、灵石、宠装及剩余装备道具继续恢复，全量active。

后续普通31002/31087完整重置已实现并离线验证，当前接线与来源边界见PET_ORDINARY_RETURN_INTEGRATION.md；本文末尾“普通重置尚未实现”为本批当时的历史状态。

2026-10-23。所属领域实现及原生 Adapter 已完成离线验收；共享 Owner 路由、发布和真实客户端操作仍待集成。全量目标保持 active，普通还童及其余进阶继续恢复。此前 PET_TRAITS_INTEGRATION 的“尚无超级保存事务”为历史阶段，当前以本文为准。

## 接线步骤与完成条件

1. 启动调用现有 Inventory.prepare，冻结新增 return_rules/score_rules/cake_rules 并创建候选、凭据、年糕表。业务热路径只使用注入配置，无建表/文件读取。新恢复宠物同事务显式初始化年糕0；旧未知仍为 None。完成条件：启动完成后，角色命令不打开配置或自行迁移旧实例。
2. 原 CUseItem `0xc03ff` 的 `>iiQ(item_key,1,pet_key)`，仅可信当前携带31576实例走 `receive_super_return(USE_ITEM,body,epoch,request_id,draws=seven_draws,now_ms=...,precommit=...)`。七个draw均为服务器在受理时固定的0..9999整数，保存为不可变tuple；与稳定受理ID绑定。普通相同线包再次受理是新命令；旧同ID重试不重新抽样或重新扣丹。通用旧用药入口明确拒绝31576。完成条件：实际同一受理命令只消费一颗，断线重登候选仍在，原宠物未被预览覆盖。
3. 原 `C0812` 查询、`C0811` 保存、`C0813` 清除均为一个正数BE32宠物实例key。查询调用同 Adapter，无draw/expected token，返回当前 `S0810` 或空逻辑消息；未确认原版无候选错误消息，当前明确设计为空回复，需实机核验。保存/清除的 Owner 必须在受理时固定当前候选的candidate_id作为 `expected_candidate`，同命令重试保留该值；线包本身没有这个token。清除受理时确无候选可固定None，形成“期望无候选”的无操作凭据，不能据此清掉后来候选。完成条件：旧保存/清除、旧预览已付重试均不能覆盖/清除/复活新的候选。
4. precommit沿用现有同步 `(db,inventory,frozen_snapshot,*,replayed)`，在同一事务同步当前唯一人物resource source；fresh=False、paid=True。随后在提交前完成当前宠物/背包/候选编码，限时技能需当前服务器毫秒。只向目标连接投递返回的逻辑消息。完成条件：扣丹、候选、宠物、悟性、年糕、领域凭据及root source任一点失败，全部回滚；paid不修补后来的pending source。
5. 共享入口由原始集成窗口修改，本文未改变 game_runtime/runtime_storage/serve/gateway/accounts，也未重启服务。完成条件：原客户端生成→切宠查询→保存/放弃→重登可玩，并核实空候选/关闭窗口显示和费用时点。SQLite临时验收不代表商业容量。

## 调用方事务 Interface

已有调用方事务可以直接使用：

- `inv.super_return(db,pet_id,epoch,request_id,'preview',item_key=key,draws=tuple7)`。
- `inv.super_return_candidate(db,pet_id,epoch)`：只读当前候选或None；外来/已释放宠物拒绝。
- `inv.super_return(db,pet_id,epoch,request_id,'save'|'clear',expected_candidate=admitted_id)`。
- `inv.initialize_pet_cakes(db,pet_id,count,added_aptitudes)`：可信完整一次导入，当前BASE已经包含历史增益；不会再加一次。普通客户端请求没有导入权限。

所有低层入口必须在角色所属有效epoch事务中调用，外层负责source/回复/提交。返回冻结ReturnReceipt仅为历史确认，`replayed=True`时不能据其candidate回写当前状态或发旧预览；原生Adapter已查询当前候选。历史已释放宠物回复当前移除/背包，不复活宠物。候选按宠物key独立保存，与原UI的map一致。每个当前宠物只有一个候选，替换仍需新丹。

## 状态与数值决定

单一政策为 design/pet-super-return-v1.json 和 pet-cake-v1.json。

- 原五项资质范围和成长档原整数来自cpetattr；kind2、野生1禁用由原代码核验。完整资格尚非原服证实，恢复设计接受当前非参战、kind1/3宝宝2且已知完整恢复字段的实例。
- 原抽样概率/悟性范围未知，设计七个独立固定draw；五资质闭区间等桶、成长档等桶，原悟性整数0..100等桶。不是原服概率。只有新鲜请求需要draw，已付可None严格只读；提供不一致draw拒绝。
- 扣丹时点设计为生成/替换候选时扣1，保存/清除不扣、清除不退款。原资料只证明预览后确认保存，并未证明支付时点。
- Profile.aptitudes是唯一当前BASE（含已实际应用年糕）；年糕added_aptitudes仅记录历史，不重复叠加、不从当前BASE机械相减。保存整组替换为新BASE后清count/history，因此确实去掉旧年糕影响。毒药减少BASE不要求篡改历史年糕审计。
- 保存仅替换新BASE、成长、悟性、年糕；保留当前等级/XP/加点、血脉、颜色、技能/保护/到期/进度、忠诚/寿命、名字/绑定。保持当前绝对HP/MP、裁剪超新上限，死亡0不复活，属于明确恢复设计。
- 候选捕获原BASE/traits/cake/blood/颜色来源；这些变化则保存拒绝。之后的经验、加点、伤势、技能或忠诚/寿命变化可以保留，并从当前状态重算，避免预览伤势回档。参战中的保存拒绝。预览冻结新BASE及血脉投影后的展示资质/score；展示资质与保存后的Pet刷新一致，该投影组合为designed。

## 原生证据

`research_pet_score.py`先重读原config.pfs的cpetgradecfg17/cpetattr158/cpetbloodconfig16，重新校验CRC/解码并逐行attributes/lists与catalog全等，记录原条目SHA；随后直接执行完整原1133e80及原普通血脉扫描11297d0、种类加分、空宠物装备helper及原float转整数，158模板×2=316例与当前支持wire纯计算一致。每次乘积/累加float32、悟性1160系数3、技能ID尾数1/2/3计数、当前普通进化0仍有(0+1)×25，均保留原行为。当前只涵盖已恢复的普通wire字段；进化/化境/额外装备score仍需扩展，不能据316例称所有评分完成。

`research_pet_cake.py`执行原Pet编解码、原1135390..11353b4把bean+111/raw refresh+119 signed byte写attr1540，以及原11378d9..11378f3的总20次门禁。空名字默认wire164即base tail155；pet_record在展开技能列表/到期map前写该byte。0/1/19/20四例全过，真实有名字/技能宠物的20和清0也通过原消费者。31268..31272各资质年糕的增益/概率尚未恢复，cpetcake字段本身不能冒充公式，来源见PET_CAKE_SOURCE_RESEARCH。

`research_pet_rebirth.py`执行原工厂/codec、原9参数投递和实际查询/保存/清除发送段：S0810九BE32为key、五资质、悟性、成长raw、score。元数据布局证据与当前服务端业务是不同验收。

## 本批方法、验证与未验

tdd在已有授权Inventory调用方事务/原生Adapter Seam做垂直切片：缺少super_return入口红→预览/单扣绿；未实现保存红→保存/清除绿；已有血脉的候选展示与实际保存不一致红→冻结有效展示资质绿。真实临时数据库、公开当前快照、原客户端codec是验证面；随机/时钟由可信调用方注入，故障使用真实SQL触发器和外层提交/编码失败。

codebase-design将随机、候选生命周期、BASE/年糕/悟性保存和幂等集中在pet_super_return Module，外部仅需小Interface、冻结命令上下文及既有precommit。writing-for-agents将集成步骤、完成条件和数值来源集中本文，首页只留触发指针。

verify_pet_super_return覆盖生成/查询/保存/清除、替换与paid乱序、每宠独立、年糕20→0、原生消费者、五个真实保存故障点、晚期编码/外层source失败、只读历史/无热I/O、未知旧档/野生/draw拒绝、opaque及过期epoch。verify_inventory_resource_hook加入实际root source的preview/save/clear False/True、CAS后保存失败回滚、血脉后展示一致且人物70/40/version0不变。其余回归与内容哈希见pet-super-return-batch.json。

尚未验：共享生产路由、实际服务发布、原生GUI；普通还童重置、年糕实际服用、进化/化境/宠装完整评分及全量剩余装备道具。目标持续推进，不以本批事务验收作为整体完成。
