# NPC离散格交互接线

当前候选采用主策划NPC_INTERACTION_CELL_DECISION.md及design/npc-interaction-v2.json。原公共CNpc离散距离路径为client_verified，恢复服采用该准入为designed；原server距离未知。36632固定运行版尚未加载本候选，现场车夫延迟恢复也未确认为距离拒绝。

## 启动及地图Interface

npc_interaction.prepare(accounts)在原npc_resources加载之后、地图创建之前冻结规则，资源二元tuple保持不变。默认load/prepare选v2；显式path仍可加载v1复验历史。将同一accounts.npc_interaction_rules注入NpcScene(interaction_rules=rules)；未来NpcLifecycle用同一对象。旧显式interaction_radius=32只保留调用兼容，v2解析为None。

唯一距离Interface为rules.allows(npc, location.position)，第二参数严格(map_id,x,y)，坐标非负整数。双方分别整除16，格差平方和<169；13格边界拒绝，格内偏移决定形状，不能改为208像素圆。v2.radius_for明确拒绝。完整MapAddress、当前实体、世代、租约、位置版本、active及业务权限仍由现有所有者复核。

## 共享及世界接线

runtime_storage.py和game_runtime.py由main唯一写入。最小静态runtime闭包是ready内三个生产输入，加共享启动import/prepare及MapOwner规则注入两文件。工作区私有实例、pool、social、story和未激活Lifecycle不是此最小闭包的一部分；最终准确候选另对固定36632 BASE逐文件验收。

世界公开离线Interface现为check_birth_site(..., interaction_allowed=rules.allows, max_visited=...)，省interaction_radius；该Module将原NpcPlacement和三段逻辑位置交给同一冻结predicate。legacy显式半径用于历史检查。root已按单写协调替换自然血手印验证中的旧radius_for调用，并执行默认无approach fixture自然链；不能沿用旧v1自然链绿当v2完成。

## 固定验证与未完成范围

原血手印同q64及合法62像素站点、说书人和女大夫64像素站点分别在Scene/Lifecycle转绿。v2八组含格边界、两种非208圆反例、当前性/移除/世代拒绝、严格启动及冻结。显式v1八组、既有Scene、Lifecycle十一组、motion十一组通过；实际Peer治疗三组、绑银七组通过。固定六文件审查见reviews/npc-interaction-v2-20261023/REVIEW.md，Standards与Spec分别0项，ready保存准确SHA。

当前完成为领域实现、固定审查和root独立共享自然链。prologue-touch-v2-root-natural-verification.json记录单角色四组；prologue-touch-v2-two-roles-root-verification.json记录双自然角色各入不同私有地址、当前频道隔离及冷重登，实际血手印接近点均(1006,1512,1096)，距原摆放平方40212，按同v2 predicate通过。两份报告记录各自源码SHA与检查期间稳定，不把旧v1结果作本批依据。此处核读root证据，未重复代跑。

最终候选、发布后验收、GUI及原完整自动接近继续分别记录。双角色报告未验证完整pool容量/卸载；NpcLifecycle领域改动已审但共享控制/广播尚未激活。旧149无近点/八服务摆放审计是v1圆盘的历史结果，不能推成v2现状。

方法：diagnosing-bugs与原生研究确认同访问包被旧规则拒绝；tdd逐公开Seam保留红→绿；codebase-design集中冻结predicate供Scene/Lifecycle及世界见证共同消费；code-review按原始字节分轴；writing-for-agents明确唯一写者与每阶段完成条件。未改真人库、客户端或运行进程。
