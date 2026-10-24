# 宠物灵石与驱灵散接线

2026-10-24。70052服用与70053清除的所属领域、保存、原生初始化/独立刷新及交叉来源已实现。70053通过实际RC4/MPPC→RoleOwner→共同凭据/唯一资源source的临时库验收；70052仍待共享入口固定随机受理接线。没有发布、操作在线角色或执行原客户端GUI；全量目标active。

## 集成步骤与完成条件

1. 启动使用Inventory.prepare：GrowthRules内冻结StoneRules，建inventory_pet_stones及inventory_pet_stone_receipts和(role,pet,item)审计索引。网络热路径不读配置或建表。PetProgress末尾新增stones；已知PetStones(version,count,added_aptitudes,policy)不可变，count0..5、五项非负、总和严格50×count。
2. 70052的原CUseItem为`>iiQ`：物品实例key、目标种类1、正signed32范围宠物key。受理时由可信Owner固定50个0..9999整数，连同稳定request_id、epoch、deadline保存为不可变命令；重试使用原批次。原线包没有随机数或五项分配。调用`receive_pet_consumable(body,epoch,request_id,now_ms=None,precommit=None,draw=None,stone_draws=tuple50)`；最后参数为新增可位置参数，原draw仍只归中毒食品。新服用缺draws明确拒绝，已付可None读原凭据；传入不同draws拒绝。
3. 已在调用方事务内时，使用`use_pet_stone(db,item_key,pet_key,epoch,request_id,draws=None,expected_version=None)`；有效角色租约、物品/宠物归属、已知完整来源、成长版本、灵石源JSON与版本、精确扣一颗、库存版本及领域凭据一起写入，内部不提交、不发包。调用方继续使用现有同步precommit，把root source/共同凭据与当前逻辑消息编码纳入同事务；失败整笔回滚。付后Interface返回历史StoneReceipt，通知必须另读当前PetState。
4. 70053不需要随机数。显式Adapter同上，或实际共享`Inventory.receive(USE_ITEM,body,precommit)`既有路径；后者必须有真正受理命令precommit。其内部`stone-current:pet:growth_version:item`只作本次资产事实键，实际root受理ID仍由既有共同凭据去重；新相同线包是新操作，当前count0返回150483且不扣物。未修改runtime_storage/game_runtime/gateway/accounts/serve。
5. 原宠物页允许明确选择的自己宠物，背包默认使用当时参战宠；确认上下文固定最终key。本模块不增加“仅参战”或“禁止选中宠物”的资格限制。Owner负责受理时非战斗、其他独占状态及连接/场景世代。模块持有效role_id+epoch执行，无全局锁或全服串行器。
6. 70052的共享接线完成条件：实际受理入口持久/冻结上述50draws，原生加密请求通过同一个当前source/共同凭据事务、故障/旧租约/重登验收；不能把本批受信seed测试算作该链路已通。通用legacy use-item仍明确拒绝随机70052，避免重试时重新抽样。

## 原版依据与集中设计

单一政策为`design/pet-stones-v1.json`。原物品/消息、确认回调、成长来源及查找范围见[PET_EVOLUTION_STONE_SOURCE_RESEARCH](PET_EVOLUTION_STONE_SOURCE_RESEARCH.md)、[PET_STONE_USE_SOURCE_RESEARCH](PET_STONE_USE_SOURCE_RESEARCH.md)；原Map/独立消息实际执行见`pet-stones-native.json`和`research_pet_stones_native.py`。这些原事实为client_verified：每颗成长+5、五资质随机总计+50、最多5；清除全部灵石效果；原目标/请求字段与成功/拒绝消息。

以下集中标designed：原服务器分配公式未知，恢复使用50次独立均匀维度抽取，每个draw按floor(draw×5/10000)分配1点；不会从客户端接受方案或在数据库重试内新抽。普通与超级还童保留灵石次数/五维及其来源版本，重新抽自然成长时加保留5×count一次；原UI来源分解不冒称原服保留规则。资源保持绝对HP/MP，降上限时裁剪，死亡0保持0；派生属性仍使用已有pet-growth和blood设计。

BASE资质保存年糕及中毒的永久变化，先走既有blood有理数规则，再叠独立灵石附加资质。年糕原预测先从最终值减灵石，再剥离血脉，现已传入真实附加五项；清除不会删后来年糕/中毒或重算它们的历史。Profile.growth_raw为唯一当前总成长，已经包含进化与5×count；读档、评分和线包不再加一次。清除仅减当时5×count。普通/超级重抽自然成长则明确重组天然+保留进化+保留灵石；超级候选baseline含完整灵石版本，add/clear回到同物理值也不能保存旧候选。

