# 首次太祖长拳：角色账本与任务事务候选

2026-10-24。集成建角、登录或十个教学任务前，读中央 `design/newbie-first-skill-v1.json` / `NEWBIE_FIRST_SKILL_DECISION.md`。当前独立Module未接shared，正式AI8001与其后战斗注册表仍为空；临时任务终局契约不证明实际战斗或生产可达。

## 所有权和真实接线

任务窗口单写 `role_skills.py`、`task_first_skill.py` 与对应TaskDomain窄事件。main单写accounts建角/登录/共享分发；World和战斗持有各自状态。全部热路径接受已有调用方事务，无connect/commit/send、DDL或配置读取。最终消息必须在同一事务内全部编码，提交后才由当前连接发布。

1. startup调用 `prepare_other_skill_storage`、`prepare_first_skill_storage` 和既有battle/story准备；`load_first_skill_rules(resources,chapter,story,placements)` 冻结中央设计、原10节点/43路线和技能三表。新表不会给任何旧角色补空技能。
2. main真实建角事务刚INSERT角色、尚未写position/lease时显式调用 `authorize_new_role_other_skills(db,aid,rid,creation_id,rules.skills)`。这是创建调用方授权，已存在chapter或new_restoration_role不代替它。调用必须与角色INSERT在同一事务；创建失败一并回滚。现有accounts尚未接此调用。
3. 历史角色纯读 `read_other_skills` 返回None即未知，既不发空包也不准授予。只有独立核验完整class6基线后，可信迁移调用方传 `VerifiedOtherSkillBaseline(entries,verification_id,evidence_sha256)` 到 `adopt_verified_other_skills`。输入须完整，不能用任务文案、等级、原先发过空包或缺记录推断。该Interface不扫描/推断历史技能、不替用户作基线裁定。
4. 原AI8001任务真正结算后，同一角色outer transaction调用 `reconcile_first_skill_successor_transaction(...,previous_task_id)`。只凭真实task battle专用凭据、原路线和本人adopted私有1501目录激活原教学任务；此时不授技能、不扣费。generic TaskChain继续不自动开启本族。
5. 当前角色在原10908/placement10交互后调用 `open_first_skill_transaction`，冻结任务/技能revision、完整Location、连接和地图generation、NPCkey及1000/300000ms许可，返回原ready3刷新和菜单。RoleOwner持有唯一pending ticket，移动、其他菜单、传送、战斗、断线即撤销；调用前保证非其他种类战斗/传送。地图返回新证明，不能用客户端任意key制造权限。1秒/5分钟是designed，原ProcessBarTime1绝对时间单位仍未知。
6. 原CCommit(task,NPCkey,option0)交 `complete_first_skill_transaction`；fresh核同一个ticket、当前NPC证明/完整checkpoint、私有目录、原前驱、任务/技能revision及期限。通过公开 `grant_other_skill(...expected_revision=...)` CAS保留所有旧key和max(原100008,1)，共同TaskWorkflow结原120人物XP/其余零，再只激活原唯一type40后继active0，登记唯一教学receipt。免费不扣币、不改背包revision、不使用训练技能公式，不推进后继战斗。
7. same accepted ticket/command的paid在receipt后只读当前完整skills、当前XP/成长资源；不重授、加revision、结奖励、激活后继或回放state1/Finish。后来合法学习的值均保留。旧epoch ticket拒绝，新租约登录使用当前角色租约纯读ledger，再 `other_skill_messages` 发当前完整快照。

## 技能命名空间和失败恢复

`role_other_skills`只管原class6的26个身份，不代表所有技能系统。部分原class6身份没有cskillitem/showlistclient显示行，仍按原class6列表保留，不把它们当战斗定义。玩家100008在三表核对；class4的600005未进入此表或SSendOtherSkills，缺失也不表示该技能等级0。

`OtherSkillsSnapshot`为冻结完整map与revision，`grant_other_skill`无第二套任务结算receipt，唯一授予操作由task_first_skills持有。未知/重复/布尔/非正或超signed32/非class6基线拒绝。已有100008高值不降级，原120XP任务仍正常完成。后继保持原任务字面值，不插入旧1010xx族。

原SSendOtherSkills消费者会删除包里缺失的旧key，flag1也一样。因此始终复用既有 `battle_protocol.other_skills` 编码完整已知map；flag1只按设计抑制可选快捷栏默认放置。传送/网络发送在SQL外；提交后发送失败关闭旧连接，新租约重读当前权威，不回放旧grant值或120XP。没有shared创建授权的旧角色会保持未知，需要独立完整基线核验；不得为让旧存档前进假填空。

## 方法、验证和未验

codebase-design把完整技能基线/修订/CAS集中到角色Module，教学许可与唯一凭据留任务Module，沿用原codec和TaskChain公开方法。research原客户端三表/原生完整替换消费及端游官方来源保留，授予数值/时点采用中央designed规则；writing-for-agents把调用顺序、所有权和失败恢复与Interface共置。未启用test-first流程或大规模重复验证。

必要检查由 `verify_task_first_skill.py` 临时DB/原公开角色任务Interface完成：新建授权及创建回滚、历史未知负例、两条原路线、人工终局经真实admit/settle、原奖励和技能保留、晚期SQL/原生编码全表回滚、paid后来学习/成长SQL authorizer禁DML及重登旧epoch拒绝。临时trigger只在离线临时连接的BEGIN前安装，玩法调用仍用FencedConnection；NPC距离32px为明示fixture。真实AI、shared接线/准确发布、网络发送故障和GUI尚未验。原生技能消费者单独报告，不能由Python包自洽推断通过。

原生反馈：本批实际教学包与后来paid包均经过 `research_other_skill_snapshot.native_other_skills` 的原decoder→Process→consumer，另有故意漏旧key的真删除敏感性。脚本/原地址/映像SHA及flag0边界见 [OTHER_SKILL_SNAPSHOT_NATIVE_RESEARCH.md](OTHER_SKILL_SNAPSHOT_NATIVE_RESEARCH.md)。这项证明完整替换的包语义，不证明GUI或实际技能可战斗。
