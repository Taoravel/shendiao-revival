# 原生帮派名单、基础资料与职位运行接线

第九批接通帮派查询 c560e、任命 c5621、辞职 c5622；登录、离线、重登及家族成员变化均刷新帮派当前名单。此处仅覆盖基础资料和成员/职位，不是完整帮派明细、NPC创建、个人修炼或GUI验收。全量目标保持active。

## 实现与所有权

`guild_protocol`编码FactionData、FactionMemberData、成员列表/单人更新/移除；基础资料已绑定名称、宗旨、等级。成员包含完整64位角色ID/帮费、家族与帮派职位、声望显示对及离线文字。保留元数据三整数和基础资料末整数的原布局，业务用途仍未知。

`guild_projection`隐藏持久成员基线、两层代次和当前投影；`guild_runtime`通过既有组织命令Seam串行处理帮派状态。GuildWake只带ID/epoch/代次，在接收角色邮箱内重新验证和投影，再交目标连接独占的RC4/MPPC流发送。成员列表先于基础资料通知，以便原客户端查到自己的职位；此发送顺序已通过原序列化/临时连接，原GUI仍待确认。

家族与帮派各自拥有状态写入权：家族加入事务只写family_join_events，帮派所有者按自身持久cursor初始化尚未消费的新成员代次，随后发布当前名单。临时nudge合并并有容量上限，不从家族所有者等待帮派；丢失/拒绝后由查询、上下线或后续帮派命令恢复。离开与重新加入分别检查family/member token，旧职位、旧名单与旧退出消息不能覆盖新归属。已消费却缺失的数据报unknown，不借查询补零；老帮派未知基线也不自动初始化。

新建帮派/明确的新成员代次按recovery-baseline.json建立零帮费、零声望及保留字段基线，均为designed；已有数据不被新政策覆盖。原140147证明家族离帮清帮派声望，不证明所有保留字段和帮费清零；此差异保留。家族退出事件的级联删除不是全服历史outbox，不用于其他系统可靠结算。

任命/辞职继续复用guild_offices同一组织事务、名额与权限检查。家族副族长不等于副帮主；授权完整mask只发当前帮主/副帮主，其他人收到0。已提交命令遇到读模型ValueError仍返回原成功凭据，显示延后由下一次查询修复；存储超时沿原所有者隔离规则处理，不能据取消推断回滚。

## 原客户端证据与推定

原映像、地址和执行结果固化在guild-native-verification.json：成员 e458d0、单人更新 d726c0、原std::list e8a7b0、基础资料 e465a0/d73dd0、移除 e464a0。测试含大于32位的ID/帮费、非零保留字段、UTF16、多节点及空列表。

原名单14bc41f从缓存+54取帮派职位，14bc42b直接调用1486190。该原函数离线执行结果：0帮众、1巡察使、2族长、3左长老、4右长老、5副帮主、6帮主；1来自原字面量，其他来自cstringres834..839。2是家族领导身份的显示值，不是直接任命选项。族长高于帮众/巡察使、低于长老/副帮主/帮主的投影优先级为inferred，单一政策guild_family_leader_overrides记录；原意义与优先级不混为已证。家族族长不能被原任命包直接改为巡察使。

## 验证与限制

- verify_guild_native：9组原序列化、原职位格式函数及名单调用字段；未启动GUI。
- verify_guild_projection：5组，覆盖18人跨家族、持久加入交接、19人加入/退出/重入、未知基线拒绝、重启、代次、离线与授权隐私。
- verify_guild_management：11组，通过实际ConnectionOwner加密/MPPC输出；含委任/辞职、族长显示/巡察使限制、丢nudge恢复、提交后显示故障、旧epoch过滤。受控暂停真实guild refresh存储之前，家族命令和另一家族心跳继续完成。
- verify_guild_tcp：4条临时真实TCP、7组，验证认证、名单、授权、委任/辞职、家族批准/退出、拒绝/心跳与关闭。创建使用临时真实钱包及显式等级夹具，不是原NPC建帮验收。
- verify_guild_offices 10组及verify_family_tcp 6组本次再跑通过。此前本批家族管理、组织设置/支付、好友群组与I/O顺序必要回归见各JSON。

verify_faction_runtime退休断言最初失败：新增独立帮派nudge尚未结束，而非所有者泄漏。最小复现表明等待guild.idle后owners/inflight均清零，故在检查完全静止的位置显式排空新增工作；原取消顺序与独立家族并发断言保留，11组重新通过。

未操作真实角色/存档，未启动游戏、重启服务或部署；已有其他窗口发布不由本记录推断当前加载状态。完整帮派明细资金/建筑/申请、NPC授权/研究/修炼菜单、个人经验/支付/效果、维护生产/活动、真实GUI与商业容量继续未完成。

## 后续接入条件

修改NPC相关请求前读GUILD_TRAINING_RUNTIME及GUILD_OFFICES_RUNTIME，先通过地图/NPC服务凭据核验Q，再进入组织/角色各自事务。继续绑定完整明细时按原控件逐字段增加，未知旧字段不得填零伪造面板。Shared入口由原始集成窗口维护；此批直接接线在所属social/faction Modules，无需同时重写game_runtime/serve/gateway/accounts。

方法：codebase-design用于小Interface、状态所有权和冻结投递；tdd沿既有OrganizationStore/native runtime Seams逐条失败再实现，族长显示先见失败再修；diagnosing-bugs最小化后台工作退休误判；writing-for-agents集中接线条件和完成标准。没有执行或声称Standards/Spec双轴审查。
