# Spec 独立复审 r2

缺失0、额外行为0、错误实现0。r1发布接线缺失已在本固定三输入组合修复；保留r1报告。

- `NPC_ASSET_RESOURCE_INTEGRATION.md:9`要求“shared两条恢复分发均注入这对规则，去掉宠物kind的临时新profile拒绝门控”。候选 `runtime_storage.py:697–701`已直接成对注入并进入settle；实际发布 `game_runtime.py:584/628`的CRecovery及CNpcService均到此处，已知resource角色不再被前置guard拦截。与BASE逐字节比较，runtime_storage仅删除这两行；修理guard及整个其余文件保持（L689–695），没有repair扩权。kind2/4解除门控符合该既有专用source合同。
- 政策L23要求“fee, care/resources, sole asset/resource source…remain atomic”，L25要求“Lookup matching old paid receipts before evaluating any new price”。候选 `npc_recovery.py:245–305`保留npc.1共同/领域指纹、receipt-first及同事务最终编码；fresh宠物/费用后同步真实current source。实际release `role_equipment_storage.py:129–153` paid仅严格combine当前profile，拒绝pending，不补写或治疗；fresh只推进来源，晚期编码异常仍由原外层事务整体回滚。
- 报价两输入与r1字节一致：候选L130–170仍逐宠合法care/current power取个位、unknown明确45、present/orphan拒绝、free gate一次；原kind2资源价/inn保留。

方法：沿用完整code-review/codebase-design、ARCHITECTURE角色事务与DESIGN_AUTHORITY来源分级，沿真实Interface复核缺失修复及授权范围；未看Standards。非Git：3候选、2BASE SHA均与scope及实际两发布source一致，1新增政策base为空。scope SHA256 `bc98e8c8a49d3c5723208d79b8dcca64791044749cd38e3057c1071977950d32`；新增shared SHA256 `7d27f9c22b9eed3aa2eb7b67e63d51b208f61025f616ea411fb555bcb5b08df1`。

仅静态复核3输入/200diff行及必要消费者；未执行测试、DB、服务、GUI、真人角色或战斗。不将他方Owner测试视为本轴执行，也不宣称GUI或商业容量已验。
