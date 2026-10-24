# detached service host 第一批固定复核

## Standards

Standards：硬违规1；heuristic判断1。

硬违规：[P1] staging/launch_detached_release.py:58–68、86；verify_windows_detached_lifetime.py:80、91、97–98。批准状态、批准manifest、runner/source digest和controlled证明依赖assert。Python -O/PYTHONOPTIMIZE删除断言，可能启动未被该批准记录绑定的manifest/runner，且probe仍写all_passed=True；runner自身按manifest校验不能证明manifest获批。违反DESIGN_AUTHORITY“部署核对最终内容哈希、采用已核验不可变副本”的规则。改显式if/raise，或入口先强制拒绝优化模式；probe通过条件同样不可删除。[Python断言语义](https://docs.python.org/3/reference/simple_stmts.html#the-assert-statement)。

heuristic：[P2] Duplicated Code，launch_detached_release.py:99、104重复while not frames读取。若服务在完整greeting/heartbeat前关闭，recv返回b''，两循环均持续喂空数据；5秒socket timeout不会限制立即返回EOF，启动检查永久空转。提取共同read_frame Interface，明确EOF失败及总体deadline。[socket.recv](https://docs.python.org/3/library/socket.html#socket.socket.recv)。

方法：实际用code-review逐hunk审两新增文件/248行，逐项判断完整12种Fowler启发；codebase-design沿批准→启动→回执Seam，diagnosing-bugs用于判断controlled normal/detached反馈是否能捕获目标生命周期故障。本轴受只读限制，未自行执行RED/GREEN。标准AGENTS/ARCHITECTURE/DESIGN_AUTHORITY优先；未找到额外CONTRIBUTING/CODING_STANDARDS或相关GLOSSARY/ADR。

已核Win32 PIDList布局与NULL查询语义，AnyJob=true不单独算失败；自有job和稳定worker handles保持明确作用域，未见全局玩法串行或修改host job。这里只认可静态契约，不宣称跨turn生存已验。[Microsoft PIDList](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_process_id_list)。

审前后snapshot/workspace SHA与scope均匹配：launcher=e30a6340cb5f6a39e45a5f2ffe9e042eb7c6d85e81445d1ccef8aa82c6b155df；verifier=b0b44cb2e119128ab42a410a4b620df42d051cfbda03f4767f8b5660560a7d03；diff=6bd018a1abb6f5a2386ddf2b563038d62a763caf7db48738a00b153f7eb2c635。两文件为empty base，无Git/旧提交。未启动service/worker、访问DB、GUI或实际战斗；未读本批Spec结论，只新增本报告。



## Spec

# Spec 独立审查

缺失0、额外行为0、错误1。

**[P2] 服务探测遇EOF永久忙循环。** 总目标为“保持本地服务可运行”；本工具应判定这次approved恢复是否成功。候选 `staging/launch_detached_release.py:99/104` 在等待101及心跳帧时，直接反复 `reader.feed(client.recv(...))`。准确approved204238依赖 `source/wire.py:58–75` 对b''返回空列表。若runner接受连接后在完整101或心跳回复前退出/关闭，recv会持续立即返回b''，5秒socket timeout无效；此时已离开L90–96的30秒connect期限，也不再poll子进程，工具既不失败退出也不能保存最终验收结果。应对空字节立即抛ConnectionError，并使整体协议探测受明确deadline约束。这不要求增加自动重启/monitor。

其余核对：r4 acceptance要求的明确release/manifest由launcher L54–65与runner hash及全部source逐项核对；未另移植玩法。L69–86遇占用只拒绝、不杀port owner；正式库只读快照/备份及前后110表核对。0x01000208无新console，caller PIDList明确排除新service；AnyJob仅记录而不误拒。controlled verifier L71–104仅创建/配置自有job，普通child归属与breakaway child分别验证，关闭自有job后核生死并按自有handle清理，不改宿主job。含义符合[Microsoft Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)、[QueryInformationJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-queryinformationjobobject)、[Process Creation Flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags)；NULL查询是当前immediate job，不把AnyJob等同该killjob。

方法：沿用完整code-review/codebase-design，以approved source/runner及进程/handle Interface追踪成功和故障路径；未读另一轴。非Git，仅两新增工具/248diff行；candidate两SHA及diff匹配scope，前后稳定：launcher `e30a6340cb5f6a39e45a5f2ffe9e042eb7c6d85e81445d1ccef8aa82c6b155df`；verifier `b0b44cb2e119128ab42a410a4b620df42d051cfbda03f4767f8b5660560a7d03`；scope `ea3b462c6df90aafc66fc46a4f8de9e6b4a2430eebaab6ad93f383ad91ee7fcb`。

仅静态/官方文档核对，未启动服务、controlledtest、GUI或访问正式DB。跨调用存活、跨app及长期稳定性未由本轴验证。


## 实际运行证据与下一步

root已对固定b0 probe原逻辑独立运行，仅ROOT报告目录外置：明确自有hJob关闭，normal child死、breakaway child保持存活、AnyJob=true，全部worker稳定handle清理，无host job/服务/DB修改；root-controlled-test.json保存。新服务16276已不在main实际caller immediate job的PIDList，launcher已退出后root多个独立tool OS/liveness通过，1442源码/445完整startup与批准manifest相等，main601/心跳/110表不变已只读核，报告detached-service-root-verification-20261024.json。未因AnyJob=true误判其仍属tool killjob。

当前游戏服务不重启；修两项staging工具缺陷：批准/源/runner关键校验不能被优化删，读取EOF立即失败并使整个probe预算有界。两轴只判固定e30/b0，改后另冻r2增量复审，不能改旧scope或假称原静态0。原所有历史退出无直接exitcode，当前证据支持宿主生命周期机制，不冒称全部旧事件因果已证。下一goal turn将复查16276过实际turn边界仍在。
