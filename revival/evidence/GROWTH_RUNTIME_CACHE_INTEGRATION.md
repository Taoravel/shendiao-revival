# 已提交成长结果发布到角色与社交所有者

2026-10-23。范围为实际非战斗任务完成后的缓存一致性；不处理未知GUI等级/属性协议，不启动游戏、战斗或线上监听，不改用户现场数据。

## 缺陷与方法

主策划已通过verify_growth_runtime.py --expect-stale取得红色基线：真实临时任务完成后数据库L2/XP61，但RoleOwner.role、其RoleSnapshot、rt.online、SocialEndpoint.snapshot及社交domain.snapshot仍L1。旧完成回调只写experience，未发布已提交level。

采用codebase-design，在runtime_storage角色事务Seam返回冻结CommittedTask（TaskCompletion与CommittedRoleState），角色状态在同一事务末读取，不另在事务外猜测成长结果。SocialRuntime新增显式publish Interface，版本包经目标社交所有者邮箱，不在RoleOwner里修改另一个所有者的domain。沿用diagnosing-bugs复用同一实际任务反馈验证红转绿；已知遗漏赋值/发布的直接路径，不扩散其他假设或战斗检查。

## 实现与约束

- 完整任务/奖励事务成功退出后，RoleOwner核验role_id/epoch并按本角色命令顺序更新level和experience。
- RoleOwner维护同epoch内单调snapshot_revision，更新在线目录及频道成员快照，再等待SocialRuntime.publish的邮箱确认。该revision是在线发布序号，不冒充持久化资产/成长/属性版本。
- SnapshotUpdate为冻结快照和发布序号。只有SocialEndpoint自己的顺序handler可以同步更新endpoint.snapshot和domain.snapshot；旧revision、同revision不同内容及旧epoch均拒绝。正常社交request也携带版本，不能偷偷用旧请求快照覆盖新版。
- 登录/普通跨图的社交join同步使用同一版本协议；跨图激活会推进发布序号。已退役epoch的回调仍受原所有者/连接围栏保护。
- 删除RoleOwner里已无用途的第二份RoleSocialOwner副本，实际社交可变状态只在SocialEndpoint拥有的domain中。
- 事务已提交后发布失败不伪装数据库回滚；沿既有背压/断线路径处理，重登从权威存档重建。没有增加全服锁或全服串行执行器。

## 必要验证

1. 同一verify_growth_runtime.py默认模式已通过：数据库、角色缓存、RoleSnapshot、在线目录、社交endpoint与domain全部L2，数据库XP61；临时原NPC/对话流程，无战斗/客户端/在线端口。
2. verify_social_snapshot_order.py通过：同一邮箱先排revision2、后排revision1，旧项拒绝；同版本冲突、旧epoch和旧request快照拒绝；endpoint/domain始终保留最新冻结快照。该检查没有数据库、socket或战斗。

产物为growth-runtime-verification.json与social-snapshot-order.json。没有重复全runtime/战斗回归；未部署，GUI显示及用户现场未验收。

## 剩余明确缺口

RoleDetail加载仍有固定实验HP/MP，显式属性基线的真实伤势尚未接入原生初始化；普通等级/完整属性刷新协议仍待原字段核对。本次没有拿训练值补基线，也没有因为缓存等级已正确就声称客户端HP/MP或等级显示已恢复。人物用药上下文接线及其限定验证见ROLE_CONSUMABLE_RUNTIME_INTEGRATION.md，未重复执行。

后续主策划交付已核对的role_attribute_protocol后，显式profile入场/首次ACK的源码已接，见ROLE_PROFILE_ENTRY_INTEGRATION.md；前段为缓存修复时的历史剩余项。新接线未部署、未运行额外检查，不视为真实GUI通过。
