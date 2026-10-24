# Standards

**Standards 0；P0/P1/P2/P3 均为 0。r1 的 P2 已修复。**

沿 code-review、codebase-design，对固定 AGENTS、架构、设计裁定及完整 Fowler 启发式作全量复审；硬标准违规0，判断性 smell 0。无 Git，使用第21批固定源、完整差异及 r1 修复差异。

独立复现原反例：提交后的 audience 读取抛 OperationalError，现在返回 accepted=7，持久经验7，正常重放一致；另注入真正的 receipt 写入 IntegrityError，异常仍向上传递，研究快照及组织 revision 全部保持。持久调用位于展示 try 之外，修复未吞提交失败。

7候选、4基线、675依赖、7规格、644资源、两份差异及原指令哈希全部匹配。独立公开 Peer 六组与原生三组全绿；26固定脚本与 stdout 哈希、160项实际导入（159个源 Module加runner）均核验通过，源和资源未变。证据见 standards-independent/checks.json。

收件人 Owner 内重读租约/双代次、当前绝对值编码及未知缓存清理符合既有所有权；无新广播后端或未知旧档初始化。仍未验生产曲线、正常维护源、正式NPC、GUI和容量；未改固定源、r1、真人库或服务。
