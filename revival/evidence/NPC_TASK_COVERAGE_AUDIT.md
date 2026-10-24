# NPC任务引用、摆放与公开领域能力核对

2026-10-24，NPC窗口。此页补全NPC_COMPLETION_AUDIT中未统计的任务引用层，不把通用服务注册或领域predicate当成完整可玩性。可复跑`audit_npc_task_coverage.py`；全量逐任务/逐引用值/静态缺口与11项关键输入SHA见`npc-task-coverage-audit.json`。无服务启动或真人库读取。

| 当前工作区范围 | 实际数量 | 解释 |
| --- | ---: | --- |
| 原派生任务记录 | 2460 | 原列表ID唯一，公开prepare_task_store加载后与全量源ID相等 |
| 正目标NPC任务 | 2003 | 原target.npc_id>0；含明确占位999999，不直接授权实体 |
| 15个公开task_domain predicate至少命中一个 | 1430 | 直接调用既有公开判定；不是该任务已受理、接线、完成或已部署 |
| 未被这15个predicate分类 | 1030 | 可能有其他专用Module；不判为1030个未实现任务 |
| 原正数引用值 | 1129 | target、DisPlayNPCID、两种对白speaker list及四个NPC命名attribute，保留各自来源角色 |
| 其中无NPC定义值 | 4 | 1/11/1366/999999；1含玩家speaker/分支字段，999999是占位，另外两值仍待来源核对；不生成四个NPC |
| 正目标NPC及地图无该图静态摆放 | 309 | 51条目标在别图有摆放，258条目标无静态摆放；不是309条都应补spawn |
| 上述309中命中公开predicate | 200 | 134普通对白、38交物、21结束对白、3问答、2交钱、1开始对白、1空scenario；优先核实际访问 |

动态活动、私有任务、室内地图与历史内容需要不同的真实来源/政策。比如新春任务使13922、雪玲珑11884、圣诞特使13160未有静态摆放；本页没有为它们选择当前时间、活动条件或权限。原NpcLifecycle的可信控制和实际内容注册仍须共享完成。

## 原102002/客栈老板：已复现的地图契约差异

`diagnose_npc_task_room_target.py`使用真实临时AccountStore、完整checkpoint、原1376/p1/NPC10157、GameRuntime和加密Peer。服务器专用offer_task合法授予102002后，拜访NPC成功但菜单不含该任务；原CCommit拒绝，实际RoleOwner邮箱取得准确`Task acceptance NPC mismatch`。受理前后TaskSnapshot一致，没有完成或发奖。约9秒反馈环原样两次复现；12项关键输入前后SHA一致，见`npc-task-room-target-diagnosis.json`。此为工作区诊断，未冒称在服48572已验。

`staging/inspect_npc_room_sources.py`另直接重读两原PFS，共7条目通过解压长度/CRC。原cmainmissioninfo的102002给ActiveInfoNpcID10157/ActiveInfoMapID1007；原cnpcconfig的10157给mapid1376，原1376/npc.xml确实在(532,920)放10157，原1007/npc.xml无它。两图原goto.xml各有25个格点相互连通；已和保存的world NPC/portal投影逐项相等。精确条目、CRC、SHA和记录见`npc-task-room-original-sources.json`。

收尾复核发现其他窗口在本批之后更新task_domain；先将原先成功的三个JSON保存在npc-task-audit-history-20261024-initial，再在新工作区原样重跑全量审计及同一Peer探针。数量和准确异常保持，当前两个报告的11/12输入收尾SHA再次匹配；初次SHA对应历史副本，未伪称它们与新源码相同。

三个假设：任务记录外层地图而NPC位于室内、任务引用已过时、原服另有动态摆放。原双向门及一致的NPC定义/摆放支持第一种解释，但没有证明原服务器接受规则；后两种尚无直接证据。首轮原资源探针对方向曾误写6而失败，改为只断言本题相关的id/坐标后通过，报告保留真实方向3；未为通过修改原资料或生产。

下一步交主策划/任务/地图单写方：核准精确任务→实际NPC地图的适用规则，再由所属Module实现，保留真实NpcInteraction、完整实例/epoch/位置版本和距离门禁。不能删除所有任务地图检查，也不能在1007伪造第二个10157。此诊断不是绕过地图边界的授权。

任务方后续已交task-room-target-research-delivery.json、TASK_ROOM_TARGET_NATIVE_RESEARCH及TASK_ROOM_TARGET_SEAM_AUDIT：原相同10157的五个任务确实混用1007/1376；其独立原生navigation选择NPC定义1376和(33,57)×16=(528,912)，不同于实际摆放(532,920)，精确原map-pair route查询也另有反馈。NPC窗口已核五产物及本窗口三份来源/反馈SHA一致，见npc-task-room-source-handoff-verification-20261024.json；没有声称本人重跑该原生任务探针。原服务器接受关系仍未知，该交付alias_authorized/implemented均false；下一步由root裁定精确allowlist、Task/World统一匹配Seam，不据navigation可达开放通用地图等价。

## 方法、产物与未验范围

codebase-design：复用公开TaskResources、task_domain predicates及实际NPC/角色Owner Seam，不复制任务资格算法；diagnosing-bugs：先构造原任务/原NPC约9秒真实反馈并两次复现，再以原资源区分三种可证伪解释，保留未解决的地图契约交所属方；writing-for-agents：将数值解释、重跑入口及下一步完成标准共置。产物为两个NPC所属审计/诊断脚本、一个只读原资源探针和三个JSON；没有修改task_domain、共享文件或原政策。

未验：2460任务的完整接取/完成/奖励、动态和私有NPC条件、309个静态缺口各自运行时行为、实际寻路/门户穿越、真实角色/GUI及部署。1430只是公开predicate命中，不替代这些完成条件。
