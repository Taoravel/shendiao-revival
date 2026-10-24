# 潜能分配稳定请求入口

2026-10-23。任务/成长窗口维护role_growth.py；主策划维护role_growth_actions和原生加点codec，运行时由原集成窗口接线。使用codebase-design将原意图指纹、历史receipt与当前快照处理留在成长Module，不在外层复制账本算法。

公开Interface：`request_potential_allocation(db,account_id,role_id,epoch,deltas,request_id,rules,attribute_rules=None)`。调用方拥有租约事务；deltas必须是内部顺序(体质,内力,力量,耐力,敏捷)的五项非负整数tuple，总和正。wire顺序转换归codec负责。

新请求读取当前GrowthState，使用当前revision规划并经apply_growth_plan扣free、写分配、同步已启用属性及持久凭据，同caller事务保存。成功重放先从原receipt.result.revision−1恢复原分配before_revision并核对指纹，不用新版本重规划；不同deltas/策略/操作重用ID拒绝。无第二张账本或外层私有算法。

**该入口新请求和重放都返回当前GrowthState**。例如请求A后又请求B，再重试A，返回B之后的当前点数/版本，不把A历史结果覆盖缓存。原request_manual_level为兼容仍返回历史成功回执，调用方应继续read_growth获取当前状态，两者返回语义分开记录。

verify_role_growth新增必要检查并通过：先分配A，再分配B，重放A不扣点且返回B当前快照；同ID换增量拒绝。检查使用临时库，没有启用在线基线或触碰客户端。完整原生加点/属性显示与role_growth_actions接线由主策划及原集成窗口验收。
