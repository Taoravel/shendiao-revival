# 宠物技能到期、有效快照与空格复用

2026-10-23。领域实现和离线原客户端指令验证通过；共享Owner接线、部署和GUI验收仍待完成。接限时技能发放、c07de查询、c07ff学习、宠物刷新定时事件或战斗技能快照时读本文。当前规则唯一来源为`design/pet-skill-expiry-v1.json`。

## 原客户端事实

原Pet+c4是精确skill ID→signed64绝对到期时间map，编码compact数量后BE32 ID、BE64时间；Pet+b8已学列表独立保存。原刷新11353c9..1135429复制这两份容器，原140dfb2..140e0ed在严格超过到期时间时给图标函数传入200534“技能空”和零到期参数。相等仍有效；原已学ID和map均保留。200534原描述明确空格可学习另一个宠物技能。这些为client_verified。

原SGameTime(c0007) ctor d53c70、decoder d53d00、process81f570→81b3e0存入全局2945088/8c，随后原signed64除以1000并调用IAT22448d4。已匹配原存档模块基址71300000及WinSxS VC80 CRT8.0.50727.9680的_localtime64_s导出71351e8e，malloc/free地址也一致。该函数使用Unix秒，因而同步值和技能到期值单位为Unix毫秒。普通bin/msvcr80.dll是另一版本，不能用其不同导出偏移充当匹配证据。

证据为`pet-skill-clock-expiry-native.json`：九例覆盖1000、1700000000123、32535215999000各自前一毫秒/相等/后一毫秒；执行原时钟解码、赋值、除法、map复制和图标循环，仅在OS日历调用及终端GUI调用观察参数。[Microsoft CRT说明](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/localtime-s-localtime32-s-localtime64-s?view=msvc-170)支持日历单位及上界。当前安全输入0..32535215999999毫秒；保留原signed64布局，拒绝超出原日历范围的投影。

尚未证明两次SGameTime包之间的客户端时钟自增。根入口应显式同步当前时间，不能凭本批证据承诺后台精确自动变图标。未操作在线客户端、服务器时钟或战斗。

## 持久化与学习裁定

以下为designed，并保留上述原字段事实：

- 新宠显式保存`SkillExpiry(version=0,entries=())`；旧宠缺行保持None，可信完整历史map一次导入，空tuple明确表示全部永久。map按ID排序、唯一、仅关联当前原技能；200534不接受到期项。
- 到期本身只改变有效视图，不写技能/到期/资产版本。`SkillTimeView`冻结技能版本、到期版本、as_of_ms、active_ids、expired_ids、slot_ids及下次变化时间。严格比较使下一变化为deadline+1；在支持日历上界不再安排越界事件。active_ids过滤过期技能和200534，raw learned继续保留。
- 学习先按有效技能处理同系升级；无有效同系时优先复用过期/200534格，持有格数与已有扩格进度。续学同一已过期ID复用原位置，不产生重复ID。若目标同时涉及另一个有效同系技能，拒绝歧义操作且不扣书。原普通扩格/保护/概率继续用learning-v3。
- 200534可在raw learned中重复表示多个空位，但不是有效能力。普通/绑定实际能力ID仍唯一；对应31099/70048空标记书拒绝学习。原191条映射保留为来源，实际能力书189条（94普通、95绑定）；不能继续把全部191条称为可学能力。
- 有效普通秘籍授予永久技能，清理被替换及目标技能的旧到期项；原特殊造型秘籍的历史限时时长未查到，不猜7天或30天。此永久授予是当前学习裁定，不能据此声称原造型物品本来永久。需要限时的内容渠道必须使用显式绝对期限的可信发放Interface。
- 保护目标必须仍有效；已过期或空标记拒绝。空格复用是成功学习，绑定秘籍依原绑定裁定置bit1，书/符、技能/进度/到期/标记、版本和回执同角色事务。
- 旧v1及本批前v3学习回执兼容读取，不补到期数据、不重新扣除。当前请求fingerprint新增到期政策版本；now_ms是执行上下文，首提交记录applied_at_ms，重放使用当前回复时间但不重规划。

## 角色Owner接入

状态仍由role_id+login_epoch拥有；表在Inventory.prepare启动建好，配置启动冻结。下面的db都是调用方已有事务，方法不另开连接或提交，不访问连接writer。调用方在有界I/O执行资源内处理，校验非战斗、非传送及当前角色授权，提交成功后投递逻辑消息。

