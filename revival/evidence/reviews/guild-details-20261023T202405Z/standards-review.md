# Standards

结论：**Standards 1**，P0=0、P1=0、P2=1、P3=0。

## 可行动发现

**[P2] 公告键的非负限制缺少原生依据或已登记设计。** `source/guild_detail_protocol.py:128` 的 `_integers((key,),1,0,2**31)` 将原 `map<i32,...>` 键限制为非负数。在固定source的临时原bean中放入公告键 `-1`，原完整详情marshal正常产出 `ffffffff`，同一 `GuildDetails` 却被公开 `guild_details` 拒绝。当前文档仅登记重复键/容量等局部预算，没有非负公告键规则，公告业务语义仍未绑定。依据 `DESIGN_AUTHORITY.md:9`（服务端用途须另记证据）、`:11`（设计上下限集中登记）及`:28`（客户端证据优先），纯codec应保留已核验的signed32键；若要限制为非负，应先取得业务依据或明确登记上游领域政策。这是规范/证据问题，不是Fowler风格判断；不表示负键已获实际玩法授权。

## 方法与验证

按 code-review 独立Standards轴、codebase-design的纯Interface/所有权和 writing-for-agents的来源/完成条件审查；完整Fowler baseline仅作判断，仓库规则优先，工具强制格式项跳过。未发现其他有证据的smell。无Git，采用第十九批固定前后差异与哈希清单，未扩大到未改依赖。

独立核验2个候选、644个依赖源码、641项资源、6份规格/规范及资源清单、diff、原指令证据哈希，全部一致。从固定source执行 `verify_guild_details_native.main`，9组原生检查通过；另执行上述负公告键边界，复现原marshal成功而候选拒绝。所有报告写入回调在本次执行中禁用，没有改候选/历史或主任务结果。

其余已核对：无DB/状态写者/外部cipher或writer；所有详情字段必填，未用默认值补未知业务；冻结容器与局部预算明确，三Q的本地signed63约定与原64位wire分开；没有将客户端驻地gate当成服务器准入。

限制：真实详情领域、生产caller、实际准入/共享接线、GUI与组织激活闭包均未验收；本次未开游戏、真人库、端口或部署。本报告不将原生9组通过解释为完整玩法完成。

Standards 总计：1；最高严重级别：P2。
