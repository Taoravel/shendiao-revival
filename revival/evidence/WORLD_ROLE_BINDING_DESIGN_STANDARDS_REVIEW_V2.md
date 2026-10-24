# Standards v2 独立复审

固定范围：`reviews/world-role-binding-design-v2`，manifest SHA256 `309c9c93856ddef356bfc5aa5a0fdbbf79a5b535f7d08d6384fb2a2ceaffcf19`；3份新增final、27份reference，`/dev/null`基线，无Git/提交。全部文件与SPEC哈希匹配；初审另保留。

硬规范违规0项；判断性Fowler代码异味0项。

沿用code-review、codebase-design及固定AGENTS/ARCHITECTURE/DESIGN_AUTHORITY标准，实际对照v1/v2差异：两条拟议命令改收投递前捕获的不可变RolePresence，地图执行时核完整当前view及domain身份，禁止现场补新成员；符合单写所有权与陈旧回调围栏原则，没有散落手工拼字段或新增第二位置权威。

新增公开leave/rejoin观察证明同Location可对应不同membership_revision。9项观察、6项源码绑定与冻结final/reference一致；只证明现有契约，没有把未实现的查询/fence说成通过。R4说明仅去除旧观察数，发布/OS/全量与子集、GUI未验范围保持分开。

仅静态复审与哈希/报告核对；未重跑测试、操作服务或GUI、访问正式数据库/socket、修改生产或固定文件。新Interface实施及真实发送/收费/客户端验收仍待后续证明。
