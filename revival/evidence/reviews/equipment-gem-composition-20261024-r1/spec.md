## Spec

按重新读取的 `code-review` Spec 方法审查固定11项新增内容；采用 manifest 的 absent-path／非Git适配，无虚构提交或tracker。未读取 Standards 报告。

输入：`verify_snapshot.py` 实跑PASS，1293项冻结依赖均匹配；11/11范围文件SHA逐一匹配。diff SHA256为 `ec94f5bc9a887a35ec856ceccfda75ceb8383c1d513d001bd3794274c7e924f1`。

(a) 缺失／部分：1项验证缺口。[P2] 原子验收依赖未进入冻结包。`EQUIPMENT_GEM_COMPOSITION_INTEGRATION.md:34` 要求“九处SQL故障、source更新后故障和当前编码失败回滚”；实际 `verify_equipment_gem_composition_atomic.py:22` 在初始化阶段因缺少 `design/world-movement-state-v1.json` 抛FileNotFoundError，尚未执行任何合成原子性断言。须在新固定包补齐准确依赖再独立执行；这不是已经证明的生产事务错误。

(b) 范围扩张：0。ordinary210／14族、600005 zaxue可信port及450/630独立体力符合两政策；技能ledger、共享入口、自动恢复和GUI明确留待接线，不能当作本片缺失。

(c) 看似实现但错误：1项。[P1] 数量恢复后会复用已经失效的材料来源。交付文档 :17 明确“任何通用奖励归并、拆分或整理改变数量/绑定/quality时，旧来源stamp失效，不能默认为flags0”。`equipment_gem_composition.py:181–201` 的stamp仅含当前模板／数量／绑定／quality；外部数量先减再补到原值就与旧stamp相等。已用冻结R1公开API独立复现：明确flags0的35001×3 → 外部AssetChange扣1 →普通grant补1，库存revision1→3，但新admit仍接受原metadata及quantity3。未知新入材料因此可被旧flags0来源接纳。新受理捕获当前库存版本不能识别此前的来源失效；需要随实例变化单调推进的材料来源版本，或各写入者同事务使旧来源失效，并加入此公开路径回归。

实际验证：指定Python／UTF-8、冻结current/revival下，五个新增verify中rules、主事务、sources、stamina四项PASS；atomic按上文失败。另上述公开API数量往返复现成功。已付SQL只读、两凭据不完整拒绝、原wire／450与630原codec和赋值有实际PASS；九处故障／真实root-source组合仍未获得本次独立运行反馈。

未验：生产技能ledger、真实迁移／恢复、共享RNG及加密投递、发布／GUI、完整宝石系统。未改冻结source或生产。

计数：缺失／部分1（验证依赖）；范围扩张0；实现错误1；Spec总计2。
