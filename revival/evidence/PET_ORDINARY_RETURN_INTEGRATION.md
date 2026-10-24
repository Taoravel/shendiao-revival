# 普通还童完整重置交单

还童与灵石交叉前读[PET_STONES_INTEGRATION](PET_STONES_INTEGRATION.md)：当前普通还童要求已知灵石源，并在新天然成长中保留其5×count一次及独立五维。

进化最新：普通kind1/3宝宝阶段、稀疏跳终阶、50次追加成长及材料/成长同事务、原生刷新与真实加密Owner共享链路已通过；普通/超级还童现保留已知进化成长。接线、原/设计边界、旧档来源及未验范围见PET_EVOLUTION_INTEGRATION.md。神兽蜕变/灵石/宠装、发布与原GUI提示/动画继续恢复，全量active。

年糕最新：五种实际服用、原预测37,920例、总20次、同事务/原生提示及真实加密Owner共享链路已通过；旧四字段审计升级、耗尽重试、故障回滚和重登已验。接线、浮点差异与设计边界见PET_CAKE_CONSUMABLES_INTEGRATION.md。未发布/GUI，进化、灵石、宠装及剩余装备道具继续恢复，全量active。

2026-10-23。31002/31087的所属领域、持久化及原生Adapter已实现并离线验证；共享请求分流、服务发布和真实客户端仍待集成。全量目标 active。超级候选/保存另见PET_SUPER_RETURN_INTEGRATION；普通没有复制超级预览阶段。

## 接线步骤与完成条件

1. 现有Inventory.prepare新增冻结ordinary_return_rules并启动创建inventory_pet_ordinary_return_receipts。新规则读取原模板参战等级、寿命/候选技能和13种仙兽必带来源；业务热路径不读配置或建表。完成条件：准备完成后可以使用注入配置处理命令，无角色热路径全表解析。
2. Owner将可信携带实例31002/31087的原CUseItem `>iiQ(key,1,pet_key)` 分流给 `inv.receive_ordinary_return(body,epoch,request_id,draws,now_ms=None,precommit=None,expected_version=None)`。服务器受理时固定15个0..9999整数为tuple，与稳定request_id一起保留重试；客户端不提供随机数。同一线包新的独立受理要新ID，已提交重试可draws=None。完成条件：完整重置及一颗正确丹只发生一次；普通低层用药旧入口明确拒绝这两丹。
3. 可信调用方已有角色事务时调用 `inv.ordinary_return(db,pet_id,item_key,epoch,request_id,draws=None,expected_version=None)`。所有写入加入同db/租约事务；返回OrdinaryReceipt是历史确认，不是当前宠物快照。可选expected_version用于受理时已冻结成长版本，重试保留原值。完成条件：所有子状态、扣丹、领域凭据与外层奖励/人物resource source成功或失败一致；不另开连接提交。
4. 同原生Adapter传既有同步precommit `(db,inventory,current_frozen_assets,*,replayed)`：调用实际root唯一resource source同步，fresh=False、paid=True，随后提交前完成当前Pet、背包、技能拓格进度编码；当前仍有限时技能的paid回复须服务器毫秒。只向目标连接排队逻辑消息。完成条件：真实source CAS后或任意编码失败，宠物/丹/候选/凭据/source全部回滚；paid不修复后来pending来源、不治疗/回滚后来宠物状态。
5. 集成窗口修改共享入口并发布后，原客户端验收普通/高级丹、野生/宝宝、仙兽必带、重登以及费用/技能显示。当前只恢复普通wire中已有状态：进化0，统御/备用出战/宠物装备的持久权威尚未恢复；这些字段接入时必须扩展资格与保留计划。完成条件：Owner使用真实战斗/统御/备用状态门禁，完整高级形态不会被普通逻辑静默覆盖。本文未改shared或重启/操作真实角色；当前离线绿不代表此项已完。

## 原门槛与原请求

`research_pet_ordinary_return.py`执行原142ac8f..142acab：CPetAttr+48(uselevel)>=95更新原dialog+fc。随后执行原1094897..10948b9，实际计算31002+flag×85选31002/31087。158模板×原UI旧flag0/1共316例全过，证实按模板参战等级，不按当前自然等级或人物等级。原142ac71取的是所选宠物template对应CPetAttr，不是attr490当前等级。

实际14293c6..14293db调用原10729f0构造CUseItem(key,1,u64pet)，再用原d98770工厂/e4d740编码/d987a0解码，3组正数/最大signed32实例用例全过。普通确认入口142a620可见当前出战190/194、其他状态1130850以及pet+a0/+a4非零相关拒绝，本文的316例不冒充已执行完整UI或还原这些所有权。

来源矩阵沿用PET_REBIRTH_SOURCE_RESEARCH；补查PET_ORDINARY_RETURN_METADATA_RESEARCH新增原NPC表5531/技能表114的全行CRC/解码比对和13仙兽必带。原说明“还童时固定/必带技能”是client_verified；物种与template整数关联由特有技能/名字联查，标inferred。不将2025后来合成规则移植进本地1.6.1。

## 重置、保留及设计来源

单一政策：design/pet-ordinary-return-v1.json；七个基础属性draw复用pet-super-return-v1明确设计，原范围仍用cpetattr。来源与实现独立记录。

