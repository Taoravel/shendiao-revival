# 已提交传送：历史凭据与当前完整位置的纯读Interface

2026-10-24。用于`TASK_DREAM_RETURN_INTEGRATION.md`要求的`read_committed_world`提供方，也可供明确历史操作的所属角色Owner确认。只有`world_transfer_storage.py`新增实现，没有修改Task、奖励、shared、政策、运行服务或真人数据。

## 调用与返回

```python
from world_transfer_storage import load_committed_transfer_transaction

# db是调用方已开启的角色事务，current_epoch是当前有效租约。
historical, current = load_committed_transfer_transaction(
    db, account_id, role_id, current_epoch, expected_receipt)
```

返回普通二元tuple：`(TransferCommit, MapInstanceCheckpoint)`，两者及其领域成员为既有冻结对象。`historical`是从World日志读取并与`expected_receipt`精确核对的历史回执，保留原epoch／operation／offer／deadline／完整源目标地址；`current`使用当前epoch，含最新地址、位置、版本和entry来源。当前角色已合法移动或换过实例时，返回后来状态，不把历史目标作为新的传送命令。

它与任务候选注入形状`read_committed_world(db,aid,rid,current_epoch,expected_receipt)`直接一致，无需把TransferCommit拆成第二份transfer ID。角色Owner负责授权“读取哪个历史operation”；该函数确认World事实，不授予新的任务完成、奖励、NPC访问或地图进入资格。

## 严格读与拒绝条件

调用方必须已有事务；World只执行SELECT，不连接、不begin／commit／rollback、不DDL、不cancel／recover／commit prepared，也不操作地图Owner或发送网络。先核当前account／role／lease及删除围栏，再读历史。历史可属旧epoch，当前租约不得旧。

历史行必须是`committed`或`ready`，原role／epoch、source、target、offer及receipt与完整规范编码一致，回执拓扑符合原预留／冻结／target-loading契约。缺失、prepared、cancelled、冲突或畸形立即ValueError；不兜底到最近一条或仅按map_id匹配。

当前必须已有明确完整实例绑定；legacy未知不自动采用。当前entry版本不得早于历史target版本；所属entry本身也须有精确committed／ready日志、完整地址及entry_version吻合。在entry版本尚无后来移动时，当前坐标须与entry回执位置一致。允许后来合法checkpoint，允许之后同模板不同实例；只核历史回执及当前entry的持久来源，不宣称完整中间传送链审计。

即使旧`commit_transfer_transaction`的同epoch replay在部分情况下不写，也不应当getter；`prepare_transfer_recovery_transaction`可能取消旧prepared，更不能用来实现本Interface。读取失败不暗中修档；调用方保持显式reconciliation unknown或独立恢复。

## 已实际验证

`verify_world_committed_transfer_read.py`：公开函数缺失准确AttributeError红，新增后正例绿；最终9组通过，报告`world-committed-transfer-read-verification.json`绑定实际源码前后SHA。真正临时AccountStore、公开完整地址adoption、真实MapOwner预留／冻结／激活回执与World同事务提交；初始位置和同模板portal均为明确夹具，不冒称自然新手全流程。

所有确认成功及拒绝均在SQLite authorizer下执行，只允许SELECT／READ／FUNCTION；DML、DDL、事务控制等任何尝试都拒绝，且验证调用方事务保持开启、total_changes不变。覆盖实际prepared拒绝、同租约精确确认、外账户／旧租约／合法拓扑但不同deadline或operation拒绝、后来真实移动、同模板不同实例、显式ready行夹具、新租约读旧epoch历史及旧租约拒绝。另13项历史／当前entry缺失、取消、畸形或错版本／地址等由明确SQL故障夹具建立，只读断言后全部rollback；不称为自然故障恢复。

首版Spec审查发现历史整数epoch的Python数值别名：三处都换True／1.0可能与整数1判等。用系统随机源Adapter令真实acquire_lease产生合法整数1，在只读公开Interface准确复现红；随后三处epoch严格检查int／str类型，并对历史和expected采用保留类型的规范JSON比较，bool／float整体替换两例均拒绝。该随机源夹具没有直接写租约表，也不把客户端声明当租约。

必要原`verify_world_instance_persistence.py`12组通过；`verify_world_transfer_recovery.py`实际prepared／committed两分支、新租约和cancelled后移动均通过。独立双轴初版P2及修复复审见`WORLD_MOVEMENT_STATE_AND_MAPS_REVIEW.md`及固定快照。

方法：codebase-design把World日志和当前实例查询保留在World小Interface内，Task不复制SQL；tdd从既定公开Seam实际缺函数红到有结果绿；diagnosing-bugs使用实际lease／事务／地址和SQL禁止写提供反馈；writing-for-agents把返回形状、当前与历史差异、拒绝和调用方责任共置。

未验证Task实际paid组合、梦醒发送失败的完整接线、第一族实际AI胜利、线上升级、GUI或完整世界恢复；当前发布private-story-20261023T190051Z不包含该新增函数。本接口可作为后续域候选交main按当前准确BASE组合，不夹入正在验收的现有版本。
