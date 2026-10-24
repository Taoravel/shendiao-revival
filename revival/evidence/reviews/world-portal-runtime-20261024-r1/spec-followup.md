# Spec follow-up: original portal binding

2026-10-24。按 `code-review` Spec 轴复核新增伴随门槛，保留 `spec.md` 与原冻结脚本不改。此前 **P2 原 portal 配置与候选 catalog 未绑定，现关闭**：该门槛已独立执行成功，可以和主验收报告以同 manifest、原包及 catalog 哈希组成证据链，不需要修改正在运行的原冻结脚本。

检查对象 `verify_world_portal_source_binding.py` SHA256 `857c64f3343140cd24bb85da334d2f0ae99bed632373e0cd2de4942df13a2c3a`。代码以准确候选 PFS/BXML 解析器重新读原 `CMapConfig` 及每张配置地图对应 goto，casefold 查找且拒绝歧义；304张地图属性、全部6275条有序原 goto 行与候选 catalog 逐项比较。保持行数仅修改一个原 `destx` 的反例确实被 `Original goto rows differ` 拒绝，非仅数量断言。

本轴独立运行冻结伴随脚本，写入新 `source-binding-spec-reproduction.json`，exit0；其完整输出与父 `source-binding.json` SHA256完全相同。实际候选 catalog 哈希重新核对为 `22d74787c6e43d66bb8aa04d4b7e91befb9fe8897b0e1db780d71219c65cade6`；全部1442生产文件前后由该脚本逐项核对，manifest SHA256 `b4ad84e07328110ecedaf753be126c4c19d3f58eadac2f0a700f1dea699eb367`。

独立结果：142个 goto 表、6275条原行、227有向组合。1412/1413各25条，原配置目录 `familyPK1/2` 与原包目录 `familypk1/2` 的大小写差异已正确匹配。140表旧研究不能当作完整枚举；本次142结果取代其完整性结论，不改旧历史证据。

该伴随门槛的 map.pfs/config.pfs 整包哈希与已审主脚本 pilot 相同，父任务最终仍须将全212运行报告按同 manifest/原包/catalog SHA正式关联。本次复核时全212终局文件尚未出现，**没有宣称212全部通过、没有独立重跑212、没有证明目的坐标单位、原服规则或GUI**。九室内 incoming 为零的其他研究结论未在本Spec跟进中另行复跑，不借此扩大结论。

Spec follow-up: **P2 closed; remaining findings 0 within this reviewed scope**。生产/shared/服务/正式数据库均未修改。
