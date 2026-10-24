# collision 202823 主策划阶段聚合

## Standards

独立静态硬0/判断0，见 Standards-root.md。

## Spec

独立静态 missing0/extra0/wrong0，见 Spec-root.md；r1 paid重复授权修正及r2当前CG晚回执误关泵修正已各自保留原反例，r3准确相同探针转绿。

## root准确运行结果及新反例

root8项隔离集成均exit0：same dd64 intro-race、strict earlyACK、terminal5组、private send terminal6组、自然private断线、自然两角色bloodmark/chat/冷重连、1006/1404/1501子集、GC隔离。另原HPconsumer8项全绿，保留原battle_protocol/training_battle SHA。每项1442/419/1205+runner前后完整SHA、实际imports皆固定。root-checks.json保存8项通过，不能当全面验收签发。

随后新增World探针db9c45e8d1d3401e5dbab6d1aa308db1b7a3a5abc857a2eadf2dcc9a73f39253对准确r3实际RED：纯公开MapOwner/SerialOwner授权transfer→finalize→新epoch重新join源图→旧receipt finalize，Domain保留新member，但runtime positions被清，新lease公开location被StaleEpoch拒绝，精确assertion `Late historical finalize erased replacement runtime membership`。原44项未含此新case；固定为supplemental，不伪改旧candidate。报告在root-world-collision-20261024/world-collision-20261023T202823Z/verify_world_late_finalize_membership.py/。

结论：新增真实反例使旧回调不能伤新成员的架构约束未满足，r3不予最终签发，原source/两轴报告/8绿和新RED全部保留。main独占共享入口窄修后另冻r4，将新case纳入验收；保留空源重复finalize幂等，旧lease/旧位置版本不得清当前cached member和新MovementContext。root未执行服务/正式DB/GUI/正式剧情AI，商业容量未测。


后续原44项现已全部准确exit0，302 actual source/harness模式完整结果all_passed、inputs_stable、candidate_production_stable为true，3443 NPC placements，所有result seal匹配64fe...。此补验未推翻新增late-finalize实际反例，最终仍拒绝，见acceptance-root.json。
