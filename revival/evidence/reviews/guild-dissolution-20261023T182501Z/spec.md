# 家族解散的帮派消费者

本页用于接入或审查家族降至0级后的帮派处理。实现增量依赖前批家族维护、原有组织/帮派投影和修炼代码；它不是可以直接覆盖36632或其它运行发布的完整激活交单。当前运行服状态不由工作区源码推定。

## 来源与采用的规则

原包 cmessagetip 141510/141511 支持帮主所属家族解散后强制继任；141512/142935 支持最后一个家族解散后帮派消失。原始资源、2012端游官网和版本冲突见 FAMILY_DEVELOPMENT_RESEARCH.md。

继任顺序集中于 design/recovery-baseline.json 的 organizations.guild_dissolution，标为 designed：副帮主、左长老、右长老、巡逻、家族长、普通成员；同职按当前关系加入时间、角色ID排序，紧急继任不套普通72小时任期。所有人选必须属于当前有效家族/成员代次。继任清除新帮主旧职位和原帮主授予的副帮主权限。未离开的原帮主继续任职。

最后一个家族消失进入 dissolution_pending，停止日常操作、聊天、申请、修炼预留和投影权限。保留历史组织ID、原帮主外键、资金和账本；返回的有效帮主为0。资金不退款、不补零，这是 designed。尚有其他关系但没有有效候选时为 succession_pending，同样停止日常授权，等待这些待解散家族的后续消费者推进。当前没有恢复解散家族的玩法入口。

## Interface 与所有权

`FamilyDissolution` 是家族所有者维护事务已经写出的冻结事件：family、due_ms、guild、guild_token、精确(role,member_token)元组、pending状态。`FamilyGuildClosureCommand(event,request_id,deadline_ms)` 是可信内部消息；无线包入口，不接受客户端名单。

1. 16个独立目录分区按索引、限定数量扫描未完成帮派阶段的outbox；用(due_ms,family)游标跳过暂时失败项，循环后可重试。维护任务和解散任务共用总容量限制，各自按family合并。
2. 目录读取事件后向 `OrganizationRuntime.consume_family_guild_dissolution` 提交，唯一写者键是 `('organization',guild)`。与帮派管理和修炼预留共用现有SerialOwner，无全服队列。
3. `OrganizationStore.apply_guild_family_dissolution(event,request_id,deadline,now)` 在一个事务校验源outbox、家族pending状态、完整guild-family代次、名单和政策；清对应成员帮派声望/旧权限、断开家族关系、决定继任或关闭、保存幂等凭据。晚到事件不得删除新代次关系。
4. 帮派事务提交并完成可重试逻辑通知后，调度器向 `ack_family_guild_dissolution` 提交给家族所有者。该事务独立核对源事件和已落盘帮派凭据，再置 `guild_done=1`。等待帮派期间不占用家族所有者；无跨所有者锁。
5. 无帮派的家族也经过家族所有者确认此阶段。该确认仅完成帮派阶段；outbox仍为pending，角色、任务、背包及地图清退尚未完成时不能标成committed。

`guild_lifecycle`、`family_guild_dissolution_done`、`guild_assets`提供可信诊断读；资金读不授予消费权限。旧资料缺失保持未知。已有修炼预留的 `resolve_practice` 允许继续查已付/撤销结果，避免关闭帮派后丢失角色结算恢复；日常新预留仍被关闭状态拒绝。

## 幂等与未知数据

幂等键为(guild,family,due_ms)，指纹含源代次、名单和政策；更换传输request_id仍返回原冻结结果。幂等凭据与全部帮派更改同事务；家族确认缺少凭据会拒绝。截止时间限制新提交和重试受理，不将已提交结果解释为撤销。

已知旧成员状态只清对应family/member token，保留其他关系和历史账本。缺少帮派成员档案时，只有仍未被帮派cursor消费的精确新家族入会事件才能证明尚未发过基线；不会凭缺失记录填零。帮派刷新若先于解散消费者推进，必须先兑现这些新加入但现已pending的成员显式基线，随后保持inactive，再推进cursor。已消费却丢档的旧成员继续pending，等待修复，不伪造声望。

组织所有者从已落盘的家族名单补发退出逻辑通知，处理提交后通知前崩溃；收件人所有者在发送前重查当前关系。已进入别的帮派时旧退出消息不能清除新关系。派生消息只入收件人邮箱，不访问外部连接cipher/writer。

## 验证与验收限制

验证 Seam 延续已采用的公开 OrganizationStore、OrganizationRuntime、收件人投影与临时Peer；SQLite临时库保留真实事务和原生RC4/MPPC解码。TDD已实际观察：缺少继任Interface、最后家族未实现、调度不消费outbox、未刷新新成员缺档、先刷新吞入会事件等红灯，然后逐个修复。

verify_guild_dissolution.py 检查继任、最后家族、重试/重启、阶段确认、待继任、未知档案、新代次保护、晚失败回滚、受控阻塞下源/其他家族独立推进，以及实际5秒周期源发原生离帮/帮派刷新。补充边界检查不宣称每条都曾红灯。报告为 guild-dissolution-verification.json；旧家族、帮派、修炼、原生TCP回归另记 guild-dissolution-regressions.json。

codebase-design把跨所有者复杂度集中在冻结事件与小Interface；tdd按公开Seam纵切；code-review按固定文件快照分别审Standards/Spec；writing-for-agents将来源、恢复、接入和完成条件共置。

完整社交恢复仍active。此次未实现角色任务取消、特产物品处置、实例清退、帮派建设/Boss/帮战，也未宣称真实NPC修炼已接线。下一步须由对应所有者消费者完成这些阶段，沿用原成员代次，不直接删任务/背包表。真实GUI、在线服激活、跨库事务、生产容量尚未验收。本批未改共享入口、部署或重启，没有打开游戏、实际战斗或操作真人数据。
