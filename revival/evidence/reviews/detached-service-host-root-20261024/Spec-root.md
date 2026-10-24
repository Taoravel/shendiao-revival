# Spec 独立审查

缺失0、额外行为0、错误1。

**[P2] 服务探测遇EOF永久忙循环。** 总目标为“保持本地服务可运行”；本工具应判定这次approved恢复是否成功。候选 `staging/launch_detached_release.py:99/104` 在等待101及心跳帧时，直接反复 `reader.feed(client.recv(...))`。准确approved204238依赖 `source/wire.py:58–75` 对b''返回空列表。若runner接受连接后在完整101或心跳回复前退出/关闭，recv会持续立即返回b''，5秒socket timeout无效；此时已离开L90–96的30秒connect期限，也不再poll子进程，工具既不失败退出也不能保存最终验收结果。应对空字节立即抛ConnectionError，并使整体协议探测受明确deadline约束。这不要求增加自动重启/monitor。

其余核对：r4 acceptance要求的明确release/manifest由launcher L54–65与runner hash及全部source逐项核对；未另移植玩法。L69–86遇占用只拒绝、不杀port owner；正式库只读快照/备份及前后110表核对。0x01000208无新console，caller PIDList明确排除新service；AnyJob仅记录而不误拒。controlled verifier L71–104仅创建/配置自有job，普通child归属与breakaway child分别验证，关闭自有job后核生死并按自有handle清理，不改宿主job。含义符合[Microsoft Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)、[QueryInformationJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-queryinformationjobobject)、[Process Creation Flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags)；NULL查询是当前immediate job，不把AnyJob等同该killjob。

方法：沿用完整code-review/codebase-design，以approved source/runner及进程/handle Interface追踪成功和故障路径；未读另一轴。非Git，仅两新增工具/248diff行；candidate两SHA及diff匹配scope，前后稳定：launcher `e30a6340cb5f6a39e45a5f2ffe9e042eb7c6d85e81445d1ccef8aa82c6b155df`；verifier `b0b44cb2e119128ab42a410a4b620df42d051cfbda03f4767f8b5660560a7d03`；scope `ea3b462c6df90aafc66fc46a4f8de9e6b4a2430eebaab6ad93f383ad91ee7fcb`。

仅静态/官方文档核对，未启动服务、controlledtest、GUI或访问正式DB。跨调用存活、跨app及长期稳定性未由本轴验证。
