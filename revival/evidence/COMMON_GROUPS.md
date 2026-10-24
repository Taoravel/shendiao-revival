# 玩家群组恢复记录

2026-10-23。本轮恢复的是好友面板中的玩家聊天群，家族/帮派另见FACTION_DESIGN_GAPS.md。全量社交目标仍为active。

最新第二批：邀请同意/拒绝、管理员任免、共享公告/加入、个人提示、踢人和原历史分页已接运行链路，详见GROUP_MANAGEMENT.md。原生检查由17增至28，另直接模拟执行4个原按钮处理函数；真实临时TCP管理流程通过。修正时间第三字段及末尾两个配置标志的语义。下文第一批方法/证据为历史，当前未完成项以本文末节及第二批为准。

## 证据、规则与实际接线

以native-image.bin的原x86序列化器为比对对象，verify_group_native.py通过17项，含非空CommonGroupInfo、成员/管理员向量、完整初始化和单群更新。群资料先编码群主再编码群号；客户端128fda0按第二个身份字段查找群，不能颠倒。SUpdateCommonGroupInfo为外层群号和内嵌bean，初始化为bean向量。建群必须先CCreatCommonGroup→SCreateCommonGroupResponse，再CSendCommonGroupName→SCreatCommonGroup。详情见group-native-verification.json和group-protocol-disasm.txt。

审批按CResponseJoinGroup的decision、申请人ID、群号解码，原生128b5d0/128b6b0、1622db0/1622dd0及请求通知128e410提供调用关系，0接受、1拒绝。消息读取路径128e1a0按群号及第二字符串从成员名单解析发送人；下行由服务端可信姓名构造，不能允许客户端填写发送人。发送路径16e5dc0取两种输入字符串，当前分别保留内容和格式化内容；具体富文本表现仍需原面板验收，附件明确拒绝。搜索的简介/人数/群主显示语义依赖消费者调用推定，原生字节布局已核验、GUI显示未核验。

[历史官方好友聊天资料](https://sdxl.wanmei.com/info/system/chat/20120728/133497.shtml)支持20级建群、等级对应的群总额上限、8字群名、60字公告。该2012资料与1.6.1精确匹配尚未证明。实现按角色数据库实际等级计算已建和已加入之和，1–19级最多1群，20–39级2群，每20级加1，最多5群。其他容量、频控、申请有效期、历史保留、邮箱和回执容量标为designed，集中在recovery-baseline.json.social.common_groups。

group_store.py封装本地持久化事务、角色租约检查、申请/成员/消息/回执；角色群额从关系表派生，在同一事务检查，不保留多份角色计数。group_runtime.py按群ID建立有界SerialOwner，创建/搜索按发起人分区，空闲即退役。取消等待不释放尚未完成的所有权；I/O超时后该群保留poisoned状态，须查清结果/重载，防止后续命令越过未知提交。没有全局玩法锁或全服队列，SQLite仍有文件单写限制。

social_runtime.py已接GROUP_TYPES、登录群名单/离线申请恢复，以及GroupDelivery收件检查；social_protocol.SOCIAL_TYPES导入群请求集，现有GameRuntime路由直接接通。本轮没有改serve.py、gateway.py、accounts.py、game_runtime.py。群所有者只排不可变逻辑消息，不等待目标社交邮箱、不接触目标writer或加密流。目标检查epoch、成员generation、资料version、群聊发送人成员资格及黑名单；退群再入群换generation，旧队列不能穿透。

## 验证

- verify_group_native.py：17项原x86消息逐字节一致，包括嵌套非空向量。
- verify_group_runtime.py：认证加密的建群/搜索/申请/审批/成员限定聊天、黑名单、退群重入旧消息、离线群主申请恢复、重启持久化、命令幂等及数据库旧租约拦截。
- verify_group_tcp.py：两位认证加密客户端，临时真实loopback监听完成创建、审批、群聊、退群及持续RC4/原生MPPC，关闭无未处理异常。
- verify_group_concurrency.py：受控暂停甲群存储，取消等待后同群后续退群仍等待原提交；乙群聊天和路人心跳在释放之前完成，结束无残留群所有者。
- verify_group_quotas.py：两个独立群同时批准同一1级角色，实际并发事务只有一个成功，另一保留申请且无半条成员；20级两群总额及无效名字回滚通过。
- 回归verify_social_native/relations/owner/runtime/tcp、verify_faction_native、verify_factions、verify_runtime、verify_runtime_io_order通过。帮派回归发现整数epoch与SQLite TEXT比较不一致，本轮修复创建者、共同创始人、聊天四处检查，新增旧聊天租约失败/新租约成功检查。

全部测试使用临时存档；20级角色、临时组织付款凭据和家族3级均仅为验收夹具。没有给真实玩家升级、发钱或改组织。

## 未完成范围

系统消息、完整富文本/附件、在线状态变更群名单推送、无成员活动一周自动解散、申请/邀请过期行后台清理、原生错误提示及完整GUI流程尚未完成。当前群主退群采用明确designed的原子解散，不能冒称原服自动转让规则。历史查询下行已在第二批接通；过期申请不再回放，但旧行仍占总申请容量，后台按群清理待补。

真实28993进程未由本窗口重启。最近读取为PID37352监听、当时无Established连接；进程状态会变化，该读数不能证明新源码已加载。原客户端GUI、当前在线进程加载、多进程商业数据库/容量、完整故障恢复均未验收。帮派、师徒、结拜、婚姻等仍属全量目标，不由群主流程通过替代。

## 本批方法记录

codebase-design用于把群状态/事务/投递授权收进小Interface（request、initial、allowed），在群所有者和目标角色收件处放置Seam；取消等待的所有权保留和跨群派生群额是实际架构决定。diagnosing-bugs用于帮派有效登录误拒：verify_factions.py已先复现stale_epoch；提出类型不一致/租约被替换/停用三项假设，临时最小存档显示returned int、stored str、归一化相等且active=1，修复统一比较并复验原命令和真正旧租约拒绝。未声称TDD、双轴code-review或实机GUI验收，无临时DEBUG日志。产物与未验证范围均在本文列明。
