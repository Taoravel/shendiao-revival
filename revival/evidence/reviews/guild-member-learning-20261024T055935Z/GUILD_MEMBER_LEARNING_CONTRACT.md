# 帮派成员生活技能学习契约

读取条件：采用member_learning_policy、处理原c36b6/service121、投递生活技能或恢复学习预留。第26批补个人学习事务、NPC Adapter和当前登录投影；正式政策、shared分发/组织目录与技能效果仍须独立整合，不表示全量社交完成。

## 原依据与采用边界

原指令、控件/表用途和可重复执行详见GUILD_MEMBER_SKILL_NATIVE_RESEARCH.md与verify_guild_member_learning_native.py。十四项bCanStudy生活技能与七项修炼共用原manager+74，和OtherSkills+40不同。SUpdateAssistSkill c36b7为逐项(id,level,proficiency/experience)；原完整c36b5会替换共享容器，生活14子集不能用它发送。原c36b8是NPC Q及完整map<i32,maxlevel>；帮内按钮mode0，目标=current+1，依据服务端已给上限查目标行。

client_verified：service121需要角色至少30并核本帮64位scene；学习按钮先检查个人 人气（outMoneyRP，角色属性0x262），再经验、银两+绑银+存款总额，之后无条件要求银两+绑银至少10000。即使费用3也不豁免；扣前10000不表示扣后保留。存款提示与callback本地完成，wire仍mode0，没有第二个确认位。原target1为经验16/银两3/声望显示1，target155为22060446/695472/155。

原inBG只绑定所需声望显示，inBangGongNeed/inBR业务未知；inSkillLevel仅证明打造熟练条分母，未证明升级门槛/消耗。当前policy必须明确提供字段映射、版本/来源/等级cap，测试采用inBangGongNeed为声望门槛、inBG消费、inBR资源费用、inSkillLevel为打造门槛且熟练保留，全部designed。个人上限取min(研究已到级,显式学习cap)、离帮保留已学技能、货币先绑银再银两最后同角色存款，均为明确本地设计，不声称原server结算。

member_learning_policy默认None。无生产费用/曲线/初始声望采用，无共用currency政策改动。原currency-v1当前不授权bound_silver用于skill_training；测试只显式构造额外授权的CurrencyRules。未授权不能跳过绑银顺序改扣现金。源资料中的“储备金”不自动等于绑银，本实现和UI只使用既有逻辑名bound_silver/cash/depot_cash。正式采用须主策划统一裁定映射和用途。

## 状态与Interface

role_life_skills只管理14项已知完整个人段。initialize需要当前角色事务及显式完整基线/来源；读取缺档拒绝，不能从角色等级/新手章节/曾发空包推断0。个人levels/proficiency独立保存，全角色life revision使并发或不同技能过时许可失效；升级固定+1，熟练不消耗为designed。load_rules只在启动解析原表，采用0..160是本地表支持范围，不宣称原服统一上限。当前研究曲线预算仍最多155，不能据费用表160虚构可达级数。

OrganizationStore/Runtime新增member_learning_policy。life catalog即使学习关闭仍在启动加载，以便已知存档独立登录投影；默认None不创建任何个人技能档。Store.initialize只prepare表，真实新建/历史迁移授权另整合。本批不改task窗口role_skills/OtherSkills、新手授予或任何共享建角路径。

可信OrganizationCommand.reserve_member_learning args=(skill,current_life_revision)进入既有该guild Owner。在同guild事务检查当前成员双代次/研究等级/角色级/已知个人快照/显式cap/熟练门槛，按当前已知声望门槛和资源存量预留；permit记录原角色epoch、deadline、个人版本/技能、费用和冻结规则指纹。声望与guild_resources只由guild写者修改，七项修炼资材账保持独立。common organization receipt、hold与guild revision共同提交，重复原键不重复预留。

