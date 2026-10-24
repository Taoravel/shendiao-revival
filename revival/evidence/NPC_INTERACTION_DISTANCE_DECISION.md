# NPC交互距离补全

当前新候选采用NPC_INTERACTION_CELL_DECISION.md及npc-interaction-v2.json；本文保留旧v1及主动走近反馈的历史。原客户端已能在超过48的合法点直接发访问，见npc-client-visit-root-red及NPC_INTERACTION_COMPATIBILITY_AUDIT；不能据旧近点绿声称原点击兼容完成。

2026-10-23，主策划依据用户授权采用`design/npc-interaction-v1.json`。原客户端交互半径和原服容差仍未知；本裁定中的32/48均为designed，不把其他原实体操作中的48当作依据。

先执行客户端验证，再核对官方端游资料，结果见[BLOODMARK_INTERACTION_DISTANCE_RESEARCH.md](BLOODMARK_INTERACTION_DISTANCE_RESEARCH.md)。原血手印是1006/placement13/NPC10498，场景坐标1668/970。配置104/60乘16用于原导航参数1664/960，不能替换场景摆放坐标。官方剧情资料仅支持任务/NPC关联，没有距离数字。

## 复现与决定

真实隔离运行时自然intro→首师父→武器→装备→车夫→说书人100160后，从嘉兴360/2264向血手印接近，原mask1、state0、半径32失败：no_witness，visited44928。原调用记录在`bloodmark-approach-root-baseline.json`。最小检查只变半径，32失败、48成功；64/96仅作诊断，路径见`bloodmark-approach-radius-probe.json`。进一步枚举原NPC周围所有整数像素：32内合法点为0，最近合法点1668/1008距离38；48见证末点1656/1016距47.54。此证据支持恢复服局部政策，不是完整原客户端自动接近证明。

保留原摆放和碰撞，仅此三重身份使用48；其余NPC/摆放保持32。平方欧氏距离包含边界，单位为逻辑像素。默认和例外都从启动冻结规则读取；见证生成和实际MapOwner校验消费同一规则，完成条件是实际自然流程从此前红例继续通过当前实体复核，而非只把寻路脚本改绿。

## Interface及写者

NPC窗口单写交互规则Module、NpcScene与NpcLifecycle距离选择；原始集成窗口单写MapOwner启动注入及共享接线。资源原二元tuple形状保留，规则独立挂启动accounts快照。热命令不读文件，不接受客户端或任务调用方传来的临时半径。

启动加载须核对唯一精确原map/placement/NPC及1668/970，字段严格类型校验。当前完整MapAddress、map generation、绑定实体、role lease、位置版本、active状态以及提交时重新证明均保留；48不授予任务完成、穿墙或跨实例访问权。生命周期未来接入使用相同规则，避免两个权威距离。

## 本批状态

方法：diagnosing-bugs先实际红例，列采样/半径/坐标解释三假设，单变量半径探测并枚举合法点；research原包CRC、原导航指令和官方窄查后明确unknown；codebase-design把距离选择集中在地图拥有的NPC交互Interface；writing-for-agents分清根政策、领域写者和共享接线完成条件。

本文件创建时仅验证到原数据、红例和离线移动见证。随后NPC实现npc_interaction.prepare及冻结radius_for，由NpcScene/NpcLifecycle共用；Scene48、Lifecycle48和错误definition.id均实际红→绿。root独立原样verify_npc_interaction_rules八组绿，五文件含policy执行前后SHA稳定，见npc-interaction-root-verification.json：48包含边界/49拒绝、38合法点、其它identity32、当前location/lease/version/address/loading及生命周期generation围栏、旧key移除、新spawn不继承、strict startup及无热读均有反馈。替代身份为明确隔离fixture，未声称自然任务流程或原UI已验证。自然接近转绿、部署与GUI仍待实际证据。

随后main仅在工作区私有候选启动独立prepare并给MapOwner注入同一规则，见证读取radius_for。root独立默认无flag的verify_prologue_touch_runtime四组绿，12文件及policy前后SHA稳定，prologue-touch-runtime-root-natural-verification：原自然前缀、正常mask接近、ready3、早提交拒绝、成熟原CCommit、私有world/task同事务及重登同址。原32红保留为历史，未改placement/mask、未用approach fixture。root再新增并实际执行verify_prologue_touch_two_roles四组：两条自然handoff后同Runtime两完整私有owner、移动/current隔离及原world/school范围、冷恢复，初始私有checkpoint也无fixture。仍未证pool完整接线/回收/故障恢复、真实GUI或新规则部署；运行服36632仅治疗最小版。

NPC后续研究NPC_APPROACH_NATIVE_RESEARCH已进一步闭合原受控交互路径：原模型坐标转格点、欧氏距离截断<13，10498跳前置目标点/分区查询但保留距离。该48例不是自动停点或原server半径，不能把当前48改标client_verified，亦不把13格直接变成全服像素圆。
