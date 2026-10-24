# 师门武器卡与 NPC 菜单发布交接

2026-10-23 19:46:50（北京时间）已部署固定发布 `npc-close-master-commit-20261023T113819Z`，当前 PID44084，唯一监听 `127.0.0.1:28993`。旧 wild PID10076 已停；后续操作必须先核对当前进程身份。

## 发布行为

原客户端 Start 对白结束产生 CCommitScenarioQuest。当前版本在合法任务、NPC、位置、租约及许可条件下收到该请求即打开武器选择卡；玩家实际选择后才获得一件武器、进入装备目标。旧版本等待本阶段不会产生的 DialogEnd，导致无卡。修改后的验证器使用原客户端消息，不再人工补 End。

同时发布训练师10086/10493的原本地菜单分组，以及空体关仓请求撤销本人仓库权限。畸形关仓请求先解码失败，保留原权限；加载/战斗占用状态仍允许合法撤权。现有退出初始化及 wild 固定基线完整继承。

生产差异仅5份文件：npc_services.py、npc_gameplay.py、task_master_card.py、design/newbie-master-card-v1.json，以及固定 wild game_runtime.py 的4行关仓接线。未整份复制工作区 shared。

## 验证与存档

- 原固定旧版本武器卡反馈准确失败，同输入在候选通过；固定候选11项检查绿，主策划 Standards/Spec 均0项并独立复验原消息链、退出4种重置与关仓占用。
- 1425份冻结源码/配置启动后哈希一致，版本601握手及未认证心跳通过，数据库 quick_check 正常。
- 停机一致备份 `runtime/deployments/npc-close-master-commit-20261023T113819Z/accounts-at-stop.sqlite3`；107张既有表（含 sqlite_sequence）逐行不变，没有删除真人角色、重写任务或自动资源迁移。
- 机器记录：`evidence/npc-close-master-commit-deployment-verification.json`；主策划只读现场核对：`evidence/npc-close-master-commit-root-verification.json`。

## 后续边界

未打开客户端、真实认证或执行战斗，GUI及玩家实际选择武器仍待用户验收。npc_state/npc_change、care、新角色资源授权、v2及其他任务/野外工作区变化未夹入本次发布。

NPC所属两个模块可解冻用于后续独立批次；固定发布源码保持不变，后续发布由原集成统一核对基线、检查和存档后执行。
