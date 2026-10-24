# detached lifecycle tool r2最终复审

## Standards

Standards（本批3文件）：硬违规0；heuristic可行动发现0。

方法：沿用完整code-review/codebase-design，对固定194行差异逐hunk核对，并逐项判断全部12种Fowler启发。沿批准记录→不可变副本→启动→有预算读取的Interface/Seam检查；依据AGENTS、ARCHITECTURE有界I/O/实体作用域及DESIGN_AUTHORITY发布最终哈希规则。无Git/提交列表，两个新helper为空BASE；未读Spec结论。

原发现闭环：launch_detached_release.py:17–18、63–78、85–96、109–124使用显式require/raise；批准身份、manifest、runner/全部source、controlled实际结果、110表完整性、caller PID列表和最终startup身份等部署关键检查不再依赖可优化删除的assert。

service_health_probe.py:5–14集中原两处重复读取，recv空值立即ConnectionError，每次接收使用总deadline剩余预算且读取后复核；launcher:100–115连接、challenge、sendall、heartbeat共享一个deadline，不因新阶段重置。verify_service_health_probe.py:11–12、27–53以显式raise/check保留EOF、分片、socket timeout、已过期及跨阶段总预算五组真实判定，-O不删除这些条件。此处为静态确认，未执行。

原只读备份、占用端口拒绝、detached/breakaway、精确caller job PID排除、AnyJob独立记录及自有资源作用域未退化。无新全局玩法队列或第二服务owner。

审前后candidate/workspace/BASE/diff均匹配scope：launcher=79c055364c0699005987cd3a7ce538dc4a582eb1cdeb211ce66da39b99ebd0c0；helper=1d032df865c6d9ae9ec7d1e5658c2eb842bf5c6b8f68b458b3372185526b8d33；verifier=e101a9d3baec0b90182f35c4925a307c4093c521e5a1dd3c123b9b7e3a0f00f2；diff=8a48c4ff6108bc126ef73b167353c3fbaebc0d2a0437f726da0d1647ade4ebce。unchanged b0 controlled probe及wire依赖SHA亦匹配scope。

限制：b0自身assert未修改，本次不认证其-O下all_passed判定；部署方已显式核normal_died/detached_survived，不能只信all_passed。未启动服务/worker、访问DB/GUI或运行测试；跨tool/turn存活及真实故障恢复仍依独立执行证据。只新增本报告，未混入repair或gameplay源码。


## Spec

# Spec 独立复审 r2

缺失0、额外行为0、错误0；r1 EOF永久忙循环已修复，保留原报告。

- “有界后台探测”：候选 `staging/service_health_probe.py:5–14`每次接收前按同一绝对deadline设置剩余timeout，空字节立即ConnectionError，收数据后复核期限；保留同一真实FrameReader累计fragment，无EOF重试。launcher L108/L115确实调用此helper，L100–115的connect/601挑战/发送及接收heartbeat共用原30秒deadline，未在新阶段重置预算；sendall亦使用剩余时间。
- “approved source不可混/单owner”：launcher L19显式require，L49–51/L63–96/L109–123的批准身份、manifest/runner/all source、原controlled proof、110表/完整启动SHA、601及heartbeat检查均不依赖assert，-O不会移除。caller exact Job PIDList仍须包含caller且排除新PID；AnyJob仅在L128记录，没有添加“必须不在任何Job”的错误前提。只读正式库/备份与占用端口拒绝、无console的breakaway方式保持；不杀别的owner、不改宿主Job或增加自动迁移。
- 新verifier L33–52通过公开Socket/FrameReader Interface覆盖EOF一次终止、真实wire碎片、socket timeout、预先到期无I/O及两阶段共用预算；check/fails均显式抛错，优化模式仍保留断言语义。原b0 controlled-job工具字节未改；本次不扩为重启monitor或商业部署。

方法：沿用完整code-review/codebase-design，追踪调用方实际使用的helper、协议Adapter和优化模式失败分支；未读另一轴。非Git，固定3文件194diff行：3candidate、1BASE、diff与scope匹配；原controlled工具及approved204238 wire依赖SHA亦匹配。scope前后 `4fcb4733fef7a147920298bdceff084182f7b64f4525acf1a1006c08d3295894`一致，三源码末次再核稳定；候选launcher `79c055364c0699005987cd3a7ce538dc4a582eb1cdeb211ce66da39b99ebd0c0`。

仅静态读取；未亲跑普通/-O五组、controlledtest或新启动，未访问正式DB、服务、GUI或真人。跨调用/跨app与长期存活仍不由本轴声明。


## root实际复验及范围

root独立执行固定helper verifier五组，在正常Python和-O优化Python均exit0，实际wire来自approved204238/source，helper来自固定candidate/staging，3项工具和wire依赖SHA前后稳定。EOF只读一次即ConnectionError，原帧碎片拼装、timeout、预过期不I/O、两phase共用预算通过；没有开正式socket/DB或重启当前服务。原r1两轴发现保留，新部署路径关键批准/manifest/source/110表/startup/job全由显式require/raise防守；未修改b0 controlled试验仍允许测试assert，故不宣称整个b0优化判定已改写。launcher显式核其实际正常子进程死亡/独立子进程存活布尔量，并核b0源码SHA。

同一16276服务已实测新工具及goal-turn边界保留，完整1442/445和main110表/601/心跳报告已核。允许main在后续准确候选发布使用本冻结版本launcher/helper/control proof（3源码+dependency SHA），仍需每次独立runtime验收、BASE PID和无在线连接/一致备份；不允许因此跳过任何发布门槛。只验收staging宿主工具，无游戏功能/数据迁移/任务资格改变；手动完整app重启与长期容量未验证。
