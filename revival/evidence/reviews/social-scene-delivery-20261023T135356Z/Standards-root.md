# Standards

硬性违规0；判断性问题0。candidate.json中两份baseline、四份candidate及规范SHA-256均实际匹配。非Git，无提交列表；只审固定两生产文件与两harness，已审RoleSnapshot保留。workspace-excluded.diff的guild.initial及组织closure明确不纳入候选范围。

沿用完整code-review／codebase-design和12项Fowler heuristic，按AGENTS、ARCHITECTURE及PRIVATE_SCENE_SCOPE_DECISION延迟投递合同核查。Delivery新增keyword-only冻结scene_key，严格验证／公共归一化，不改变原位置参数及继承字段顺序。SocialEndpoint先拒绝旧epoch／场景key，保留关系过滤；带key仅交异步共享hook，缺hook或拒绝不会回退通用连接投递，None沿原路径。中间转换保留原key，无新SQL、全服串行或跨Owner可变状态。

未见需行动的命名、重复、越权读取、空抽象等smell；共享hook为实际连接／场景围栏Seam。

仅静态审查及文件哈希核对，未运行harness、imports、DB、真实服务、GUI或战斗。共享ticket／pin／scene_token与真实drain终止、私有入场及收件人分发仍由主集成独立验证，不由本小增量证明。
