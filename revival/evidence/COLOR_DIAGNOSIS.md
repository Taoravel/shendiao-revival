# 创建角色界面颜色诊断

采用 `diagnosing-bugs` 的截图回放、最小化、对照假设与单变量像素比较；
采用 `research` 直接核对原 PFS、imageset/layout 和已解包程序。此处未修改
原资源、运行客户端或构图，也没有生成/重绘素材。

## 已证实的范围

左侧头像颜色异常不是原头像画成蓝皮肤。原资源
`artres/ui.pfs:imagesets/maincontrol20.tga` 的头像有正常肤色；同一张 atlas
还包含选择框、攻击/站立按钮。截图中这些控件原本蓝色的部分变为金色。
这组变化符合该 atlas 在渲染路径中发生 R/B 通道互换。

1. 原 `maincontrol20.imageset` 指向 `MainControl20.tga`；头像 `Head9`
   区域为 x704/y528/w200/h108，是截图左上云夕头像。
2. 用 Pillow 标准 TGA 解码器从原 PFS 载荷转换 PNG，生成
   `maincontrol20-original.png`；这是格式转换，没有改色。
3. 原 atlas 肤色点 `(808,591)` 为 RGBA `(255,234,202,255)`；
   注册到截图后邻近对应点 `(250,399)` 为 RGB `(200,232,254)`。
   R/B 互换后几乎一致，G 不变。
4. 对 22,134 个不透明头像像素进行通道排列对照：保留原 RGB 的均方误差
   为 3173.92，仅交换 R/B 后为 675.03，误差降低 4.70 倍。
   截图有选中光效、缩放、插值，因此不能要求所有像素完全相同。
5. 用户截图中的五个皮肤采样 5/5 满足 B > R+15。详情与哈希在
   `color-diagnosis.json`。

可重复执行 `revival/diagnose_color.py`。已运行的信号输出为
`BLUE_SKIN_REPLAY 5 /5`，再进行 atlas 标准解码和 R/B 单变量对照。
这条回放检查针对已捕获症状，不能冒充修复后的实时验收。

## 假设与结论

- 原 atlas 自带蓝肤色：离线原图肤色正常，已排除。
- 单独头像控件 Tint：同 atlas 的非头像蓝色按钮/边框也变金色，而且肤色
  的 G 通道保持，R/B 交换解释更强。layout 头像窗口没有显式 ImageColours
  或蓝色 Tint；仍未检查运行态是否另行设置颜色。
- 图像加载/上传通道排列错误：像素对照强支持，继续原生定位。

主插画与 3D 角色颜色正常，故不能从此截图推断整个屏幕/系统的通道异常。
没有显卡型号/驱动根因证据。原图未损坏，不应通过改原画或 AI 重绘掩盖。

## 原生根因定位（尚未修改客户端）

原程序包含 `SILLY::TGAImageLoader` / `SILLY::TGAImageContext`。
`0x2472aac` 是 `TGA Image loader (builtin)` 字符串；loader vtable
`0x2472acc` 的槽包括 `0x7acb30` 与 `0x7acc80`。
构造引用见 `0x7ab55e`、`0x7acaf3`。

已追踪完整颜色路径：

- `0x74c3b0` 是 `CEGUI::SILLYImageCodec::load`，RGBA 来源选择目标
  SILLY 格式 2、CEGUI 格式 1，随后调用 Texture vtable+0x10。
- `SILLY::TGAImageContext` 的像素写入器 `0x7ad150` 接收 B/G/R/A，
  格式 2 分支输出正确 RGBA。已用 Unicorn 原生执行证明，示例输出
  `FF EA CA FF`，即肤色 `(255,234,202,255)`，解码本身没有交换错误。
- `CEGUI::Direct3D9Texture` vtable `0x2472858` 的 +0x10 是
  `0x7967c0`，对应 `loadFromMemory`。
- RGBA 分支 `0x79687a` 指令 `C7 44 24 14 20 00 00 00` 选择纹理格式
  十进制 32，即 D3DFMT_A8B8G8R8。
- 但该函数的上传循环 `0x796a42`..`0x796a6f` 将输入 RGBA
  转成 DWORD `AARRGGBB`，内存布局为 BGRA。原生单像素执行实测
  输入 `FF EA CA FF`，写入 `CA EA FF FF`。
- D3DFMT_A8B8G8R8 按 RGBA 字节解释它，因此显示
  `(202,234,255,255)`，精确解释截图蓝肤色。这个上传循环应配
  D3DFMT_A8R8G8B8（十进制 21），这样输出恢复 `(255,234,202,255)`。

格式枚举来自 [Microsoft 官方 D3DFORMAT 文档](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dformat)。
这不是显卡猜测，而是原程序的格式常量与上传字节排列不匹配。

最小候选兼容修复位置为虚拟地址 `0x79687e` 的单字节 `20 -> 15`
（十六进制，即格式 32 -> 21）。应先匹配完整旧指令并限定隔离运行副本。
没有必要改头像、PFS 或增加材质染色。此子任务未应用该修复；由根任务统一
处理兼容改动和重启验证。

已按根任务要求准备候选 `revival/launch_client.py`，仅 `--check-only` 已执行，
固定运行副本哈希与 asInvoker 清单校验通过，未启动客户端。启动路径将只持有
自己新建子进程的 Popen handle；等待完整旧指令后改一字节，恢复保护并刷新
指令缓存/回读校验，失败终止自己的新进程并报告。未调用该启动路径、未接触
此前已有客户端进程。启动器 WinAPI 写入路径仍需根任务审核和实际启动验证。

原生验证脚本 `revival/verify_color_native.py` 已运行通过，结果见
`color-native-validation.json`。该脚本只执行离线映像的两段纯像素逻辑。
仍未验证的范围是修复后的真实 GPU 显示，以及其他纹理输入格式/上传调用。
修复后需同一创建角色场景重新截图，复测头像肤色及该 atlas 的按钮/边框。
