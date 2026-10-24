# NPC修理 R2：当前原生装备消息与同事务资源

2026-10-24。所属候选；未替换工作区npc_repairs.py，未修改shared或运行服。R1的9e297b就绪件、E648源码、27组合原生证据及各历史审查保持原样。接本片时先核对本片的新审查清单，不能把R1封签当R2封签。

## 接入与完成条件

1. 根确认修理fresh1/3、旧paid4只按真实稳定凭据读当前的最终兼容政策；主复原聊天在当前PVE发布之后选择本片。R1的历史token4只用于receipt fingerprint，不对外映射本人/NPC容器。
2. 启动选定资产窗口已审的equipment_native_columns.NativeEquipmentRules，并准备socket/score表。资产固定件为equipment-native-columns-20261024-r1（生产E9130e）；本片只用其五个只读适配依赖和两份政策、三份原目录，验证中Inventory、runtime_storage和其他生产模块均为023920发布原件。不会整份引入工作区Inventory或其他付费Gem/宠物功能。
3. main单写repair_role_equipment：把startup选定规则绑定到当前生产者，`equipment_messages(db, inventory, key)` 调用 `equipment_native_columns.item_messages(db, inventory, native_rules, key)`，再把此callable显式传入npc_repairs.repair。保留现有resource_rules/equipment_rules及equipment_projection_messages precommit。这是调用方接线，NPC没有修改共享入口。
4. repair在原有同一角色租约事务内完成修理、费用、唯一source/HPMP、凭据、Asset当前详情/耐久和完整人物属性编码；全部成功才提交。新生产者只读当前实际owned实例，已穿发3、携带发1，保留已知Gem/score；编码/来源异常须整笔回滚。调用方不能在提交后补编码，也不能连接/提交/发送或变更资产。未选择生产者的旧调用方保持原行为，不等于原UI修复。
5. main完整本人query3、登录/重连、穿脱/任务装备、tips/endures仍按资产交单接齐；服务2回购4独立。实际连接所有者加密投递、原CEquipDialog点击、部署和现场显示各验收后才称上线。

## 所属规格与验证

公共Seam沿既有NPC plan/repair、Inventory和钱包契约；用户授权全部NPC恢复/接入/部署，本批沿该范围完成生产者接缝，不另设审批。精确BASE是已审E648，不假造Git提交或问题号。新生产者是已存在Asset适配与legacy生产者的实际差异，按codebase-design显式注入，NPC不导入Gem领域或改写其政策。

TDD：先用023920真实Owner/Peer在新临时库创建旧paid4稳定凭据，另一个进程新租约调用E648+新生产者，实际exit1为缺equipment_messages。新候选完成11组公开行为：旧paid4/3当前native3不重抽/不重扣；较新损耗不被历史回放；fresh3收费一次并原codec解码且完整20属性；真实已持久socket但缺score时native编码失败，费用/condition/凭据回滚，公开补齐来源后同ID重试只扣6；可变生产者消息被拒并回滚，同ID再试只扣4；脱下后旧paid4/3输出当前carried1；fresh4/错位3拒；fresh1扣2；旧lease拒；真实已迁移L21单资源fixture中末尾人物编码失败全部回滚、同ID再试只扣20并保持HP10/MP20/version；paid读当前source不再结算。所有测试使用新disposable.sqlite3，既有receipt由真实旧Owner产生，无SQL伪造。

初次green1的11组前段完成后，验证脚本错误地把自身__main__计入模块来源白名单而失败；修正仅该检查，历史失败日志保留。green2完整11组通过。审查阶段把两个相同的不可变消息检查合为一个私有函数，保留两种原错误文本；随后按新封签重跑正向和实际RED、R1回归。

code-review按Standards与Spec两个独立轴固定审查。本文件是本批Spec；标准为根AGENTS、ARCHITECTURE、DESIGN_AUTHORITY及Fowler判断项。writing-for-agents将startup依赖、同事务提交和shared完成条件与步骤放在一起，避免把纯适配green当上线。

## 尚未验证

新equipment_messages在main实际RoleOwner路由尚未注入，故本片没有宣称这条生产者已经加密投递或GUI通过。实际迁移资源与legacy20属性已在公开领域事务内验证；含非空宝石的完整人物派生source属于资产/根集成，不能由known-empty修理证明。最终兼容政策采用、登录/重连统一投影、回购query4/价格一致、部署、容量与完整NPC恢复仍单独待办。
