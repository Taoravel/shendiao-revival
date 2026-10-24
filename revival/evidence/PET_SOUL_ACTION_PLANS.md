# 元魂穿戴、摘除的显式资产计划

本批先完成纯计划，**未实现实际资产动作、受理/幂等控制器或共享路由**。原数据、背包来源和消息模块已分别封签；这份计划不会扣物、返还、收费、提交、发送或改变任何生命/真气。全量目标active。

## 明确的设计选择

先读 `design/pet-soul-actions-v1.json`；原来源见 `PET_EQUIPMENT_SOURCE_RESEARCH.md` 和 `PET_SOUL_ITEM_SOURCE_RESEARCH.md`。原CUseItem数量1/宠key、精确模板重复、五槽、四→六交叉映射、经验/有效级和38045原摘除数量均有客户端证据。以下服务端选择仍是明确 `designed`：普通五槽全部可用、最低空槽、采用精确ID互斥而不额外猜普通/高级同族互斥；穿戴目标为当前已选参战宠且有明确当前许可；普通穿戴/摘除不收现金；摘除按绑定优先再key取移魂符，返还一颗新的binding1/nonbinding_flags0实例。

已知穿戴历史raw6必须精确复制，包括负数；只有明确没有该历史的完整已知背包珠才按本地设计使用当前实际binding0/1生成新的raw6。显示函数返回的0/1不能回写历史。移除生成的新实例保留四项原始数据与完整历史raw6；“新返还旗标0/绑定1”是结果策略，不是猜旧珠原旗标。

## 纯Interface

启动加载 `SoulActionRules.load()`。`SoulActionAuthority` 是可信角色所有者提供的当前role/pet/epoch、来源政策/版本、许可、已知flag22及逐材料非绑定旗标快照；缺失不当0。后续受理/写入者必须从真实当前状态读取并在同一角色事务内重验，不能把该对象交给原始客户端构造。

`plan_wear(rules, current_soul_basis, current_orb_basis, authority)` 要求同角色/账号/库存版本、当前已选参战宠、完整已知且无其他限制旗标的背包珠；验证未知/重复模板并选最低空槽。输出下一完整元魂map、单扣一颗珠、无返还/现金费及当前原始效果列表。累计经验不随有效等级裁剪，四→六顺序正确，raw6按上面的明确来源规则处理。

`plan_remove(rules, current_soul_basis, slot, tools, authority)` 仅收当前存在的1..5单槽，真实原经验级而非有效级决定38045数量。所有实际扣除的移魂符堆必须有精确已知0非绑定旗标，来源列表不重复；数量不足或受限拒绝。输出下一完整map、确定的材料debits、一颗新绑定珠grant、独立四项数据与精确raw6、当前剩余原始效果。此计划不直接初始化返还实例，必须由实际Inventory writer与来源writer同事务落实。

后续实际控制器需要稳定服务器request_id（原请求没有重试ID）、原CUseItem/c0805精确解码、真实来源再读、Inventory.apply_settlement、元魂map CAS、返还OrbSource、公用及专用凭据、当前人物唯一资源hook、完整宠物属性投影、Bag→逐珠tips/完整元魂map及其他当前刷新预编码。任一异常回滚全部；paid必须只读当前并保留当时已付意图，不重放历史资产或效果。当前阶段这些条件尚未由本Module实现。

## 实际方法和验证

TDD 沿已授权纯计划Seam逐片执行：缺Module红灯后实现穿戴计划；缺plan_remove红灯后实现摘除计划。字面fixture来自原字段/阈值和明确策略，不查询私有存储；这不是实际受理或扣费验收。已验证原31276的61经验/10001魂技在宠模板500001的当前有效档得到外攻原scalar32；历史raw6=-2与signed raw4/raw5保留；明确新历史走binding1策略；38045原二级费用2，绑定堆1枚先扣、普通堆再1枚；返还四项和完整raw6不变。未知/受限/库存来源不一致/重复模板/空槽/不足材料均拒绝。

codebase-design 将计划、当前来源和变更许可分开，避免在原始wire或背包编码器里决定资产。writing-for-agents 把原证据、设计与未来写入前置并列；code-review 对固定清单做Standards/Spec独立审查；无Git/tracker，沿用此前字节清单适配，不制造提交或issue。

未验证：真实世界/战斗/技能来源的许可读取者、原请求受理与稳定命令、实际扣珠/扣符/返还/source及多凭据事务、完全数值/宠物HPMP上限与战斗计算、共享/发布/GUI/容量。原自身装备wire3与内部4的独立适配见 `EQUIPMENT_NATIVE_COLUMNS_PLAN.md`，此纯元魂计划不改编号或解锁NPC货架4。
