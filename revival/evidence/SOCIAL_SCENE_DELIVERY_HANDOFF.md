# 当前频道延迟投递：精确候选交单

主集成接私有地图与连接发送围栏时读取本页。固定候选在 `reviews/social-scene-delivery-20261023T135356Z/`；测试已通过，独立 Standards 与 Spec 审查均为0项发现，最终记录见该目录 review-result.json。工作区仍有组织/维护恢复进展，不能整目录取代候选。

## 固定范围与基线

只有 social_owner.py、social_runtime.py 两个生产文件。baseline/social_owner.py 是已审 scene_scope 版本 SHA256 `2fa52148624f11b79e82818c59d8afe814bdc504a795e10848e6620cb394b075`；baseline/social_runtime.py 是实际36632发布源，SHA256 `7afecf6e05aa01df139e11d5eb66fba95c2d8791e82ed4a47b7e5da1b4c59fa9`。base36632/另保留原两文件。

since-approved-scope.diff 是新交付精确增量，since-36632.diff 包含已审RoleSnapshot/Publish范围和本次增量；candidate.json固定各文件哈希。workspace-excluded.diff 明确展示候选没有带入工作区的 guild.initial(self)。没有引用新的guild/faction/maintenance实现或激活NPC服务，未改共享GameRuntime/连接、地图或账户源码。

## 新 Interface

`Delivery(role_id,login_epoch,kind,body,*,scene_key=None)` 保留原四位置参数。scene_key 为 None、非bool的正signed63整数或严格三元tuple `(map_id,instance_id,partition_id)`，map/instance正、partition非负，各值小于2**63。公共 `(map,map,0)` 规范成原map整数；私有完整tuple保持不变，mutable/畸形/越界拒绝。字段冻结且仅关键字，GuildWake/FamilyWake/GroupDelivery/History/OrganizationDelivery的继承构造不被默认字段打断。

SocialEndpoint先检查epoch，再检查带key投递与当前snapshot.scene_key相同，旧范围计scene_delivery_stale并丢弃。之后继续原群/组织/收件人关系及黑名单过滤。带key最终只await `runtime.offer_scene_channel(current_snapshot,delivery)`；缺hook计scene_delivery_unavailable，hook明确返回False计scene_delivery_rejected，两者均不落通用target.offer。None保留原投递路径。

派生投影展开逻辑包及群/组织准备返回新Delivery时继续携带原scene_key，避免中途丢掉范围后绕回通用发送；不跳过这些投影自身的资格检查。此额外保留不改变None的旧行为。

主集成负责Publish fanout填入key，以及共享hook对真实完整地址/epoch/connection generation/scene_token、SceneDeliveryTicket、ProjectionUse和连接队列/drain/close的完整围栏。这里只验证社交消费Seam，不能拿本候选代替共享链的验收。

## 验证与复现

`verify_fixed_candidate.py` 在独立Python进程只装载候选和固定36632代码，原资源只读绑定到项目目录；结果写本目录results。新8组覆盖迟到oldkey跨instance、同key只交hook、缺/拒绝hook、不匹配与非法键、继承兼容、None世界/门派、真实持久黑名单和旧epoch；已审scope6组回归同过。两条主要纵切实际先红后绿：Delivery缺字段、旧实例消息走通用发送。

`verify_fixed_regressions.py` 完成6项固定基线回归：社交运行8、快照顺序5、群运行8、家族管理9、组织运行11、实际临时TCP5。results/import-closure.json和regression-import-closure.json记录全部实际导入代码路径/哈希，确认没有工作区未审代码依赖；资源绑定和报告重定向另标明。基线原生TCP不证明新场景ticket/pin/drain。

复现工作目录 `D:/神雕侠侣/revival`，Python使用项目已配置运行时，先执行本目录verify_fixed_candidate.py，再执行verify_fixed_regressions.py。没有Git仓库，审查以已固定的两组源文件、统一diff及哈希替代commit范围；规格为PRIVATE_SCENE_SCOPE_DECISION.md，标准为AGENTS/ARCHITECTURE/DESIGN_AUTHORITY与code-review smell baseline。

方法：codebase-design维持小冻结Delivery Interface和共享投递Seam；tdd使用真实SocialEndpoint邮箱及关系存储先红后绿；code-review由独立Standards/Spec代理审固定diff；writing-for-agents把范围、依赖、未验证链和复现标准共置。未部署、重启、打开游戏、实际战斗、操作真人数据，完整社交目标继续active。
