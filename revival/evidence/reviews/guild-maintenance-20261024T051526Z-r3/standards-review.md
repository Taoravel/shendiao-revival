# Standards：第25批维护 r3

固定候选 SHA `9a7bc1f32301cef107a60f7e50f6c11d8698451025e5bdc1cf89e4dbbee734e6`；基准第24批 accepted source，精确冻结diff代替Git，commit列表不适用。**P0/P1/P2/P3：0/0/0/0。** 未发现剩余文档硬标准违规或可行动的 Fowler 判断性 smell。

r1 两项 P2 和一项 P3 已独立复核修复，原报告/反例保留：

- `guild_maintenance.py:228,330`：固定绝对形状校验在前，旧凭据先读，当前观察上限只约束新结算。旧两人观察在新cap1下重放成功；新来源两人观察仍拒绝且状态不变，符合 ARCHITECTURE 与维护合约幂等规则。
- `guild_maintenance_runtime.py:11,21,30–45`：每分区一枚有界准入标记，按被拒顺序分配共享槽。相同8周期反例现接纳 `[2,3,2,3,2,3,2,3]`；空目录及实际 loop 读取故障均移除标记。真实 Store 索引分页，容量1保持；变更任务是受控异步失败 Adapter，未冒称完整周期经济验收。
- `verify_guild_maintenance_native.py:19,173`：使用实际执行文件目录；固定及独立原生结果中的源码/资源哈希均绑定冻结源。

方法：code-review 完整仓库标准和12项 Fowler 基线逐项判断；codebase-design 核单guild Owner、事务及小Interface，目录标记不承载全服命令；writing-for-agents 共置证据及限制。

独立核10候选、752依赖、653资源和冻结副本、8规格、基准来源和重建diff；核固定32脚本全部exit0及178实际imports（177冻结源Module+runner）路径/SHA。另跑维护12组、原生5组；实际 Owner 尾部 IntegrityError 传播并完整回滚，提交后展示 OperationalError 返回成功且重试XP仍7。两条目录SQL均使用覆盖索引，无临时排序。证据见 standards-independent/checks.json。

未验证正式数值/shared接线、真实GUI及完整详情mapper、终末其他Owner清理、跨库/商业容量；跨分区反例采用受控扫描相位，非完整自然周期压测。r2仅中间快照，未作为验收基准。未改固定源码、真人库、服务或启动游戏；不代表全量社交完成。
