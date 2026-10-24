# 接手说明

## 先确认当前状态

1. 读 `revival/PROGRESS.md` 和对应模块的 `revival/evidence/` 报告，逐项区分源码实现、离线测试、集成、已部署和实机验收。
2. 改服务器状态、并发、数据库或网络投递前，读 `revival/ARCHITECTURE.md`；改玩法或数值前，读 `revival/DESIGN_AUTHORITY.md`。
3. 本仓库是各模块当前文件的归档，不是历史在线发布的复刻。文件哈希以 `MANIFEST.json` 为准；同一批文件不等于经过全系统验收的发行版。

完成标准：接手者能指明目标模块、资料来源和实际验收范围，再开展修改。

## 准备环境

- Windows 和 Python 3.12+。保留根目录与 `revival/` 的相对位置。
- `catalogs/`、`design/`、`decoded/` 已保存。`revival/runtime/` 在公开仓库中留空，由实际运行步骤生成。
- 原生对照工具依赖 `unicorn`，部分工具还依赖未公开的 `revival/evidence/native-image.bin`、本地候选快照或历史绝对路径；先查工具入口，不能假定所有 `verify_*.py` 都可直接运行。
- 原客户端版本依据本地资料为 1.6.1，网络协议版本 601；这两个版本号含义不同。

## 离线检查

从仓库根目录运行：

```text
python revival/verify_role_growth.py
python revival/verify_world_pathfinding.py
python revival/verify_group_quotas.py
python -m unittest discover -s revival -p verify_battle.py -v
```

前三项使用临时库或内存夹具，并在归档副本生成验证 JSON。最后一项只发现并执行 `BattleChecks` 单元测试，不执行文件脚本入口的原生对照段。这些检查不连接现有游戏服务；结果见 `ARCHIVE_VALIDATION.json`，通过的层次仅为相应限定检查。

完成标准：所选检查的退出码为 0；缺输入、报错或失败必须保留原结果。

## 本地服务与客户端入口

服务入口为 `python revival/serve.py`，监听 `127.0.0.1:28993`，使用 `revival/runtime/accounts.sqlite3`。只在独立目录、端口空闲且已确认运行规则后启动。归档批次未启动此入口，也未验证从空数据库启动。

真客户端相关入口是 `prepare_client.py`、`client_compat.py` 和 `launch_client.py`。先将相符原客户端置于根目录所需位置，再核对 `evidence/original-manifest.json` 中的原件哈希；准备工具会拒绝覆盖已有运行副本。原清单是特定安装环境的历史基准，先检查其条目，不能跳过哈希检查强行运行。

`inspect_client.py` 会扫描根目录中 `revival/` 以外的文件。重新提取原件时，建议另用干净客户端目录运行恢复工具，避免把本仓库文档、Git 元数据或归档文件混入原件基准。

`staging/` 中部署脚本引用历史 PID、候选清单和冻结目录，只作为恢复发布流程的资料；复用时先读其目标和验证条件。

## 未完成及待验证

原客户端黑屏/绘制、自然主线后续、战斗实际呈现、跨地图与重连、各系统最终集成及大量后续玩法仍需按路线逐项确认。历史局部成功和模块级测试不能替代当前客户端验收。

完整内容与边界由 `RESTORATION_ROADMAP.md`、模块报告和 `DESIGN_AUTHORITY.md` 维护。本说明只提供接手路径。

## 本地保留但未公开的内容

原安装目录、运行客户端副本、SQLite 玩家存档与备份、认证原始流、运行日志、原客户端内存映像，以及大量重复的候选/审查快照仍保留在原电脑。公开归档不具备还原这些私人运行数据的能力。
