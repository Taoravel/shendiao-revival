# Spec

0项可确证缺陷、遗漏或越权。

沿用code-review独立Spec轴、codebase-design的角色调用方事务Seam，只审39796→候选的固定7文件。14个base/current哈希全匹配；候选manifest自身哈希匹配，1429个source条目逐项全匹配。非Git，无提交列表。

current/design/npc-role-healing-v1.json:12要求“restore current HP and MP to actual final caps”，:20–24规定fresh满/死拒绝、paid当前且不再收费。current/npc_role_healing.py:50–73仅绑定已核10380/1007/p34；:120–144严格当前profile、HP>0/缺失量与普通等级校验，以level×30现金及唯一资源/两凭据同事务；:115–119核paid原意图，:145–149只编码当前profile/钱包。game_runtime.py:559–560沿当前NPC证明分发到既有有界I/O，原战斗/交接门禁保留。资源/currency revision、其它服务及默认激活未改。

仅静态审查与文件哈希核验，未执行代码、DB、服务、GUI或战斗；不把当前workspace私有地图等并行增量归入本候选，真人效果及现场部署仍待验。
