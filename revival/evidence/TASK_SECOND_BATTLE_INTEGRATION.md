# 首次教学后的第二战：Task 接口交单

2026-10-24。按角色成长恢复，沿原 `100179→100190→100161` 等十族、43条路线推进。用户要求少量必要检查；本批通过后即交main集成，不启动多轮或重复父层复核。当前已发布053218首战/教学保持原样；以下第二战接口尚未接入运行服。

## 采用与范围

唯一第二战政策是 `design/task-pve-ai8027-v1.json`，SHA256 `7bbef4665a11366718fee6c2d465902286fa0b7f7adec1e138fac84f2e65ba59`，主策已接受设计；不从相同AI推能力。新生产文件仅 `task_first_skill_proof.py`、`task_second_battle.py`，没有修改已发布Task、角色技能账本、main共享入口、engine或存储代码，无新表。

`codebase-design`：将教学收据解释留在Task自己的纯读Module，第二战调用该Interface，不让main读取Task私表。`tdd`：使用同一公开读/菜单/准入Seam，逐个真实缺接口红→实现绿；沿自然流程到已完成教学，不手插completed。用户已有“先批量恢复、不过度复核”的指令优先，不再为确认测试范围暂停。

## main 的接入顺序

1. 启动加载 `load_second_battle_rules(resources, first_skill_rules, second_registry, placements, *, path=...)`。`second_registry` 由实际已实现的AI8027 engine提供，仅启十个精确任务；旧AI8001 registry/revision保留。默认空registry仍不能打开第二战。
2. 当前角色Owner提供正常状态0、本人已采用私有1501位置、MapOwner新的10908/placement10证明、连接generation和地图投影generation，调用 `open_second_battle_transaction(db, aid, rid, epoch, resources, rules, task_id, proof, current, *, generation, map_generation, now_ms, deadline_ms, movement_state)`。返回 `.ticket/.messages/.skills`；`.skills`是完整当前技能map，不授技能、不发奖、不改Task。菜单仅原SVisitNpc；共享方先同步原active0 bean。
3. 原12字节C请求仍经 `decode_task_battle_request`。main从实际装备、资源、完整技能来源构造Participant，授权能力仅 `(100008,)`，与完整已学map分开；调用 `admit_second_battle_transaction(db, aid, rid, epoch, resources, rules, ticket, request, fresh_proof, current, participant, battle_id, *, generation, map_generation, now_ms, movement_state)`。返回原 `TaskBattleAdmission`。
4. 在同一事务保存main自己的实际战斗入场记录及完整来源，并**绑定整个SecondBattleTicket**，包括 `.teaching_fingerprint/.skills_fingerprint`；只保存里面的generic `.battle_ticket`会遗漏第二战资格来源。generic TaskBattle原plan/表未扩字段。提交成功后才启动真正AI8027；`.replayed`不能启动第二场。
5. 原有准入/终态恢复接口保持；恢复按原admission的recipe/revision选registry，不能拿新registry覆盖旧8001。main新producer、资源CAS、唯一consumer/outbox及第二战255XP/SMoney600仍由main接实际终态。获胜后只激活原CG10001节点，原电影与下一战不能由此跳过。

公开教学证明可单独用：`read_completed_first_skill_proof(db, aid, rid, epoch, resources, first_skill_rules, teaching_task_id)`。返回 `.task_id/.chapter_id/.operation_id/.fingerprint/.predecessor/.source_address/.skills`。当前租约只授权读取，保留历史教学epoch；不会重放旧ticket、补账或奖励。它核原创建路线、首战胜利、教学ticket/grant/Task命令与effect、120XP及零道具/宠物渠道，读取完整当前技能，保留合法后续高值。

## 本批必要证据

命令：`python -B -X utf8 revival/verify_task_second_battle.py --source revival/runtime/deployments/task-pve-20261024T053218Z/source --report revival/evidence/task-second-battle-verification.json`。

实际通过：053218准确BASE；一次性临时库按旧创建配置自然创建，首战真实engine胜利后完成教学；公开教学读与第二战菜单由SQL authorizer确认只读；43路线/十任务及101004反例；坏grant/前驱/XP收据和未知技能拒绝；提交时地图代/教学/完整技能版本复核；原12字节提交绑定实际装备属性Participant，100008高值7保留；同准入幂等、竞争菜单拒绝及全库外层回滚。只执行一次必要通过链后交付；此前缺接口红和一次FencedConnection测试Adapter修正另列机器交单。

限制：AI8027 registry是明确Task契约fixture，未执行新第二战engine、双目标技能、实际HP/MP扣除或新producer/consumer；实际首战数值来自装备投影，但attribute_version是显式测试见证。原脚本中首战resource/outbox消费者未验，主集成已有的真实检查不在本批重复。新租约整场恢复、CG10001、发布及GUI仍由后续实际接线证明。当前真人角色、客户端和在线服务均未操作。
