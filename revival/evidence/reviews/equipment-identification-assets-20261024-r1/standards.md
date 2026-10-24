# Standards 独立审查

方法：已读取并实际采用 Matt Pocock `code-review` Standards 轴与 `codebase-design`：按固定差异逐文件检查文档规则，再以 Fowler 基线检查判断性气味；关注角色所有权、事务 Interface 与领域规则的 Locality。未读取 Spec 轴报告。

固定比较：本项目非 Git，以 `manifest.json` 与 `changes.diff` 适配，不虚构提交历史。diff SHA256 实测为 `c24c933cef06f02f0ae3a8e0dbbdf8aa9c6a6e206474c18d6cf4f07078f77f13`；三个 production_scope 与四个 added_tests 的 current 文件 SHA 全部与 manifest 匹配。基线来源按 manifest 的 exact baseline proofs：inventory 为 pet-stones-batch，另外两项为 private-story-20261023T190051Z 发布 BASE。

硬规则依据：`current/AGENTS.md` 的归属与共享入口约束；`current/revival/ARCHITECTURE.md` 的单一写入者、同角色原子事务、不可变快照、启动加载配置与当前租约规则；`current/revival/DESIGN_AUTHORITY.md` 的来源分级、固定基础结果鉴定及同事务 CAS/费用/source/编码裁定。未发现 CODING_STANDARDS/CONTRIBUTING。

| 改动文件 / hunk | 硬规则结果 |
|---|---|
| inventory.py：Basis/Change 与三个新事务 Interface | 未发现违反；重读当前租约/完整实例/版本，不开独立提交，编码读当前 |
| equipment_detail.py：`_identify_fixed_clean` | 未发现违反；只改 identified，限定持久来源与完整 before JSON |
| design/currency-v1.json：新增现金 purpose | 未发现违反；明确 designed、单一规则及旧凭据兼容范围 |
| verify_equipment_identification_cas.py | 未发现违反；临时库验证 CAS、故障回滚、租约与原生详情 |
| verify_equipment_identification_currency.py | 未发现违反；验证现金专用、拒绝替代及旧凭据只读 |
| verify_equipment_identification_source.py | 未发现违反；验证实际唯一 source 同事务与资源保留 |
| verify_equipment_identification_npc_compat.py | 未发现违反；验证现有 NPC 消费公开资产 Interface，未改 NPC production |

判断性气味一项（非硬规则、可选改进）：**可能 Duplicated Code [P3]**，`current/revival/inventory.py:1243–1245` 与 `equipment_detail.py:148–149` 两个新增 hunk 均检查 `identified!=0`、`prefix_quality!=1`、`score!=0`、`base_properties!=...templates[template][0]`。同一个“固定干净结果”定义分散在两处，后续政策修订可能漂移。可由 equipment_detail 提供一个纯校验函数，两处继续调用，保留读取与写入前各自的校验时机和所有权围栏。

实际验证：在冻结树 current/revival、指定 Python、UTF-8 下执行 cas、currency、source、npc_compat 四个验证脚本，均 PASS；覆盖完整来源 CAS、现金与真实 source/凭据/晚期编码故障原子回滚、paid 严格只读和当前状态。生成证据仅位于该冻结树 evidence。未验共享加密路由、部署、真人存档、GUI、商业并发容量；本报告不等于全量系统验收。

计数：hard 0；smell 1（判断性 P3）。
