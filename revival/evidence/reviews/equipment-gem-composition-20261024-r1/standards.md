# Standards 独立审查

方法：本批重新读取并采用 Matt Pocock `code-review` 与 `codebase-design`，逐新增 hunk 检查文档规则及完整 Fowler 基线，检查角色所有权、事务 Interface、不可变命令与 Locality。未读取 Spec 报告。

固定输入：非 Git manifest 适配，11 owned 路径为上一 R2 不存在的新增文件。`verify_snapshot.py` 实跑 PASS 1293 项冻结依赖；diff SHA256 为 `ec94f5bc9a887a35ec856ceccfda75ceb8383c1d513d001bd3794274c7e924f1`，11 owned SHA 全部匹配。未检查实时工作区。

标准来源：`current/AGENTS.md` 的职责及共享入口约束；`current/revival/ARCHITECTURE.md` 的单一写入者、当前租约、同角色同事务、不可变快照和启动加载配置；`current/revival/DESIGN_AUTHORITY.md` 的来源分级、来源与实测分报、小 Interface 隐藏状态细节。未发现 CODING_STANDARDS/CONTRIBUTING。

| 新增文件 / hunk | 硬规则检查 |
|---|---|
| equipment_gem_composition.py：规则、受理、fresh/paid、物料来源与编码 | 未发现明确硬规则违反；留一个判断项见下 |
| role_stamina.py：显式初始化、当前租约、版本消费与刷新 | 未发现违反；450/630独立于440/620，未知不补基线 |
| design/equipment-gem-composition-v1.json、design/role-stamina-v1.json | 未发现违反；明确本地设计、来源及未实现恢复 |
| verify_equipment_gem_composition_rules.py、verify_equipment_gem_composition.py、verify_equipment_gem_composition_atomic.py、verify_equipment_gem_composition_sources.py、verify_role_stamina.py | 未发现代码规则违反；执行结果分列如下 |
| evidence/EQUIPMENT_GEM_COMPOSITION_INTEGRATION.md、evidence/GEM_COMPOSITION_RESOURCE_SOURCE.md | 未发现违反；600005/class4杂学来源与测试 Adapter、生产 ledger 未有及共享接线责任区分明确 |

判断项：**possible Feature Envy [P3]**，`equipment_gem_composition.py:260–261,280–284` 自行生成 Inventory 的资产 fingerprint，再读取 `inventory_settlements`，要求 `asset==(_asset_fingerprint(change),'[]')`。合成 Module 因而依赖另一 Module 的私有凭据序列化和空结果字符串；Inventory 修改格式时要同步修改此处。建议 Inventory 提供同事务、严格只读的凭据核验 Interface，保留合成自己的双凭据完整性检查。这是维护性判断，不是单一写入者硬规则违反。

实际验证：指定 Python、UTF-8、冻结 current/revival 下，rules、composition、sources、stamina 四脚本 PASS。atomic **未通过启动**：`runtime_storage.prepare` 读取冻结包缺失的 `design/world-movement-state-v1.json` 抛 FileNotFoundError；故本次未重证九处 SQL/source/编码故障回滚。未补文件、未改冻结 source。

未验：生产600005 ledger/学习、体力自动恢复与真实基线、共享受理/RNG/加密投递、部署/GUI/商业容量；不宣称全量可玩。

计数：hard 0；smell 1（判断性 P3）；验证受阻 1。
