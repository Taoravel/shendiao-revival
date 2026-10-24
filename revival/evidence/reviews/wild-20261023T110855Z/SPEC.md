# Spec最终复核（仅静态）

结论：0项未解决问题，原断线P2已关闭。

沿用code-review与codebase-design，按需求1–7复核实际移动、快照、独立战斗、终局事务、重试及跨lease恢复。8文件前后hash全匹配；基准为master-ready-exit-20261023T110056Z，无Git提交。重基context已核：四个任务/退出文件逐字相同；game_runtime相对该基准仅继承已审close两处修复，世界初始化及退出路由保留。

wild_runtime_storage.py:109冻结format2完整RoleResources；187先比较全部source/版本/数值，再消费终局。旧已付重放先返回当前值；旧未付迁移记录缺source在192拒绝显式核对。新增来源回归检查同五数、不同source拒绝且回滚后仍可结算。未发现新guard造成遗漏或越界。

game_runtime.py:341–353继承finally清理战斗/地图，870继续真正close；继承入口与资源Module范围保持分别审核。

本次只读取/hash核对，未执行测试、DB、服务或GUI；11项执行结果属集成方证据。候选未发布，现场版本与客户端验收不在本结论内。
