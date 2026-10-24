# 302资源图的真实加密运行时批量核验

2026-10-24。`verify_world_resource_runtime.py` 默认冻结完整源码/政策/catalog/原映像，在该副本执行全部302个available地图。全304配置中1302/1307原资源缺失，保持不可用，不映射替代。没有启动游戏/真实服务或修改真人数据。

## 实际结果

`world-resource-runtime-verification.json`：302图全部通过，每图两次真实加密登录（共604次）、两个原Scene解码、一个实际MOVE/STOP同格1像素步骤及断线重连。285图原本有NPC、17图原本为空；3443个原摆放完整key/config/name/位置与独立原catalog逐项一致，294批SAddUserScreen全部交原构造/decoder，并在观察者读取原链表每个实体内容。原439个空名字及175重复配置组保持，未以config ID去重，也未套服务器同一过滤器当expected。

完整map.pfs SHA256 `c81c813d8ac8b2d08d6f19e0bf6ffb1de1e6a9d1bc655b35fd7eb74e118d8c6d`，config.pfs `eee475d5ffe7eecbde99abc119c2b9b8faa899489e2f7e13533a8de81f40d915`；两个原档及实际源码前后一致，冻结副本逐文件manifest亦一致。报告记录受测模块实际路径/hash，代码变化不自动进入该副本。

## 准确fixture与边界

同一真实历史创建角色在安装新手政策前由公开create_role产生，不手删章节。每图只在离线无租约时用公开租约/保存接口建立**明确初始checkpoint**，确认没有durable实例绑定再保存；不伪造传送或自然入口，不覆盖已绑定实例。正式GameRuntime、Peer、RC4/MPPC、角色/地图Owner、checkpoint、断线与新租约重连均运行。

选择非portal、mask1清格中心→同格+1px，保留真正wild_move；当前暗雷Module的cell-equality在RNG前返回，因此没有替换wild/战斗、概率或宽限时间。MOVE仅意图，STOP实际落盘；重连保留精确坐标/版本及公共完整MapAddress。它未证明自然地图访问资格、远距离寻路、跨图、连续轨迹、碰撞拒绝、实例动态恢复或GUI。

**运行时碰撞仍有独立红例**：真实加密STOP可写入1006墙格。见WORLD_CURRENT_CELL_COLLISION_HANDOFF及world-encrypted-collision-verification.json；不能用302个clear正例覆盖这个缺口。新增显式current-cell领域Interface尚待唯一main接入。

NPC数量绿也不等于隐藏条件/朝向/模型演出恢复。1086条非零hide含义、64组重复配置不同dir、321条特殊14500..14999/bodytype5分支及原field48方向consumer继续按WORLD_FULL_RUNTIME_ENTITY_AUDIT追溯，未猜字段或修改NPC权限。

## 敏感性与方法

先用1006/1007两图跑通。初版错误期待断线后的location返回None，真实Interface应以StaleEpoch拒绝旧成员，修正测试后两图绿；不把该工具错误算作游戏缺陷。`--maps 1006 --fault-drop-npc-batch`在真正发包前丢首批，独立catalog对照准确exit1：原62条/实际0；报告world-resource-runtime-fault.json保存修改前首包hash与冻结输入，不称“没有崩溃”即通过。

方法：diagnosing-bugs用真实接口、独立catalog oracle及实际漏包故障建立反馈；codebase-design沿既有连接/角色/地图/存储Seam，不增加生产状态或共享写者；research核原数量、dir/hide/特殊consumer及真实碰撞负例；writing-for-agents共置正向范围与红缺口。固定审查状态另见WORLD_RESOURCE_RUNTIME_REVIEW。资料/运行时/原codec/GUI分别举证，全量目标仍未完成。
