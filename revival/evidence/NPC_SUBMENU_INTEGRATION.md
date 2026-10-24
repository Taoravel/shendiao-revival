# 原生NPC子菜单与实际服务授权

2026-10-23，NPC窗口，开发工作区增量。本批未重启或发布，未改shared入口、人物数值及common policy。实际运行版本以runtime/deployment.json与evidence/latest-deployment-verification.json为准；工作区增量不随运行服自动生效。

## 需求与Interface

为已实现服务恢复原客户端childservice菜单层级。展示组不能新增实际行为权限；每个可执行叶节点必须保留该NPC原有明确ServiceBinding，动作继续经当前地图证明、角色租约及领域事务。任务vector原样保留；父菜单与本地返回不作为服务器命令；不激活未知业务。

`load_services(bindings,path=...,*,menu_groups=((npc_id,root_service_id),...))`在启动解析原childservice，NpcServices按相同keyword-only Interface接受预加载child_services/menu_groups。显示树完整展开后验证每个真实叶节点具有同NPC绑定；重复组、重叠行动叶、循环、未知子项或越界遍历均在启动拒绝。显示根不进入bindings；plan仍只按原明确叶节点授权。未启用原目录的断边不影响其它已实现服务，也不会获得权限。

本批仅将现有政策已明确的训练师10086/10493的10/11/12，用原295（children10,11,12,10001）作为展示根。NPC和恢复权限仍来自原有design/npc-services-v1.json#recovery；NPC→295的展示关联是本地重建设计，不冒称原服NPC服务列表已找到。其原父子关系和本地展开行为属于client_verified；没有新增费用、恢复数值或NPC领域行为。其它NPC保持原菜单。

原10001是本地返回根菜单，与关闭窗口不同；icon6本身不被解释为通用服务器权限。图中的原缺失child10011只在有人明确启用包含它的展示树时拒绝，不能按相似编号改为NPC10011或别的服务。

## 原始依据与验证

原5531条服务、699个非空childservice及2519条边来自config.pfs对应表，图无环；唯一缺失边为1277→10011，无重复直接边。已独立复跑[NPC_SUBMENU_NATIVE_RESEARCH.md](NPC_SUBMENU_NATIVE_RESEARCH.md)的原指令探针，30项通过：295本地展开、10001回根、10002/10003固定缓存层1/2、10004原虚方法调用、170纯说明全文及10/11/12实际构造提交CRecovery kinds2/3/4与负例。10004未验证可见关闭效果。该研究实际执行原菜单分支，不以Python模拟或仅codec通过代替业务证据。原层级缓存不是任意深度UI承诺，本批只启用一层295。

已跑红→绿：verify_npc_services初因缺少menu_groups参数失败，实现后原295菜单/任务vector、叶绑定及父295/返回10001拒绝通过；扩展验证未绑定叶、循环/缺失/重叠/伪造local return分支。verify_npc_pet_recovery_runtime在实际GameRuntime/连续RC4/原MPPC从原平列10/11/12的菜单断言失败，到295分组通过；真实kind4同时治疗两宠、费用5000→3160、寿命5950保留、重试一次和重连保持，伪造父/返回服务包不写资产。

上述实际Owner检查分别覆盖原10086和10493两个训练师，均通过。首轮6项公开服务Interface检查通过；code-review对刚部署固定副本的四文件增量分Standards/Spec两轴审查：Standards 0项，Spec初发现中间父项仍可被绑定为实际动作，已补根/中间父/返回项冲突的真实失败用例，再统一拒绝全部本地节点动作绑定；复核剩余0项。固定基线、diff与报告见reviews/npc-submenu-20261023。必要商店、新profile资产领域和实际Owner来源回归通过。

方法：codebase-design将展示树/授权放在启动冻结NpcServices，角色领域事务Interface不变；tdd沿公开menu/plan与实际Owner分发纵切；research回溯原配置和原指令。后续发布由主集成核对准确快照，与并行wild接线区域协调，避免未验工作区增量混入真人版本。

后续独立读取共享源码并运行verify_resource_npc_care_runtime也已全绿：集成方已移除新profile repair/pet临时门控并显式注入规则，真实Owner的新/旧paid、实际新租约及晚期回滚成立。这是工作区结果，运行快照仍保留此前NPC版本，未把后来shared增量算作已加载。

新增说明/导航切片：原170只含10001，无资产行动叶；原101、265→267/268、327覆盖10002/10003/10004。公开menu/plan用例分别先红后绿，当前9项通过；四个本地导航若被显式绑定为行动，无论是否在启用树内，均在启动拒绝。说明组按明确menu_groups启用，未增加任何生产NPC分组。两个原训练师实际Owner恢复回归仍通过。此增量独立评审快照见reviews/npc-menu-info-20261023：Standards硬违规0/判断问题0，Spec初1项P2（树外导航仍可绑定），四个独立失败案例补齐后统一拒绝，最终剩余0项。manifest核对真实文件字节SHA256，保留initial历史快照。

未验证：原生GUI实际点击和返回画面、全部699组后端功能、完整NPC服务及商业容量。菜单增量及关仓已随npc-close-master-commit-20261023T113819Z/PID44084统一发布；只读核对唯一28993监听与发布哈希记录一致。未实际操作原生GUI，NPC全量目标继续进行。
