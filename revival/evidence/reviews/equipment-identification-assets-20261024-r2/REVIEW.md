# 固定基础结果鉴定资产 R2 双轴审查

固定manifest/差异为本非Git项目的审查适配，不虚构Git历史或issue。R1的一项P3重复判据已在审查阶段集中并复审，两个独立轴分别核SHA并运行四个冻结验证。

## Standards

方法：沿用上下文完整的 Matt Pocock `code-review` Standards 轴及 `codebase-design`，逐 hunk 检查文档规则，并独立检查完整 Fowler 气味基线；关注领域判据的 Locality 与事务 Interface。未读取 Spec 报告，未改冻结 source 或生产文件。

固定输入：本项目非 Git，以 manifest/changes.diff 适配。diff SHA256 实测为 `8839a50cdc1669f84ce045721b1a3035ede1373fb55480121ebdac32c2b4b752`。三个 production_scope 与四个 added_tests 的 current SHA 全部匹配 manifest；标准源实际 SHA 也匹配且与已读 R1 一致。基线沿用 R1 已证明的 pet-stones-batch inventory 与 private-story-20261023T190051Z 另外两项 BASE，无虚构 Git 历史。

规则来源：`current/AGENTS.md` 的归属/共享入口要求；`current/revival/ARCHITECTURE.md` 的单一写入者、当前租约、同角色原子事务、不可变快照与启动加载配置；`current/revival/DESIGN_AUTHORITY.md` 的来源分级及固定结果鉴定裁定。未发现 CODING_STANDARDS/CONTRIBUTING。

| 改动文件 / hunk | 复审结果 |
|---|---|
| inventory.py：Basis/Change、读门禁、写 CAS、当前 tips | 无硬规则违反；origin、租约、完整实例/JSON 与库存版本围栏保留 |
| equipment_detail.py：共用结构判据与写前更新 | 无硬规则违反；固定结果校验集中，写前仍再次调用；只更新 identified |
| design/currency-v1.json：现金 purpose | 无硬规则违反或新增气味；设计来源、旧 revision/凭据兼容与范围明确 |
| verify_equipment_identification_cas.py | 无硬规则违反或新增气味；覆盖版本/来源/租约及晚期故障 |
| verify_equipment_identification_currency.py | 无硬规则违反或新增气味；覆盖现金专用、拒绝替代与旧凭据 |
| verify_equipment_identification_source.py | 无硬规则违反或新增气味；覆盖真实唯一 source 原子更新与资源保持 |
| verify_equipment_identification_npc_compat.py | 无硬规则违反或新增气味；覆盖现有 NPC 公开资产 Interface 消费与只读 paid |

R1 判断性 **Duplicated Code [P3] 已闭合**：`equipment_detail.py:94–99` 的 `DetailRules.fixed_clean_unidentified` 统一 identified0/prefix1/score0/原模板完整 map 判据；`inventory.py:1243` 与 `equipment_detail.py:154` 分别调用。抽取仅集中纯结构规则，未削弱两次校验时机，也未混入 NPC 权限、价格或持久来源。新增函数承载被两处实际复用的领域判断，未形成空转发层或假设性 Seam。

实际验证：指定 Python、UTF-8、R2/current/revival 下，四个 `verify_equipment_identification_{cas,currency,source,npc_compat}.py` 全部 PASS。反馈包括完整 CAS、现金/source/凭据/编码故障全回滚、paid 严格只读与后续当前状态保持。证据写在该冻结树 evidence。未验共享加密路由、部署、真人存档、GUI 或商业容量；不据此宣布全量系统验收。

计数：hard 0；smell 0；R1 判断项已闭合 1。

## Spec

沿用完整在上下文的 `code-review` Spec 方法：冻结 diff 对照 NPC 单一政策／决定文档，静态审查与实际验证分别举证。范围为生产三文件及新增四测试；NPC 生产仅为只读依赖，未读取 Standards 报告。

输入验证：R2 `changes.diff` SHA256 `8839a50cdc1669f84ce045721b1a3035ede1373fb55480121ebdac32c2b4b752` 与 manifest 一致；7/7 current 审查文件、3/3 base 文件逐一匹配。原政策、决定及架构／来源边界文件 SHA 与 R1 相同；沿用同一已证明 BASE，不虚构 Git 历史。

(a) 缺失／部分需求：0。政策 `design/npc-equipment-identification-v1.json:23–24` 要求“already persisted…explicit_known_clean_instance”及“Preserve slot, binding, quality, condition”。`inventory.py:1230–1266` 仍检查当前租约、库存版本、携带量1、普通非特殊模板、已知color1、完整实例及持久来源；NPC继续唯一持有ticket／报价／扣费／领域凭据。

(b) 范围扩张：0。`equipment_detail.py:94–99` 的 `fixed_clean_unidentified` 仅集中原有固定结果判据，读门禁与写前各自调用；未改变默认生成、存量、随机属性或共享激活。政策 :39 的隔离实现／临时验证边界仍保持。

(c) 看似实现但错误：0。政策 :34 明确“revision+origin+full before JSON and expected inventory_revision；…identified0 to1 only”。`inventory.py:1250–1266` 的完整basis比较及库存CAS和 `equipment_detail.py:147–162` 的原JSON／来源CAS保持；新helper仍精确要求identified0、prefix1、score0及canonical基础map。公开同事务当前tips与cash-only追加purpose未改变。

实际验证：在 R2/current/revival，以指定Python及UTF-8独立运行四个 `verify_equipment_identification_{cas,currency,source,npc_compat}.py`，全部退出0／PASS。验证反馈包括六槽原生详情字段保留、版本／原JSON／旧租约拒绝、旧币种凭据兼容、实际钱包／唯一source／NPC凭据及晚期编码全回滚、严格只读已付重试与后来移动保留。证据仅生成于冻结 current/revival/evidence。

未验证：真实GUI、共享加密入口、部署、商业数据库及容量；不据此判定该资产片缺失。

计数：缺失／部分0；范围扩张0；实现错误0；Spec总计0。

总计：Standards硬规则0、判断项0（该轴无最严重问题）；Spec0（该轴无最严重问题）。仅本固定结果资产片，未代表共享路由/发布/GUI或全量验收。
