# World member metadata：Spec审查

固定范围：reviews/world-member-metadata-implementation-v1，manifest SHA12744038076a37193e9d77bae9a64aa076da2c93dd8a014f4ae34537b956d532。已核2份真实base、6份final、49份reference及SPEC哈希；无Git/commit，以changes.diff审查。方法为code-review Spec轴，依据固定SPEC、已接受MEMBER_BINDING_DECISION r2、GLOSSARY/ADR0001及架构。

## 发现

**P2：裸process_one拒绝配套模式之前，已消耗被接受的移动命令。**

SPEC第3项要求“Once registry configured, bare mutators refuse before change”。final/world_owner.py:513–519先执行`_mailbox.get_nowait()`，然后调用move；直到:621–622才由`_paired_members(None)`拒绝metadata模式。

已用冻结final的真实公开Interface运行：member_projection→join_with_view→submit一条合法STOP，返回accepted；inspect_lifecycle公开队列为1。调用裸process_one报`Use this owner's paired member projection`，队列却变0；随后正确process_one_with_view返回None，位置仍在原地。拒绝造成已接纳命令丢失，不能再以正确路径处理。

建议在dequeue前执行配套模式检查；加入“裸出队拒绝后，正确出队仍取得同一命令”的公开回归。此为新metadata opt-in路径缺口，不是当前已发布shared默认路径的现场故障。

## 其余范围

未发现其他明确Spec偏差。Domain固定注册实例/真实generation、同Location旧presence隔离、许可fence、metadata与AOI分离、loading/ready、受控freeze例外的实现与裁定相符。原型generation红、13组绿和9份旧回归范围明确；共享join研究准确保留repair BASE红和受控完成回调边界，没有冒称共享接线、Writer/client ACK或GUI完成。

结论：Spec开放1项P2。未复跑13组/9份长回归；只运行上述短公开队列probe，未改生产、冻结文件、服务、GUI或正式数据库。
