# Spec 独立复审 r2

缺失0、额外行为0、错误0；r1 EOF永久忙循环已修复，保留原报告。

- “有界后台探测”：候选 `staging/service_health_probe.py:5–14`每次接收前按同一绝对deadline设置剩余timeout，空字节立即ConnectionError，收数据后复核期限；保留同一真实FrameReader累计fragment，无EOF重试。launcher L108/L115确实调用此helper，L100–115的connect/601挑战/发送及接收heartbeat共用原30秒deadline，未在新阶段重置预算；sendall亦使用剩余时间。
- “approved source不可混/单owner”：launcher L19显式require，L49–51/L63–96/L109–123的批准身份、manifest/runner/all source、原controlled proof、110表/完整启动SHA、601及heartbeat检查均不依赖assert，-O不会移除。caller exact Job PIDList仍须包含caller且排除新PID；AnyJob仅在L128记录，没有添加“必须不在任何Job”的错误前提。只读正式库/备份与占用端口拒绝、无console的breakaway方式保持；不杀别的owner、不改宿主Job或增加自动迁移。
- 新verifier L33–52通过公开Socket/FrameReader Interface覆盖EOF一次终止、真实wire碎片、socket timeout、预先到期无I/O及两阶段共用预算；check/fails均显式抛错，优化模式仍保留断言语义。原b0 controlled-job工具字节未改；本次不扩为重启monitor或商业部署。

方法：沿用完整code-review/codebase-design，追踪调用方实际使用的helper、协议Adapter和优化模式失败分支；未读另一轴。非Git，固定3文件194diff行：3candidate、1BASE、diff与scope匹配；原controlled工具及approved204238 wire依赖SHA亦匹配。scope前后 `4fcb4733fef7a147920298bdceff084182f7b64f4525acf1a1006c08d3295894`一致，三源码末次再核稳定；候选launcher `79c055364c0699005987cd3a7ce538dc4a582eb1cdeb211ce66da39b99ebd0c0`。

仅静态读取；未亲跑普通/-O五组、controlledtest或新启动，未访问正式DB、服务、GUI或真人。跨调用/跨app与长期存活仍不由本轴声明。
