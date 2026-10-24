# Spec 独立复审 r4

缺失0、额外行为0、错误0。未读取另一轴结论；仅就冻结实现复核旧地图回执与当前投影的归属，不以他方probe结论代替静态证据。

政策.2 L25–28要求“exact current membership/position version”及旧代不能重装，L33要求上下文与当前位置一起推进；ARCHITECTURE要求当前实例/租约唯一Owner。候选 `game_runtime.py:183–189`现在先核返回Location属于本map且等于Domain当前完整Location，才投影；仅实际projected改变时失效。准确release `world_owner.py:650–652/677–680/775–777`确实可能幂等返回历史freeze/activate/resume：新epoch或同epoch后续version与旧Location不等，故不能覆盖缓存或撤销新context；当前activate的loading重复及当前resume重复projected相等，亦不再毁掉pending/admitted context。首次真实转换仍更新投影，ready仍保留其既有确认语义。

`world_owner.py:705–729`的正常finalize删除Domain frozen源但返回目标receipt；候选L183的本map核对防止把目标写回源。L190–197只有cached epoch/完整position/version均等该frozen source且Domain已无成员才清理：正常旧frozen缓存可清、同ID新租约或后续成员不能被旧幂等finalize删掉。此处无跨Owner等待，判定和更新仍在所属map执行器。

其它五文件SHA与r3一致，沿用完整审阅；paid evidence guard仍在L580，postdrain专用迟到处理仍在L1241，发送前typed barrier/精确body、finally清理、special Scene/location顺序和仅此前normal成员battle恢复未改。本修复没有把历史receipt视为新权限，也未扩大移动/战斗范围。

方法：沿用完整code-review/codebase-design，通过真实Interface、Domain幂等返回与缓存投影逐项对照；非Git，固定6项681行/32行增量。6candidate+4BASE+6previous SHA、两diff、manifest/candidate记录及seal均匹配；scope前后SHA `b6ca0fc530494f5e66cec9bc95df2ca728c671bc95cd9251dd3365b9d6984cde`相同，6source末次复核稳定；seal `4dcc6a0b0b3aea28d338508dd081419e1294bd498aa9d7ef683ac23ff1287917`。

仅静态，未亲跑lateprobe/10replay/46checks或302图；准确运行验收仍由集成方闭合。未操作DB、服务、GUI、真人或战斗。
