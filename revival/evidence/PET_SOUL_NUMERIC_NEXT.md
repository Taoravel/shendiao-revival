# 元魂恢复的下一实际链路：宠物最终属性与唯一资源

2026-10-24，当前实际穿戴/摘除控制器与本人装备原生列Adapter均已独立审查；批次分别查 `pet-soul-action-storage-batch.json` 和 `equipment-native-columns-batch.json`。全量目标active，本文件是下一实施片定位，不是功能完成凭据。

## 已经查明的实际依赖

元魂 `SoulRules.effects` 返回原始14类修正，尚不改变宠物最终属性。直接读当前原 `cattributedesconfig` 可联查7个flat numid→基础字段：81→80外伤、811→810内伤、101→100外防、821→820内防、151→150真气上限、141→140生命上限、131→130速度；112/122分别是110命中/120躲闪的percentid，不是flat。1551/1561/741/1581/1591分别是1550外防穿透/1560内防穿透/740外伤减免/1580内伤减免/1590毒伤减免的numid，原值为精确正/负比例。映射来自该表明确键，不使用“减1”猜映射。组合公式、比例参与阶段和上下限仍需原调用/端游资料/显式设计。

`pet_growth.Attributes` 已有7个flat字段和五维/潜能；尚无命中、躲闪和上述5个比例基线。不能给缺少的7项暗补0。现有唯一宠物HP/MP位于 `inventory_pet_growth.state`；`pet_growth_store._project/load_pet` 每次生成裸成长/血脉/石头属性，`Inventory._pet_state`、`pet_record`、`battle_loadout.selected_pet` 从这里读。新建第二份可写HP/MP会制造双权威，应先确定一个正式投影/资源Seam，并让这些实际消费者共同选择该政策，旧政策保持可识别。

新研究指向 `MedalManager` 的第一vector、CMingwen entry22“铭文·简易”的激活状态控制普通宠物有效元魂级上限+1；不是VIP、bit22或cmedalconfig同ID。完成证据与原getter复现以 `PET_SOUL_PRIVILEGE22_RESEARCH.md` 最终状态为准。未来真实reader应从明确known的铭文22来源读取，缺档不等于关闭；这是元魂上限来源，不自动构成地图/战斗操作许可。

## 直接继续的完成标准

1. 完成铭文22来源报告的父复现，明确原状态消息/条目与服务端持久来源之间哪些已知。采用新版本化、显式来源的角色只读权威输入；与真实世界/战斗许可组合，去掉控制器中外部flag fixture依赖。材料完整flags仍须真实来源，单独恢复，不从binding推全flags。
2. 按 codebase-design 明确成长、元魂、额外基线、最终属性和唯一宠物资源之间的Interface。TDD沿已授权真实角色事务与原生/战斗快照Seam，以“真实佩戴太阳珠使该宠物上限提高、当前HP不被暗回血；摘除降低上限并按明确政策clip；旧paid只读当前”作为下一纵片。须同批实际落库与原生/战斗输入组合，不停在另一个纯向量函数。
3. 原表7类flat先精确使用，百分比/额外基线在有针对性的第一方核对后仍未知才采用版本化designed政策；已知新角色初始化与历史完整导入分开，历史缺档不自动迁移。组合成长/血脉/石头时每个来源只算一次。
4. 元魂map/orb/材料/最终宠物caps与唯一HPMP、人物root库存source、成对凭据和当前原生编码必须同调用方事务。覆盖真实写失败/编码后失败回滚、旧epoch、缺来源、旧paid不复活/不回血、死人仍0、成长/换珠/等级上限变化和后续药物治疗。人物HP/MP保持独立；共享入口由main统一集成。

仍需继续：融合c0804目标/材料/flag语义与经验守恒、魂技效果和点化、完整宠物战斗/技能/资源、装备制造/强化等其余玩法、共享实际投递/部署与客户端可玩验收。完成任一候选不缩小全量目标。

方法：codebase-design在实际现有单一state及消费者处放置Seam，避免仅新增旁路结果；TDD下一片以真实HP/MP与资产联动而非复算向量断言验收；writing-for-agents把当前真实断点和逐项完成条件放在一起。本文只有源码/表联查与实施要求，没有宣称额外公式或真实许可/运行服完成。

## 本轮推进后的准确断点

条目1的铭文来源与真实reader部分现已实现并审查：`ROLE_MINGWEN_SOUL_SOURCE_INTEGRATION.md` / `role-mingwen-soul-source-batch.json`。完整22项来源实际落库/current CAS；元魂实际穿戴从持久铭文读cap2/scalar32，实际状态改rawActive2后旧paid严格只读当前cap1/scalar11；未付旧来源拒绝，新意图成功。世界/材料许可、真实铭文授予/付费/建角来源仍待恢复，不是整条许可链完成。

直接继续条目2的真实最终属性/唯一资源纵片。新证据 `PET_SOUL_FINAL_ATTRIBUTE_RESEARCH.md` / `pet-soul-final-attribute-research-batch.json` 已父独立重放全部3段：195/28/158原表全行、14显式映射/420原值、原float-map完整消费者和普通Pet绝对值消费者。**原c32c9会把比例小数截成0**，不能直接发Fraction后宣称生效；普通Pet9整数绝对属性可保真投影。比例客户端scale/显示路径未证，保留精确服务端比例并在发布门槛明示，不能静默丢弃另外7种修正。

现有实际结构的实施约束：`pet_growth_store.load_pet` 是Inventory、pet_record、battle_loadout和成长/用药的共同入口，最终投影须在这处真实Seam集中选择并防旧策略误读。源读者目前通过Inventory快照互相调用，直接在load_pet内调用SoulStorage.read/Mingwen.read会递归；应先在各自来源Module公开不依赖整份宠物投影的同事务只读来源Interface，复用原baseline/版本/provenance验证，避免复制私有SQL解码。源CAS及资产结算中间存在合法待结算状态；内部资产读取与最终caps/HPMP读取须明确区分，最终消息/战斗快照只能消费已结算来源。保持 `inventory_pet_growth.state` 唯一HP/MP，旧paid只读当前，默认旧政策及未采用实例继续可识别。不能用第二HPMP表、无门禁旁路快照或只改纯向量掩盖这些实际调用关系。
