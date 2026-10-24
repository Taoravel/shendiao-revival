# 客户端配套包

这是已准备的 Windows 本地客户端副本，版本资料为 1.6.1，协议版本 601。含原资源文件、已做启动兼容修正的 knightclient.exe 和指向 127.0.0.1:28993 的选服配置。

## 下载与解压

从同一 GitHub Release 下载以下三个 ZIP：

1. shendiao-revival-2026-10-24-source.zip
2. shendiao-client-2026-10-24-part1.zip
3. shendiao-client-2026-10-24-part2.zip

把三个 ZIP 都解压到同一个父目录，并合并其中同名的 shendiao-revival 文件夹。这两个客户端 ZIP 是可独立解压的文件分组，不需要拼接文件，也不是 7-Zip 多卷包。

完成后应当同时存在：

```text
shendiao-revival/revival/serve.py
shendiao-revival/revival/launch_client.py
shendiao-revival/revival/runtime/client/bin/knightclient.exe
shendiao-revival/revival/runtime/client/artres/map.pfs
```

## 启动

在 Windows 安装 Python 3.12+，从 shendiao-revival 根目录执行：

```text
python revival/serve.py
```

保持服务窗口运行，再用另一个终端在同一目录执行：

```text
python revival/launch_client.py
```

已有客户端副本已经做过准备，不需要再次运行 prepare_client.py 或 client_compat.py。使用 launch_client.py 启动，由它在所启动副本的内存中进行经过指令校验的 RGBA 兼容修正。直接运行安装目录的 launcher.exe 并不等价。

## 数据与验收范围

原安装日志、运行日志、报错文件、最近登录账号配置及账号/角色数据库未打入客户端包。此包仅选取原件清单中的客户端文件，并核验所有原件哈希；允许的原件差异只有已校验的客户端兼容候选和本地选服配置。文件校验清单见 CLIENT_MANIFEST.json。

下载源码与客户端能保留已有研究环境，但完整游戏仍未复原；本归档批次没有从空数据库启动服务或完成新机器、登录和 GUI 验收。运行要求和已知缺口见 HANDOFF.md 及模块报告。原有私人账号和角色存档仍仅保留在原电脑。

原客户端、资源及相关内容的权利归各自权利人；本归档不提供商业使用授权。
