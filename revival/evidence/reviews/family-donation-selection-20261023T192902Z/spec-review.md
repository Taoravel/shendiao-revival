# Spec review

结论：0 个当前可行动发现，P0/P1/P2/P3均0，无审查阻塞。仅针对第十八批增量，不将全量社交目标或未激活状态误判为本批遗漏。

基准为固定batch17r2/source；无Git，按candidate.json与since-family-donation-r2.diff审7个增量。沿用完整已读code-review、codebase-design、writing-for-agents，读取tdd并仅在既定公开Interface补查；核对本目录四份规格、根独立数值报告及ARCHITECTURE/DESIGN_AUTHORITY的所有权和来源约束。

逐项检查missing/partial、scope creep、wrong behavior，未发现本批范围内偏差：

- NATIVE_HANDOFF要求“permit、fingerprint和重试固定实际选择”“不能拿另一绑定箱替换”：family_donation.py:124–126、144–165保存冻结units及原顺序，209–231仅校验并扣选中当前owned key/quantity；旧count-only正文不补units，沿原fingerprint和绑定优先分支。
- 该规格要求“必须对照已存服务器窗口”“最多五个不重复正key/数量”：family_donation_protocol.py:16–52要求显式冻结窗口、复用原codec，对context/NPC/type逐一比较并校验units；不从请求生成expected窗口，不赋予NPC准入。原五行确认及marshal/consumer证据记录测试Adapter和未知历史context/mode/opaque，没有把夹具731/0/0称原服事实。
- FAMILY_VIEW_CONTRACT要求尾Q为客户端家族场景标识，真实绑定由main另接：faction_protocol.py:119–154仅纯投影完整signed63标识，旧构造兼容、默认0；不推导组织地址。ROOT_DECISION要求“每箱声望逻辑奖励只有5”：执行政策仅numeric_review元数据变化，两槽仍为同一逻辑5的既定投影，无新增消费/双份奖励授权。

独立验证：7候选、614依赖、636资源输入及11规格哈希匹配；固定资源副本补齐后同hash，未改候选。公开Store/Inventory临时库证明预留后选中key已移除时拒绝且不扣替代绑定箱；旧无units持久permit仍兼容；独立比较JSON确认只有numeric_review元数据变更。核阅固定源selection8组、原指令5组及原家族协议检查产物；18脚本完整回归仍续跑，汇总方须核最终结果/import-closure，不将首次资源装配失败当功能红灯。

未验：完整驻地/NPC准入、唯一资源source实际shared Peer、GUI、部署、跨库/生产容量及全套家族帮派修炼。未改source、历史r2、共享入口，未开游戏、服务端口或真人DB。