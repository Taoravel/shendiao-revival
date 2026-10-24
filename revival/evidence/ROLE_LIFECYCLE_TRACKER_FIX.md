# 退出、选角、删角与ESC后任务显示修复

2026-10-23，原始集成窗口。适用方法：diagnosing-bugs用实际加密ConnectionOwner请求构建可红可绿反馈；codebase-design把账号退休事务放在role_lifecycle Interface，角色退出仍复用现有角色Owner清理；research以原x86按钮、协议和tracker分支裁定线状态。

## 原因与决定

退出c0011、回登录c0032、回选角c002d、删角c0028原请求此前没有共享入口路由，因此点击得不到原确认。现在先完成当前角色检查点、社交/地图退出与租约释放，再经原连接发送c0031/c0033/c002e。返回选角保持同一连续RC4/MPPC流，可以接着删角。允许剧情门禁期间退出，不借关闭全体客户端实现。

删除body严格8字节正signed64角色ID。认证账号候选与租约epoch经单事务比较，拒绝其他账号、在线Owner、租约竞争及畸形ID；提交后才回c0029。采用本地设计的可审计退休：隐藏选角、禁重登、释放建角名额；保留角色、资产、任务和结算外键，名字继续保留。客户端证据只证明立即移除列表，不证明官方保留期限或物理删除政策。

ESC后的现场只读核查：角色3 root100101已完成、后继100186仍active，章节completed，奖励未重复。原tracker更新0x160daa0把ScenarioQuestInfo.state=2走failure helper，实际读取原SpecialQuestConfig1000+0x90“任务已失败”；0/3走原任务TraceListA。因此修正普通active线投影为0，remove1/failed2/ready3分开命名；领域持久状态和章节政策版本不改。此前将NPC类别2当作wire active2的推断撤销。

完成章的卡片后继不满足plain-dialogue能力检查，原resume会跳过。新增纯resume_newbie_messages仅凭独立chapter来源和当前active快照恢复精确后继bean，RoleOwner ACK去重；不凭等级/XP/空表补任务，不假称卡片或装备任务已完成。

## 验证

- verify_role_lifecycle_runtime：改前c0011无SRoleOffline失败，改后剧情中退出/仅清当前角色、位置检查点、同连接回选角删角、回登录、重复幂等、账号/在线/畸形拒绝、租约竞争、晚期失败全回滚、旧epoch拒写、资产/结算保留与空位恢复全部通过。另一角色心跳继续。主策划独立复跑通过。
- verify_task_tracker_runtime：改前真实Owner root state2进入原x86 failure分支而失败；改后首root、END/ESC相同原结束包后的后继、重连唯一后继全部normal。重复END与重连不改任务/奖励。主策划独立复跑通过。
- verify_task_tracker_native原0/2/3及失败文案实际选择器通过；verify_task_newbie_chapter全部43路线事务/错误拒绝/回滚/重连通过；verify_task_native_effect_dialogue原10条普通本地效果对白与奖励必要检查通过。

全部角色/删角/写入检查使用临时数据库，无真实角色删除。现场仅只读存档与无登录健康探测；真实按钮WM_CLOSE、界面切换、任务画面仍由用户验收，不把离线x86/临时Owner结果冒称GUI通过。首师父卡与装备共享入口接线继续后续批次，不纳入本次完成声明。

部署进程、启动哈希、备份与迁移保留证据见runtime/deployments对应目录及latest-deployment-verification.json。同期其他窗口源码变化不等于对应玩法已实机验收。

## 本次实际部署

14:55 CST启动PID8724，发布副本runtime/deployments/20261023T063445Z/run_release.py；同快照两项实际Owner检查通过。为隔离其他窗口持续编辑，源码固定在该目录source，数据与资源仍使用原项目ROOT/OUT。发布没有后来工作区的role_vigor共享接线。启动hash与预检逐文件相符，601挑战/未认证心跳通过；at-stop备份与启动后全部70张原表原列/行一致、quick_check ok、role_deletions为空。用户已收到短暂重连更新提示，精确停止旧PID31052；周期保存后的已提交位置保留，无真实角色/任务重写。工作区后续源码不热加载，后续部署需显式选择新发布。
