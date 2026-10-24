# 当前本地角色：首次教学时登记设计基线

2026-10-24。仅采用主策 `design/local-prologue-other-skills-baseline-v1.json` / `LOCAL_PROLOGUE_SKILL_BASELINE_DECISION.md`，固定候选 `reviews/local-prologue-first-skill-20261024-r2/source`。这是一项明确designed兼容规则，不宣称旧角色历史技能为空；原VerifiedOtherSkillBaseline仍只表示独立核实的完整历史基线。

## main实际接线

1. startup继续 `prepare_other_skill_storage(db)`，现同时准备空的 `role_other_skill_baseline_migrations`；原 `prepare_first_skill_storage` 不变。显式冻结 `load_local_prologue_baseline_rules(path,attribute_rules=...,growth_rules=...,currency_rules=...)`。返回值包含独立政策/证据SHA、原任务对、真实建角profile契约和币种映射；本调用不登记任何角色。
2. main实际新建角色仍沿原INSERT事务 `authorize_new_role_other_skills`；已有完整账本全部保留。登录只读当前完整map，UNKNOWN不发空包。兼容登记不在登录、startup、首战或NPC访问执行。
3. NPC教学访问调用原 `open_first_skill_transaction(...,baseline_policy=frozen_policy)`。UNKNOWN只在通过本人creation/chapter/route、真前驱胜利、精确已采用私有目录/当前NPC/当前教学active及完整前缀证据审计后，获得 `skill_revision=None`、`baseline_eligibility=SHA` 的只读ticket；不会预填revision0或插ledger。主集成仍管理当前连接/地图代和移动/菜单/战斗/传送/断线撤票。
4. 原CCommit交 `complete_first_skill_transaction(...,baseline_policy=frozen_policy)`。Task重新核当前票据、最短1000ms/期限、NPC/精确checkpoint和完整cohort来源，与opening冻结SHA一致后才构造 `LocalPrologueBaselinePermit`。Role技能公开 `enroll_local_prologue_other_skills` 在同caller事务插独立designed-origin完整空起点及唯一迁移receipt；随后正常max授100008/value1、原120XP、原后继100190等active0、教学receipt与完整消息编码同时提交。任何晚期错误一起rollback。
5. 已有完整ledger走原r3路径，不迁移、不覆盖；malformed/foreign/未知来源不被清理或过滤。已迁移receipt先读，跨新租约仍只返回当前值并保留原accepted epoch。已付教学沿原current-only路径，不重新套cohort、发120XP、重置技能或播放state1。原known票据编码去掉新字段None，保持已审r3表示。

## 完整来源审计与r2修正

Task实际读取本人一致的建角文档、普通成长/属性policy、原选定intro及到首技前所有已完成节点、唯一教学active、command/effect/reward/教学和相关资产收据；断裂、已付教学、后续或跨路线矛盾拒绝。原前驱仍通过真实TaskBattle唯一胜利凭据验证，private目录仍通过World公开读取核本人地址。

r1 Spec P2指出缺前缀奖励通道或JSON null可能漏检，已分别实际跑红。r2经现有公开 `plan_task_reward` 核原源指纹，并要求每个前缀应有的XP、空物品、原零宠奖及对应币种通道齐全，receipt字段、原task/channel/金额/决策摘要一致；缺损只拒绝，不补发历史奖励。当前43路线首技前共113原节点均无物品、非SMoney货币或宠奖，空catalog只用于来源指纹验证，不授权新发物品。已知整包技能语义仍是原manager+40五身份，不涉及轻功/坐骑其他容器。

## 本批证据与边界

`verify_local_prologue_teaching.py --source runtime/deployments/npc-repair-20261024T023920Z/source --report evidence/local-prologue-teaching-verification.json` 将明确Task层和政策先复制冻结，再导入准确旧BASE：自然建角/intro/武器/车夫/嘉兴/血印→本人private1501→原NPC准入→真实TaskPveBattle原指令/播放ACK胜利→Task原终态凭据→UNKNOWN教学→设计登记/1000081/120XP/100190。bad creation、缺命令、已付教学、缺政策及两种损坏前缀奖励拒绝；真实late SQLite教学receipt失败回滚到UNKNOWN；后来合法学习/成长后paid SQL-authorizer禁DML且完整当前消息一致。

该检查的属性版本是显式snapshot witness，battle资源/outbox消费者由main另一准确候选验证，不能把此Task纵切称共享完整接入。`verify_local_prologue_skill_baseline.py` 另验同/新租约原receipt/后来7级技能纯读不重置；原 `verify_task_first_skill.py` 八组known完整基线/高值/原native完整消费者回归通过，其历史角色测试明确选择旧创建配置，不删除新创建授权ledger。

固定r1/r2双轴各自保留：Standards硬0、继承非阻断schema耦合建议1；r1 Spec P2在r2闭合、当前未解决0。该建议不加发布门：后续可由资产/钱包所属Module提供公开只读收据证据，现不泛化重构。

方法：TDD沿预定公开ledger/教学caller事务完成缺接口与UNKNOWN自然链红绿；diagnosing-bugs将审查缺口变成两个真实损坏源反馈；codebase-design将cohort留Task、完整技能与唯一登记留角色Module；code-review独立规范/规格；writing-for-agents共置入口、来源、完成标准。未读真人role4资格、未改在线服/当前客户端；准确shared/发布/GUI由main/root单独证明。10019演示CG与下一战AI8027不因本候选自动恢复。
