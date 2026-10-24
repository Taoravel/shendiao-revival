# 新手开场章节事务接口草案

主策划政策已发布且独立事务实现已交付；本草案仅保留历史讨论，当前调用顺序与检查结果以 [TASK_NEWBIE_CHAPTER_INTEGRATION.md](TASK_NEWBIE_CHAPTER_INTEGRATION.md) 为准。原successor_movie字段已更正为successor_card_effect_id，首师父选择卡不是root CG。

2026-10-23，任务窗口给主策划/原集成窗口。已读当前world_newbie.py与NEWBIE_ORIGIN_RESEARCH。按请求先提交必要持久字段和Interface，等待主策划集中确定chapter来源/恢复政策；不复制43组合和root分支算法，不改共享入口或当前客户端。codebase-design将world_newbie的纯授权/原路由与任务事务存储放在不同Seam；writing-for-agents将创建、播放、提交、重连、重复分支列在一起。

## 可复用的现有Interface

- NewbieFlow.route / initial_task_plans / successor_task_plans选择原角色×门派路由和纯任务计划。
- start返回冻结IntroTicket和原SStartPlayCG；finish在角色/epoch、连接generation、当前Location、movie与期限匹配时返回scenario_finished证据；committed在外层成功后清本地票据。
- TaskDomain/complete_task_transaction已支持type50可信剧情证据及同角色任务、人物、道具、钱币、宠物奖励。通用chain会将多角色分支保留pending；本章成功后应只用NewbieFlow的确切successor_task_plans激活该角色next，原边列表继续保留。

## 待主策划确认的最小持久结构

1. role_id主键、chapter_instance稳定ID、章节policy版本；原character_id/school_id、intro task/movie、successor task/movie及route fingerprint。重试不得以当前资源重选不同分支。
2. creation_origin_ref及其fingerprint：由可信创建流程提供可核对的持久创建凭证。不能只检查钱包来源标记、XP0、入服intro字段或空任务表。已有role_restoration_origins.creation_profile/receipt由原集成窗口所有；建议其提供同事务验证Interface后返回不可变创建证明，任务Module保存引用而不复制其私有验证算法。
3. phase=authorized/playing/completed，revision；首次root的offer/accept请求键及完成task receipt引用。旧任务进度非空时只恢复已存章节，不初始化为新生。
4. playback attempt ID、稳定request_id、source_id、login_epoch、connection_generation；冻结Location的address/position version/x/y、movie ID、期限与状态。各次播放独立记录或追加审计；新登录不得沿用旧epoch许可。
5. completion/reward稳定键及已选择successor记录。奖励已提交后重复CEnd只能确认已有完成；不能再选宠、发钱/道具或重开root。

建议startup-only prepare_newbie_chapter_storage(db)，调用方事务内initialize_newbie_chapter(...已验证创建证明...)、authorize_newbie_playback(...NewbieFlow/current Location/generation...)、finish_newbie_chapter(...原CEnd body...)和resume_newbie_chapter(...)。这些操作均不connect/commit/send，返回冻结章节和逻辑消息；调用方成功commit且epoch仍有效才发送。

## 状态和接线约束

初始化须与root激活及章节授权同事务。播放授权须在真实入图后、权威home场景active时，先持久化attempt再返回start包。收到end时同时匹配NewbieFlow内存票据和持久attempt，使用原type50完成→奖励→确切角色next激活→章节completed的一笔事务；异常回滚所有资产/章节，保留同一票据供同命令重试。

重连恢复要区分authorized/playing与completed。建议旧playing在新租约明确失效，再按政策在同一home图重新授权新attempt；不会从超时或断线推定影片完成，也不重放已完成root。是否允许在新epoch恢复相同未完成影片、是否要求回到原播放Location，交主策划确认，不在任务窗口重置出生点或角色位置。

CEndPlayCG只有movie ID，不携带服务端attempt nonce；连接epoch/generation和当前授权能隔离旧连接，但同连接上两次同movie的完全相同迟到正文不能完美区分。恢复政策应避免同generation重复授权同movie；文档保留协议限制。

root任务原ScenarioInfoAnimationID既是本次已验证影片，完成后应保留原值、明确标记该效果已执行，不能清原字段或让通用outbox再播一次。原角色next可能仍有自己的动画/装备任务；激活不代表完成。真实原图Return、位置与新出生点由世界窗口/主策划负责，任务章节不写role_positions。

## 完成证据要求

只做临时库必要检查：可信创建来源一次初始化、43原路由复用；任意movie/错epoch/generation/Location拒绝；成功end使root奖励与next及章节共同提交；故障一起回滚；重连未完成可按政策重授权、已完成不再播/奖。不启动客户端、运行战斗、重启服务或改在线存档。草案本身不是章节持久化已实现或运行服已接线的声明。
