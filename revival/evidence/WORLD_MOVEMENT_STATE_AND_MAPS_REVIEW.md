# 移动状态、逐图碰撞与历史传送纯读：固定双轴审查

2026-10-24。首版reviews/world-movement-state-and-maps-v1与修复版v2各自保留不可变base/final/reference/manifest/SPEC/changes.diff。7文件中唯一生产world_transfer_storage的真实修改前base为d034f37f…，其余6文件新建，无Git/commits。评审不是服务或GUI验收。

## 首版发现

Standards硬违规0／判断性异味0；Spec有1项P2：expected历史整数epoch1可能被三个Location的True／1.0数值别名冒充，因dataclass数值相等而被接受。父实际用公开租约接口和外部随机源夹具建立整数1，再现安全断言红；修复后三处epoch严格类型检查并规范JSON精确比较，9组绿。首版生产84ba69…与后续65e2709…不混用。

## Standards

Standards v2增量：硬规范违规0项；判断性代码异味0项。

已确认只有storage、reader verifier及交单三文件变化，全部final哈希匹配manifest；九组报告绑定本次storage／verifier字节。

world_transfer_storage.py:325–331的小helper集中检查三处epoch类型，供持久回执和调用方凭据共同使用，具有实际复用需求，未见不必要抽象。规范JSON比较保留类型差异；新增逻辑仍为内存校验与SELECT，没有新增事务控制、I/O入口或状态写者。

验证通过公开租约生成接口及外部随机源夹具建立整数epoch1，bool／float反例仍处于SQL authorizer保护下；交单准确记录原Spec P2及修复范围。该类型修复没有引入新的Standards问题。

仅静态只读增量复审，未重跑测试或启动服务／GUI。

## Spec

Spec复审：原P2关闭，新增0项可行动问题。

七个final文件实际哈希全部匹配manifest，地图及35例原生研究文件保持v1字节。

新增检查同时覆盖历史解码与expected receipt的三个epoch，拒绝bool/float；历史与expected改用规范JSON比较，避免dataclass数值别名。测试通过真实租约接口建立整数epoch1，并整体替换三处epoch，准确覆盖原漏洞；固定报告为9组通过，绑定最终storage65e2709c…。

当前checkpoint的完整地址、entry版本及其committed/ready来源检查未放宽；后来移动和同模板换实例仍返回当前状态，不重放旧目标。纯SELECT及调用方事务合同保持。

本次只读静态复审与哈希核对，未重新执行测试或修改文件。

Standards硬违规0、判断性异味0；Spec初版P2关闭、当前0项可行动问题。两轴分别保留。新302图领域报告绑定当前owner/movement，233图没有mask8合法非portal代表点仍如实记录；35例原native证据未扩成完整World/跳跃producer或服务器授权。World reader未接Task/shared；运行时碰撞仍须main接maze及可信state，整体恢复未完成。