角色当前事务调用guild_member_learning.settle(db,Inventory,guild,reservation,now,life_rules,learning_rules,currency_rules,popularity=known)。个人人气由可信角色Owner提供最新已知值，不来自学习包，不把帮派人气或声望代入；未知拒绝。fresh时再核epoch/deadline/成员代次/研究/当前life版本和费用recipe，按原10000门槛检查预算，role_learning_costs统一扣wallet/depot/角色XP，learn_one及role父凭据同事务。它只读guild证明，不修改guild permit/资源/声望。

经验使用既有role_progress，无第二套XP余额。只花费不降级或改变属性/潜能，保留stat growth revision；现有Growth CAS比较完整before（包含XP），旧成长proposal会拒绝。费用journal+wallet子凭据+学习父凭据提供幂等证明；尾SQL/编码失败整个角色事务回滚。余额不足、未知存款或缺XP记录不填0、不部分扣费。

角色返回后以resolve_member_learning args=(reservation,)进入原guild Owner：真实角色父凭据及费用子证明齐全则committed，无支付证明则同事务退款/cancelled；费用证明存在但父凭据缺失为outcome_unknown，保留hold待修，禁止退款或再次收费。取消先持久化则迟到角色提交拒绝。同SQLite Adapter通过共享事务顺序围栏；跨库需要可靠消息协议另实现，不冒称跨库原子。

refund只回原family/member generation的声望行；即使退出重入也不向新代次增发。终末guild允许此恢复命令，退款只归档原guild状态，不复活组织资格。历史成功学习先验源/支付证明，返回当前技能与当前绝对余额，规则关闭/变化后不再扣费；旧NPC有效期/当前资格依然由NPC入口重查。缺凭据/畸形数据明确拒绝。

## NPC与投递

member_learning_npc要求原service121、handler、当前租约/位置/完整MapAddress，以及主集成目录给出的LearningResidence(guild,address,generation,evidence)。该DTO只传可信当前目录结果，不根据模板1394、guild ID或wire Q派生场景身份。prepare后guild等待结束，finish必须重新提供最新NPC证明与目录结果并匹配prepared，位置/实例/目录代次变化拒绝。本模块没有实际目录producer或registry binding；隔离fixture的10076/1394不是正式授权。

open_panel读取已知14个人增量及当前14项可学上限，生成原c36b8。finish编码14当前增量、两个已知wallet余额及当前角色XP，所有编码在提交前完成；用了存款必须有可信precommit回调投影当前库存/存款源，失败整体回滚。回放也读当前值，不用旧receipt等级覆盖以后学习。发送由目标连接Owner完成，本模块不持连接/writer或其他Owner可变对象。

GuildRuntime沿既有登录hook独立恢复14增量，即使七项修炼缺档或学习关闭也不吞已有生活技能。旧/过期学习hold与原practice恢复共用已有有界恢复任务；仅持ID，等待guild前没有持角色Owner，当前同epoch未过期请求不会抢先取消。组织命令仍与本guild其他管理共享串行Owner，未新增全服命令队列。

## 验证与未完成范围

verify_guild_member_learning沿已授权Store/Runtime/角色事务/加密Peer seams，SQL仅用于明确旧档/资金夹具或故障注入。覆盖已知基线/不重置，费用三源/EXP原子，真实预留/结算/确认/退款，晚父凭据和编码回滚，个人RP/版本/研究/钱包门槛，155字面费用，退出重入旧代次，EXP旧成长CAS，孤支付证明，真实登录/重启/学习关闭投影与过期hold恢复，8同guild重复及另一family/加密心跳独立。角色购买与NPC fresh proof在真实事务Adapter验证，尚未注册到main实际RoleOwner或raw请求分发，不把guild运行和登录验证称完整购买运行接线。

原生脚本验证请求、共享辅助容器/完整替换危险、原14上限map、金额/经验/声望显示、30级/64位场景和10000等18边界；UI/config/CRT等Adapter明确，非完整GUI或原服务器结算。正式货币/费用字段采用、当前个人RP读源、目录及NPC/Main RoleOwner接线、技能实际属性/制作/战斗效果、熟练成长、组织任务/活动、跨库/商业容量、真人GUI仍未完成。未改main共享入口/生产政策或操作实际服务、角色、存档/游戏；全量目标持续active。
