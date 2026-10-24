# Spec review: empty-projection recovery fence

2026-10-24。沿用完整 `code-review`，重读AGENTS与`tdd`；按既定公开 `inspect_relocation` / `retire_recovered_relocation` Seam复核。对真实r1 before→r2 after执行 `git diff --no-index`，核manifest SHA `6a536ada07f956ca1b2f7f6fb0b0ac5c97b55f3a93dd59d9c4b5606429fc4cae`。原r1封存、审查及反例保持。

## Findings

**原 P2 已关闭；新增 open findings: 0。**

Owner的唯一实现差异是在取得实际current后、空幂等分支之前，无条件核当前与捕获的 `projection_generation`。因此相同旧Owner、相同原投影的空重试仍幂等，丢弃投影或替换同地址空投影均拒绝；其他成员/准备身份、SQL决定前提及唯一位置权威合同未变。新增公开projection断言覆盖首次清理后这一分支，而不只检查清理前的非空状态。

独立重放原反例：正确view首次清理后，原view重试返回无删除的空回执；None和foreign空view均报 `projection lifetime changed`，没有新状态被修改。结果为 `spec-empty-projection-r2.json`。原r1独立反例与封存red/green报告证实该断言确能抓住旧缺口，不把检查引导缺失资产误算领域红。

## Verification and limits

独立运行r2 reference全部11组，exit0；`spec-independent.json` 保留完整结果及追加来源绑定。执行前后逐项核before/after清单与reference1419项，关键实际生产导入及native_inspect来自reference。映像现由reference直接读取，SHA `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`；原map.pfs SHA `c81c813d8ac8b2d08d6f19e0bf6ffb1de1e6a9d1bc655b35fd7eb74e118d8c6d`。映像、map/config原包前后均稳定，完整哈希及实际导入路径见该报告。

未独立复跑最终旧10/9/5回归，只核封存及本次11组。结论限所属Module恢复能力；caller仍负责真实SQL提交和旧写者围栏，shared/cache、真实write/drain、入口政策、完整世界与GUI仍未验收。仅新增本轴报告及独立证据，没有修改封存源、共享文件、服务或真人状态。

Spec findings: **0 open**。
