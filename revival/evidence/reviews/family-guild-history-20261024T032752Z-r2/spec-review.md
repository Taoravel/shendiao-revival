# Spec

Spec：P0=0、P1=0、P2=1、P3=0。r1容量拒绝条目的问题已修，但公平性仍有一个缺口。

**[P2] 扫描轮无上界，已服务家族的后续事件可持续饥饿** — `family_maintenance_runtime.py:76–88`。契约25行要求“有界公平目录”。独立真实Store/actual scheduler：limit1/batch2，17号家族的加入已消费并ack，真实离帮仍pending；此后每轮只新增一个高ID家族，cursor依次33/49/65，17号离帮一直跳过。每轮结束仅两个pending家族，非增长过载；持续新ID使“无结果后绕回”永不发生。应固定每轮最高待处理family ID，走到该上界后开启新轮，再纳入新到ID。

其他无新发现。9候选/692依赖/647资源/6规格与完整/repair差异hash核验一致，完整diff可重建。独立trace及candidate绑定见spec-review.json；已明确实际来源、与r1已修边界的区别。

未改固定source或r1。全量社交、跨库、template7、GUI/NPC和商业容量仍未证明完成。
