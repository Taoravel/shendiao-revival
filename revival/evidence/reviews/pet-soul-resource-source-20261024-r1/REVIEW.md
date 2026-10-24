## Standards

# Standards

status: completed

固定对象：`changes.diff` SHA256 `06e4e08c6dc71e0479fde3a839a6d2021b0e9bc39012f1250b97ff5d3756bdb9`；1373项固定依赖。production_scope为空，仅测试和说明两个新增hunk，与清单一致且前批清单均缺席。无Git/tracker，沿用固定清单适配，无虚构提交或issue。独立Standards轴，未读取Spec报告。

## 发现

硬性违反：0。判断性气味：0。本轴无最高严重项。

沿用完整上下文中的code-review和codebase-design方法，复核本批四份标准文件哈希均与前批一致：`current/AGENTS.md`、`current/GLOSSARY.md`、`ARCHITECTURE.md`、`DESIGN_AUTHORITY.md`。

- 符合`ARCHITECTURE.md`的角色所有权、当前租约、同调用方事务与唯一资源存档约束。测试通过公开元魂CAS和两条真实资源来源Interface组合，未修改生产文件、增加资源写入者、使用全局锁或开启实际网络服务。
- fixture以临时AccountStore/Inventory建立角色、宠物与明确数值基线；已知零值有显式初始化来源，未声称迁移真实旧档。SQL仅用于明确测试基线和故障注入，最终状态从公开Inventory/元魂/资源profile读取；没有用私有方法、mock内部合作者或旁路数据库查询代替行为验证。
- 根资源凭据INSERT故障必须实际到达真实写入点，异常类型和标记均检查；回滚后公开完整状态相等。paid先拒绝待结算来源，成功后在SQL禁写条件下只读。预期70HP/40MP、100/100上限为独立fixture字面值，不以实现公式生成。
- 说明遵循`DESIGN_AUTHORITY.md`的证据与实现范围区分，明确这是已有组合行为补验，未伪造缺失实现红灯；付费动作、共享、GUI、战斗与容量仍另列未验证。

逐项判断全部12项气味基线，未发现值得提出的问题。测试中两个真实政策分支由局部fixture helpers收拢，未复制生产资源转换、伪造第二Adapter或引入假设性抽象。

## 实际验证

固定`current/revival`目录，指定Python、PYTHONUTF8=1：

`verify_pet_soul_resource_sources.py`独立执行exit0：普通v2与完整gem两条真实来源hook均加入元魂CAS；真实resource receipt故障回滚全部状态；70HP/40MP、上限和资源数值版本保留；paid严格SQL只读。

`verify_snapshot.py`验证前后均通过：1373项固定依赖及diff未改变；额外验证两新增路径和scope/base证明。

未验证：背包元魂双向保真、宠物最终属性、付费穿戴/摘除/融合、权限与材料、幂等控制器、共享接线、部署、加密投递、GUI、战斗和容量。未启动服务/客户端、读取真实角色库或修改固定输入。

Standards：0 hard / 0 judgement findings；本轴无最高严重项。


## Spec

# Spec

Status: completed

Independent Spec axis using the code-review and codebase-design Skills already read in full. Fixed diff `06e4e08c6dc71e0479fde3a839a6d2021b0e9bc39012f1250b97ff5d3756bdb9`, 1373 frozen dependencies; non-Git fixed-manifest adaptation with no invented commits/tracker. Only the new resource-source verification and its specification are in scope. No production changes are claimed. Standards report is not consulted.

Findings: 0.

Reviewed the two added paths against `evidence/PET_SOUL_RESOURCE_SOURCE_VERIFICATION.md`, the prior `PET_SOUL_SOURCE_FOUNDATION.md` / `ROLE_EQUIPMENT_GEMS_INTEGRATION.md` Interface conditions and the architecture's caller-owned same-role transaction requirement. No missing in-scope verification, incorrect asserted behavior or scope creep found.

The fixture creates actual temporary AccountStore/Inventory roles, pets and explicit known attribute/resource/equipment bases. It calls each real public ordinary-v2 and complete-gem source hook directly. The assertions independently require literal70HP/40MP,100/100 caps, unchanged resource numerical version and final attributes, with the committed root source revision matching the actual soul CAS inventory revision.

A real root receipt INSERT trigger fails after the soul CAS and source transition have begun; reopening via current public Interfaces verifies the complete soul, inventory and resource profile rolled back. A pending source is rejected by each paid branch; after fresh settlement, SQL write denial proves the paid path only reads the current state. The test exercises source synchronization, not a manufactured paid gameplay controller. No second resource writer, shared activation or missing-production red is claimed.

## Independent verification

Fixed working directory: `current/revival`. `PYTHONUTF8=1`; interpreter `C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`.

- `verify_pet_soul_resource_sources.py`: exit0; both actual root hooks, root receipt rollback, resource preservation and paid SQL-readonly checks passed.
- `verify_snapshot.py`: passed before and after; all1373 dependency hashes and the fixed diff remained unchanged.

No source/fixed inputs were modified, no Standards report was read, and no service/client or real role database was opened. Unverified: soul item metadata/flags, paid equip/remove/fusion admission/materials/receipts, final pet attributes, actual shared integration, encrypted delivery, deployment, GUI, battle effects and capacity.

Spec summary: 0 findings; no worst issue within this axis.


Standards: 0 hard / 0 judgement findings; Spec: 0 findings. No worst issue in either axis. Full restoration remains active.
