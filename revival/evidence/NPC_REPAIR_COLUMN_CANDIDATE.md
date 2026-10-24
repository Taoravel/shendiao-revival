# NPC修理原栏目与已付兼容候选

后续R2已完成与Asset实际原生消息Interface的领域事务组合，见`NPC_REPAIR_NATIVE_MESSAGES_CANDIDATE.md`及新不可变`npc-repair-native-messages-ready.json`（d0ce9f00）。源码60820efa仅staging，18正向/3实际E648 RED、Standards/Fowler/Spec各0；新provider11组包含当前3/1、真实来源异常回滚与迁移HPMP/source组合。main/root已收到统一接线发布交单。最终policy采用、实际shared注入/加密投递、GUI/发布仍待。本页以下保留R1历史规格与其独立seal，不能把R1 seal当R2 seal。另已证query4是回购tab，普通购买走本地模板，不造stock4。

R1所属候选已完成固定双轴，Standards/Spec各0。主窗口与两位审查者各跑六项：合计15次候选/回归正向验证、3次准确旧版red重现，每次前后校验22本地/3078外部输入。封签`npc-repair-column-candidate-ready.json` SHA9e297b2f66678c2a198492a3240ec72cf3d7bf4659531427e5d759582b5e1543，审查`reviews/npc-repair-columns-20261024-r1/REVIEW.md`。R1封签时工作区/现役仍3cc，E648仅staging；root最终policy及Asset实际消息Interface尚待合审。商店query4所属tab当时另在追原来源，不能据本片把普通货架造作column4资产。

2026-10-24。所属候选位于`staging/npc-repair-column-candidate-v1/npc_repairs.py`，不覆盖工作区3cc或现役023920。主策已要求：本人装备3/商店4由Asset按原来源接线；旧paid4仅恢复已有真实stable receipt的当前结果，fresh4不再收费；完整兼容policy仍与Asset实际Interface一起审定。本页是准备阶段规格，非上线批准。

## 本片行为与数据约束

1. 原method2普通修理的fresh请求只授权column1携带、column3已穿；对应当前真实owned item的`equipment_slot`分别为空/非空。仍需原NPC513证明、角色租约/实例/位置/期限、普通装备condition与既有费用/资源规则。特殊855、method0/1及未知旧资产保持其所属授权范围。
2. decoder可接legacy4用于查已有付款凭据，新的4在实际交易内拒绝，并保持资产、钱包和凭据不变。允许解析不是允许新交易。
3. 旧fingerprint把已穿意图写成数字4。候选仅在私有receipt fingerprint中沿用该历史token，让新的原生3与相同NPC/同物品/同stable request表示同一物理修理；携带1和其余fingerprint字段/算法保持原样。该token不是Inventory栏目，也不转换商店query4或迁移存档。
4. 只有已有匹配fingerprint的稳定付款记录才能走paid恢复；换物品/换意图冲突拒绝。paid4或3都只编码当前结果，即使后来修理、钱包变化、脱装或再次损耗，也不回放历史状态或重复收费。由于旧表只有fingerprint，不另存原wire版本，新的原生3亦沿用同一私有物理token；该兼容方案由root最终policy审验。
5. 原有同事务资源来源检查、普通修理随机过程、收费、所有凭据和最终编码仍通过同一Module执行。失败按原事务整体回滚。新的相同线包没有客户端重试ID，仍是新受理命令；这里只对同一服务器stable request幂等。

## 红绿与既定Seam

`staging/verify_npc_repair_column_candidate.py`先在准确发布3cc/9cd真实Owner中创建付款记录，再在另一个进程/新租约使用同一临时库。付款记录由原RoleOwner公开receive Interface产生，没有直接插SQL凭据。准确BASE无法以3恢复旧paid4，真实red为“Real legacy paid4 cannot replay original-column3”；同一探针选单个候选模块后转绿。

候选验证还要求：fresh4在损耗状态拒绝；actual encrypted Peer原生3修理成功、原完整人物map和正确费用；改物品重放拒；后来修理、脱装、再损耗后，旧paid4/3保持当前资产及钱包；损耗的携带物不能被fresh3修理。所有其它生产/助手/配置来自准确发布，前后校验；唯一模块替换须明确记录来源路径和SHA。

固定回归包含原携带1费用/幂等/失败回滚、原实际携带Owner，以及把既有known-profile/已穿加密检查的测试请求4改为已证原生3；测试数据适配逐行声明，生产dispatcher和投影保持真实。资料依据为`NPC_REPAIR_COLUMN_RESEARCH.md`的27组合与`npc-repair-column-independent.json`，不是以服务器4绿灯倒推原UI。

## 接入条件与未验证范围

本片只完成NPC修理入参与私有已付身份准备。准确发布Inventory的网络装备刷新仍用旧4，Asset的自身bag3/refresh/tips/gem来源及NPC商店query4尚待接线；本片输出中的旧4须如实记录，不能称原GUI已能看到装备或完整修理已恢复。

root最终policy与Asset实际Interface审定、各Module完整候选接入、固定双轴/实际Peer全链转绿和main统一发布完成后，才能关闭运行时问题。当前PVE候选保持其独立来源，9b05鉴定和761c方向封签不变。

方法：tdd沿既有公开Owner/Peer Seam先保留原BASE red，再最小修改所属Module；codebase-design把原wire、物理资产位置和历史receipt token分别封装在真实使用位置，不向调用方扩散数字转换；diagnosing-bugs使用单字段对照和同一晚期状态恢复反馈；writing-for-agents共置兼容规则、完成条件及外部未完成范围。固定版本code-review的两轴与实际验证以本片后续报告记录。
