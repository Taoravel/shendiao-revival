# 群邀请、管理、设置与历史：第二批

2026-10-23。上一批是实际进展：群主流程已接线并通过真实临时TCP。本批继续完整社交目标，新增原生管理请求、持久邀请、个人/共享设置、历史分页与收件复核；没有改共享入口或当前手动客户端现场。全量目标保持active。

## 客户端证据与修正

- 群管理窗口`decoded/ui/layouts/groupsettingmanager.layout`明确列出MsgTips、AllowAddMember、GroupBoardEdit、InviteRole、DelRole、NewManagerRole、CancelManager；普通成员窗口只有个人消息提示和退出。原生16e9900/16eb390分别生成共享scope=1和个人scope=0配置请求。
- CChangeCommonGroupConfig：群号Q、scope i、个人提示i、公告字符串、辅助输入字符串、允许加入i。CommonGroupInfo末尾两个整数及SChangeCommonGroupConfig对应顺序为“个人消息提示、允许他人加入”。上一批两个默认值均为1，无法识别反序；本批以0/1不同值运行原序列化器，已纠正编码并按收件成员保存提示。关闭提示仍收消息。
- CAppointOrCancelManager：Q任命(1)/撤销(0)、Q群号、Q成员。原构造器d74b40的实际UI调用16e9f75/16ea152证实。CInvite/CExpel先Q目标角色，再Q群号。
- 邀请与公开入群审批使用相反的同意枚举。verify_group_ui.py直接执行原x86按钮处理函数（只适配网络取得/发送、关闭窗口和CRT cookie）：ReplyInviteGroupDlg/Agree→16ef820→1、Refuse→16ef8b0→0；OwnerReplyJointDlg/Agree→16f0280→0、Refuse→16f0310→1。原窗口创建中的控制名绑定也已核对。该检查是原代码模拟执行，**不是运行中的GUI实测**。
- 时间字段修正：SSendMessageToCommonGroup第三字符串是时间。原历史UI16e854a/16e856c以0x22ca500处UTF16模板`  (%s)`拼入姓名旁边；第一字符串才进入内容显示。上一批错误地回显辅助正文。verify_group_management先在真实运行对象/加密连接中复现第三字符串为“群内报时”而非时间；修正为可信服务器时间后相同断言通过。第二客户端输入仍作为辅助字段保留，不能据此声称完整富文本已还原。
- CQueryGroupMsgHistory为Q群号+i页号；原UI初次请求-1表示末页，之后按页号±1请求。SQueryGroupMsgHistory为i页号、byte是否末页、HistoryGroupMsg向量；每条为内容、姓名、时间、分隔标志、附件ID向量、附件向量。目前附件向量为空，原x86非空历史bean向量逐字节比较通过。

上述源码/反汇编依据在group-management-disasm.txt。原生格式检查现为28项，按钮模拟4项，均带相同native-image SHA256。原生字节布局、原按钮枚举与GUI完整表现分别记录。

## 领域与运行决定

GroupStore新增有界common_group_invitations，保留邀请人、成员generation、唯一token和时刻；目标可离线，登录后重放。接受仅作用于该目标自身的当前有效邀请。普通成员不能邀请/任命/踢人/改共享公告；群主可任免管理员，群主不可被踢，管理员不能踢其他管理员。踢人/退出/撤销权限会删除相应旧邀请；迟到通知仍需在收件时校验token、当前邀请人权限、黑名单和目标尚未入群。

个人提示存common_group_members.flash；共享公告/加入开关仍属群所有者。个人操作不改共享revision，不广播给其他成员；共享设置给每位成员编码其个人提示，并带完整当前群资料，避免旧资料被version过滤后丢失名单变化。启动迁移只增加列/表，不重置旧群名、公告、成员或generation。GroupStore/GroupRuntime消费只读策略快照。

历史仅给当前成员，在请求时按黑名单筛选再分页；GroupHistoryDelivery只携带冻结标量元组，到目标社交所有者再次查成员generation、当前黑名单后编码。退出再加入的新generation不能接收旧请求的历史；已离开的历史发送人仍可显示，但当前黑名单依然按稳定角色ID过滤。消息和历史第三字符串由同一时间规则生成，不能信任客户端代填。

参数单一来源为baseline.social.common_groups。每页20条、最多保留100条、成员可查群内保留历史、3秒重复邀请间隔、管理员邀请可绕过关闭公开加入、UTC+8与时间格式均明确designed；客户端仅证实字段/翻页/显示契约。没有证明这些数值为原服值。主策划费用接口currency.py和CURRENCY_DECISION.md已读，家族帮派费用下一步仅经角色cash可信扣款凭据衔接；本批未初始化钱包、未消费或混兑绑定银，也未接生产扣费。

## 验证与边界

- verify_group_native：28项原x86消息比对，含不同提示/加入标志、管理请求和非空历史向量。
- verify_group_ui：4个实际原x86按钮处理函数构造出的不同同意/拒绝标志。
- verify_group_management：旧表迁移保留、时间错误原复现转绿、个人/共享权限、分收件人设置、邀请同意拒绝/离线恢复、历史翻页/双重黑名单、踢人撤权旧消息失效、坏包无状态变化/连接继续、重启持久化，共8组。
- verify_group_tcp：两位真实loopback TCP认证加密客户端完成主流程与邀请入群、管理员任免、公告/个人提示、历史时间、踢人/非成员历史拒绝；持续RC4/原生MPPC和关闭无未处理异常。
- verify_group_runtime、verify_group_quotas、verify_group_concurrency及好友关系/运行/TCP、共享verify_runtime、verify_runtime_io_order通过。没有把有界测试当作商业容量验收。

全部数据库、等级与25条历史分页种子仅是临时夹具。当前运行服务未部署/重启；原客户端GUI、群生命周期（过期行清理、一周不活跃解散及群主通知）、在线名单实时变化、系统消息、完整富文本附件/原生错误提示尚待完成。群主退出仍是明确designed的原子解散，尚无原生转让流程证据。家族帮派、师徒、结拜、婚姻等完整目标没有缩小或标为完成。

## 方法参与

codebase-design用于把权限、邀请失效、历史授权集中在群Module内，通过request/initial/prepare_delivery的小Interface隐藏表结构与收件处理；冻结历史记录和目标重编码是实际Seam决定。diagnosing-bugs反馈循环用于时间字段：先运行可复现的加密请求、观察明确错误内容，再以原UI格式化路径确定字段用途，修复后重跑原场景和真实TCP。未声称完整TDD、双轴code-review或实机验收。具体产物、通过和未验证项如上，无临时DEBUG日志。
