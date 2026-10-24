# 帮派建筑接入

第25批补充：建筑预估与真实小时费用复用同一normal_cost；显式维护政策下工坊资源、练功房研究力/XP及降级建筑裁剪/代次隔离已接入，见GUILD_MAINTENANCE_RUNTIME.md。此变化不表示正式数值/NPC/建设任务或完整GUI已激活，当前完整候选查guild-buildings-current-review.json；下文保留第24批建筑原增量。

读取条件：整合建筑事务/查询，传入building_policy或接真实建设任务源时。最终固定版本查guild-buildings-current-review.json；正式采用数值、NPC和任务源另验。本页描述第24批增量，不是完整帮派激活交单。

## 接入Interface

OrganizationStore/OrganizationRuntime新增可选kw-only building_policy，默认None。显式规则先冻结为BuildingRules，含recipe指纹；只有真实create_guild事务初始化三建筑、selected、generation与人气。initialize仅建表，旧帮派不补档。原研究参数和旧构造保持兼容；GUI/真实服务仍从准确发布BASE验收。

- `OrganizationCommand(..., 'choose_building', (type,))`：类型0聚义厅、1工坊所、2练功房。当前帮主或有效bit5副帮主，扣帮派资金及200人气、推进建设代次，进度按建筑保留；组织ledger/revision/命令receipt同事务。它是已有可信命令Seam，调用方仍需证明当前组织NPC资格。
- `guild_building_snapshot(guild)`：内部可信读冻结状态，不给线包直接调用。`guild_building_panel(actor,epoch,guild,family_token,member_token)`在同读事务复核当前租约、双代次和bit5再返回。
- `ConstructionWork(guild,generation,request_id,deadline_ms)`经`apply_guild_construction`到该帮派所有者，每个可信稳定源只加1。达到需求升一级、归0、selected=-1、代次推进，状态/revision/专用receipt同事务。旧成功源返回历史结果；通知总是读当前视图，不把旧receipt编码成当前进度。
- 新c5627空body查询已在所属社交类型/组织运行时接入；用户身份来自当前角色Owner。收费c5631只有纯decoder和原按钮证据，没有注册raw线包。当前完整地址/位置/NPC证明由main/地图入口统一接，不能拿一个Q或地图1395当许可。

生产任务完成源尚未接入。任务Owner须保存稳定guild/建设代次与真实完成事件，再用可靠outbox/inbox交付；不把客户端“完成任务”或任意新request_id当授权。旧代次拒绝保护新目标，实际未完成任务取消、个人奖励与组织历程7仍须各自Owner接入。

## 费用、曲线与未知档

原建设需求/资金/人气计算、类型0..2、原body/receiver/名称及三数字列已经原指令验证，准确函数与范围见GUILD_BUILDING_NATIVE_BINDING.md。初始等级/人气、cap、12小时储备的计算时点/取整及维护预估系数见GUILD_BUILDING_CONTRACT.md，属于显式本地设计。没有生产默认规则；夹具(1,1,1)/2000/4..20/维护10000等不供运行服使用，不以Native level20分支推原服绝对上限。

recipe变化不改旧存档。缺原行/畸形进度和凭据明确报错；旧成功建设receipt仍可恢复。新源在terminal帮派拒绝。选择换目标全价收费、不退款，保留各建筑进度；维护预估只做选择资金门槛，不执行小时维护或研究/产量刷新。主策划正式采用须登记统一政策、适用档案和替换条件。

## 当前投递与验收

GuildProjection新增kw-only可选BuildingSnapshot。当前有权限的接收者经现有GuildWake、角色Owner和连接独占的发送流编码完整三行c5628，登录/查询/选择/贡献/重登覆盖；撤权、离家重入及旧代次不投建筑数据。原空消息不会清建筑缓存，所以未知档不伪造空/零响应；完整GUI缓存清退另验。

选择和贡献的事务提交位于展示try之外。提交后读面板/邮箱背压或SQLite错误只延后通知，当前原查询可恢复；真正DB提交失败继续抛错并整体回滚。组织Owner不等待其他角色Owner，受控阻塞该帮派存储前，另一family命令和原4字节加密心跳继续。

验证入口verify_guild_buildings.py及verify_guild_buildings_native.py：9组事务/当前加密Peer检查和5组原生检查；完整固定回归30项及最终Standards/Spec数字以批次JSON为准。测试中的建设源和数值政策显式为夹具；不是原任务完成链、实际NPC、小时维护、研究联动或GUI证明。

集成时从自己的当前准确BASE合入9个候选文件及其组织依赖，重新冻结整合闭包。固定source里的shared/其他系统只作验证依赖，不整份覆盖main或运行发布；无Git按精确23批r3文件基线/diff/SHA验收。家族/研究/解散指针同步只为避免混用组织Store/Runtime，不授权发布。
