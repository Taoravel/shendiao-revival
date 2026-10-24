# 同实例重定位：旧进程成员的精确恢复清理

2026-10-24，接续 [SQL恢复](WORLD_RELOCATION_STORAGE_HANDOFF.md)。本批补旧地图对象的不可变检查与精确退休，将已提交的新租约SQL决定和同一进程内旧成员清理串联。**没有接GameRuntime/连接发送或入口政策，没有部署或GUI验收；完整世界目标仍未完成。**

## Interface与顺序

角色所有者先冻结旧写者并取得真实新lease。地图操作均在实际地图单写执行器上执行，存储操作在角色有界IO资源中执行；不携带可变地图/投影对象跨所有者等待，不在地图操作内查SQL或等待发送。

1. `inspect_relocation(role_id, request_id, *, view=None)` 返回冻结 `MapRelocationSnapshot`：实际MapAddress/Owner代次、当前Location及成员关系ID、prepared/终态/脱离状态、源offer、投影代次与该角色presence。`inspect_relocations(role_id, *, view=None)` 在有界回执集合中发现该角色操作，覆盖freeze已发生但journal尚未写入的窗口。快照只是观察，不是新状态许可。
2. 角色事务执行既有 `prepare_relocation_recovery_transaction`，必要时传上述实际prepared；**事务提交后**才将返回记录投影为 `RelocationRecoveryDecision(prepared, authority, committed)`。authority使用当前checkpoint的完整地址/坐标/版本和本次new_epoch，state为供随后加入的active候选；不是已激活成员。
3. `retire_recovered_relocation(snapshot, decision, *, view=None)` 核同一真实Owner代次、原准备身份、捕获成员关系/位置及投影，且只接受与历史source不同的合法新租约。只有当前快照精确相等，才删除捕获的旧角色、旧投影及该操作记录；源offer只删精确原offer，其他终态仅脱离旧成员。另一个pending操作须先完成它自己的恢复，不能借旧历史清掉。
4. 返回 `MapRelocationRetired` 和 `RoleSceneChange`，只是旧Scope清理回执和逻辑投递，不加入authority、不发送、不安装新许可。调用方重新核当前角色/连接代次及流程后，再按当前SQL checkpoint在正确完整实例加入、建立新移动声明和精确发送屏障。若有其他跨图恢复，先按其合同清理旧源/目标，不能把后来实例拉回原同图点。

回执的removed只表示本次实际删除的旧Location，record_removed表示是否释放了本操作预算。Adapter清旧位置/成员缓存时还须匹配该旧身份，不得按role_id盲删；回执authority是不可变观察信息，不是直接覆盖角色当前位置的命令。旧离屏与新入屏逻辑投递仍须由连接所有者保序处理。

SQL返回None只证明无SQL历史，不能伪造decision或跳过旧内存状态检查。未知实例继续依显式采用合同处理。本方法也不验证SQL提交本身：调用方必须先取得实际存储决定并完成事务，不能把客户端字段转成可信decision。

## 成员与投影身份

MapOwner新增每成员关系ID索引，保存实际关系身份，不保存第二份坐标。真实join、跨图activate和同实例commit建立新关系；普通移动、freeze、取消恢复及ready保持该关系；退出、跨图finalize或恢复退休清理时删除。索引随本地图角色容量有界，只由其Owner写入。相同epoch/坐标/version的leave→join仍是不同关系；其他角色活动不会使本角色快照过期。

RoleScene公开只读owner_generation，即其真实投影生命周期，空投影也保有身份。metadata投影仍由实际Domain唯一注册；全AOI必须传本Owner自己的投影。捕获时使用了投影的请求不能在清理时丢掉它或换成另一个空投影。

新lease authority版本至少达到原计划终态版本；等于该版本时，committed必须是原目标、cancelled必须是原源，完整地址亦须匹配。更高当前checkpoint可以属于后来完整实例，清理不回写原点。旧租约、bool/float地址及数字别名、旧Owner、准备身份冲突、成员重入或位置/投影变化的旧快照拒绝。若同一旧Owner中的本操作、角色、offer和presence均已消失，重复清理仅返回空回执；新成员出现后不能继续按空重试清理。

地图Registry若已没有那个旧代次，应依据真实Registry观察处理，不能为清理创建一个新Owner并把它冒充旧Owner。旧回执也不能清新Owner中的同值角色。

## 已执行验证与仍缺范围

`verify_world_relocation_recovery.py`：11组，覆盖快照/真实关系生命周期、清理及精确重复、新成员ABA、严格输入、空投影身份、无关成员活动、外来pending拒绝、跨图关系ID维护、后来实例及热路径无文件IO。TDD先观察缺inspect/decision退休Interface的红结果，再实现；float分区别名误收也实际红→严格类型绿。真正旧关系ID来自Owner接受成员事件，不用位置version充作成员身份。

实际SQLite组合覆盖freeze-gap、prepared、SQL已提交未发布、loading、ready、cancelled、后续走动七窗口：先提交新lease恢复，再清理**同一个旧地图对象**，再从当前checkpoint加入并继续合法一步；迟到旧清理不能删除新角色。另经真实跨图事务进入另一个完整实例，先清跨图旧状态，再清原同图历史，原Owner不创建新角色，正确目标Owner接纳新lease。actor/检查点和外观均为明确临时fixture，不是真人自然触发。

当前新源码还执行5项既有回归、原10组Domain与9组SQL回归，另存本批报告，保留旧冻结/已交结果。具体来源与双轴审查按本批固定before/after/依赖快照记录，不能转签已发布BASE。

尚缺：共享MapRuntime/RoleOwner和连接控制接线，实际缓存退休、新移动/成员许可安装、真实write/drain、原生批次/迟到输入隔离及具体同图消息/入口政策；实际客户端黑幕、移动、新手全流程及全部15特殊入口仍独立验收。本批未修改shared、正式存档、服务或客户端。

方法：codebase-design将观察/精确退休放在已有MapOwner与RoleScene Interface，唯一位置权威仍在地图；tdd按公开Seams逐段红→绿；code-review用真实旧源与新增文件空基线进行Standards/Spec审查；writing-for-agents共置SQL提交、观察、退休、重核、加入与投递的前后条件。目标继续active。
