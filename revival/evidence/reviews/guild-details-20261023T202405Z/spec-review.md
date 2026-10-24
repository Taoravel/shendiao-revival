# Spec review

结论：1 个可行动发现，P2=1，P0/P1/P3=0；当前r1不能记为Spec通过。

## 发现

**[P2] 公告map错误缩窄原signed32键域。** `source/guild_detail_protocol.py:128` 使用 `_integers((key,),1,0,2**31)`，拒绝所有负键。规格 `GUILD_DETAILS_NATIVE_HANDOFF.md:20` 明确原布局为“map<i32,FactionBulletinDetail>”，32行要求“未知i32原样保留signed32”；34行列明的designed限制包括容器预算和重复键拒绝，没有非负键政策。公告key业务尚未绑定，codec不应猜测非负业务域。

独立原x86反例：用显式 `GuildDetails` 构造公告key=-1，`original_detail`执行原0xf90c50完整marshal成功，输出127字节；同一快照调用公开 `guild_details` 却抛 `invalid_guild_detail_scalar_group`。应将公告键改为完整[-2^31,2^31)并保留signed升序，增加负键、signed32两端及混合键的原marshal逐字节对照；越界/bool/重复仍须拒绝。

## 范围与其余结论

以第十九批固定source及since-family-history.diff审2个新文件，无码库Git/commit，采用精确冻结差异。沿用完整已读code-review、codebase-design、tdd、writing-for-agents，读取固定AGENTS/ARCHITECTURE/DESIGN_AUTHORITY及具体规格。逐项检查missing/partial、scope creep、wrong behavior；除上述缩窄外未发现其他可行动偏差。

all-required冻结快照保留原完整布局；原五intSkill、两intPractice、GuildCourse模板7三参数、raw标量组及tail没有猜赋金额/建筑/经验用途。三驻地1393/1395/1394分别使用slot0/1/2，signed63明确是本地sceneID约定，raw Q保留unsigned64位模式。原body限制65535与局部designed预算分开；无DB/schema、生产caller、准入、shared修改、部署或GUI集成声明。完整社交/家族帮派修炼仍active，其未完成部分不作为本次codec增量缺陷。

验证：2候选、644依赖、641资源、规格/diff/原disasm哈希匹配；核阅固定5项脚本均exit0，17个实际仓库Module哈希匹配，无未固定工作区代码导入。现有绿灯未覆盖独立实证的负公告键。未修改source/历史；补查只执行离线原x86与公开codec，没有游戏、真人库或正式端口。

未验：真实详情状态、raw业务含义、组织驻地准入、实际NPC/shared Peer、重连恢复、完整激活闭包、GUI及生产容量。