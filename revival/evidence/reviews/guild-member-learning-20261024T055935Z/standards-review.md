# Standards：第26批成员生活技能学习 r1

候选 SHA `98f81d7c1f1324372b345adf25e4f467f51ae6510aa4bd1d8bcf88ecb6b33eee`；对 accepted25r3 的精确冻结diff，无Git/commit列表。**P0/P1/P2/P3：0/0/3/0，需修复。**

文档标准问题：

- **P2 — 未知经验伪装为0。** `role_learning_costs.py:50` 沿通用 reader 的缺行默认值。真实学习支付后当前XP984，删除当前经验行，再重放原源返回成功/XP0/技能1。违反学习契约“缺XP记录不填0、重放读当前绝对余额”及 DESIGN_AUTHORITY 的未知旧档规则。学习当前读取须独立严格校验存在与signed64范围。
- **P2 — 新坏预留阻断旧修炼恢复。** `guild_runtime.py:79–81` 必须两类pending读取都成功才处理任何项。实际加密登录中，一个学习hold的body损坏使健康旧practice继续reserved、资材6；仅修复该body再nudge，旧practice取消、资材回9。违反 ARCHITECTURE 局部故障隔离和学习契约的旧恢复兼容。两类读取/逐项处理应隔离，坏源保留报错，不猜退款。
- **P2 — 只读展示失败中断已提交登录。** `guild_runtime.py:49–56` 仅捕ValueError。给生活技能reader注入OperationalError，真实Peer.login抛错时在线租约已注册，既有7项practice零投递；恢复reader后同endpoint初始化送出7项。应隔离此可选只读展示的预期SQLite错误，保留过时代次/超时围栏及结算错误传播。

Fowler判断性smell：未发现额外可行动项。方法：code-review完整12项基线与仓库标准分开判断；codebase-design核角色/guild事务及不可变许可Seam；writing-for-agents共置反例、身份和证据限制。

核10候选、772依赖、658冻结资源及副本、9规格、基准来源和精确重建diff。独立新脚本9领域组/6原生组（18购买边界），以及currency、practice、pill、practice_login回归均exit0；该次运行前后manifest资源核验通过。root34末核遇其他窗口pet政策漂移，最终两索引缺失，未记全套通过；额外运行时反例绑定固定Python及当时资源，非完整读取闭包。证据见standards-independent。

未验证正式费用/货币映射、main RoleOwner/raw购买、当前RP/目录producer、技能效果/熟练成长、真实GUI、跨库及商业容量。未改固定源码、共享文件或其他窗口资源。
