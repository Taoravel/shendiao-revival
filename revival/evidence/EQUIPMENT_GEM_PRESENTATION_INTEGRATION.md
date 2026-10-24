# 宝石评分与颜色成对写入 Interface

接列表CAS之后的score/color保存、同阶替换或摘光恢复前读本文。2026-10-24。`equipment_gem_presentation.py`是同一角色所有者内的装备持久化Adapter，扩展本窗口所属详情/condition写入能力；**不是收费action或shared ready**。原score公式未知，当前数值按`equipment-gem-score-v1.json`的明确designed候选执行。

## 调用顺序

1. 启动准备Inventory、GemRules、GemScoreRules、socket表及不可变pre-gem score来源。没有已知完整socket profile、原装备详情/耐久、明确pre-gem基准或资格时拒绝；本Module不导入/补档。
2. 角色Owner在一个当前lease事务取得`before=equipment_gem_storage.read(...)`和实际`score_basis`，由纯embed/remove产生next GemState，再用`equipment_gem_score.project`产生不可变GemScoreChange。
3. 同db先`state_saved=equipment_gem_storage.replace_state(db,inventory,gem_rules,before,next_state)`，立即调用`equipment_gem_presentation.apply(db,inventory,gem_rules,score_rules,before,state_saved,score_change)`。三份数据均是服务器固定来源，不由原线包声明。between步骤不提交或插入别的库存变更。
4. 此后同外层事务组合材料/工具/现金/绑定/返还/凭据和root唯一资源投影，编码当前全量gem详情及其他当前回复，全部成功后仅commit一次。任一异常回滚**整个外层事务**；控制器不得捕获本Adapter错误后提交已经保存的gem列表。

## 围栏与写入

公开Adapter要求before/state_saved都是严格冻结EquipmentGemBasis、同角色/账号、同完整ItemState/原detail和condition来源；state恰好下一版本、inventory恰好+1、skill不变且新origin=socket_change。再从同事务读取当前socket完整basis逐项相等，读取实际持久score基准，重新执行纯评分策略。提供的GemScoreChange必须与重算结果一致，拒绝bool伪整数、错误score/颜色/耐久/绑定、后来变化的来源。

实际持久化始终使用重算的结果。detail只改score，condition只在颜色改变时更新color_tier并推进version，当前/最大耐久不变；两行都按完整旧revision/原JSON及item当前角色/数量1作CAS。保留现有详情origin与policy revision，因为仍是相同四字段模型，不制造另一个旧loader不认识的来源。原来源有额外未知字段时既有严格loader先拒绝，不能为方便丢掉随机附加属性。

score或color实际变化后，库存revision再作一次expected→+1 CAS；返回当前完整EquipmentGemBasis。若同阶类型替换等导致score/color全不变，本Adapter严格只读返回，不产生空UPDATE或额外库存版本。此前**列表CAS仍已推进来源**，root必须按新列表重新计算属性；不能因presentation no-op就跳过外攻换内攻等真实效果变化。

这是首次公开成对写入，不滥用`equipment_condition.reconcile_color`的实验v1迁移接口，也不修改冻结equipment_detail.py/inventory.py/currency-v1.json或既有发布。只有此public Adapter保存该复合变更，后续Gem action控制器调用它，避免在路由里临时写JSON。

## 退款、重试与剩余闭包

本Interface没有paid receipt、连接、内部BEGIN/commit、材料/现金/工具扣除、HP/MP状态或网络发送。完成过的action必须由外层控制器核历史完整意图并跳过列表CAS/本writer；当前回复只读。不能把再次调用writer的拒绝包装成已付成功，也不能自动修补不完整的历史交易。

验证脚本`verify_equipment_gem_presentation.py`使用明确10级40101、pre-gem1040及原首颜色阈值1062：列表+一级猫眼→1090/color2，原完整parser实际读到新score/color/list，当前耐久42/80不变。真实details写、condition写和**第二次**库存版本写故障，旧JSON/score来源变化、错误或可变proof、原生编码之后的外层异常，均回滚gem/score/color/库存来源。等阶替换的presentation在禁止DML下通过；摘光恢复1040/color1并清原gem效果。测试特意断言材料仍2颗，证明没有冒称收费已交。

下一步必须继续：完整材料/现金purpose/工具/返还metadata/多凭据控制器；原生所有读取入口消费新gem来源；root完整gem-aware装备政策、磨损/修理/穿脱/登录及HP/MP源过渡；shared准入/投递、准确BASE发布与真实GUI。旧role-equipment v1/v2没有gem语义，不能因此Adapter已保存score就宣称人物实际加成完成。

方法：TDD通过缺Module、bool0伪贡献proof被接受两次真实red→green；在已授权角色调用方事务和原完整native接缝验证。codebase-design把配对写入集中为装备Adapter，领域入口只传不可变来源，复用公共socket/score来源及纯策略，不复制现金/资源权威。writing-for-agents共置顺序、CAS与no-op/paid拒绝规则；固定新增片再按code-review独立Standards/Spec审查。全量目标保持active。
