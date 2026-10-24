# Spec 独立复审 r3

缺失0、额外行为0、错误0；未读取另一轴结论。r1的paid重授修正保留；本轮迟到初始Scene不再阻断真正当前CG的发送路径。

- 政策.2 L28“increment context generation so late callbacks cannot reinstall an old state”、L35“stale…never installs context”：候选 `runtime_movement.py:111–118`仅在完整current==expected、同map generation且当前context generation更高时抛专用SupersededMovementDelivery，发生在安装context前；不改pending或当前上下文。位置/版本、成员/epoch、完整地址或mapgen不同不进入此分类，仍普通ValueError。Role入口 `game_runtime.py:1007–1014`先验证当前连接/代际/scene token，foreign及closed也未被吞掉。
- L26要求“precise logical message…written and drained”：候选 `game_runtime.py:1211–1236`的类型、精确队列kind/body和pending_current预检仍在write前；只在实际write/drain之后的回调捕获专用异常，计数并继续下一条。预检失败、发送错误及其它回调异常仍关闭路径。因此有效CG开始使旧状态失效后，旧Scene终止不会重新装状态，也不会以通用ValueError终止其新CG队列。continue仍穿过L1239–1244的delivery清理、字节扣除及task_done。
- L22的intro授权与L23的battle恢复不退化：L569–571保留evidence非None才声明；close失效、原special Scene先终止再独立location0、transfer ready/确认及battle terminal仅此前normal成员恢复均未修改。其余四文件SHA不变，沿用前轮完整审阅；未扩大跳跃、客户端ACK或完整resync能力。

方法：沿用完整code-review/codebase-design，以map/role/connection Interface及异常传播检查状态所有权和发送终止；仅固定6项667行/51行增量及对应release/source。非Git：6candidate+4BASE+6previous、两diff、manifest/candidate记录和seal全部匹配；scope前后SHA `5bca435f554bc79b99423736480ee215f97b0bb0f1808c6b0413065911c2a83b`一致，6source末次再核稳定；seal `64fe9c419eb76aa2884429f65742c849273ec2abc522e47afaadf39de418e2b6`。

仅静态，未亲跑race/strict/terminals、44项或302图，不声明它们完成；未操作DB、服务、GUI、真人或战斗。最终准确运行验收仍由集成方闭合。
