# 神兽永生分类、养护免损与战斗门槛

后续已继续提供PET_BATTLE_CARE_SETTLEMENT.md及完整普通养护结算Interface，含神兽免损、计数、等级/擂台例外及真实source同事务。本文末“下一批普通计数待实现”为较早阶段记录；实际宠物战斗接线与GUI仍未完成。

2026-10-23。本批已完成所属领域及离线原指令验证；没有修改共享入口、重启服务、操作真实角色或执行战斗。全量恢复目标继续active。原包/官方来源详见PET_IMMORTALITY_SOURCE_RESEARCH.md；原生可重跑证据见research_pet_kind.py及pet-kind-native.json。

## 原版证据与补全分开

原cpetattr158行全部life6000，不能用寿命数值判断永生。后台研究重新读取原PFS六表并全量核对attributes/lists，CRC/SHA及官方PC冲突已存来源报告。本窗口另执行原kind读取a72fbe..a72ffa，确认CPetAttr.kind落record+44；执行完整1129900与原89e280/root+b60、884e60表分派，158行严格kind==2为真，缺行返回假。

原显示分支1404931比较record+44==2，只有2进入CStringRes2676“永生”；kind1/3均去1404aaf普通分支。该分支不读寿命哨兵，所以服务器仍编码真实非负PetCare整数，无需伪造-1或把存档重置6000。另执行143db26..143dc5f：kind2或pet+29==1进入原消息146589“神兽类宠物或野生宠物不能进行超级还童操作”；只证明此拒绝分支，不代表普通还童或超级还童完整资格已恢复。

原bookanswer36002/36003/36035直接说明神兽忠诚、寿命永不减少。分类和免损均标client_verified；“永生宠不受最低50寿命限制”作为inferred，仍要求已知合法care及忠诚>0。不因永生自动修复低忠诚/寿命、治疗或忽略HP、等级、选择、技能与战斗归属。

kind2原9模板为500069/70/71/72、500101、500123/124/125/126。kind3原17模板保留独立分类；现定向原包、原显示分支和官方PC调查不能证实其服务端免损，继续普通规则明确标designed，单一政策pet-kind-care-v1.json。kind1“囧囧有神兽”及部分“·仙”名字保持普通，不按名字或模型归类。若新证据要求kind3免损，应显式升级政策和回执读取，不改原kind。

没有新增永生宠食品禁令，也未推导免疫中毒资质损失。四种寿命食品沿用已核验的现行行为；未知原规则不借本批免损偷偷改成拒绝消费。

## 给角色和战斗集成方的Interface

启动Inventory.prepare加载CareRules中的只读template_kinds、immortal_kinds与kind_revision，不在角色热路径读文件。新增`CareRules.has_immortal_care(template_id)`严格接受原已知int模板；`battle_care_ready(care,template_id)`为只读、含分类的养护门槛。它不会代替HP、等级、技能/期限、选择或战斗所有权校验。旧ordinary_battle_care_ready只供已确认普通规则的调用方，不用它判断神兽。

角色Owner在现有同一fenced事务调用`Inventory.change_pet_care(db,pet_id,settlement_id,expected_version,'defeat',1)`，签名不变。pet_care从当前所属、未放生的行读取真实template_id，不接受外部kind/永生bool。可信普通战斗死亡才可调用，不从客户端HP变零猜死亡。低层Interface依赖调用方当前租约事务；生产采用LeasedAccounts/FencedConnection，不能拿任意裸连接替代租约权限。

kind2免损返回原PetCare，不更新care或inventory_revision，但同事务保存结算凭据，以便重试与payload冲突判断。普通/kind3保留原20忠诚、50寿命减损及floor0。旧未知care仍须显式权威导入；本批不会初始化它。pure CareRules.apply的defeat现在要求关键字template_id，防止脱离身份计算；角色结算方应直接使用上述Inventory Interface。

care持久revision仍是pet-care.1，因现有数值和存档结构未迁移。新增care receipt format2保存kind_policy/template_id/kind和历史care；旧flat PetCare回执继续可读，绝不重算或补回旧错误扣损。已付回执返回历史ack，当前消息必须另读当前PetState；不能把ack序列化成当前刷新。kind政策不兼容时拒绝并要求显式核对，不自动重解释。

无实际变化不推进资产source。角色通用结算仍须按已有约定在同事务校验/同步当前根source，再编码当前消息；本批未另建人物资源载体或提交连接。现有寿命食品、技能、血脉、NPC恢复Interface与同事务precommit不变。

## 验证与未验范围

先在现有Inventory事务/冻结快照Seam复现神兽死亡错误扣损，再最小实现转绿。verify_pet_immortality覆盖9种kind2的低值37/12保留且无版本/source churn，158种分类在寿命0/1/49/50的care gate，名字陷阱与kind3普通17/0；未知/bool拒绝；旧flat回执；后来喂至42/12后的SQL只读历史重放；原Pet decoder保留42/12；凭据保存失败、外层回滚、同键恢复、冲突版本/payload、真实opaque租约替换/旧Owner拒绝和重开。

verify_pet_care、verify_pet_battle_care、verify_pet_lifetime_items、verify_pet_quality_lifetime、verify_pet_toxic_lifetime、verify_inventory_resource_hook、verify_resource_npc_care_runtime(all)、verify_pet_blood_items均复跑绿。根source真实同事务、食品回滚及加密NPC普通链路仍兼容。原native分类/显示/超级还童门禁158行绿，使用离线镜像与明确XML/CRT/表lookup终端，不是启动原客户端。

实际方法：research逐条追原包与官方PC；tdd沿已授权并持续使用的Inventory事务/快照Seam先红后绿；codebase-design将kind资格与扣损放在CareRules/pet_care隐藏，调用方不复制分类；diagnosing-bugs用确定的真实结算失败→绿闭环；文档按现有交接约定写出来源、签名和不可推断范围。

未验证/未接入：神兽及仙兽实际战斗加入/每场扣1/每3场忠诚计数、等级≤30忠诚豁免、完整战斗结算与低忠诚不服从、还童及进阶、现场UI、部署和容量。原生永生显示分支成立，不把离线原分支当现场已经显示。下一批继续普通战斗养护计数/可信结算契约，并推进还童、剩余装备道具及跨模块可玩链路。
