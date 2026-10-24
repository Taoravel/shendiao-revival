# 本地旧序章角色：OtherSkills 完整基线研究

2026-10-24。P0 只读、有界研究；仅新增本文。未读取任何真人 DB（含发布备份）、客户端、运行服务或战斗，未修改实现、裁定、发布清单。调用方提供“role4 已到100107”作为问题背景，本批未核其真实存档，不能据本文宣称该角色符合迁移条件。

## 结论

**未取得 `client_verified` 的真人完整 OtherSkills 基线。** 原生管理器 `+40` 的支持身份为 `100007/100008/100009/310202/700004`，这些身份属于同一完整替换包，不意味着每个角色已学或未学。当前与已保存历史发布代码未提供旧角色完整技能保存/授予/同步的独立历史凭据。缺功能、缺新 ledger、处于100107、过去可能发过空包，都不能证明完整空 map。

可判定的本地来源是“可信建角流程记录了独立 creation/chapter/route”。它能作为**待根裁定的 designed 旧序章迁移资格之一**，不能直接传给现有 `VerifiedOtherSkillBaseline` 假称已验证完整空技能。建议契约见下文；本代理不审批、启用或执行它。

## 方法及范围

已重读 research 技能、ARCHITECTURE、DESIGN_AUTHORITY、r3 `role_skills.py`、NEWBIE_FIRST_SKILL_DECISION。research 明确要求后台研究；本代理作为根任务委派的后台研究者，根任务并行推进，无重复委派。方法用于追到原始发布源码、实际调用与发布 hash，分开“源码能力”与“某角色实际历史”。架构决定：来源判定、迁移 receipt、完整技能写入应位于角色所有者的同一调用方事务。

范围：`runtime/deployments/` 下现有26份直接 `source`，按 `(文件名,SHA256)` 去重的268份非研究/测试 Python；只读直接 `.py`，排除 verify/research/audit/inspect/diagnose/dump/probe/test 前缀及 probe 文件，不递归扫描资产/数据库。检索 `other_skills/OTHER_SKILLS/0xc36c3` 及五身份；另重点读建角、章节、任务 receipt 与候选 ledger。静态检索未证明动态代码、未保存版本、手工迁移或外部工具不存在。

## S1：发布 BASE 与建角实际能力

BASE：[npc-repair-20261024T023920Z/source/accounts.py](../runtime/deployments/npc-repair-20261024T023920Z/source/accounts.py) SHA `2f9022a4b40aaecffbd2bb57491f8f1678980e4a6405f8fc28e78d0099db34ff`。

- `create_role` 行65..101：同一 `BEGIN IMMEDIATE` 下 INSERT roles；规则存在时写 `role_restoration_origins` 的成长设计 profile；规则存在时调 `record_newbie_creation`，再插 position/version。没有完整技能表、创建技能授权调用或技能同步。
- `new_restoration_role` 的 `creation_profile` 仅记录角色成长/属性设计来源，不含五身份完整技能 map。不能把该标签当空技能证据。
- [task_newbie_chapter.py](../runtime/deployments/npc-repair-20261024T023920Z/source/task_newbie_chapter.py) SHA `35bd78e73b84863a77872313f54df84150d9a720e7c794ab9ff05e2de6ba7095`：行171起创建 Interface 核本人所有权、level1、无 lease/position/journal/offers、合法冻结角色/门派路线；记录 creation_id、chapter_id、policy、route 及指纹。行160起读取还核路线一致；行205起章节初始化缺独立 origin 则不推断 legacy。
- 这些创建约束能证明“由受信调用方按该本地流程授权创建章节”的数据结构和检查能力；本批没有读取某个角色的记录，也没有证明历史 DB 从未导入/手工更改。章节 `completed` 指开场播放章节，不等于完成太祖长拳教学。
- [battle_protocol.py](../runtime/deployments/npc-repair-20261024T023920Z/source/battle_protocol.py) 行21、41：只定义 `OTHER_SKILLS=0xc36c3` 及 encoder。BASE 非研究生产源码无调用命中，不能把 encoder 的默认 flag1 当已同步记录。

BASE [manifest.json](../runtime/deployments/npc-repair-20261024T023920Z/manifest.json) SHA `b4ad84e07328110ecedaf753be126c4c19d3f58eadac2f0a700f1dea699eb367`；本批实际重算 accounts、task_newbie_chapter、battle_protocol、gateway、runtime_storage 五文件，均与 manifest 的 `sha256` 一致。发布 [deployment-verification.json](../runtime/deployments/npc-repair-20261024T023920Z/deployment-verification.json) 声明 source_frozen、preexisting_rows_unchanged、无 role/task rewrite；这只是该次发布保存的检查结果，不证明全部历史角色状态完整。

## S2：保存的历史发布差异

26份直接 source 都不含 `role_skills.py` / `task_first_skill.py`。268份去重源码检索只命中以下两版 battle_protocol 的常量/函数定义，无五身份 literal、OtherSkills 实际发送/授予调用：

| 保存版本 | 证据 |
|---|---|
| 20261023T054401Z | accounts SHA `ecfceca95281acfb0996cb67943a46d2d4d77130584f322ee028d631ce0fb4ba`；battle_protocol SHA `dca9640e8f8a1dad9aab5a2b2ea4fe86dba4a7246a6b5311097d020ba0df75dd`，行20常量/31 encoder |
| 其余25份，包含 BASE | accounts 均为 S1 的 `2f9022…`；其中 battle_protocol 后版 SHA `1a472edf4f1a9db20d8c08ba05eb5516b56b723b87b2b2c80ca0c0a60c75cd22`，行21常量/41 encoder |

