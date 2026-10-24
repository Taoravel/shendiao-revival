# 好友申请、分组与黑名单恢复（2026-10-23）

后续状态更新：本文件描述的RelationWake、pending_notices、收件过滤已通过social_runtime.py接入GameRuntime源码。加密运行对象与真实临时TCP的端到端检查通过，见social-runtime-verification.json、social-tcp-verification.json；目前正在连接的28993进程未重启，原客户端GUI尚未验收。下文“未接入共享入口”为该批历史状态。

## 实际状态

已完成社交所有者模块与持久化Adapter实现；`verify_social_relations.py`、`verify_social_owner.py`通过。原生序列化检查从16项扩展至29项，全部通过，见social-native-verification.json。旧加密会话联调verify_social.py通过。

本批没有修改serve.py、gateway.py、accounts.py，没有重启服务，也没有在真实存档中创建联系人/申请。新增功能**未接入共享运行入口，未在原版游戏界面验收**。social.py旧兼容Adapter不实现本批新功能；SOCIAL_TYPES扩展不代表旧入口已经支持处理。

## 原生证据

|消息|编号|序列化地址|字段顺序|
|---|---|---|---|
|CRequestAddFriend|0xc4e30|0xe47410|UTF16问候，u64目标|
|SRequestAddFriend|0xc4e2f|0xe48a80|问候，u64申请者，姓名，空资料文本，i32等级|
|CAgreeAddedFriend|0xc4e43|0xe46890|u64申请者|
|CRefuseAddFriend|0xc4e34|0xe47080|UTF16文本，u64申请者|
|SRefuseAddFriend|0xc4e33|0xe48830|姓名，文本，u64拒绝者|
|CRoleMoveTeam|0xc4e2d|0xe475f0|分组文本，u64目标，姓名文本|
|SRoleMoveTeam|0xc4e2e|0xe49030|分组文本，u64目标|
|CBreakOffBlackRelation|0xc4e66|0xe468f0|u64目标|
|SBreakOffBlackRelation|0xc4e65|0xe47ff0|u64目标|
|CToTryAddFriend|0xc4e36|0xe47af0|u64目标，姓名文本|
|SToTryAddFriend|0xc4e3d|0xe492e0|u64目标，姓名，i32等级|

业务字段命名结合本地UI调用推断，消息布局由原x86序列化器逐字节核验。尚未执行这些回包的UI处理器，因此文本显示含义和审批按钮流程仍需真实客户端核对。

`knight.gsp.message.cstringres.xml`原表936/937/938行分别为“我的好友”“仇人”“黑名单”。SAddFriend处理器0x1282f00经0x1282470比较字符串936/937/938，分派至不同名单；FriendInfo第三个字符串、SAddFriend第三个字符串是分组资料。新所有者初始化和添加回包明确传“我的好友”，黑名单传“黑名单”，修正之前空分组实验值。两个带真实分组名的原生序列化比对已加入29项检查。

## 资料与设计边界

检索官方端游资料站并读取[好友聊天](https://sdxl.wanmei.com/info/system/chat/20120728/133497.shtml)（2012-07-28路径；1.6.1精确适用性未证实）：支持按ID/姓名查找和添加、重新分组，默认“我的好友”不可改名/删除。该页没有充分确认好友申请审批和黑名单服务端规则，不采用检索中其他IM平台的行为代替游戏规则。

本批设计策略登记于design/recovery-baseline.json.social：申请通过只允许申请人添加审批人，沿用单向联系人策略，不自动替审批人添加；黑名单过滤私聊、公共聊天与新申请。移入黑名单仅支持已有联系人，移回“我的好友”解除屏蔽；CBreakOffBlackRelation删除黑名单联系人及屏蔽。任意自定义组、仇人组及好友设置仍拒绝，未宣称已恢复。

待审批收件箱、未消费审批事件均沿用max_contacts_per_role上限。请求文本沿用max_text_characters。容量检查在事务中执行；满载不回报成功。已处理记录和命令去重记录保留在数据库，尚未实现历史清理策略，不是无限内存队列。

## 所有权与可靠接线

- `REQUEST_SEND`经申请人所有者提交到SQLite持久化收件箱。申请人不直接改变收件人的好友关系；同一request_id和相同参数重试不重复通知，参数变更返回request_id_conflict；相同角色对已有待审批申请不刷通知。
- 收件人所有者处理AGREE/REFUSE；无对应待审批记录的角色不能操作。审批状态与social_relation_outbox事件在同一个事务中提交。重复相同审批返回同一RelationWake；相反结果不覆盖已有决定。
- `RelationWake(role_id,event_id)`只提示目标角色所有者处理持久化事件，不携带Session或writer。申请人所有者调用`apply_relation(wake,online_snapshot)`；Adapter核对事件确实属于该角色，幂等修改该角色自己的联系人并确认事件。容量失败回滚并保留事件，以便恢复后重试。离线申请人可在重登时补处理。
- 集成方在角色启动时：先从`store.relation_events(role_id,limit)`分批取得待处理事件并调用apply_relation，再发送owner.initial，然后owner.pending_notices恢复离线期间收到的申请。pending_notices只返回有界列表，不自行发送。
- 对RelationWake效果路由到目标角色邮箱；目标离线时不缓存于无界内存，已落盘事件在下一次登录处理即可。临时通知失败不撤销已提交关系，重登初始化反映真实保存结果。
- 投递给角色的私聊、公共聊天、申请通知先经收件角色所有者`filter_delivery(delivery)`过滤。此方法包含同步存储查询，必须在有界持久化执行资源中运行，**不能在连接的网络循环里直接调用**。检查后才排入目标连接的有界逻辑发送队列，连接还须在出队时验证epoch。
- 过滤覆盖屏蔽前已排队、屏蔽后才处理的申请；分组变更后刷新频道的屏蔽索引或走角色过滤，不得只在发送时检查一次。频道Publish不能直接跳过收件人过滤。

所有SQLite方法由有界持久化Adapter执行，领域模块不自建生产线程池，不引入世界锁。数据库中单文件写竞争仍是本地Adapter限制。共享入口目前正在迁移，本窗口只交付独立模块，不声明运行时并发隔离或商业容量达标。

## 验证记录

diagnosing-bugs：先通过真实RoleSocialOwner.execute重现CRequestAddFriend返回unimplemented，随后扩展公开命令入口验证。codebase-design：把审批提交与申请人自身关系写入分开，以持久化事件连接两个角色所有者；编码集中在social_protocol，收件过滤明确留在角色所有者。

verify_social_relations验证：持久化待审批、请求去重/参数冲突、收件人权限、拒绝不添加、审批outbox重开恢复、重复审批/事件幂等、其他角色冒领事件拒绝、带原分组名称初始化、黑名单保存及收件过滤、旧epoch拒绝、离线申请、收件箱容量、容量不足回滚保留事件、解禁与畸形报文。verify_social_owner保留受控慢存储时另一角色独立推进检查。原生29项逐字节比较和旧加密会话通过。

未验证：原版UI、新共享运行入口、按角色分区的完整socket联调、同一角色切换epoch期间的存储租约 fencing、跨进程outbox投递、压力/故障恢复容量、好友配置和自定义分组。原协议审批仅有角色ID，没有申请token；当前依赖角色所有者顺序和登录epoch排除旧连接，不能宣称客户端请求本身携带了审批版本。