评分与神兽形象结论见[PET_STONE_SCORE_SHAPE_RESEARCH](PET_STONE_SCORE_SHAPE_RESEARCH.md)：完整原1133e80执行11,376例，既有公式直接消费最终资质/成长，没有独立石头评分项。完整1138370→kind2形象链1,278次，同自然成长时当前成长+5count与1930相消，保持分支/形象。诊断stage/成长输入不授权这些神兽的进化资格；气质1760和宠装仍未恢复。

## 原生状态与历史处理

初始Pet bean最后+134为map<int,float32>，已知状态显式发送1930次数、1940/1950/1960/1970/1980附加五维，包括六项零。pet::SRefreshPetData `c07d5`不会把此map更新到既存内部灵石属性；因此服用/清除再发送独立**attr::SRefreshPetData `c32c9`**：BE32 column1、BE32 pet key、compact float map。原完整113daa0循环绝对赋值；清除必须发零覆盖旧值。当前paid及带时间查询同样刷新已知map；不对未知None伪造来源。

原SSendMsgNotify `c1775`：150454成功需五个本颗增加值参数（成长+5在原文本）；150456清除成功空参数；150453上限/150483空清除均空参数。历史重试不再次提示成功。先编码当前基本Pet、背包、独立灵石属性和提示，再提交。已付当前回复通过审计索引识别原已删物品并用可信Unix-ms时钟同步限时技能，绝不把root旧monotonic值当Unix时间。

新恢复宠物明确初始化0。旧缺行仍None，读档/热路径不会补；新的灵石、年糕、还童和进化需要完整已知灵石来源。可信完整导入使用`initialize_pet_stones(db,pet,count,added_aptitudes)`一次；调用方须已经证明Profile为BASE资质且成长已含该灵石效果。此方法不补成长/历史奖励，验证已有血脉和有效资源；不能通过当前成长猜次数。旧2/3段成长历史仍可只读，新4段尾部保存完整带policy的灵石状态，不把旧历史补成0。

新增stones或显式导入会改变冻结资产source。旧已确认root source须由迁移/集成在可信事务核对，paid读档不能自动修复pending，也不能把新字段假设为已知。发布应基于最终完整哈希快照，工作区中途文件不等于完成批次。

## 验证与方法记录

- `verify_pet_stones`：独立原Pet初始化及c32c9循环、单扣/成长5/总资质50、年糕/血脉/中毒/进化及普通/超级叠加、清除保留其他来源、50边界draws、5上限/空拒绝、超级候选版本失效、死亡0/耗损MP；五个真实保存点与晚期基本包/属性包/提示、source回调故障全回滚，同失败ID重试一次；历史已删物品/后续状态/SQL只读/no hot IO、非法draws/旧版本/epoch、未知拒绝/一次导入/重开/已放生不复活。
- `verify_pet_stones_runtime`：真正RC4/MPPC驱灵散请求、Owner→共同/source事务、原零属性/成长/150456、Unix时钟与原限时技能；共同凭据和晚期属性/提示失败回滚；只读paid、空150483、重登、旧Owner、放生后paid。70052仅可信调用方事务seed，未伪称真实随机共享链。
- 成长原生旧测试现在分别核对独立原scalar序列化和实际原非空map读取；不再把新增已知来源错误要求成空map。普通/超级、年糕及加密Owner、进化及加密Owner、血脉/中毒、战斗养护/神兽、经验/潜能/技能/到期、背包当前paid/source/snapshot、NPC养护、任务宠物经验回归见`pet-stones-batch.json`。

tdd在既有Inventory公开事务/原生Seam先得到缺stones红，逐条修复服用清除、年糕漏来源、还童丢成长、共享清除缺分流；每片红后实现再扩展。codebase-design把状态和叠加集中于pet_stones/GrowthRules→pet_growth_store，调用方传现有成长规则即可，避免每个资源消费者另写算式；受理随机性与事务模块分离。research后台独立执行原评分/神兽形象，父执行原map/消息；writing-for-agents把受理/完成条件和旧档约束放在本交单，索引仅保指针。

未验证：70052共享固定随机受理，实际原客户端确认/显示/重登GUI，正式发布，完整神兽进化/蜕变/气质/宠装/高级数值与正式战斗，商业数据库/容量。完整系统仍持续恢复。
