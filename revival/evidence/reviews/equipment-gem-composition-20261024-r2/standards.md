# Standards 独立复审（R2）

方法：沿用本批已读完整 Matt Pocock `code-review`、`codebase-design` 和 Fowler 基线，逐新增 hunk 检查硬规则，再检查判断性气味；关注角色事务 Interface、不可变命令与规则 Locality。未读取 Spec 报告。

固定输入：非 Git manifest 适配；11 owned 为相对上一鉴定 R2 的新增路径。`verify_snapshot.py` 实跑 PASS 1297 项冻结依赖，11 owned SHA 全部匹配；diff SHA256 为 `5b51333daba10cd633292594c91a51268ef97fbb4d57e8b53d51164c4db7eff4`。未访问实时源码或真实数据库。

规范源：`current/AGENTS.md` 的职责/共享入口约束；`current/revival/ARCHITECTURE.md` 的单一写入者、当前租约、同角色同事务、不可变快照及启动加载配置；`current/revival/DESIGN_AUTHORITY.md` 的来源分级、事实与实测分报、领域 Interface。未发现 CODING_STANDARDS/CONTRIBUTING。

| 新增文件 / hunk | 复审结果 |
|---|---|
| equipment_gem_composition.py：受理、fresh/paid、来源触发器与结果保存 | 未发现硬规则违反或新增气味；角色围栏与同事务 source/编码契约保持 |
| role_stamina.py：显式初始化、租约、版本消费及刷新 | 未发现违反或气味；450/630独立于440/620，未知不推基线 |
| design/equipment-gem-composition-v1.json、design/role-stamina-v1.json | 未发现违反或气味；来源、designed结算和未实现恢复明确 |
| verify_equipment_gem_composition_rules.py、verify_equipment_gem_composition.py、verify_equipment_gem_composition_atomic.py、verify_equipment_gem_composition_sources.py、verify_role_stamina.py | 未发现违反或气味；实际结果如下 |
| evidence/EQUIPMENT_GEM_COMPOSITION_INTEGRATION.md、evidence/GEM_COMPOSITION_RESOURCE_SOURCE.md | 未发现违反或气味；600005/class4杂学、可信 Adapter 与生产 ledger 缺口分开陈述 |

R1 **possible Feature Envy [P3] 已闭合**：`equipment_gem_composition.py:291–301` 只检查两份凭据是否存在，再由公开 `Inventory.apply_settlement` 自行验证资产 fingerprint 并解析 receipt；不再复制算法或依赖 `'[]'` 字符串。存在性守卫有阻止孤立历史误走 fresh 的实际用途。

另核 `prepare` 的所属来源失效触发器：通用数量/模板/绑定/quality更新或删除会删旧来源；`_save_known_result` 集中恢复本次已验证余料/产物。公开外部3→2→3回归确认相同最终数量不能重新取得旧来源，slot移动仍由受理版本围栏处理。未新增共享入口或第二资源写入者。

实际验证：指定 Python、UTF-8、R2/current/revival 下，五个新增 verify 脚本全部 PASS；包括九处真实 SQL故障、source后异常、晚期编码失败全回滚，稳定ID重试一次、paid禁DML，HP/MP/现金/活力保持。R1缺movement policy的执行阻碍已消除。

未验范围保持：生产600005 ledger/学习、体力自动恢复与真实基线、共享受理/RNG/加密投递、部署/GUI/商业容量；不宣称全量可玩。未修改冻结 source 或生产文件。

计数：hard 0；smell 0；R1判断项闭合 1。
