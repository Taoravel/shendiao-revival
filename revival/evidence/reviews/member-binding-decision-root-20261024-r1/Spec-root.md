# Spec 独立审查

缺失/部分1、额外行为0、错误实现0。本批是术语/裁定审查，不批准runtime或部署。

**[P2] 配套命令禁令遗漏原freeze路径。** 冻结细则 `ARCHITECTURE.md:33`要求“预留目标→冻结源移动→切换带版本的归属→确认后清源”。新增 `MEMBER_BINDING_DECISION.md:17`却列出join/move/leave/ready/resume/finalize后，普遍规定“已有成员时不得绕开配套路径直接改变权威成员状态”，未定义freeze的合法配套路径或例外。L21又要求冻结拒签、恢复保留fence代际。准确approved BASE的 `world_owner.py:645–666`只有原freeze（无freeze_with_view），必须将现有active成员改为frozen/version+1，真实 `game_runtime.py:909–911`正调用它。接入者若按L17禁掉原路径，原交接无法继续；若直接沿旧路径，则不清楚冻结期间投影的合法状态与幂等同步。应明确保留原reservation→freeze→activate协议，并说明freeze受控配套/只读拒签及cancel/resume怎样沿已fence世代同步；不要留下需实现者猜测的禁令。

其它内容符合：GLOSSARY区分真实成员关系、许可、快照/投影和AOI；决策L9–13固定真实Domain generation与唯一metadata view且不授RoleDelivery。L19–31要求captured presence、active/完整地址、可信连接代际、CAS控制身份及入队/编码前复核。L25的撤销投递与地图fence可通过受控异步阶段实现；L27–29明确不能把发起当生效，需实际屏障与pending gate，未把等待解释成全服锁。L35–39保持main独占、禁止捎带收费/资产和纯模块冒充shared完成。

方法：重读domain-modeling全文，沿用完整code-review/codebase-design；用同Location重入、旧callback、fence后freeze场景检验领域关系，并与实际原协议交叉。仅审两新增diff，四固定source SHA全匹配且末次再核稳定。原scope的diff SHA因CRLF记录错误，保留不改；采用 `scope-corrected.json`，前后SHA `3856d98324de0beab5d6bf929ea259af42494a7516b134b16eae8f1d9b372cea`，实际diff SHA `162817e8d5f6446f8bb4dabb3939e6789d9ca1a353408d36c295affb4ec14525`匹配。非Git，无commit。

仅静态；未执行模块/共享测试、DB、socket、服务、GUI或战斗，未读另一轴。实现、共享投递、运行时与商业容量均未由本轴验证。
