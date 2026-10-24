# 原生新角色全屏黑幕：离线完整链验证

采用research的原始映像/资源追溯和diagnosing-bugs的单变量反事实。验证入口：[verify_world_intro_black_native.py](../verify_world_intro_black_native.py)；结果：[world-intro-black-native.json](world-intro-black-native.json)；指令：[world-intro-black-native-disassembly.txt](world-intro-black-native-disassembly.txt)。2026-10-23执行8组fixture/资源检查全部通过。只执行原映像指令与读取原包，未启动客户端、GUI、网络或服务，未写在线进程/真实经验。

## 已确认的黑像素来源和五分钟生命周期

原SEnterWorld处理`0x83380a..0x83384c`把packet+0x48/+0x4c视为signed64，<=0时global byte`0x2945438=1`，调用当前Scene的`0x11df870`。本批保留原比较、跳转、调用及effect constructor：0和-1两份fixture创建effect；1和2^32两份fixture不创建。这些值仅存在离线模拟内存。**+0x48不是经验字段**，此前收到任务后将它沿用为experience的措辞已撤回；暂命名intro判别q64，真实业务身份仍需追溯，不猜lastlogin/created timestamp。

真实经验来源已另外原生核验：`0x833ef3..0x833f0d`把packet+0xf8/+0xfc复制到临时RoleInfo+0x80/+0x84；`0x113b430`把manager+0xf8作为`0x113abd0`目标；`0x113ac53..65`复制source+0x80/+0x84到target+0x80/+0x84，即最终RoleDataManager+0x178/+0x17c。这与SRefreshUserExp setter`0x11355b0`目标相同。fixture执行三段原指令，以64位sentinel证实上述路由，packet+0x48保持0独立不变；未执行整个初始化器。不能将真实EXP=0与intro判别值=0混为一谈。

`0x11df870`分配0x18字节effect，原constructor`0x12ba630`写vt=`0x229ef5c`、alpha+0xc=1、elapsed+4=0、finished byte+0x15=0。随后原调用读取UTF16资源字符串`/artres/image/movie/movieblack.tga`、将duration+8置`0x493e0=300000`、将texture保存到+0x10，调用start vt+4=`0x12ba650`，向Scene+0x38c容器注册，另保存Scene+0x39c。

资源不是根据文件名猜黑：直接读原`artres/image.pfs`的`movie/movieblack.tga`，PfsArchive完成CRC验证后PIL解码为1024×768 RGBA，**全体像素均(0,0,0,255)**。文件SHA256=`8fba646a8a42017f8148bc34c5d87154518c95431908ea72a000eae164e7a6f3`。

原Scene effect draw调度`0x11d3770`遍历Scene+0x38c容器，调用每项vt+0x10。该effect方法`0x12ba8f0`在texture+0x10非零时，从renderer+0x34取viewport，原生计算rect=(0,0,width,height)，以alpha+0xc乘255构造ARGB，调用renderer+0xf8。真实原指令fixture提交rect=(0,0,1024,768)、ARGB=`0xffffffff`，配合原纯不透明黑texture即构成全屏不透明黑幕。该证据是资源像素和原绘制调用参数，未冒充完整D3D/GPU截图回归。

原Scene effect update调度`0x11d2a30`将第二个参数传给每项vt+0xc=`0x12ba660`。fixture一次传299999，elapsed=299999，texture仍在、finished=0；再传1，原方法达到300000后调用vt+8=`0x12babd0`→`0x12ba690`释放texture、finished=1。Scene原update继续析构effect并移除容器项。之后再执行原Scene draw，**没有任何texture提交**。这是黑→亮的原生五分钟超时机制，不是昼夜或后台置前机制。**该超时不清global2945438**，fixture到期后仍为1；所以自然亮并不意味着移动锁解除。

此前只核查Scene+0x330/+0x334那条覆盖路径，未覆盖Scene+0x38c/+0x39c，此处补齐遗漏。原渲染update/draw正常推进、地表纹理存在，都不能排除之后的这层遮罩。先前24c低byte变化仍是时间区间标志，不能用相关性覆盖此更直接的像素来源。

## 明确解除入口与生命周期调用者

原`0x11d3a10`读取Scene+0x39c，若非零调用`0x11d37d0`在effect容器里移除、停止与析构，随后清零+0x39c。本批额外fixture从intro判别值0的真实原链创建effect后直接执行此原清除方法，证实只释放该texture、容器变空、Scene+39c清零。此验证证明原方法效果，未向在线客户端调用它。

全映像direct-call扫描找到两个调用点：`0x12c0ac4`、`0x12c306e`。两处均先通过`0x813830`获取对象，检查其byte+0x3d8，再清除此byte并调用Scene清除函数。还存在tail-jump入口，不能仅扫call漏掉：**`0x12bc870`完整函数**先执行原getter`0x813830`（恒返回`0x2945060`），检查/清除+0x3d8，恰为global`0x2945438`，再tail-jmp到Scene的`0x11d3a10`。新增fixture真实执行整个`0x12bc870`，证实intro锁=0、Scene+39c=0、effect容器为空，texture被释放。这是最小原清除contract；不依赖EXP、网络、任务奖励或服务端地图改变，也未向在线客户端注入调用。

Return命令静态注册链：UTF16`Return`@`0x229f194`在`0x12c3bbe`注册handler`0x12c2e90`；该handler创建`0x12b8ed0`构造的command（vt`0x229ed64`）。start vt+4=`0x12b99d0`调用manager global`0x2945620`的`0x12c0bf0`，最终传manager+0x40保存值到Scene的`0x11e0a80`。后者比较Scene+0x110并走Scene/角色本地恢复路径；本批只完成静态链和清除函数重放，没有完整重放Return的资源切换或角色位置恢复，不用它断言整个演出已可验收。父任务继续将原开场11001接入有可信授权的演出会话，不把任意CEnd包当作完成所有任务。

## 适用范围和未完成验收

原生分支、constructor、Scene draw/update调度、effect draw/update/资源释放及显式解除函数均真实执行；仅操作系统堆分配、UTF16 string导入、引擎/renderer外部接口和注册容器边界用host adapter。容器注册adapter将原调用的effect写入fixture容器，之后Scene遍历、更新、移除与析构使用原函数。resource adapter返回fixture handle，原包texture像素另以CRC验证解码。未执行实际设备混合/呈现。

该机制同时给出不透明全屏黑和精确300000ms自然解除，与同进程几分钟后自然显示的症状高度吻合。旧before快照没有保存Scene+39c和effect状态，因此不能补称现场已实读该遮罩；仍需由合法开场流程修复后，用原黑屏视觉判据确认世界立即可见及角色可移动。当前用户禁止打开游戏，本批不启动新现场，不以离线绿色替代客户端验收。
