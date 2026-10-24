# 私有梦境目录：调用方事务交接

2026-10-23。已实现 `world_story_instances.py`，遵循主策划 `NEWBIE_BLOODMARK_INSTANCE_DECISION.md` 及单一 `design/story-instance-v1.json`。本页供任务和共享运行时接入目录时读取。它补上持久身份；没有接入共享完整地址路由、真实血手印入场、投影卸载或GUI，也没有启用AI8001。

## 公开Interface与归属

启动阶段调用 `load_story_instance_rules(task_resources,newbie_chapter_rules)`：读取两份已发布政策，逐条沿原43章节的唯一后继链定位十个血手印节点，冻结只读映射。歧义、环、缺行或原目标不符均拒绝。启动时另调用 `prepare_story_instance_storage(db)` 建表；当前 `runtime_storage.prepare` 尚未接这两项。

角色Owner/任务Module传入不可变 `StoryInstanceIntent(chapter_id,creation_id,origin_policy,route_fingerprint,source_task_id)`。前四项直接来自可信的 `chapter.origin`，最后一项是本角色原路线的当前血手印任务，不能由原请求自由指定。

| 调用 | 返回与拒绝条件 |
|---|---|
| `allocate_story_instance_transaction(db,account_id,role_id,epoch,intent,rules)` | 当前角色已打开的事务中分配或返回同一 `StoryInstance`；核账号、有效租约、未删除角色、持久已完成开场/原root、原创建及实际路线。不得用它代替当前血手印任务/票据资格检查。 |
| `load_story_instance_transaction(db,account_id,role_id,epoch,intent,rules,expected_address=None)` | 同样核真实归属；未知身份返回None，不分配。恢复时传当前完整检查点的 `expected_address`，缺行、不同实例或非法字段明确拒绝。 |

两项只经调用方提供的数据库Interface执行DML/SELECT，不开启连接、控制事务、建表、读配置或等待地图执行。返回的 `StoryInstance` 冻结kind、账号/角色、intent、目录policy及完整 `MapAddress(1501,instance_id,0)`，不包含第二份位置权威。以 `(kind,role_id,原origin.chapter_id)` 幂等，epoch只用于访问校验。不同epoch重试沿用原ID；目录冲突拒绝而不替换。

生产默认使用 `secrets.randbits(62) | 2**62`，实际数据库唯一约束保护ID，每次调用最多8次尝试。`random_bits(count)` 是外部熵源测试Seam；其返回须为非bool的62位非负整数。冲突耗尽仅拒绝本次分配，不新建全服锁或阻塞队列。SQLite写事务仍遵守既有本地Adapter限制，调用方负责有界I/O执行及提交/回滚。

## 与任务和地图交接的顺序

1. 任务Module核当前血手印资格、真实NPC/完整位置及票据，按角色事务分配目录身份；提交后才向异步地图执行投递该身份。政策允许提前持久的空目录，失败后该行存在不代表进入或任务已完成。
2. 运行时按返回完整地址选择/冷建目标MapOwner，资源仅按map_id1501选取。使用单成员预算，随后目标reserve、源freeze、目标activate；每次等待后重核角色租约/连接和任务授权。这里不得持有SQL写事务等待跨Owner响应。
3. 正式进入的外层角色事务再次 `load(...,expected_address=reservation.target)`，采用精确源检查点，并将持久handoff、位置/完整实例绑定、任务/原唯一后继和共同凭据一起提交。目录Module本身不写这些状态。此前分配事务回滚的身份不能被发布或当已存在使用。
4. 提交后才清源/投递场景；失败按持久handoff裁定恢复。新租约先恢复handoff，再load完整位置绑定及匹配目录，提交后按同一地址加入。缺身份拒绝，不改用公开1501或重新分配。线场景仍使用原模板，未证的q64高位不拼私有ID。

目录规则对象包含已发布的member_capacity=1、loaded_capacity=128、idle_unload_after_ms=60000。它们是运行时接入参数，**当前没有实现128投影加载限额、60秒空闲卸载或动态实体冷快照**。这些须由目录/地图运行时按完整地址及全部空闲条件实现，不能因参数存在称已验收。

## 实际反馈与未验证范围

`verify_world_story_instance_directory.py` 在临时真实SQLite、实际加密角色Owner中自然创建3角色并完成其匹配开场，没有手写chapter/task成功状态。12组通过：同章持久重读/重试、真实ID碰撞重试和不同角色分配、完整地址严格类型/创建路线围栏、外账号/角色/租约拒绝、两个实际MapOwner的受控移动隔离、待播拒绝分配、8次冲突耗尽、坏熵拒绝、晚期实际SQL约束失败整笔回滚、无嵌套连接/DDL/文件读、持久身份冲突拒绝、新自然登录租约保留旧地址。

TDD实际红→绿：首次公开入口缺失；第二片在真实唯一ID碰撞时抛IntegrityError，加入有界重试后绿；第三片 `MapAddress(...,partition_id=False)` 被数值相等误接收，加入完整严格整数检查后绿。初始化/角色事务及配置策略采用codebase-design；本页按writing-for-agents将调用顺序、归属与完成条件共置。测试脚本曾有with语法及MapOwner.location参数错误，已改正，不计游戏根因。

两个私有MapOwner的加入是明确的独立领域fixture，尚未通过真实血手印、完整共享路由或传送提交进入；不声称任务流已经通到梦境。NPC/怪物跨实例动态状态、commit后清源失败恢复、冷重建和真客户端移动/交互/重登仍待共享纵切验证。旧 `verify_world_instance_persistence.py` 的12组不是新目录接线验收。

复验：

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/verify_world_story_instance_directory.py
```

结果 `world-story-instance-directory-verification.json` 保存12组、43路线及库/验证程序/两政策在执行前后相同的哈希。本批未改shared、发布、真实角色，未开游戏/GUI/战斗。
