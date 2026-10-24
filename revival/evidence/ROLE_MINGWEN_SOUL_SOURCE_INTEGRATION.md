# 铭文22真实来源与元魂受理组合

2026-10-24。所属候选接口；实际临时角色与现有元魂资产控制器已组合验证，未授权铭文授予/付费或修改真实角色。原证据见 `PET_SOUL_PRIVILEGE22_RESEARCH.md` 及父复现 `pet-soul-privilege22-research-batch.json`。原22是CMingwen第22项“铭文·简易”激活投影，不是VIP或bit；原消息缺席条目保持原值，不自动代表未激活。原外层type、raw2/raw3完整业务义与激活/授予规则尚未知。

## 角色来源 Interface

启动冻结 `role_mingwen.MingwenRules.load()` 并 `prepare(db)`；唯一政策 `design/role-mingwen-source-v1.json`。本模块不在角色热路径读文件、建表、开连接、提交、投递或发奖。所有读写通过当前 `Inventory.immutable_snapshot_transaction` 验证角色所有权与有效epoch。

`MingwenEntry(entry_id, raw2, raw3, raw_active)` 精确保留4项signed32，第一项必须为已知1..22。`MingwenState(role_id, version, policy, source_ref, entries)` 要求按1..22排序、完整22项，缺档不补0、不接受客户端稀疏map冒充完整基线。`soul_cap_increment` 只在第22项raw_active==1时为1；2/负数均不是激活，原值仍保留。原raw2/raw3负值测试只是保真，不证明合法业务等级/经验。

`read(db, inventory, rules)` 缺档返回None；known inactive是完整来源且明确raw_active不等于1，二者不同。返回 `MingwenBasis`，包含当前角色/库存版本、完整状态及原始state/baseline。`initialize(..., state, 'explicit_known_mingwen_ledger')` 仅可信完整version0原始导入，首次推进库存版本；原角色从未有物品的已知库存版本0也可建立首个version1。精确重试验证原始baseline，返回**当前**状态且只读；历史导入不能重置后来变化。

`replace_state(db, inventory, rules, before, after)` 对完整current basis作CAS，要求version+1且原role/policy/source_ref不变，推进同角色库存版本。它只是来源writer，不是铭文激活许可、收费或付费动作控制器。原消息稀疏更新必须由可信所有者按已有known完整状态合并再保存，不由遗漏项造未激活。本次更新的根人物inventory-source hook及宠物最终caps/资源变化仍须由调用方在**同一事务**组合；任何异常退出整个事务回滚，提交后连接所有者投递。缺乏真正旧档来源时保持unknown；不因新角色构造默认0自动授予已知铭文状态。

## 元魂 authority_reader 适配

`pet_soul_authority.SoulOperationClearance` 是不含铭文flags的外部操作许可快照：role/pet/epoch、许可policy/version、allowed及实际扣除材料keys的完整非绑定flags。世界/战斗/材料所有者继续负责这些字段的真实性，客户端不能构造许可。

在元魂控制器已有 `authority_reader(db, inventory, pet_id, material_keys)` 中调用 `pet_soul_authority.resolve(..., mingwen_rules, pet_id, material_keys, clearance_reader=real_reader)`。它同步读取实际完整Mingwen来源，再返回原 `SoulActionAuthority`，历史 `known_flag22` 字段保留以免改变已存命令格式；该值由真实第22项投影生成。完整Mingwen政策/不可变baseline/当前原始source与外部许可policy纳入SHA256政策标识，外部version保留，fresh执行可精确重验。库存版本与材料列表不纳入这个独立许可标识：本次合法扣物/材料消耗不能自己改变许可身份。实际材料keys必须sorted唯一并与reader返回的flags逐项齐全；awaitable/错角色/错pet/旧epoch/缺档均拒绝。

当前真实临时库验证中，铭文从actual source store读取；外部世界/操作许可仍显式fixture。没有把删除flag fixture说成世界许可已恢复。正式接入仍需真实地图成员许可、战斗状态及实际材料flags提供者；缺少任一项不默认放行。

## 验证与实际影响

`verify_role_mingwen_source.py`：真实完整导入/current CAS；已知与缺失分开；rawActive1/2与原signed字段保真；SQL禁止DML的历史导入返回当前；两个真实SQL故障与调用方后续异常整笔回滚；库存版本过期/他人/旧租约/不完整状态拒绝。首次真实空库存导入暴露version0缺row的失败，随后以精确0→1 CAS修复，不为角色暗建铭文状态。

`verify_pet_soul_mingwen_actions.py`：真实宠物/珠/map/资产凭据/root唯一资源已初始化，实际穿戴31276 XP140，无魂技加成；持久铭文22激活给有效2级/scalar32。随后真实CAS保存rawActive2，旧paid在SQL禁止DML下读当前有效1级/scalar11，保留人物70HP/40MP；外部许可关闭也不重扣旧款。未支付命令因真实铭文变化拒绝，新的受理命令可成功；缺材料flags/异步reader拒绝。

方法：TDD沿已授权真实角色来源/资产控制器Seam，缺Module红→actual import绿、真实空库存CAS失败→精确CAS绿、缺authority Adapter红→实际控制器组合绿；codebase-design将铭文来源所有权与外部世界许可分开，用稳定来源标识组合，保持caller事务；writing-for-agents把source writer与业务授予分开并明确paid当前结果。code-review按固定清单独立Standards/Spec检查，结果另存批次。未验证：真实铭文授予/升级/收费/新建角色来源、外层消息type/shared、实际世界/材料许可、宠物最终属性/唯一资源/战斗、部署/GUI/容量。全量目标active。
