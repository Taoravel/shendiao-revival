# 社交窗口部署冻结状态

更新：已收到主策划解除冻结通知，且只读核对最新发布记录、PID8724与063445Z/run_release.py确认运行进程从不可变source副本导入。本窗口恢复所属模块的离线开发；shared入口仍交原始窗口。随后出现的新guild_training启动规则误拒已在所属Module修复，真实临时启动通过，见GUILD_TRAINING_STARTUP_FIX.md。下方是冻结期间的历史快照，不是当前开发状态。

本窗口在收到主集成首次冻结通知后，停止所有.py与政策JSON写入；后续仅只读、隔离临时数据库验证和evidence/文档记录。第二次冻结通知继续遵守。

本批未修改game_runtime.py、serve.py、gateway.py、accounts.py，也未修改social_runtime.py。没有自行启动/停止服务、客户端或战斗。

首次冻结前的本窗口源码改动：新增guild_offices.py、verify_guild_offices.py；faction_domain.py接组织事务内职位逻辑；verify_faction_runtime.py补测试夹具结构代次；faction_protocol.py新增纯职位枚举/辞职/授权编解码；design/recovery-baseline.json补职位规则、九授权位。它们仍是源码/隔离验证进度，原生帮派管理请求没有加入SOCIAL_TYPES。

以下哈希与mtime只反映当前磁盘，mtime不是编辑归属证据。部署时按实际快照记录；本文件不授权解冻、不宣称真实进程已加载。

```json
[
  {
    "path": "game_runtime.py",
    "sha256": "3e9e60da29e2ba4da4cac2d5a281523e99408d4246856d9c3dc6df5bf541323f",
    "modified_utc": "2026-10-23T06:37:38.733858+00:00"
  },
  {
    "path": "serve.py",
    "sha256": "bb9c316647f158378e0e4bb28a04d6d602ff1a21a5e202c38ec8773c64a78779",
    "modified_utc": "2026-10-23T03:17:13.413446+00:00"
  },
  {
    "path": "gateway.py",
    "sha256": "f10c45bae5870990a0092543496dc0e7e2a3b7f3e99c07fa28b6b87db4aba1b8",
    "modified_utc": "2026-10-23T03:17:13.414445+00:00"
  },
  {
    "path": "accounts.py",
    "sha256": "2f9022a4b40aaecffbd2bb57491f8f1678980e4a6405f8fc28e78d0099db34ff",
    "modified_utc": "2026-10-23T06:12:18.436408+00:00"
  },
  {
    "path": "social_runtime.py",
    "sha256": "d83d78234afb689d94fa3af83f289a90bc5616d3fd1674fcf28652954207bf7c",
    "modified_utc": "2026-10-23T05:54:12.403856+00:00"
  },
  {
    "path": "faction_domain.py",
    "sha256": "c7b9232221d893913a9fe9d7a753ab5138b3b6f988db63e0ca552d790069ee12",
    "modified_utc": "2026-10-23T06:22:42.583854+00:00"
  },
  {
    "path": "faction_protocol.py",
    "sha256": "5abb578f564805fd91a73a77061fdc88da3604145f11f978cb3d200bd623a0e0",
    "modified_utc": "2026-10-23T06:35:35.003624+00:00"
  },
  {
    "path": "guild_offices.py",
    "sha256": "22d4c0d22aa3ad6fe9ba297d10eb90429f0360df70c21e618100ca60f06662fa",
    "modified_utc": "2026-10-23T06:20:23.091363+00:00"
  },
  {
    "path": "verify_guild_offices.py",
    "sha256": "b3c88aac91746488da5dd1733cca1666ca6132ce394f5ece4d745faa4bd18ca4",
    "modified_utc": "2026-10-23T06:35:35.004626+00:00"
  },
  {
    "path": "verify_faction_runtime.py",
    "sha256": "2ac657bd921b204c353c495c57473ec46a35740f28d976ed6f988e2cce4710d2",
    "modified_utc": "2026-10-23T06:22:18.661834+00:00"
  },
  {
    "path": "design/recovery-baseline.json",
    "sha256": "f89c4a14c20169f902304feb2e04f2f958e09a2848b4ca6fc8422c76c0c892a2",
    "modified_utc": "2026-10-23T06:35:35.002623+00:00"
  }
]
```
