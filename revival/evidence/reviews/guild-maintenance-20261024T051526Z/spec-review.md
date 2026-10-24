# Spec

P0/P1/P2/P3：0/0/1/0。固定manifest `8ebf4028b91c982be0f95e95d1febedeb6794add037592462e1df097f9eb897c`。

**P2：新观察上限挡住旧成功凭据。** 合约第21行要求“历史凭据先读，经济政策关闭或改变后仍可重放”。`guild_maintenance.py:228–229`在查旧凭据前使用当前member_limit；真实Store先以两租约观察成功，改member_limit=1后原命令重放报invalid_guild_maintenance_observation，清空观察才能读回旧结果。Runtime/Store预验证也受影响。应先做固定形状/绝对上限验证，当前经济上限仅约束无旧凭据的新结算。独立复现见JSON。

code-review按Spec轴分查缺失/越界/错误；codebase-design通过公开Store/Runtime测试。10候选/752依赖/653资源原件及副本/8规格与精确diff全核。两新脚本独立15组绿；另验终末全库尾回滚、混合降级进度、人气1000与48等值、resume后仅下一小时收益。实际调度器限1槽、两次故障且持续新高ID，7轮恢复旧源。全32脚本exit0及178实际导入的路径/哈希已补核。另一轴报告的跨分区抢槽未独立复现，不计本轴。

生产policy、共享激活、完整详情/GUI、其他Owner终末消费及商业容量未验，不宣称全量恢复完成。未改候选。
