# 家族、帮派频道与组织执行接线

修改组织频道、提交/撤销调度或目标授权时读本文。付费角色入口与恢复步骤见FACTION_PAYMENTS.md；名单和面板仍有未绑定字段，完整目标继续active。

第六批更新：5种家族原生管理请求、面板/名单/申请及在线/重登已接，最新路径与来源见FAMILY_MANAGEMENT_RUNTIME.md。完整帮派、原生创建、建设与GUI仍待完成。

## 当前运行路径

social_runtime的角色顺序处理器将CHAT_SEND的家族10、帮派4交给OrganizationRuntime.request。角色租约下读取所属组织只是路由提示；组织所有者在实际事务中重查租约、成员、禁言、冷却。原生下行复用已核验的SSendChatMsg，姓名和等级来自服务器角色快照。

每个组织键单独拥有有界SerialOwner邮箱和有界阻塞I/O。独立组织可以推进；组织只向目标角色邮箱排队，目标自行检查租约、组织名单凭据与黑名单，最后由目标连接编码。command和revoke使用OrganizationStore.owner_key的同一队列，取消等待保留已接受命令的所有权。存储超时保留有疑问的所有者直到重新加载，避免新所有者越过尚未完成的写入。

组织聊天receipt与冷却共同提交。同键同内容重试保持静默，同键改内容拒绝；仅清理该角色已过期receipt，尚有效窗口满时拒绝新消息。上限和邮箱/所有者容量是baseline.organizations集中登记的designed参数。

## 授权凭据

OrganizationBroadcast冻结组织revision、发送者、接收者ID及各自的family_id/family_revision/joined_ms/guild_joined_ms。发送前同时核对组织revision、发送者和接收者的成员凭据。家族退出再加入会改变家族revision，即使所属帮派revision未变，旧帮派消息仍失效。

当前策略保守：组织职位/公告等revision变化也可能丢弃排队的旧聊天，家族revision变化会令该家族相关旧帮派消息失效。即时频道没有离线补发或可靠历史保证。后续精细化时可改为持久成员generation，保持退出再加入和发送者撤权测试。

## 继续接线步骤与完成条件

1. **原生请求**：从客户端按钮追到请求字段。现已确定名单等级、声望显示对和离线文字；剩余+2c元数据、声望消费语义及完整帮派职位仍待绑定。完成条件：每个业务字段有原生消费者或明确设计依据；FamilyMemberWire要求显式提供未知值，当前不生成伪造的完整名单。
2. **普通管理**：家族的申请、职位、退出和驱逐已翻译成冻结OrganizationCommand，经social_runtime.organizations.command提交。已验证原生上下行、当前权限、申请出队隐私及重登快照；完整帮派与家族邀请/推荐/特殊确认等扩展仍待恢复。
3. **付费管理**：创建按FACTION_PAYMENTS由角色先扣现金，再await组织command，最后角色resolve；失败使用同Seam的revoke=True。宗旨按ORGANIZATION_FUNDS直接由组织账本扣款，历史现金意图单独恢复。完成条件：原生NPC/团队共同同意和角色自动恢复均接通；当前仅组织调度及财务事务组合验证完成。
4. **界面验收**：在获准的原客户端现场验证成员、职位、聊天、重登和建设入口。完成条件：记录实际操作及界面结果；临时TCP和原函数模拟均不替代此步。本批未启动或操作游戏，未部署/重启当前服务。

## 本批验证与方法

verify_faction_runtime通过11组，含家族/跨家族帮派频道、成员范围、禁言、冷却、接收黑名单、重试/容量、旧投递、替换登录、持久重启和受控暂停/取消。verify_faction_tcp通过四条实际临时TCP连接的原生加密/压缩链路。组织/成员夹具均在临时数据库，既有钱包未被初始化。

verify_faction_payments扩到13组：实际cash扣款后，组织提交被受控暂停，调用者取消等待，再投递撤销；验证同一组织所有者先完成提交，撤销读到committed，角色不退款。反方向先终结撤销则迟到执行失败，角色只退款一次。此项通过实际OrganizationRuntime.command，原生付费入口仍未接。

codebase-design将组织状态、命令顺序与逻辑投递收进小Interface，保留角色资产所有权；writing-for-agents将后续接线条件与协议、原生界面三类验收分开。共享好友/群管理、运行时、I/O超时顺序、货币及好友TCP回归通过。本批没有声称TDD、双轴代码审查、商业容量或GUI完成。