最早两版 accounts 实际 diff 只有删除生命周期、过滤已删除角色、租约拒绝删除角色等变化；建角段没有技能授权新增。最早 [deployment-verification.json](../runtime/deployments/20261023T054401Z/deployment-verification.json) 保存 startup hash，与最早 accounts/battle_protocol 内容一致。后续 BASE 的 previous-deployment startup hash 也记录相同 accounts。未对全部26份发布作全量完整性或运行路径验收。

因此可以说“已保存的这些源码没有提供该历史技能能力/调用证据”，不能推出“角色从未在其他版本、工具、导入或手工流程获得五身份”。尤其不能因为新 ledger 后加，拿其缺行覆盖旧状态。

## S3：现有 r3 接口与缺项

冻结 [r3 role_skills.py](./reviews/task-first-skill-20261024-r3/source/role_skills.py) 明确 `read_other_skills=None` 为 unknown；新建空授权要求真实本次建角事务；历史 adopt 要求完整 `VerifiedOtherSkillBaseline`，不读 chapter 标签作技能授权。`grant_other_skill` 要已知完整基线与 revision，取 `max(old,value)`，`other_skill_messages` 发完整 map。

[NEWBIE_FIRST_SKILL_DECISION.md](./NEWBIE_FIRST_SKILL_DECISION.md) 明确禁止旧来源/缺记录推空，当前100008/value1授予与120XP结算仍须真实前驱及教学许可。原消费者删除未发送旧 key，见 [OTHER_SKILL_SNAPSHOT_NATIVE_RESEARCH.md](./OTHER_SKILL_SNAPSHOT_NATIVE_RESEARCH.md) 和 [QINGGONG_LEARNING_STATE_NATIVE_RESEARCH.md](./QINGGONG_LEARNING_STATE_NATIVE_RESEARCH.md)。本批无新增 native 执行。

旧 BASE 有 `task_journal`、`task_command_receipts`、`task_effects`、`task_reward_channels`、`role_settlements`；源码见 [task_persistence.py](../runtime/deployments/npc-repair-20261024T023920Z/source/task_persistence.py)、[task_rewards.py](../runtime/deployments/npc-repair-20261024T023920Z/source/task_rewards.py)。它们可支持今后同事务核真实任务进度/已付奖励，但不是 OtherSkills 全量历史。未完成教学且无教学 receipt 不能单独证明另四身份都未学。

## 建议：最小 designed 本地旧序章迁移契约（未批准）

1. **独立政策来源**：由根主策划明确批准、固定 revision 与允许 cohort，显式标 `designed_local_prologue_baseline`。若设计采用本地旧序章初始空 map，应写明这是兼容迁移设计，不是 client_verified 历史事实；不要伪造 `VerifiedOtherSkillBaseline(entries=())` 的来源标签。
2. **本人可信建角/章节**：当前 RoleOwner 核 account/role/login_epoch；必须有一致 creation_id/chapter_id/原路线指纹及本地受信创建来源。孤立 new_restoration_role、客户端 intro 标志、level1、缺表/缺行均不够。导入、来源断裂、手工恢复无法核验时拒绝该迁移，另行取得完整基线。
3. **严格首技前 cohort**：核本路线原路径，当前任务阶段仍在冻结首技前允许节点；允许角色正常成长，不要求现等级仍1。检查完整 journal 与现有任务/奖励/教学凭据，没有该路线首技或其后继已完成/已付证据，无矛盾或跨路线状态。100107 只能作为路线上的阶段条件，不能凭 ID 一项放行；AI8001 的正式前驱授权仍按原合同独立核验。
4. **已有完整账本绝不覆盖**：若存在可验证完整 map，直接保留全部合法五身份 key/value 和 revision，不重新初始化；100008 高值保留。外来/未知身份、部分 map、无法证明完整的历史输入一律拒绝，不静默过滤。absence 只进入该显式设计资格检查，不自动变空。
5. **唯一基线迁移 receipt**：以稳定 `(role_id, policy_revision)` 或等效唯一迁移 ID 保存来源 evidence hash、creation/chapter、冻结资格/原 revision 指纹与决定后的完整 map hash。同 ID 相同 intent 重试返回既有迁移；不同 intent 冲突拒绝。它只证明基线迁移，不制造第二个教学结算 authority。
6. **同事务**：在一个角色调用方事务内重核资格/CAS、插完整基线及迁移 receipt；如与首次合法教学一起执行，技能 grant、原120XP、任务推进、唯一教学 receipt 和消息编码同事务。晚期失败全部回滚；无独立 commit/send、热路径DDL或客户端输入授权。
7. **不补历史奖励**：迁移不改既有经验/等级/货币/物品/任务完成；不重放历史120XP，不补已越过教学的角色、不替造AI8001胜利。完整当前快照只能提交后发送，断线重登重读当前状态。必要验收只覆盖资格拒绝、已知值保留、receipt幂等与事务回滚。

以上需要根裁定及 ledger/接入方独立实现；本文没有绕过当前 unknown 拒绝规则。未验证真人 role4 资格、完整现有技能、实际学习/技能使用、共享接线、发布、GUI或真实战斗。
