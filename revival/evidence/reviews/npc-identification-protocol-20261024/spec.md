# Spec

需求缺失：0项。额外范围：0项。错误实现：0项。

按已读code-review Spec、codebase-design、tdd及架构约束，依据冻结原研究与模型边界审查两个新文件；base/current四个真实字节SHA匹配manifest，无Git提交。

查询按compact vector<i32>、u64 NPC、i32 mode解码，保留顺序、重复、负key与全64位NPC；回复为u64 NPC、vector<pair<i32,i32>>、i32 mode，仅回复key须正数，state/mode保留signed32。确认严格三signed32，第二字段仍auxiliary_argument，未赋NPC/column/currency语义或mode2权限。max_items必须由调用者显式给出；精确长度及预算在分配向量前校验。

独立优先导入冻结current、仅将验证Module.OUT指向临时sink，六组通过：真实原decoder→同对象marshal oracle、空127/128计数、64位高位/signed边界、非法长度/预算、冻结及无文件I/O。未用Python往返代替原codec证据。

产物：本报告。纯wire Module未注册服务、修改资产或费用，也未宣称495查询/鉴定领域、shared、发布或GUI已接。未改生产/shared、政策、真人库、服务或冻结源。
