# 自然序章共享入口接线准备

2026-10-23，原始复原集成窗口。本记录保留最初接线准备及Interface收敛决定；当时尚未修改执行源码或运行检查。后续共享接线和限定验证已完成，当前状态见NEWBIE_RUNTIME_INTEGRATION.md；仍未访问现场、部署/重启客户端或运行战斗。

## 方法和依据

沿用本批已读且仍在上下文的codebase-design，将持久章节、角色内播放授权、地图权威位置及连接编解码分在既有Module/Seam；不把NewbieFlow的内存ticket当持久章节，也不复制任务/奖励逻辑。已读design/newbie-opening-v1.json、NEWBIE_OPENING_DECISION、NEW_CHARACTER_OPENING_RESEARCH及当前world_newbie/accounts/runtime_storage/game_runtime/world_protocol。43路线来自客户端，出生终点选择、章阶段/跳过/超时和intro的0/1投影明确designed。

## 核定接线位置

1. **启动**：runtime_storage.prepare加载不可变政策、43合法角色行/门派路线、世界窗口提供的出生点检查和任务章节schema。把准备依赖注入AccountStore，启动完成前不提供创建；不得在收包/奖励热路径读取全配置或执行DDL。
2. **创建事务**：AccountStore.create_role插入角色、现有成长来源、独立新手来源及对应门派设计出生位置，全部同一调用方事务。失败不得留下半角色/来源/位置。学校和角色行通过原shape映射选择，不能固定100101或100192。既有growth-only origin不补新手来源。
3. **首个有效租约**：runtime_storage.load_role在现有fenced事务先兑现成长，再调用任务Interface激活对应root与持久chapter。顺序不能反过来：现有_initialize_creation_profile会拒绝带任务进度的尚未兑现角色。任务root只offer/accept，不完成；出生位置不得在重试/重连覆盖后续已提交位置。
4. **入场快照**：从持久章返回intro投影，authorized/playing为0、completed为1，无章旧角色维持兼容。世界已提供world_snapshot明确可选intro_discriminator参数，真实经验仍单独编码到native+f8；不得从XP计算intro，也不得把0/1命名成原服已证实字段语义。
5. **首次世界ACK**：完成现有角色/任务/地图初始化后，在角色邮箱取MapOwner的冻结Location及当前连接generation，建立并持久化播放授权；最后排队对应SStartPlayCG。持久化成功前不可发送启动包；首次ACK不是剧情结束凭据。播放持续期间不等待电影时长，不占用阻塞线程。
6. **完成**：精确解析正i32的CEndPlayCG，角色内NewbieFlow验证movie、actor/epoch、generation、完整Location/version和期限；任务Interface在一个fenced事务完成root、选择唯一原后继、奖励与稳定章凭据。成功提交后才清内存ticket、发布当前人物快照和逻辑消息；宠物刷新沿提交后的固定接受者重读契约。原movie的Setmap/Return不写服务器位置。
7. **重连/失败**：pending保留root并由新连接重新授权，旧ticket失效；completed恢复当前位置/任务且不重播。过期只失效授权、不完成任务。相同movie迟到报文没有wire nonce，不能声称彻底消歧或证明自然观看完成。

## 门禁覆盖位置

门禁应在RoleOwner现有具体玩法路由之前，同时覆盖可信写命令settle、initialize_wallet、offer_task与线包的移动/NPC/任务/背包/用药/成长/社交写入，不只挡CEnd之外的某几个已知包。load、close、必要连接控制及首次初始化仍可推进；tick不能在开场期间启动/推进玩法或以超时完成root。未知写入口默认不能绕过。首次ACK只调度播放，普通scene_sent不能充当结束。

位置凭据取MapOwner公开location Interface返回的Location，而非RoleOwner.Position近似副本；地图join会将初始version至少置1，创建/播放的持久版本契约须与任务及世界Interface一致。epoch/连接generation/播放ID与chapter长期身份分开，稳定完成键不能随重连变化。

## Interface收敛追加

已读取task_newbie_chapter当前caller-transaction Interface。authorize/finish会修改传入NewbieFlow，不能将RoleOwner持有的可变flow直接传给数据库工作线程。已向根窗口提出：角色只持有冻结IntroTicket/结果，存储Adapter每个事务创建局部flow，世界Module提供公开从冻结ticket恢复/验证的方法并保留source_id；共享入口不读取/改写其私有_ticket。待接口交付后依此接入，不为便利绕过不可变参数约束。

世界路线原successor_movie_id更名为successor_card_effect_id：43个200xx为首师父武器卡效果，不是CG。共享开场入口仅播放intro_movie_id，卡片的授权/选择/发装另按后续Interface处理。创建政策与路线记录尚未部署，本批不需要对现场章节作数据迁移。

后续世界已提供NewbieFlow.from_ticket，任务契约已明确只接事务局部flow。共享入口据此实现：RoleOwner仅存冻结ticket/章；启动、创建、首租约、ACK与CEnd均已接，自有43路线/门禁/回滚/冻结许可检查通过。前文“待交付”为历史准备状态，不代表当前尚无源码；GUI和部署仍未验收。

## 后续验证分工与未验证范围

根窗口将新增verify_newbie_runtime.py独立检查实际Owner建角→门派root/CG→匹配CEnd→唯一后继→重连，以及pending断线、错movie、重复报文。本窗口不创建同名脚本，不修改根窗口维护的verify_new_character_growth.py；旧growth+trusted100192夹具由根窗口明确为旧growth-only来源，生产门禁不能为测试放松。

后续必要检查还须覆盖43组合、创建/首登/完成异常原子回滚、旧epoch/generation/位置版本/截止时间拒绝、完成后可写与重连不重播、连续RC4/原生MPPC的初始化顺序。实际CG画面、自然End/Return及接近首NPC需另行授权GUI验收；当前没有证据证明本批解决用户黑屏或移动问题。
