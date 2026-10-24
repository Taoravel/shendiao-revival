# Standards

0项可行动发现。manifest原4条SHA-256均实际匹配，含base及三个current；仅审固定首片生产diff与两验证脚本，非Git，无提交列表，不读取后续working改动。

沿用完整code-review／codebase-design，依据AGENTS、ARCHITECTURE、DESIGN_AUTHORITY检查地图状态所有权。game_runtime.py:88–97严格校验完整MapAddress／signed63整数，旧整数仅归一化公开图；:100–117按map_id取原模板／NPC和entitykey，按完整地址隔离WorldDomain及mailbox；:1073–1082以完整地址注册／查询，不混淆同实例号不同模板或分区，查询不创建。未新增热配置IO、跨图可变状态共享或全服队列。

12项Fowler smell逐项作heuristic判断，未见有实际后果的问题；真实身份归一化集中于同一Seam。

仅静态核对冻结源码及脚本，未运行测试、DB、服务、GUI或战斗。受控join／移动不等于自然role handoff；私有入场、容量与生命周期属后续接线，未计为本片缺陷或已完成。
