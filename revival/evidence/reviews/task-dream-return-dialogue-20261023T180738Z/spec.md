# Spec 轴

固定范围：两个新文件对空基线的367行changes.diff；manifest内全部source SHA逐项匹配。无Git历史，不虚构提交或merge-base。沿code-review独立Spec轴，未以Standards替代；只静态/哈希，未运行DB、客户端或线上。

## 发现

**[P3][c：验证声称过宽] 第一族组合缺前提，不能标成单独战斗前驱围栏已验证。**

Spec：`source/evidence/PROLOGUE_DREAM_RETURN_RESEARCH.md:12`明确“第一族紧前是原type40/AI8002”，并要求不越过真实前置；本批委派要求fixture与验证声称如实对应。

`source/verify_task_prologue_return_dialogue.py:77`对100111的拒绝样本同时缺少该任务active、AI8002完成，并沿用第二族10140/placement6证明。`source/task_prologue_return_dialogue.py:150`先因任务不active短路，未执行`:151`的前驱条件，也未进入第一族NPC检查。因此verifier`:111`的通过标签“first-family absent combat predecessor refuses”不能作为单独前驱fencing的实际反馈，会使后续交接高估该负例覆盖。建议仅改成“第一族未激活/缺前驱组合上下文拒绝；未独立验证战斗前驱条件”，保留`:116`有效post-AI8002案例未验；不要求伪造胜利或扩大测试。

## 其余核对

未发现有据的(a)本批要求缺失或(b)扩域。精确两族20ID、43路线顺序、旧族排除、原奖励/Jump字段与NPC摆放由loader核对；章节/现有active/前驱、私有目录和已采用地址、当前NPC proof、完整位置、任务revision、连接/地图generation、租约与期限在开窗/提交路径核对。菜单保留原真实key、显式ready刷新；输出保持raw unresolved且settlement_authorized=False。模块无DDL、世界/任务/奖励写入或坐标采用。

本批未授权的结算、传送政策、激活、shared/deploy不报缺陷。未复跑既有五组检查；第一族有效post-AI8002、自然完整故事及GUI仍未验证。结论：1项P3验证文案问题，未发现功能性Spec缺陷。
