# 世界移动验收：Spec 独立审查

2026-10-24。按 code-review 的 Spec 轴、diagnosing-bugs 的反例敏感性与实际路径原则，只读审查固定 `reviews/world-runtime-movement-acceptance-v1` 的 base→final；无 Git/commits，不审参考生产代码为本批实现。manifest SHA256=`9eb2641ca6868b835f390898e7a30e63f08e4710aa905ead3824a3be3d23f0b3`，10个final及33个reference实际哈希均匹配。未复跑302、原生研究或运行时测试，未启动游戏/服务或修改shared。

## Spec：1项 P2

**harness仍可遮盖未列出的核心生产模块。** SPEC第3项要求候选/harness类型一致并防核心生产遮盖；`final/verify_world_resource_runtime.py:44–48`、`final/verify_world_movement_delivery_boundaries.py:28–32`只拦截7个名字，随后把harness置于candidate之前。`runtime_core.py`、`runtime_story_maps.py`、`world_collision.py`等未被拦截。例如harness附带旧版runtime_core.py时，candidate的GameRuntime会实际使用该SerialOwner；候选manifest字节仍全部匹配。resource verifier的sources清单也未记录runtime_core/world_collision，且只对4个模块验证candidate目录，因此仍可能把混合执行归属为准确候选验收。建议用明确的测试helper允许名单或覆盖运行模块的遮盖检查，并核实际生产导入路径；两入口均加不运行长测的拒绝用例。当前冻结报告并未证明发生此污染，本发现针对入口允许的错误验收路径。

## 实查范围与限制

早到C003d先令joined为真并排除旧门槛，历史红与r2绿保持分离；全302报告只归200906Z，r2仅两图诊断。typed barrier保留精确kind/body。19方向与10 shape研究明确原指令、typed bean/XML/actor Adapter及单模型边界；未扩大为全NPC/GUI。late-finalize报告准确保留r2红，分别观察domain未变、cache被删和公开StaleEpoch，未伪装已修。其余未发现明确需求偏差。
