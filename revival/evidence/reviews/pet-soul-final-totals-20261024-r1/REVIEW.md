## Standards

# Standards

status: completed

硬性违反：0；判断性气味：0；本轴无最高严重项。独立沿用完整已读code-review、codebase-design，未读Spec报告。非Git固定清单适配，无虚构commit/tracker；diff SHA256 `bb6ee1a4758160b02096bf65aebc902a7e0d1a5d03c37562ab5befb970c7d1f9`。

按固定AGENTS/GLOSSARY/ARCHITECTURE/DESIGN_AUTHORITY审15个scope。实际load_pet以显式可选规则作逐宠政策分流；未采用维持原路径，旧reader明确拒绝已采用实例。来源helper抽出并复用原owned/provenance/baseline验证，不回调Inventory而递归，也不成为session准入。唯一HP/MP仍在inventory_pet_growth.state；新表只有基线/source/caps/version/receipt，没有第二可写资源副本。

角色epoch由实际Inventory事务fence，内部source writer只使用调用方连接。元魂map/资产、宠物资源完整CAS/receipt及root hook在同事务组合；paid只读当前，新租约可确认历史已付，旧租约新写拒绝。source pending时普通属性/ratio getters、native/battle消费及新admit拒绝，不能拿新caps配旧资源发布；已采用的旧change_pet（含旧paid分支）、aptitude/blood写者拒绝裸caps。schema/config仅startup，无连接/commit/send/全局锁或shared改写。

codebase-design实际用于核共同读取Seam、原始source与最终消费的区别及状态所有权。投影、原唯一资源和原生编码各有职责；pending包装承担真实守卫，并非空转Middle Man。12气味逐项考虑，无值得报告项；5个既有Module的修改围绕同一政策接入，没有无关散落职责。全部14类保留，flat/percent/有理数合计与cause明确designed，五比例显示/战斗pending没有被编码绿灯掩盖。

## 独立验证

固定current/revival、指定Python、PYTHONUTF8=1：4个新增驱动均exit0。原28珠/14映射字面算例、单次取整113/负−7/50、已采用共同reader、原native及实际battle核心、202/157上限与80HP保持/195裁剪、死亡0不复活、paid SQL只读、新epoch、7 SQL+2编码后异常整笔回滚通过。另3回归（pet_growth、pet_soul_storage、role_mingwen_source）均exit0。

前后snapshot exit0：1481依赖/diff不变；另核5个before逐字匹配前批、10路径前批缺席。只写报告，未操作固定输入、真实库/服务/客户端。

未验：其余采用后成长/道具cause、完整技能/比例显示与战斗、真实操作/材料许可、shared/部署/GUI/商业容量。

Standards：0 hard / 0 judgement findings；本轴无最高严重项。

## Spec

# Spec

Status: completed.

Findings: 0. No worst issue within this axis. Independent code-review Spec review; no Standards report read. Applied codebase-design to the shared `load_pet` Interface, owned raw-source readers, pending-consumer guards and caller-transaction resource Seam. Non-Git fixed-manifest adaptation; no invented commits/tracker. Diff SHA256 `bb6ee1a4758160b02096bf65aebc902a7e0d1a5d03c37562ab5befb970c7d1f9`.

Reviewed all15 scope paths against frozen integration instructions, selected totals policy, original final-attribute research and architecture/source rules. All14 modifiers are retained: canonical growth/blood/stones receive flat contributions once; two percent sums floor once; five signed rational sums retain signs and reject bounds overflow. Complete seven-field explicit extras are required. Source stamps contain actual growth/state, baseline/extras, canonical/final attributes, blood/stones and complete soul/Mingwen sources.

Actual common growth reads expose final totals; default old readers and adopted legacy growth writers, including historical receipt paths, refuse unsafe naked-cap use. Pending source snapshots cannot reach ordinary native/battle attributes or new soul admission. HP/MP remain solely in the original growth state; source changes preserve absolute values/downclip, medicine cannot decrease/revive, combat cannot heal. Full before-source/state/metadata CAS and durable receipts support current-only paid reads under a new valid lease. Integer native110/120 values require exact float32 representation; five ratios are explicitly pending, not silently truncated. No in-scope omission, wrong behavior or scope creep identified.

## Independent verification

Specified Python, PYTHONUTF8=1, fixed inputs:

- Four new drivers: exit0. All28 templates/14 mappings, literal hit113/ratio−7/50; final common reader/native/battle core; actual wear cap202/no heal, medicine195, original2-tool removal→cap157/clip, death0 unchanged; seven SQL/two late native rollbacks and old-epoch/current-only guards.
- Direct regressions: Mingwen source, original soul-action storage and pet growth, all exit0.
- Additional temporary-store public checks: exit0. Medicine/combat replay returns current70HP/20MP; cause conflicts/reversed directions refuse; pending read/native/battle/old-paid refuse without repair; outer rollback restores exact profile.
- Snapshot verifier before/after: exit0,1481 hashes and diff unchanged.

Only this report written. Unverified: remaining source-aware XP/allocation/blood/stones/return and other adopted mutators, actual world/material permission, ratio client scale/display/combat mechanisms, complete battle final settlement, shared routing/deployment/encrypted delivery/GUI/capacity. These remain explicit release gates; this candidate does not complete the full restoration goal.

Standards0 hard/0 judgement, no worst issue. Spec0 findings, no worst issue. Whole restoration goal active.
