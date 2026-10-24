# 新创建角色的明确资源授权

2026-10-23，主策划裁定。实现真实创建、首次加载资源兑现或未来开启新建profile前读本文。单一政策为`design/role-resource-creation-v1.json`，基于已有ROLE_RESOURCE_STORAGE_INTEGRATION与RESOURCE_SHARED_RUNTIME_INTEGRATION；共享文件仍由原始集成窗口修改。本批授权实现和隔离库验证，**自动激活及部署保持关闭**。

## 来源与适用角色

已有format1创建模板明确给出人物初始五维、属性与已知满资源；这是designed模板，不是对原服出生数值的断言。现有new_restoration_role字段只授权原钱包和人物创建合同，不能因升级代码成为资源转交许可。新的资源许可必须在真实建角事务中单独持久；没有许可的历史角色沿原合同，等级1、零经验或未登录均不构成授权。

本政策只绑定现有growth .1、attributes .1、equipment .1及resources .1。装备封印强度0为既有新建设计；封印抗性仍为null/未知，保持v1合同，不借本政策启用普通六槽v2。v2角色路由与基线属于后续独立政策。

## 创建时记录

启动统一建表`role_resource_creation_authorizations(role_id INTEGER PRIMARY KEY REFERENCES roles(id), authorization TEXT NOT NULL)`并冻结加载政策。真实AccountStore.create_role在同一创建事务完成角色、原format1创建模板、新手creation_id之后，仅当明确新建资源开关开启时插入许可。默认开关false，配置已加载不代表开启。

许可为政策列明的精确字段，拒绝遗漏、额外字段或错误类型：format=1、policy为本政策revision、真实account_id/role_id、原新手creation_id、四项冻结policy、seal_strength=0、seal_resistance=null，以及creation_profile_fingerprint。指纹是数据库实际creation_profile原字符串UTF-8的SHA256，不从后来重新序列化的对象猜测。许可统一`json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)`保存；稳定migration_id为`'resource-creation:'+sha256(authorization.encode('utf-8')).hexdigest()`。

创建记录之前核对同db角色归属、等级1/经验0、匹配新手creation_id、原format1模板及准确规则；尚无lease、growth/attributes/resource profile、task章节状态或奖励。实际调用必须处于可信新建事务；这些防护不将任意旧的休眠新建记录变成可以事后补授权的入口。许可不含客户端可控开关、当前HP/MP或新的一本资源账，也不在登录时补写。任一晚期失败与角色和创建来源整体回滚。

## 首次兑现与已付读取

load_role使用原有当前lease调用方事务，在原人物模板、章节与v1装备basis初始化后读取许可；缺许可直接保持旧合同。存在许可时先核对归属、精确字段、四policy、原创建字符串及其兑现receipt、新手creation_id，以及对应原形象的v1 basis（revision0/强度0/抗性未知/原newbie-creation来源）。策略或身份错误明确拒绝，不降级成缺许可。

首次兑现还须证明是未推进的新建状态：真实growth仍为初始L1/XP0/revision0、基线与模板一致，实际InventorySnapshot revision0且物品/宠物均空。读取实际已初始化VitalState并与该角色initial_profile.vitals(role_id)完整相等；存在后来伤势、成长或资产时拒绝并保留数据，交显式核对。用真实current_equipment_totals计算final caps，再调用migrate_role_resources(origin='new_restoration_role',migration_id=上述稳定键)，严格组合当前profile并真实原生预编码，最后统一提交。禁止另开连接提交或在普通reader做治疗。

已有resource profile时，先核对其origin确为new_restoration_role、migration_id精确对应当前许可、resource policy一致，再严格读取当前profile。此分支允许后来成长、资产、伤势和死亡，不重新用出生caps或当前伤势重建初始化意图；不得再调用初始裸身reader。许可和创建来源始终不可变，当前来源不匹配应拒绝而不是借加载补source。

## 可判定验收

在临时库用真实create_role、当前租约和load/Owner公开Interface验证：开关关时新旧角色均无许可/无自动资源；测试显式开启后只有新建带许可，历史format1来源不追补；首次加载初始化且能接原intro/card/穿戴/嘉兴成长。重复加载与新租约返回后来资源/死亡，不能恢复出生满值。

真实末端原生编码失败须回滚此次属性/章节/basis/资源兑现及初始化凭据；同许可重试一次成功。原创建末端失败不能遗留角色或许可。许可被改account/role/creation_id/模板指纹/任一policy、半套依赖、未知抗性、stale lease或pending source均拒绝而不写库。已付读取可加SQLite禁写authorizer验证，但不要将首次加载其他既有钱包/章节的幂等调用误称整个load零写。

完成repair/pet实际Owner验收、秘籍稳定可信draw/时间及全部可用资产消费者核对之后，才由主策划依据这些结果决定开关；仍不得自动迁移现场旧角色或重启服务。本政策存在不构成这项完成声明。

方法：codebase-design把授权放在真实创建事务、兑现放在既有角色调用方事务Seam，读取仅组合最终profile；writing-for-agents将新旧角色、fresh/paid及激活判据共置。已核对四规则revision与当前JSON一致；本批仅政策和交单，无共享实现、GUI、真实库或战斗验证。