1. 旧存档导入：`initialize_pet_skill_expiry(db,pet_id,entries)`要求已知完整skills/care；entries为排序tuple((skill_id,deadline_ms),...)，可用()显式声明永久。读取不会自动补行。完成条件是公开快照包含准确的冻结SkillExpiry；无依据时保留未知。
2. c07ff：调用`receive_pet_skill_book(body,epoch,request_id,draws,now_ms)`，最后的now_ms可位置传参，适配Owner.io只接*args。两个服务器draw固定0..9999；时间由可信服务器提供。已有无到期map的调用可省时间兼容；非空map的新学习和限时回复必须提供。Adapter在事务中编码当前Pet、真实cash、进度；绑定再完整栏。完成条件是本次书/符/技能/到期/回执原子提交且顺序发送当前c0007→宠物消息。
3. c07de：`receive_pet_query(body,epoch,now_ms)`接受原12字节BE32column1+BE64target0/当前role，返回同一fenced只读快照中的当前时钟、完整栏、XP与参战选择。普通`receive(QUERY_PETS,body)`仍是历史无时钟入口；有到期技能时由root切换新Adapter。未知旧到期仍保持未知，不从查询中导入永久。
4. 可信限时奖励：构造冻结`TimedSkillGrant(settlement_id,pet_id,skill_id,expires_at_ms,source,expected_version)`，调用`grant_pet_timed_skill(db,command,epoch,now_ms)`。期限必须未来且有来源，缺省时长不存在。已有限时同ID只允许延长，永久技能不转临时；复用空格或按血色上限追加，满格不覆盖有效能力、有效同系冲突拒绝。技能/到期/资产版本与独立回执同事务，重试只确认原结果。此Interface未开放免费客户端命令；具体道具/活动授权和期限渠道另接。
5. 当前/到期刷新：`pet_skill_time_messages(db,epoch,now_ms,pet_ids=None)`返回tuple，先c0007再当前Pet，None表示当前全部宠；不写资产。定时事件由角色Owner按当前epoch/世代接收，在执行时重新读取当前状态，不能使用旧回执作为当前宠物快照。按next_change_ms安排事件时须考虑重登/取消/新版本；本批未改root定时器。
6. 战斗：在开战同角色读取事务用`pet_skill_view(db,pet_id,epoch,now_ms)`冻结有效ID及时间/版本，再随属性快照跨Owner交给battle。raw PetState.skills仅供审计/原生投影，不足以证明技能当前有效。战斗内期满按开战冻结语义处理是待战斗方确定的策略，不能在独立战斗Owner读取角色可变状态。

`game_time_message(now_ms)`是纯逻辑包投影。喂养、加点、经验奖励等已有刷新保留完整绝对map；其共享消息发送也应先提供可信当前时钟或统一当前时钟同步。角色装备HP/MP仍跟随根ROLE_RESOURCE_TRANSITION_DECISION的单资源账本迁移，本批未创建另一份角色资源账。

## 本批实际方法与验证

tdd沿既定Inventory事务/快照/receive Seam逐个red→green：新宠缺到期字段断言失败后实现存档；过期复用缺时间Adapter失败后实现学习；可信发放缺命令失败后实现；完整带时钟查询缺方法失败后实现。codebase-design将时间注入、有效视图与同事务保存集中在pet_skill_expiry，根与battle调用小Interface。原单位由原指令链及匹配CRT实证支撑；writing-for-agents将查询、学习、奖励、定时与战斗触发分支集中在本接线文档。

`verify_pet_skill_expiry.py`公开事务通过：前/相等/后原图标、冻结视图、空格复用/多空格/同ID续学、进度保持、过期保护拒绝、学习及奖励真实expiry/receipt触发abort、外层失败、缺钱包、v3旧回执兼容、未知旧数据先拒绝再显式导入、改名/经验/喂养保持map、原完整栏converter、重开及真实opaque LeasedAccounts查询/发放/视图。结构化结果见`pet-skill-expiry-verification.json`。

既有认证/技能/绑定、原学习请求、任务宠物经验、背包事务/快照/现金/租约、宠物显示/成长/照料/消耗品/原命令、穿脱装备事实/详情回归通过。没有执行战斗、部署或实机GUI。共享c07ff/c07de时间路由、定时消息、战斗实际能力效果、内容发放渠道和全量高级玩法仍未完成；本批成果不是全量恢复验收。
