# Task PVE shared core：Spec 预审

Missing/partial：0；Extra：0；Wrong：1（P2，未修）。仅审固定050244937564候选七项core相对repair023920；非Git，使用固定文件no-index差异与SHA，不存在commit列表。

**P2 已付重试仍依赖原参战宠存续。** accepted task-pve-ai8001-v1:63要求“Same-key retry reads current state”；TASK_TERMINAL_RECOVERY_DECISION:7要求成功consumer回执重试只读当前。task_pve_runtime_storage.py:477–486的settled分支调用`_committed`，其:442–445在原参战宠已放生时仍抛错。可判定公开Interface反例：带真实OwnedPet完成并成功settle→合法休息/放生原宠→同battle_id调用paid public settle；Inventory.read_pet_state:1403–1415明确对released返回None，故即使所有奖励/回执一致也无法返回当前结果。此为静态反例，未声称wire可触发或重复奖励。paid应省略已不存续的旧宠刷新；fresh消费须继续严格CAS，不可因此放宽。

其余：game_runtime:1198–1244将原12字节请求经当前NPC/地图证明、真实Participant和持久admission接到专用engine；无Training/Wild假胜。runtime_storage启动冻结依赖；accounts只在真实建角事务授权空技能。runtime storage:70–143、203–227重读完整角色/资产/技能/任务/章节/目录来源；:255–322先落producer，:452–586保留原epoch并以完整basis/CAS在同consumer事务消费raw资源、专用复活、Task奖励/后继和settled标记。教学不在战斗中grant。固定notice经当前请求连接回复，无广播。

方法：沿用完整code-review/codebase-design及已读ARCH/DESIGN/accepted engine/Task政策，检查Interface、所有权与原子/重试场景；未读另一轴。已知compat r1 P2不重报，最终换已接受r2后仍须差异复核。

manifest SHA256=16ded94bdd79aa7b73868c1ba9736d21800f843df9174ab581407fe43ad7ff21；全部1454 source登记项审前后匹配。七core SHA前缀：accounts274775fb5f60、game_runtime d7ad6871c52c、runtime_storage990e2c74b387、role_resource_storage8cb585c88ff5、task_dream_resources4cd6a9ab2d1d、task_pve_runtime_storage58a6c6cbce86、task_pve_recovery f17074484f53（完整值由manifest绑定）。

未验：仅静态，未运行测试/DB/socket/服务/GUI；现有自然win/recovery/notice证据不替代source drift/宠物全链/最终exact验收。本报告为预审，不给发布许可。
