# 新角色创建来源与首登普通成长接线

2026-10-23，原始复原集成窗口。仅源码与临时存档必要检查；未部署、未打开客户端、未运行战斗、未修改现场角色。

## 方法与决定

采用codebase-design：AccountStore创建事务保存创建时来源与不可变规则，runtime_storage隐藏首次有效租约兑现、事务与编码校验，RoleOwner通过既有load/role_load_profile Interface获得冻结结果。存储工作者不发送网络消息，无新增全服执行器。diagnosing-bugs仅用于事务/重试反馈；没有黑屏原症状的新运行反馈，不以成长接线解释或宣布修复黑屏。

基线复用主策划AttributeRules.initial_profile及design/role-attributes-v1.json：L1、XP0、自由潜能0、五维各10及100HP/100MP等明确designed，不宣称原版出生平衡。

## 源码行为

- prepare只加载规则和迁移schema，不创建人物基线。role_restoration_origins增加可空creation_profile、creation_profile_receipt；旧三列表逐列迁移，旧行保持NULL。
- prepare后新建角色，在同一创建事务记录完整模板、成长/属性policy及设计来源。依赖残缺或policy不一致则回滚。prepare前角色及旧wallet-only来源不具备成长自动初始化授权。
- load_role有效租约事务首次兑现。模板须匹配准备时规则及来源，人物须仍L1/XP0，且没有成长/属性、任务进度或结算记录；否则拒绝并待核对，不按当前等级补历史点。
- initialize_growth、initialize_attribute_baseline、已知入场五槽及growth_refresh编码校验、模板SHA256兑现凭据同事务。重复加载核对凭据和基础记录存在，不重建资源或重置后来成长。已兑现残缺档不能降级成兼容实验100值。
- 旧角色NULL/无记录保持兼容或已有显式迁移基线；旧钱包origin不等于人物属性来源。入场/首次ACK继续读取当前属性，不用历史奖励回执覆盖伤势。

## 验证与范围

本窗口运行verify_creation_profile_storage.py，通过真实AccountStore/runtime_storage Seam及临时库验证旧schema/旧来源不初始化、模板先保存后兑现、L1/XP0/五维/完整刷新、后来150XP至L2/XP61/free5且伤势80HP/46MP重登保留、重复兑现、旧租约拒绝、首次XP/policy漂移与已兑现残缺拒绝。受控原生编码失败发生在写基线后，成长/属性/凭据一起回滚。证据creation-profile-storage-verification.json。

主策划独立运行verify_new_character_growth.py，证据new-character-growth-verification.json：未用夹具初始化新角色基线，经过Peer认证/入场/首次ACK、可信NPC100192完成、连续原生解码、重建runtime重连，L2/XP61/free5及单份基线/凭据通过；L7/XP42旧角色及旧origin无自动成长。本窗口读取独立结果，未重复运行。trusted offer仍是夹具，未验证自然开场。

verify_growth_runtime的手工基线由主策划调整成prepare前旧角色；本窗口同样把verify_role_consumable_runtime两个夹具移到prepare前创建，并复跑限定药品检查通过。生产围栏未放松；仅guard sentinel，未启动战斗。

未验证：真实人物界面、场景可见/移动、自然主线、旧角色迁移工具、商业数据库与容量。没有部署/监听/GUI，运行进程不视为加载新源码。
