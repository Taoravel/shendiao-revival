# 嘉兴血手印与私有剧情场景发布

2026-10-24 03:27:37（北京时间）已发布。实际 PID14480，唯一127.0.0.1:28993监听；运行副本为 `runtime/deployments/private-story-20261023T190051Z`。BASE 是已上线的 wild-auto-20261023T181143Z，自动普攻和伤害结果修复均保留。

## 用户可验收的行为

已完成嘉兴说书人100160但缺少后续的角色，重新登录后只恢复本角色原章节的血手印100106，不要求重做对白、删除角色或重发奖励。按原任务访问血手印、完成调查后，事务同时记录完成、原唯一后继100107 active0和独立1501场景归属。移动、NPC访问、当前频道、断线和重登均使用完整实例地址；同一模板的不同角色不会共用剧情实例。此批不推进后续正式剧情战斗、画卷或梦醒。

旧角色没有新手章节时，原世界入口使用普通已结束标记，避免请求一段无剧情包可结束的开场锁。NPC访问采用已核原客户端离散格规则；动态NpcLifecycle仍未激活。实际客户端画面、寻路、进场和新阶段内容仍需真人验收，离线检查不替代GUI结果。

## 实际采用的方法与决定

`diagnosing-bugs` 通过实际加密Peer、Owner、临时数据库及原消费者构建故障反馈，先红后绿：

- loading中断线留下incoming1：断线ready后回收原传送凭据，所有计数归零后才允许空图回收。
- 原消息批次取消后，未入队suffix遗留一个场景票据：三个生产者统一批次终止清理，排队、拒绝、取消各自有明确清理责任。
- 回收命令真实队列deadline失败后丢失卸载身份：保留原ticket，获得当前活地图确认后才撤销卸载围栏。
- 地图已retire但Adapter.close失败：保留原retirement receipt与Adapter，后续仅重试清理，真实终态后才释放进程名额。
- 逐图清理被一张慢图拖住：实际每秒计时器只调度或复用每地址一个维护任务，不等待全图gather；另一张后来空闲的地图可先回收。
- 场景finish队列deadline失败后丢失重试归属：保存原TrackedSceneDelivery和pin，按所属地图重试，旧实例代回调先拒绝，不重新变成pending。

`codebase-design` 用目录、投影池、地图和连接各自的Interface隐藏租约、预算、投递与清理；可变玩法仍由各地图或角色自己的邮箱持有。TDD沿既有获准的Peer/Owner/持久化事务Seam执行，不另造全服串行队列。

## 固定范围与验证

1439生产输入，18项变化；来源及SHA见candidate.json/manifest.json/changes.diff。shared runtime_storage只纳入剧情、完整地址和启动依赖，未发布的修理/恢复资产契约改动恢复为BASE；inventory、宠物进化、组织、新鉴定、忠诚新费率、梦醒新域均未夹入。社交取已审clean片，不复制工作区组织增量；任务域取已交f0c622快照，不复制梦醒新能力。serve从BASE仅增加明确prologue_touch=True。

固定验收集合seal：`85b8a3067fe27d94c203093fed5a65ede85ec748aeb8f084cc80ed7dab4c0790`。29项全部通过同一seal，包含自然单角色/双角色链、旧BASE跨解释器pending存档恢复、场景隔离/重登、目录权限、真实队列过期、关闭/取消/满队列、维护失败重试、真实GC计时器隔离、旧开场原消费者、静态NPC、原自动普攻与伤害消费者回归。生产1439、406个harness及实际读取的1187个workspace静态输入前后绑定核验；历史JSON报告不充当静态输入，原NPC两份捕获JSON单独绑定。

初次打包发生测试资源路径缺失和过宽ROOT替换，已明确修正harness资源/报告路径，未改生产。完整重跑后只静态NPC旧脚本的捕获资源缺失；补齐原捕获输入，并按实际仅NpcScene激活范围使用独立4组静态检查，保留动态域8组为独立历史结果。最终29项均在上述最终seal重新运行，未复用早期结果。

额外两项准确候选故障检查也通过：事务末尾场景编码失败→回滚并在新租约恢复公共源；持久提交后source.finalize拒绝→在新租约恢复私有目标。均通过真实临时Peer、原任务身份与旧receipt清退，未改生产。第一次未排序查询误读旧车夫记录属于测试问题，已改为明确rowid顺序。证据在发布目录 checks/private-transfer-recovery-extra.json。

规划根独立Standards与Spec均0项发现，原始报告在 reviews/private-story-release-20261024，聚合REVIEW-root.md；另独立复跑8项高风险与伤害8例，保持精确候选输入。规范轴与规格轴结果分开保留。

## 发布与未验证范围

发布前精确核对12336旧runner、全部生产SHA、最终空服快照；保存停止点一致备份 accounts-at-stop.sqlite3 后启动新runner。后验确认1439输入和实际启动SHA匹配、601未认证握手/心跳通过、quick_check=ok，108张旧表所有行不变，仅新增空 task_prologue_touches 和 world_story_instances。未还原旧库、未修改真人角色或任务。报告：private-story-deployment-verification.json / latest-deployment-verification.json。

未操作真人客户端，未代玩正式剧情战斗；完整原生渲染、用户实际操作与商业容量未验证。目录、初始私有checkpoint、旧场景token、慢writer与失败Adapter等fixture的范围分别写入对应检查报告；自然双角色入梦另有无checkpoint fixture的正向验收。空服发布守卫是瞬时检查，不宣称原子热迁移。
