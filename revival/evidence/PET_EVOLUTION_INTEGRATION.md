# 普通进化、稀疏终阶与追加成长

进化与灵石交叉前读[PET_STONES_INTEGRATION](PET_STONES_INTEGRATION.md)：进化要求已知石头来源且保留其效果，清除只减石头成长；原评分/神兽形象另经独立执行核验。

2026-10-24。已恢复kind1/3已知普通宝宝的进化阶段、原生表示、材料事务、还童保留、实际共享及加密Owner路径。未发布/GUI，神兽蜕变、气质、灵石及宠装继续恢复，全量目标active。来源调查PET_EVOLUTION_STONE_SOURCE_RESEARCH.md，原程序执行pet-evolution-native.json；资料存在不代表所有特殊分支已恢复。

## 接线与完成条件

1. Inventory.prepare启动冻结EvolutionRules并建inventory_pet_evolution/receipts；PetState末尾追加evolution，冻结PetEvolution(version,stage)。新恢复宠物明确stage0；旧缺行仍None。可信调用方在有效租约事务可initialize_pet_evolution(db,pet,stage)一次导入，当前Profile须已包含该已知进化效果，不会再加成长。必须确认是本批支持的完整普通来源；不能从当前growth/外形反推阶段。
2. 原CReqPetEvolve 0xc07fc仅一个正signed BE32宠物key。原1402030确认回调由普通丹、神兽画皮及追加成长共同使用；本批只开放kind1/3普通宝宝。进化丹outbattleuse0，未为CUseItem新增第二条扣丹路径。
3. Inventory导出的INVENTORY_TYPES及INVENTORY_CURRENT_MUTATION_TYPES加入原type，实际RoleOwner和runtime_storage沿既有分流自动使用；共享文件未改。generic receive要求真实accepted-command precommit，内部evolution-current:pet:成长写前version只标识资产事实，外层稳定受理ID继续去重。新受理相同线包执行下一次，已付受理回当前。wire没有所确认阶段/版本，不能从字节区分同pet迟到旧确认与新确认；可信调用方可额外冻结expected_version，本批不虚构客户端阶段字段。
4. 既有事务用inv.evolve_pet(db,pet,epoch,request_id,expected_version=None)；独立原生Adapter为receive_pet_evolution(body,epoch,request_id,*,expected_version=None,now_ms=None,precommit=None)。有效租约、阶段/成长/完整metadata、材料、成长与阶段CAS、资产版本、领域/共同receipt及root source保持同一事务。receipt是历史事实，paid不应用其中历史结果。
5. fresh/paid回复是当前原生Pet刷新、当前包与原Unix毫秒；已放生paid发原双BE32移除，时限技能deadline保持。fresh普通进化发送原143571(当前宠物名,原阶名)，追加成长发送148963无参数；原SSendMsgNotify decode→remarshal已通过，paid不重发成功提示。提交前任意刷新/提示编码失败完整回滚，连接所有者提交后发送逻辑消息。原GUI实际提示/动画仍待验。

## 已证的原规则

158模板的原cpetevolution与cpetattr、50行cpetfinal及CString直接重读PFS、CRC/解码/全行相等，指纹在原生artifact。出生raw0对应显示一阶，普通变化每次成长+5；达当前模板cap后，每次成长+1，最多追加50次。

原1130640形象上限与1130b20 UI上限实际执行一致：末needlevel=-1时取首个-1前下标，否则取6；后者158模板各执行raw0/cap/cap+1。totalShape不是最大下标。普通1138370执行1,043组输入，选shape[min(raw,cap)]；kind2另有成长/灵石/蜕变分支，未替换为普通形象逻辑。

原14063bc..1406591执行487组可用前阶的下一阶/等级检查/丹种/数量：先raw+1，若needlevel[next]≤0直接next6；next≤2用31227，3..5用31228，6用31229，数量保留原needitemnum。等级使用宠物当前490。500050实际路径0→1→2→6，消耗20/28初级丹、1终极丹，总成长+15；不补不存在的3/4/5阶段。

若stage≥cap，原UI静态数据流按stage−cap+1查cpetfinal；第1行高级8/终极1，第50行195/8。成长+1来自原确认/成功文本。本批实际事务逐一通过50行再拒绝超限，未将它们误作新造型。小灰狗cap1：第一进化扣初级2、成长1006→1011；下一次高级8+终极1，raw1→2、成长1011→1012，造型仍二阶。

原Pet bean+110的signed byte经SRefresh+118写1440，与相邻年糕+111/1540独立。6组原存储及3组原确认构造/工厂/编解码通过；1,043组原113a6bc..113a6e3阶名选择读CString2485+min(raw,cap)，一阶至终阶按原字符串发送。评分当前增加(raw stage+1)×原系数，474组完整1133e80执行（158模板×raw0/2/56）与纯投影一致；这是表示/算式验证，不授权每模板任意阶段。

## 明确的设计选择及旧档处理

policy为design/pet-evolution-v1.json。原表/原消费者事实标client_verified；确定性成功、材料binding1优先再实例key排序、完整普通宝宝/非选中参战门禁、保留绝对HP/MP及死亡、派生属性采用既有designed成长模型均为本地设计。当前源码将新增type纳入RoleOwner既有战斗门禁，实际战斗另验；其他未恢复统御/展出/备用/蜕变权威不能由此称完成。

当前Profile是总成长的唯一可变权威，已经包含进化；读档不加第二遍。EvolutionRules.bonus只为替换天然成长时计算保留量：普通实际开放进化每次+5，post-cap每次+1。普通/超级重新抽天然成长后保留该增量及阶段，不重发潜能；超级候选baseline包含阶段来源，旧BASE/阶段改变后保存拒绝。候选旧格式可能需清除并重生，不能把旧baseline改写成当前已确认来源。

旧资源source包含冻结资产。新增evolution字段或明确导入改变资产描述时，旧已确认source不能自动修复；集成/迁移须在可信事务同步来源。已付重试保持strict readonly，不为后来pending source补初始化。部署前须核对旧档/新字段来源，当前运行服未热加载这些改动。

## 验证

- verify_pet_evolution：首次/双丹/绑定优先/稀疏/全部50追加、普通及超级保留成长；当前原生stage、绝对资源与metadata、SQL只读paid、四真实写入点及晚期编码失败回滚、同失败ID可重试；未知旧stage拒绝/显式一次导入、已放生历史不复活。
- verify_pet_evolution_runtime：真实RC4/MPPC→Owner→实际共同/领域/source事务→原stage刷新；相同新线包继续进化、旧ID SQL只读当前与时限技能Unix时钟；实际共同receipt及晚期时钟失败回滚；重登、旧Owner拒绝、已放生paid；人物HP10/MP20/version0保持。
- 普通/超级还童、年糕所属及真实加密Owner、实际root source hook、共同当前回复、事务快照、NPC养护和任务宠物经验回归均通过，具体文件/hash查pet-evolution-batch.json。

方法：TDD先在既有Inventory事务Seam得到缺失evolve_pet红，再实现首次增长；保留进化的还童测试实际失败后修正替换计划，扩展稀疏/50行/故障/真实Owner纵切。research子任务给11表原包、官方PC及确认链静态证据，父执行原程序作独立预期；codebase-design把阶段/材料/成长计划隐藏于同事务Module，root资源仍单一权威；writing-for-agents将接线与验收集中本文。

未验：神兽画皮/蜕变/气质与灵石、统御/备用/宠装高级权威；原服务器成功概率/全部状态资格/平衡；正式发布与原GUI实际提示/动画/变形/重登；商业数据库与容量。本批只完成上述普通切片，不等于全量系统验收。
