# 暗雷实际接入：本窗口直接授权

2026-10-23。用户在怪物/活动窗口直接要求「那你接入啊」。收到原始复原窗口关于共享入口冻结的通知后，本窗口已保留全部现有源码，没有回退；向用户说明共享冻结和原始窗口要求交接，并询问归属。

用户选择原文：「由本窗口完成接入」。因此按AGENTS「用户当前指令优先」，本窗口负责本批暗雷局部共享接线与验证，继续完成实际入口；没有获准向其他聊天发消息，不通过跨聊天工具转发用户内容。

本批局部涉及game_runtime.py、runtime_storage.py、battle_owner.py、wild_battle.py、wild_rewards.py、role_resource_plan.py、role_resource_storage.py和新wild_runtime_storage.py。未回退其他窗口功能；已由本窗口发布最终暗雷，准确时间/PID/备份/验证见WILD_RUNTIME_INTEGRATION实际发布。每次修改与验证结果在WILD_RUNTIME_INTEGRATION.md更新；实际发布须核对当前进程与不可变源码，不将工作区等同已加载版本。

直接用户授权覆盖暗雷接入；不能据此称日历全部活动已接入或重新执行其他窗口的未授权现场战斗。本批所有战斗验证均是临时数据库/内存连接，未操作人类客户端或实际在线角色。

共享编辑当前范围：runtime_storage.py的wild启动加载/迁移已完成，本窗口后续不改repair_role_equipment、npc_recover_resources，亦不改这些函数的签名；原始集成窗口可继续其NPC局部接线。game_runtime.py的本窗口范围仅move_for_encounter、ScheduledBattle可选wild engine、RoleOwner野外状态/移动触发/battle_step/finish/断线与登录恢复。资源Module的plan_combat_resources/battle_terminal差异保持现状交主策划独立审查，不再扩写同文件。普通暗雷不会自动迁移任何旧资源档或打开新角色资源政策；已迁移走同一carrier，旧已知profile只在原vitals与当前投影完全一致时接入。