| 状态 | 当前行为 | 来源边界 |
|---|---|---|
| 自然等级/五维/加点/经验 | level0、XP0、已分配0，按新Profile和当前血脉重建初始五维/潜能 | 回0级、属性点重置client_verified；XP0和当前成长初值designed |
| 五基础资质/成长/悟性 | 原范围内重新抽取；成长保原整数，悟性0..100 | 原五项范围/成长档client_verified；分布、独立性、悟性范围designed |
| 宝宝颜色/血脉 | 原grade、power、level、上限不改；原血脉奖励潜能回到未分配池一次，不再额外发历史奖励 | 保颜色/血脉client_verified；当前potential/分配投影designed |
| 野生身份/颜色/血脉 | origin1→2；抽新grade1..6；power0/移除历史血脉潜能 | 转宝宝、重抽颜色/重置血脉client_verified；六色权重与power具体值designed |
| 技能列表 | 从原候选重新生成，旧礼包/秘籍技能无额外保护；13种仙兽必带原专属技能 | 重置技能及13物种必带文字client_verified；数量/抽样designed |
| 忠诚/寿命 | 忠诚到新grade原maxloy，life=原模板life | 重生成client_verified；选满忠诚/固定模板life为designed |
| HP/MP | 普通重生重新获得满的新资源，原死亡也如此 | 原治疗/复活行为未知，明确designed；超级仅三项仍保绝对值/死亡0，两者不同政策 |
| 标志、绑定、名字、template/ID/归属 | 完整原flag byte和版本原样保留，不因petbangding0解绑；不删宠重建 | 保身份/opaque bit为designed；普通flag具体原规则unknown |
| 到期map/拓格进度 | 新生成永久技能，清旧到期map；points0；各自版本递增 | 普通附属规则unknown，designed。新抽同ID也不继承旧期限，paid不清后来限时技能 |
| 年糕/每三场养护余数 | BASE整组重抽；cake count/history0；mod3=0，版本递增 | 普通原年糕/余数规则unknown，designed；不引用超级清糕条款假称普通已证 |
| 超级待保存方案 | 原子清掉同宠候选，其他宠候选保留；历史凭据仍只读，不可复活旧候选 | 普通影响候选原细节unknown，designed |

15 draw顺序：0..4资质、5成长档、6悟性；7仅用于野生新颜色，权重白/绿/蓝/紫/橙/金为6000/2500/1000/400/90/10每万；8技能数量，在0..min(原候选数,当前色上限)中等桶，有已证必带者最少1；9..14不放回选其他技能。权重/抽样均为集中恢复设计，不是原服概率；宝宝忽略颜色draw仍保原色。没有把所有候选都自动发给结果。

普通kind2与全部kind3的服务端完整资格仍未知，原普通UI未查得超级那样的kind2比较。本政策明确designed允许当前已恢复的1/2/3已知完整形态；不把这项许可称原版事实，也不因超级提示虚构普通永久禁令。13种kind3则另有明确物种文字。化境、进化/统御/宠装不能据此称已恢复。

## 状态所有权与历史

Module pet_ordinary_return封装完整规划、每张表原值CAS、扣物、候选失效及单次凭据。先读冻结当前Pet/所有子状态与计数，全部规划合法后写入；各版本保持单调，旧未知任一必需子状态拒绝，初始化接口仍是可信一次导入，未作自动0填补。当前BASE继续唯一权威，清年糕不是再叠加/相减一遍历史增益。

已付回执在当前有效role lease下只读返回，不重新执行计划；历史Pet放生后仍能确认旧操作，原生回复当前移除/背包，不重建Pet。当前晚于还童的经验、伤势、技能、到期和拓格状态由当前快照决定。新的独立还童依然是新付费命令；expected_version冲突、错误丹、外来资产、错误目标、缺draw或过期epoch均先拒绝。

## 本批方法、验证及未验

tdd在已有授权Inventory调用方事务/当前快照/原生Adapter Seam逐片红绿：普通入口不存在→宝宝重生/血脉保留/单扣绿；原生Adapter不存在→真实CUseItem重置/当前消息绿，再覆盖野生与元数据。随机/时间由可信调用者注入，存储用真实临时SQLite；故障用实际SQL触发器，不mock自有事务协作者。codebase-design将复杂状态迁移集中Module，沿用既有precommit小Interface，无全局锁/队列或网络线程新增IO。research后台发现13仙兽文字，实际改变必带生成；writing-for-agents将集成步骤、完成条件、原数值和设计集中本文。

已过verify_pet_ordinary_return：宝宝保血脉/颜色、level/XP/加点重置、current level100仍普通丹、95模板level0需高级丹；野生带非零血脉/限时技能/进度/年糕/mod3→宝宝新颜色/全部重建，精确绑定/名字/ID保留；旧限时200091恰被重新抽为永久，原超时icon消费者也正确保留新技能，不沿用旧deadline；13仙兽实存必带；158模板×6grade×3draw=2844种纯生成合法性；12个真实写入点、晚期source/编码失败整体回滚；current原Pet/时钟/技能/进度消费者；只读历史/无热I/O、不清后来限时、鲜还童满资源设计与参战拒绝；外来/未知/错误上下文/opaque/reopen/放生历史。

verify_inventory_resource_hook在实际root source上新增普通完整重置后CAS失败全回滚、同键再成功、SQL禁止写入的paid True，人物HP70/MP40/resource version0保留。超级、技能、到期、血脉、养护、快照、当前消息、实际加密NPC修理/治疗all及任务宠物经验均回归通过，内容哈希与清单见pet-ordinary-return-batch.json。

未验：生产共享分流/稳定draw受理、正式发布/原客户端普通确认和重登；统御/备用/进化/化境/宠装高级状态；原服抽样和未知metadata规则；年糕实际服用与其余装备/道具全量缺口；商业数据库/容量。原有绿测试不能替代这些完整可玩要求，目标继续 active。
