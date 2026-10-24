# 本人装备列3：所属当前消息 Adapter

2026-10-24；候选接口，shared/部署/真实GUI尚未接入。`equipment_native_columns.py` 从真实当前角色资产编码本人原生列3，内部 Inventory 装备视图4及数据库编号保留。NPC商店回购列4由NPC命名空间管理；普通货架为客户端本地模板，不创建stock4。来源：`NPC_REPAIR_COLUMN_RESEARCH.md` / `NPC_SHOP_CATALOG_NATIVE_RESEARCH.md`，原本人 CEquipDialog 查询/修理使用3，新商店研究纠正4为回购。旧 `staging/verify_equipment_native_column_red.py` 仍针对未修改的legacy入口，预期exit1；本Adapter通过不等于该入口或GUI修复。

## 接入步骤与 Interface

启动时冻结 `NativeEquipmentRules.load()`（原GemRules与明确GemScoreRules），统一准备 Inventory、equipment_gem_storage 和 equipment_gem_score_storage schema。配置/DDL只启动执行。调用均由当前角色所有者在已有连接与同一事务执行；返回冻结逻辑消息，不开连接、不写状态、不提交、不投递。

- `query_bag(db, inventory, payload)` 仅接原CGetBagInfo精确12字节 `>iQ`、column3、target0或当前role。返回当前本人已穿SGetBagInfo，column3/16容量，Item.position为实际装备slot；内部负slot与视图4保留。现金字段0沿用现有非背包装备容器表达，不代表人物钱包归零或原服金额规则证明。拒绝NPC4/外国target/尾随数据；背包1仍用既有当前钱包及orb-aware生产者。
- `equipment_bag(db, inventory)` 为登录/重连、穿脱/任务穿戴后的当前已穿消息；只从当前租约下快照选真实equipped实例。可与所属背包1消息组合。它只投影物理列表，不证明人物唯一资源来源已经完成；变更调用方仍必须先加入所选根source/HPMP结算再整体编码、提交。
- `item_messages(db, inventory, rules, key)` 从当前同角色实例生成tips、当前耐久map与最大耐久：实际已穿为3，实际携带为1。适用于穿脱、损坏、修理及历史paid确认；输入不是历史Receipt。`query_tips(..., payload)` 精确8字节 `>ii`，校验请求列1/3与实际容器一致，只返回当前tips。非普通装备/其它道具类型继续由对应Bean生产者处理，不以此代替元魂等专用tips。
- `query_endures(..., payload)` 精确4字节列1/3，读取该实际容器里已恢复的普通六槽装备，返回当前耐久map+逐实例最大值。普通详情/condition缺失拒绝，不补新基线；其它装备体系未纳入本普通耐久投影。
- `socket_basis(db, inventory, rules, kind, payload)` 只按已封普通Gem decoder解析原source字节0/1，公开 `request_basis` 精确查当前携带/已穿实例，再验证当前宝石/评分来源。返回 `(SocketRequest, EquipmentGemBasis)`；`request.source_column` **继续表示内部1/4**，已穿对象对外消息属于本人3，不是原wire4。source1不会搜索携带或NPC回购。此函数只解析/定位来源，不授予付费镶嵌许可、不验证材料/现金/地图资格、不扣料。

原始Item固定48标量继续使用公开Inventory.item_record，未扩展未知extra字段。普通clean详情沿既有明确clean政策编码；已存在宝石来源时，必须有独立评分basis且当前score/color符合所选政策，再使用原宝石详情encoder；缺失/冲突拒绝，不退成空宝石。gem state刚CAS而score尚未配对时tips/耐久拒绝。缺表由启动集成修复，不在热路径补建。

main须统一替换真实本人query3、详情、耐久、登录/重连、穿脱/任务穿戴及损坏/修理后的消息生产调用；只替换query仍不够。读写仍按角色epoch与根source契约。NPC修理fresh1/3与E648组合由NPC/main另审；历史paid4兼容只读由其政策裁定。提交前完成当前Bag/tips/endure/人物属性编码，任一异常退出整个事务回滚，提交后连接所有者投递。不提供任意帧4→3转换，也不接NPC4。

## 实测与尚未验证

`verify_equipment_native_columns.py` 使用真实临时Inventory：本人49001slot0查询3、原Bag codec；详情/耐久原codecs；真实损耗100→80和可信fixture修理→100；真实腰带45001slot4与绿宝石35005 source/score/presentation，原完整详情parser得gem35005/score50；待配对score拒绝；SQL禁止DML读取。脱下后tips变1、source1拒绝/source0精确定位；原生耐久编码后调用方异常整笔回滚。外角色/旧租约/NPC4/错误target/尾随字节/不支持source均拒绝。真实NPC许可、付费Gem结算、人物最终HPMP组合不由这个只读Adapter认证。

方法：diagnosing-bugs沿既有真实RED复现和三假说，确认请求/出参仍用内部4而原本人UI是3；TDD先缺Module红→Bag绿，缺详情Interface红→当前详情绿，再缺query/source Interface红→完整普通投影绿；codebase-design把外部容器与内部归属分别留在有意义的Seam，复用公开资产、Gem、score与原encoder；writing-for-agents把shared替换范围、source字节语义和提交门槛放在步骤旁；code-review独立Standards/Spec固定清单审查结果另存batch。尚未验证shared路由/真实客户端CEquipDialog点击、E648修理组合、历史paid4兼容、部署/加密投递/GUI/容量；全量恢复目标仍active。
