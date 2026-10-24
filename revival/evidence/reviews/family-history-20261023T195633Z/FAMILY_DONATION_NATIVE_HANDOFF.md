# 家族296、驻地标识与选中银箱接线

读取条件：注册家族捐献296、绑定FamilyData尾Q、处理CSubmit2Npc捐献请求前。2026-10-24。本增量只提供原生证据及纯Adapter，不定义组织驻地准入。数值按FAMILY_DONATION_ROOT_DECISION已获批准；唯一执行配置仍为baseline。

## 原生证据与Interface

原NPC分派0x1637fbf的service296跳0x1638449，调用FamilyManager的0x148c1f0；成功经0x163983a把296交0x1627be0，失败到0x163845c。296点击发送NPC服务，选择器须由服务器另回包打开。297是独立帮派分支，不能套此家族条件。

SUpdateFamilyData处理0x14a4360把FamilyData交0x14a2950，bean+4写manager+d0家族ID，bean+78/+7c写manager+d8/+dc。0x148c1f0要求家族ID非零，且该Q完整等于world(全局0x2944564)+30/+34。离线执行已覆盖高32位不同。FamilyView保留旧构造参数unbound_identity，新增family_scene_identity只读属性；family_scene_view(view,client_scene_identity)纯投影main提供的真实标识，默认未绑定仍0。

客户端这个Q不自行证明服务器完整MapAddress或准入；组织→完整地址/代次政策仍由main提供，不能由家族ID、1401模板、地址hash或客户端报文生成。NPC证明与成员关系同时有效，也不能证明身处本家族实例。

SSubmit2Npc c233f的原marshal0xe6fe10、consumer0x168bed0：非空模板vector交0x1685430，保留context、NPC Q、submit_type、模板和opaque；空vector才走0x168a1e0任务/config fallback。family_donation_protocol.DonationWindow要求显式提供全部四个窗口字段，prompt只列36076/36201。实际历史捐献context/type/opaque仍unknown；测试731/mode0/opaque0仅隔离夹具，没有注册为政策。

原确认0x1684710遍历五行、步长0x138，将选中的item key/quantity构成CSubmit2Npc c2340；原marshal0xf16270和SubmitUnit0xf16160保留原顺序。decode_submission(body,server_window,maximum_count=...)必须对照已存服务器窗口；expected窗口不能从待验包反向生成。最多五个不重复正key/数量、合计不超100。它只校验窗口/形状，不授予NPC权限。

OrganizationCommand的reserve_family_donation现支持(count,units)，units为冻结((item_key,count),...)。permit、fingerprint和重试固定实际选择；pay只扣这些当前角色携带的银箱，缺少/数量不足/其他模板则整笔拒绝，不能拿另一绑定箱替换。旧(count,)调用和存档继续沿原设计自动排序，不重写旧fingerprint。两UI声望槽均+5只投影同一逻辑5，消费含义仍unknown。

## main接线顺序与完成条件

1. 主集成建立家族及成员代次→完整MapAddress/驻地代次/客户端Q的可信绑定；真实入场、离开与重连保持同一权威。证明跨家族同模板实例拒绝后，才将Q供FamilyView投影。
2. 当前角色路径取得本家族完整地址、原NPC实体及新位置证明，检查租约/版本/战斗/loading和296；保存服务器窗口及受理request_id。按独立政策选取窗口字段，发prompt。
3. c2340重新验证当前窗口、NPC/位置/本家族代次，解码units并发reserve(count,units)。退出角色事务后等待家族Owner，返回角色后重取NPC证明再付款，避免等待期间移动/撤权。
4. pay的precommit使用当前唯一资源source消费者，编码失败回滚扣物/共同凭据/source。提交后才发逻辑包，家族Owner确认贡献；断线以同键读当前结果恢复。跨库还需durable outbox/inbox。
5. 固定实际共享源码闭包验证加密Peer、迟到失败、源围栏、断线重登、跨Owner恢复及双轴审查，再由main统一部署。此增量不混入private-story发布。

verify_family_donation_native执行原指令五组，dialog初始化入口即停止，CRT/网络/对话框获取与关闭使用隔离Adapter；未初始化真实GUI。verify_family_donation_selection经公开codec→OrganizationStore→角色Inventory付款→家族结果验证选择、幂等与拒绝行为。两者均未打开游戏、操作真人数据或改共享入口。

方法：codebase-design把协议解释集中在纯Adapter，保持两个状态写者；tdd在既有公开Interface验证选择与场景投影，实际红灯见本批记录；writing-for-agents将接线顺序及完成条件共置。固定双轴与哈希以family-donation-current-review.json当前指针为准。
