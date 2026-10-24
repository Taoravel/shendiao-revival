# Spec

P0/P1/P2/P3：0/0/1/0。固定manifest `98f81d7c1f1324372b345adf25e4f467f51ae6510aa4bd1d8bcf88ecb6b33eee`。

**P2：成功重放把缺失经验当0。** 合约25行要求“缺XP记录不填0”，29行要求历史返回当前绝对余额。`role_learning_costs.py:50`沿用read_experience缺档默认0；新付款另查存在性，历史分支直接调用current。真实临时Store学习后XP984，单独删除role_progress，再以有效租约、policy=None重放仍成功返回XP0，记录仍缺，后续可编码虚构余额。应在current统一校验记录存在且为合法非负signed64，保留共享兼容语义。

采用code-review独立Spec轴与codebase-design公开Interface。10候选/772依赖/9规格、精确diff全核；658资源原件初核及冻结副本后核通过。两新脚本独立9+6组绿（18原生购买边界）；另验真实退款竞态、迟到付款、双epoch与缺wallet子证据。未见越界。

末核发现其他窗口更改原pet-soul-totals-v1资源，原件657/658匹配、副本全匹配，已告知根任务；不把仍在跑的34项算完整通过。正式政策、Main/NPC目录/RP读源、GUI/技能效果与商业容量未验，不宣称全量社交完成。详细复现/hash见JSON；未改候选或工作区。
