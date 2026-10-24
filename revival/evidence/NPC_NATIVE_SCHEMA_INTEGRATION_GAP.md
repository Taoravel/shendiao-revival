# 本人装备原生适配：仓库来源表启动闭包

2026-10-24。修理领域R2/d0的11组并未失效，但它未宣称完成的startup/shared闭包现在有准确RED。此门槛在激活Asset本人3适配前处理；不能仅把Gem/score prepare放到npc_depot.prepare之后，省略下次启动。

## 已实际运行的反馈环

指定项目Python `-X utf8 -B staging/diagnose_npc_native_schema_reprepare.py --label <新label>`：默认实际exit1，子进程报告 `ValueError: Warehouse metadata preservation required for inventory_equipment_gems`。父进程先在新无角色disposable.sqlite3完成正常prepare，再通过Asset公开prepare创建Gem/score两来源表，然后由另一个全新Python进程重新加载AccountStore并prepare。所有生产/配置来自已封原生适配上下文，前后哈希保持。

当前脚本同SHA的控制：加 `--omit-native-schema` 时第二进程prepare实际exit0；默认加表时第二进程实际exit1。精确记录在`npc-native-schema-reprepare/control_without_native_schema/`和`npc-native-schema-reprepare/current_actual_red/`，每个目录有两个进程ID、子报告/日志、输入闭包hash。更早的实际RED在parent_actual_red，其当时执行脚本已单独保留并核原49e5a26b字节；不是把预期失败说成功。

这个单变量对照排除了首次启动本身/角色存档/普通重复prepare作为原因，定位到新增来源表与既有FK保护契约不匹配；两库均无角色。无需增加生产日志或猜测随机/网络原因。未运行真正PVE完整startup、未停开真实服务、未访问真人库或GUI。

## 与当前版本的关系

当前运行BASE为task-pve-20261024T053218Z/PID37096，独立OS/源核对见npc-post-pve-source-readback-20261024.json。该BASE的npc_depot.py SHA757500201d39dabb7f39a0614221f5af738abb42bc2ece8c745462fb96422b16、npc_gameplay.py SHA7212aa304509721bf82c4e5d6545212a5cc8c21b26bfbbf3901ed3c946c83387与上述冻结上下文相同。故此具体consumer约束仍相关，不能扩大成已运行新PVE全链或说现服已经启动失败。现服修理/商店仍3cc/5bf；native新表候选未部署。

原NpcDepot.prepare会扫描inventory_items的CASCADE外键，只接受已支持的condition/detail来源。Gem及score表是新来源，尚无仓库封装。take_carried静态仍删除inventory_items，而StoredItem只携带旧基础来源；sale/buyback也复用该路径，因此后续保全范围需同时覆盖仓库和出售缓存。后一句是静态数据流风险；本批没有冒称动态执行过非空宝石丢失。

## 下一步与完成标准

1. root转Asset提供实际Gem/score来源导出及保留原版本/基线的恢复Interface，或者正式声明可组合的分期采用契约；NPC依据真实Interface扩展所属保存/恢复封装，不先造通用插件、不重新初始化已知来源。
2. main按新PVE BASE只接局部owned变更。保留未知FK保护；仅白名单放行表名或取消检测不能证明来源保全。完整仓库功能仍是总目标，临时门控不算完成。
3. 在新临时库用真实公开来源创建、存取/出售缓存/回购、重登与第二进程再次startup验证；当前source、condition/detail、Gem/score、key/绑定/数量、唯一HPMP及费用/凭据同事务。故障时全回滚，旧未知源不补零，旧paid只读当前。固定双轴后才交main备份发布，原GUI另验。

本批diagnosing-bugs采用真实两进程紧反馈及单变量控制，源明确的既有保护直接指向缺少来源保全，未进行泛化日志或全表生产试验；codebase-design把该约束留在资产保存/恢复的实际Seam，不通过协议数字转换绕开；writing-for-agents将激活触发条件与所需Interface/再次启动验收放在一起。d0/9e/9b05/761c及本批回购c8封签未改。状态是具体跨Module接入门槛待解决，全量NPC目标active。
