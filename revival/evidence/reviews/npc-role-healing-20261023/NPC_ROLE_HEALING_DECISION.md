# 普通人物治疗294裁定

2026-10-23，主策划。单一配方design/npc-role-healing-v1.json；实现294、人物治疗或添加NPC绑定前读本文及ARCHITECTURE。它补全独立CNpcService入口，不把人物治疗套成客栈、家族声望治疗或复活。

客户端证据见NPC_ROLE_HEALING_NATIVE_RESEARCH：service294经原switch实际构造CNpcService，原标签等级×30；包只含完整NPC key和service，无价格、效果或币种。原配置与摆放进一步读到10380女大夫位于1007/placement34/(1996,3963)。主策划明确设计只给这个现存原实体增加294，标designed关联；不因“医生”名字推原服服务。10009游方郎中没有静态摆放，不凭空生成；10054家族郎中属于1401，另需组织资格，不套本配方。

官方历史家族说明仅支持家族郎中功能，未给294的服务器效果或复活规则（见研究报告）。本轮另核[2012官方装备资料](https://sdxl.wanmei.com/info/intro/20120623/131855.shtml)，NPC与家族修理费用属于不同用途，不能据“金钱”一词给人物治疗通用绑银权限。294完整效果仍未知，按用户授权设计：当前生命大于0时补满实际最终HP/MP；现金费用为本事务内权威人物等级×30。满资源新请求拒绝、不收费；死亡拒绝、不复活。伤势、活力、宠物、耐久、经验、章节均不改变。原×30标签证据与现金/效果/满状态/死亡处理的设计分别标注。

第一片只接受已明确初始化/迁移的无伤势资源profile，核真实当前装备/成长source；缺来源拒绝，不以兼容显示100当满血，也不在治疗时自动迁移。权威普通等级限制1..155，特殊1001段不减1000猜映射。新增独立npc_heal cause，cash独立npc_role_heal用途；既有resource.1/currency.1版本和原已付记录保持。该cause只是数值层允许值，不赋予NPC资格或收费权限，NPC Module仍验证当前ticket/角色活跃/非战斗/非交接及现存实体。

费用、唯一资源carrier、领域与共用凭据、最终原生投影预编码同一角色事务，任何晚期异常整体回滚。已受理同ID的paid分支先核历史意图，严格读取当前资产/余额；不受后来满血检查阻断，不再治疗或按后来等级重算费用。新的相同线包有新内部身份，仍需当前资格和缺失量；重放旧治疗不能抹掉后来的伤害。数值因果/费用不能从可伪造线字段生成。

NPC窗口负责所属294资格/领域handler，root负责独立资源cause与货币用途；共享CNpcService路由由主集成在当前mode1最小发布之后接。先在公开实际NPC Interface建立红→绿，验证cash扣30、70/40至当前caps、满状态不扣、死亡/旧租约/未知source拒绝，晚编码失败整笔回滚及同失败ID成功，paid保留后来资源。原其他治疗service不扩权，原家族和特殊修理仍独立恢复。

方法：codebase-design将NPC资格/费用效果留在NPC Module、最终资源校验留在已有公开事务Seam，避免新生命账本或全服执行器；writing-for-agents将原证据、明确设计、调用方事务与完成标准共置。root公开数值Seam用tdd：verify_role_resource_healing首先因不支持npc_heal真实red，配置及启动loader最小增加cause后推进到cash用途拒绝的第二red，再仅增npc_role_heal转绿。实际临时事务70/40→100/100、现金1000→970/绑银500不变、真实最终投影后晚错全回滚/同键再成功、paid保留后来80/60/version2和970、旧租约/旧before/绑银费用/复活拒绝。原verify_role_resource_plan/storage及verify_currency必要回归绿。数值/费用接缝绿不证明294资格、满资源免收费、NPC领域/shared/发布/GUI；后者由所属Module继续验证。root不操作真实角色或服务。
