# 世界移动验收：Spec 独立复审 v2

2026-10-24。沿 code-review Spec 轴及 diagnosing-bugs 的准确反例原则，只读比较固定v2与保留的v1。v2 manifest SHA256=`e341f15c3c648af0f63906974afd43b96a046cd11c7fb2028ccdd37a8704981a`；10个final、48个reference实际哈希均匹配。无Git/commits，未重跑302或原生/运行时程序，未启动服务、GUI或改shared；仅新增本审查记录，不覆盖初审。

## Spec：原P2关闭，新增0项

两条standalone入口在harness进入sys.path前，明确只允许verify_/research_/diagnose_命名的测试helper，并检查Python文件、pyc/pyd与包；原runtime_core/world_collision遮盖入口被覆盖。执行前后另核已加载candidate生产模块的实际来源并记录hash，inspect_client作为资产根工具显式例外，早期pfs/bxml在runtime类型加载前从candidate重载并重新绑定，防止缓存混源。

固定guard报告8项反事实准确区分旧冻结脚本实际执行未经批准的文件/包，与修后在导入之前拒绝；不是仅检查错误字符串。r3两条受测脚本报告均列117项actual production imports，输入稳定；没有把受控可信helper机制写成恶意代码沙箱。

r1全302仍是其原准确版本的历史反馈，r3普通/特殊两图保持diagnostic subset，不转签全量。late-finalize原probe不变，在准确r3再次保留预期红：domain权威不变、runtime cache被删及公开读取失败；没有把shared修复写成本批产物。19方向/10 shape与原指令、typed/XML/actor Adapter边界保持v1范围。

其余未变文件沿用初审无明确偏差的结论。本结论仅覆盖这10个固定验证/研究/交单文件；未审参考production为本批实现，不宣称完整地图、GUI、部署或全故障验收完成。
