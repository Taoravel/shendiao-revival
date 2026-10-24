Standards：硬违规1；heuristic判断1。

硬违规：[P1] staging/launch_detached_release.py:58–68、86；verify_windows_detached_lifetime.py:80、91、97–98。批准状态、批准manifest、runner/source digest和controlled证明依赖assert。Python -O/PYTHONOPTIMIZE删除断言，可能启动未被该批准记录绑定的manifest/runner，且probe仍写all_passed=True；runner自身按manifest校验不能证明manifest获批。违反DESIGN_AUTHORITY“部署核对最终内容哈希、采用已核验不可变副本”的规则。改显式if/raise，或入口先强制拒绝优化模式；probe通过条件同样不可删除。[Python断言语义](https://docs.python.org/3/reference/simple_stmts.html#the-assert-statement)。

heuristic：[P2] Duplicated Code，launch_detached_release.py:99、104重复while not frames读取。若服务在完整greeting/heartbeat前关闭，recv返回b''，两循环均持续喂空数据；5秒socket timeout不会限制立即返回EOF，启动检查永久空转。提取共同read_frame Interface，明确EOF失败及总体deadline。[socket.recv](https://docs.python.org/3/library/socket.html#socket.socket.recv)。

方法：实际用code-review逐hunk审两新增文件/248行，逐项判断完整12种Fowler启发；codebase-design沿批准→启动→回执Seam，diagnosing-bugs用于判断controlled normal/detached反馈是否能捕获目标生命周期故障。本轴受只读限制，未自行执行RED/GREEN。标准AGENTS/ARCHITECTURE/DESIGN_AUTHORITY优先；未找到额外CONTRIBUTING/CODING_STANDARDS或相关GLOSSARY/ADR。

已核Win32 PIDList布局与NULL查询语义，AnyJob=true不单独算失败；自有job和稳定worker handles保持明确作用域，未见全局玩法串行或修改host job。这里只认可静态契约，不宣称跨turn生存已验。[Microsoft PIDList](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_process_id_list)。

审前后snapshot/workspace SHA与scope均匹配：launcher=e30a6340cb5f6a39e45a5f2ffe9e042eb7c6d85e81445d1ccef8aa82c6b155df；verifier=b0b44cb2e119128ab42a410a4b620df42d051cfbda03f4767f8b5660560a7d03；diff=6bd018a1abb6f5a2386ddf2b563038d62a763caf7db48738a00b153f7eb2c635。两文件为empty base，无Git/旧提交。未启动service/worker、访问DB、GUI或实际战斗；未读本批Spec结论，只新增本报告。

