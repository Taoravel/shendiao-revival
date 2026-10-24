# collision 204238 主策划最终聚合

## Standards

Standards：硬违规0；heuristic可行动发现0。

方法：沿用完整code-review/codebase-design，以固定副本SHA比较6输入/681行，逐hunk复审r3→r4全部32行，按Module/Interface/Seam追踪domain权威与Adapter投影，并逐项判断完整12种Fowler启发。依据AGENTS、ARCHITECTURE单写者/旧世代失效/有界执行及DESIGN_AUTHORITY；无额外CONTRIBUTING/CODING_STANDARDS。未读Spec结论。

证据：game_runtime.py:183–189仅当回执地址属于本map且完整Location等于当前domain成员时更新positions；缓存是权威派生投影，没有成为第二位置权威。相同投影重放不重复invalidate，保留当前pending/已确认context。193–197同时核对缓存epoch、position、version和domain无成员才清除离场投影，历史finalize不再清新epoch、同epoch后续version或仍在场成员。上述检查与修改在同一地图邮箱内无await，未引入全局串行器。

依赖world_owner.py:674–680、705–727、771–794保留历史activate/finalize/resume幂等结果；Adapter过滤陈旧投影而不改领域回执或吞异常。其余5生产输入与r3逐字节相同，原声明身份、发送前校验、drain后专用过期处理和finally清理未变。

审前后6candidate/6previous/4非空BASE及2空BASE均匹配scope，6candidate匹配真实release/source；manifest/candidate记录及双diff均匹配。新game_runtime SHA256=34f0b6dc6d7cf2d4fb1ddfb1e46be0ba3cad65ae9b61cff581dc33aba06a52bc；其余完整值见scope.json。完整diff=0272b7c10437da66989b5ea7aeccd814425a63b06d939a7f8e817c47ffbab4cb；增量diff=db989abc49a259b4cc0626418e8f6316e41a1bc4aca7d0597c7ca78a95b061af。候选记录绑定seal=4dcc6a0b0b3aea28d338508dd081419e1294bd498aa9d7ef683ac23ff1287917。

仅静态审查；未运行latefinalize探针、测试、服务、DB、GUI或实际战斗。既往静态0不证明调度与重放闭包；准确候选动态回归由root独立验证。只新增本报告。


## Spec

# Spec 独立复审 r4

缺失0、额外行为0、错误0。未读取另一轴结论；仅就冻结实现复核旧地图回执与当前投影的归属，不以他方probe结论代替静态证据。

政策.2 L25–28要求“exact current membership/position version”及旧代不能重装，L33要求上下文与当前位置一起推进；ARCHITECTURE要求当前实例/租约唯一Owner。候选 `game_runtime.py:183–189`现在先核返回Location属于本map且等于Domain当前完整Location，才投影；仅实际projected改变时失效。准确release `world_owner.py:650–652/677–680/775–777`确实可能幂等返回历史freeze/activate/resume：新epoch或同epoch后续version与旧Location不等，故不能覆盖缓存或撤销新context；当前activate的loading重复及当前resume重复projected相等，亦不再毁掉pending/admitted context。首次真实转换仍更新投影，ready仍保留其既有确认语义。

`world_owner.py:705–729`的正常finalize删除Domain frozen源但返回目标receipt；候选L183的本map核对防止把目标写回源。L190–197只有cached epoch/完整position/version均等该frozen source且Domain已无成员才清理：正常旧frozen缓存可清、同ID新租约或后续成员不能被旧幂等finalize删掉。此处无跨Owner等待，判定和更新仍在所属map执行器。

其它五文件SHA与r3一致，沿用完整审阅；paid evidence guard仍在L580，postdrain专用迟到处理仍在L1241，发送前typed barrier/精确body、finally清理、special Scene/location顺序和仅此前normal成员battle恢复未改。本修复没有把历史receipt视为新权限，也未扩大移动/战斗范围。

方法：沿用完整code-review/codebase-design，通过真实Interface、Domain幂等返回与缓存投影逐项对照；非Git，固定6项681行/32行增量。6candidate+4BASE+6previous SHA、两diff、manifest/candidate记录及seal均匹配；scope前后SHA `b6ca0fc530494f5e66cec9bc95df2ca728c671bc95cd9251dd3365b9d6984cde`相同，6source末次复核稳定；seal `4dcc6a0b0b3aea28d338508dd081419e1294bd498aa9d7ef683ac23ff1287917`。

仅静态，未亲跑lateprobe/10replay/46checks或302图；准确运行验收仍由集成方闭合。未操作DB、服务、GUI、真人或战斗。


## 准确运行验收与发布范围

Standards硬0/判断0，Spec缺失0/额外0/错误0。root独立10项隔离Interface脚本、原HP consumer8项全部实际exit0：db9历史finalize原例转绿、10 transfer replay、dd64当前CG迟到回执、terminal5组、strict earlyACK、私有投递6终态、自然private断线、自然两角色bloodmark/chat/冷重连、GC隔离、1006/1404/1501诊断子集；每项1442/421/1207和runner前后稳定。

main准确46项均exit0，逐result seal及actual origins由root独立复核；生产模块均source，harness仅明确verify/research助手与一个显式diagnose_npc_loyalty_quote临时库测量助手，单一旧NPC验证fixture匹配显式封存SHA，无生产shadow。准确302图结果稳定/完整，3443静态NPC摆放；root只读此全量报告，root自身三图不能冒充302。原r1重复CEnd、r2当前CG迟到回执、r3旧finalize失败全部保留，不改旧source。

启动前检查正式库只读备份，丢弃副本启动110旧表所有行/结构不变、quick_check ok、无新表/无自动迁移，root读报告不直连正式库。BASE为已恢复approved loyalty193742/PID3396，root已独立OS与1440source/444startup核过。允许唯一main依既有授权执行精确204238协调发布，最终重核BASE/源码/无Established连接/at-stop一致备份和601+未认证heartbeat/110表，不允许并行第二次切换。发布后由root独立OS/完整source/启动SHA复核。

仅恢复普通行走的原网格当前格和显式发送生命周期；未把send drain当客户端load/像素ACK，Jump仍未完整恢复，实际正式剧情AI仍暂停，未宣称GUI或商业容量完成。普通repair、真实RoleViewBinding与clean identification仍后续独立接线。
