# 社交恢复：证据、设计值与缺口

续批状态（以本段为准）：好友申请、同意/拒绝、持久化审批outbox、原生名称分组、已有联系人黑名单及收件过滤已在social_owner.py实现，详情SOCIAL_RELATIONS.md。29项原生序列化、社交关系与所有者检查通过。共享运行入口和真实UI尚未接入/验收；自定义组、群聊、好友配置、离线私聊仍未恢复。下文第一批“申请/黑名单未接入”是历史状态，不代表本批领域模块仍缺实现。

最新架构状态：按新根AGENTS/ARCHITECTURE约束新增social_owner.py，提供角色独立有界邮箱、冻结快照/命令/投递效果、epoch/截止时间校验及独立关系存储Adapter。verify_social_owner.py受控慢存储隔离检查通过。共享入口尚未迁移，当前运行SocialHub仍为旧兼容接线，不能称商业并发恢复；确切Interface与接线见SOCIAL_RUNTIME_HANDOFF.md。本窗口已停止修改serve/gateway/accounts，交由集成窗口统一完成。

2026-10-23。统一依据 `../DESIGN_AUTHORITY.md`；来源状态和实际接入/实测分别记录。

## 本批实际接入

- client_verified：好友ID/姓名查询、添加/删除、初始化、在线状态、私聊和公共聊天的原生消息布局；见 `SOCIAL_PROTOCOL.md` 与 `social-native-verification.json`。公共频道映射表由原生代码和原UI布局交叉确定。
- implemented：ID/姓名精确查找；单向联系人SQLite持久化、幂等添加、删除；重登初始化；上线/离线通知；在线私聊；世界广播、同场景当前聊天、同门派聊天。目录按角色而非账号索引。
- designed：联系人上限100，文本最多256个Python Unicode字符（非UTF16字节数）；直接添加只影响发起人列表，不替对方添加。当前聊天暂按整个同场景投递，无距离限制。值已接入 `../design/recovery-baseline.json` 的social字段，未声称原服规则或容量。
- 自动联调采用临时数据库及两账号三角色，实际走认证、加密、分帧、Session分派与原生MPPC解码，验证跨角色隔离和持久化；不会给真实账号创建测试联系人。

## 未完成/未实测

- 尚未在真实游戏界面点击好友、发送中文聊天或双开验收；协议探针不能替代客户端交互验证。
- 好友申请/同意/拒绝（CRequestAddFriend/CAgreeAddedFriend等另一套消息）、黑名单、好友分组/配置、亲密度、群组、队伍和帮派聊天未接入。当前直接添加策略不代表原服申请规则。
- 离线私聊、历史记录、富文本附件/物品链接、语音及自动回复未实现；此类请求拒绝且只记录类型及受控错误原因。拒绝的界面提示协议尚未接入，用户可能只看到未送达，不能显示为已送达。
- 原始频道等级/体力/道具消耗、频率限制、距离范围未确证，当前仅本地基础实验投递；未改成原版规则。
- 原资料存在阵营、签名和其他数字字段，未确证的保持原构造默认值；已知角色资料字段对应业务含义仍需客户端展示核对。
- 非空好友列表整体原生解码、收件人UI处理、慢连接背压/刷屏压力、多进程目录同步未验。服务只监听本机。

## 跨模块接口

在线目录及投递由`SocialHub.online`（roleid→Session）和`Session.push(kind,body)`提供，原连接循环独占socket写入。`Session.close()`必须被网络清理路径调用。当前聊天读取`WorldMovement.position[0]`，传送后自动使用最新场景；门派取已有roles.school。群组类投递必须由所属系统提供已校验成员目录后再开放。跨模块应复用同一hub，不新建独立在线目录。

## 方法与验证

采用diagnosing-bugs：先实际重现CSearchFriend无回包的失败，再定位缺少处理分支和跨连接投递入口；回归通过原Session公开入口完成。采用codebase-design：社交状态、持久化及路由集中为SocialHub，协议布局单独收敛；网络层只注入投递函数并负责关闭。未声称TDD或完成code-review双轴审查。

产物：social.py、social_protocol.py、verify_social.py、verify_social_native.py；共享gateway.py、serve.py仅局部接入，保留地图、任务和道具窗口的新增分支。验证结果见social-verification.json；16项原生序列化布局验证（包含非空好友列表整体）见social-native-verification.json。

运行服务：确认28993没有Established连接后，验证原监听进程为本项目serve.py，重启为PID31844（runtime/gateway.pid）。真实socket测试完成认证、角色进图、好友初始化、ID查询和当前聊天回包；social-live-verification.json记录结果，未向真实账号添加好友或创建角色。此为实际网络测试，仍不能替代原版客户端界面验收。账号/角色存档未清空，聊天正文未入日志。
