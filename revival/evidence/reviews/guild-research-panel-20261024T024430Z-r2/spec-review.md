# Spec

Spec：P0/P1/P2/P3均0；r1的P2已修复。按既读code-review/深Module方法完整复审，无新增可行动的缺失、范围夹带或错误实现。

契约13行“不把提交伪报失败”：独立真实Owner/Peer中，展示读OperationalError/DatabaseError/InterfaceError均返回已提交receipt；原query恢复当前值。实际receipt尾部IntegrityError仍向上传递，研究状态及组织revision全回滚，删除触发器后同事件只补一次；旧成功事件重放发送当前XP5。提交调用仍在catch外，未误吞结算错误。

整家族/成员双代次过滤、租约优先、未配置旧档仅空clear、完整原receiver另独立通过。7候选/675依赖/644资源/7规格、完整及repair差异哈希与重建均一致；26脚本全绿，160实际导入含runner逐Path/hash核对。

正式曲线、维护来源、NPC、地图准入和GUI仍未验。未改任何source或r1；证据见spec-independent-result.json、spec-fixed-results-audit.json。
