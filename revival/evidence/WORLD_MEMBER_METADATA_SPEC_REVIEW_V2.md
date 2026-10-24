# World member metadata：Spec复审v2

固定范围reviews/world-member-metadata-implementation-v2，manifest SHAb60c9a36e8e3c7f6e76cc9a44aaf10154ace36af810210d228d1b29c239e3819。已核2份base、6份final、56份reference及SPEC哈希；对比v1真实diff，唯一生产变更是在process_one出队前调用`_paired_members(None)`，RoleScene不变。初审记录及v1冻结保留。

**原P2关闭，新增0项可行动Spec问题。**

SPEC3要求裸mutator在状态变更前拒绝；现在错误消费者在get_nowait之前被拒绝，已接受命令仍可由正确配套消费者取得。新增第14组以公开submit/inspect_lifecycle/process_one/process_one_with_view观察：accepted后队列1，错误消费拒绝后仍1，正确消费位置推进至(7,104,100)且队列0。红/绿报告绑定相同新verifier，分别对应旧5ab41f…与新9a701d…的真实源hash，明确保留实际红。

本复审另独立运行冻结final的paired_dequeue_preserves_admitted组，显式--domain-source指向冻结final，exit0、输入前后稳定，两个核心Module路径确在冻结final。初次启动缺少helper搜索路径，尚未进入测试；补工作区只读helper路径后才实际执行通过，不把启动错误当实现反例。未复跑全部14组或10份旧回归；其冻结报告与范围已核，v2追加说明明确取代初始13/9计数。

Domain唯一投影/实际generation、完整captured presence、许可fence与metadata/AOI分离等其余生产实现未变。共享join在准确repair BASE的红仍明确未修，不以本片绿色覆盖；未声称共享接线、收费、Writer/client ACK、GUI或全目标完成。

方法沿用code-review Spec轴及真实公开Seam验证；未改生产/冻结文件，未操作服务、GUI或正式数据库。
