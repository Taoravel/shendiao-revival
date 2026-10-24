# 原任务按角色形象选择物品奖励

2026-10-23，本地 1.6.1 端游、网络版本 601。采用 `D:/User/Documents/Codex/.codex/skills/research/SKILL.md` 的一手材料追溯方法；本任务作为后台研究执行，未递归委派。已读根 AGENTS、ARCHITECTURE、DESIGN_AUTHORITY。只新增本报告与独立离线 probe `../research_task_reward_variants.py`；没有修改生产模块、在线数据库、共享入口，没有运行客户端或战斗。

## 已证结论

`RewardItemShapeIDList` 是**按 RewardItemIDList 原下标过滤**的角色形象条件，非门派奖励列表，亦非要求所有奖励列表等长。客户端原代码：

```python
for i in range(len(RewardItemIDList)):
    if i < len(RewardItemShapeIDList):
        selector = RewardItemShapeIDList[i]
        if 1 <= selector <= 10 and selector != original_role_variant:
            continue
    display(RewardItemIDList[i], RewardItemNumList[i])
```

`original_role_variant` 由原函数 `0x1129490` 计算：角色形象模型 ID 除 10 的余数，余数为 0 时取 10。本包所有 10 个 `CreateRoleConfig` 行、每行 `color1/color2/color3` 三种模型均满足 `variant == CreateRoleConfig.id`。所以普通建角可从已核验 `shape → create row` 映射取得同一结果；不能把门派 school 作为 selector，也不能把完整模型 ID 1010109 直接与 9 比较。

列表尾部缺 selector 的物品是共用物品，照常保留；已有 selector 若 ≤0 或 >10，原 UI 也不加过滤。后两种边界本包六行未使用，属于原分支行为的离线核验，不是鼓励伪造配置值。`RewardItemNumList` 按相同**原始 index**读取，不能先过滤 IDs 再从头 zip 数量或绑定。

来源强度：上述均为原客户端读取/显示代码及本包配置的 `client_verified`。服务器采用相同选择结果发奖，是依据原客户端可见奖励恢复的实现规则；本研究未取得原服务器结算二进制，不能声称已经证明原服实际到账、倍率或跨版本行为。

## 原函数与字段身份链

原映像：`native-image.bin` SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。

原配置解析函数逐字段匹配 UTF-16 名称，列表容器偏移如下（容器内 begin/end 为 +4/+8）：

| 字段 | 字符串 VA | parser 匹配/容器地址 | begin/end |
| --- | --- | --- | --- |
| RewardItemIDList | 0x226bd04 | 0xbb694d..0xbb6960，bean+0x124 | +0x128/+0x12c |
| RewardItemNumList | 0x226bce0 | 0xbb6972..0xbb6985，bean+0x134 | +0x138/+0x13c |
| RewardItemShapeIDList | 0x226bcb4 | 0xbb6997..0xbb69aa，bean+0x144 | +0x148/+0x14c |
| RewardItemIsBindList | 0x226bc88 | 0xbb69bc..0xbb69cf，bean+0x154 | +0x158/+0x15c |

奖励显示函数 `0x17c58c0` 附近的实际路径：

- `0x17c590c` 调任务表 getter `0x89ebd0`，按任务 ID 查 `CMainMissionInfo`，结果 ESI。
- `0x17c5950..0x17c596b` 以 IDList 的 begin/end 和 EDI 原下标控制循环。
- `0x17c5971..0x17c598c` 检查 selector vector 是否存在、EDI 是否小于其长度。无 selector 即进入保留分支 `0x17c5a1c`。
- `0x17c59c2` 比较 selector 与 0；`0x17c59e5` 比较 selector 与 10。范围外进入保留分支。
- `0x17c5a06..0x17c5a16` 从全局 `[0x2944550]` 取得当前角色，调用 `0x1129490`；selector 不同则跳到 `0x17c5aa0`，不加入显示列表。
- `0x17c5a4d..0x17c5a87` 用同 EDI 取 IDList、NumList，`0x17c5a8b` 调 `0x15ff710` 加入奖励展示项；`0x17c5aa0` EDI 加 1。

形象字段不是根据英文名字猜测：`SEnterWorld` handler `0x8338d2` 从消息外层 +0x3c 读取形象，并在 `0x8338da/0x8338f8/0x833904` 写入本地 `[esp+0x4c]`（旧形象兼容映射或直接模型值）。同 handler 在 `0x833f99` 调 `0x113b3e0` 将 `[esp+0x24]` 为起点的临时角色资料交给全局角色；故形象在临时资料 +0x28。`0x113b430..0x113b437` 将资料复制到角色 +0xf8，copy routine `0x113abfa..0x113abfd` 保留源 +0x28，目标即角色 +0x120。`0x1129490..0x11294a6` 对此字段执行有符号除 10、取余、零变 10。已恢复的 [WORLD_PLAYER_INITIALIZATION.md](WORLD_PLAYER_INITIALIZATION.md) 另核了同消息的 school 外层 +0x38 和 shape 外层 +0x3c，两字段分开。

绑定容器本身已由 parser 与原配置确认，但本次展示循环只构造 ID 和数量，不读取 IsBindList。因而“服务端给获选原下标的 binding”需要沿用既有奖励绑定解释；本报告不把本轮显示循环说成绑定语义的独立原生证明。不能因为 selector 缺尾部就把原本完整的 IsBindList 尾部扔掉。

## 六条实际配置与选择结果

下表“形象 1..10 物品”按 selector 值排序，非简单截取前十项；221002 正是反例。所有绑定原列表均为 1，每条的 ID/Num/Bind 长度相同，selector 长度均为 10。

| task | 形象 1..10 的专属物品（各 1） | 所有形象共用尾部 |
| --- | --- | --- |
| 102071 | 40301,40501,40401,40201,40101,41001,40901,40801,40701,40601 | 无 |
| 102096 | 49193,49193,49193,49193,49193,49194,49194,49194,49194,49194 | 无 |
| 102223 | 40313,40513,40413,40213,40113,41013,40913,40813,40713,40613 | 33032×20、33022×20 |
| 201209 | 49195,49195,49195,49195,49195,49196,49196,49196,49196,49196 | 36130×1 |
| 220902 | 36671,36671,36671,36671,36671,36670,36670,36670,36670,36670 | 32029×1 |
| 221002 | 36735,36734,36736,36738,36737,36743,36742,36741,36740,36739 | 31253×1 |

221002 原 selector 顺序为 `2,1,3,5,4,10,9,8,7,6`，原物品顺序是 36734..36743 再 31253。故形象 1（模型 1010101/1020201/1030301）显示 36735×1 + 31253×1；形象 10 显示 36739×1 + 31253×1。220902 形象 1 显示 36671×1 + 32029×1，形象 10 显示 36670×1 + 32029×1。相同 ID 的多个条件行不应累计给五份。

## 原包复核及离线验证

直接以 `PfsArchive.read` 重读 `D:/神雕侠侣/artres/config.pfs`，校验本地/中央目录一致、解压长度和 CRC，再 BXML 解码。按 attributes 与 lists 对已提取 JSON **全行相等**核验，不只抽查本报告六行：

| autoconfig/ 条目 | 行数 | 展开字节 | CRC32 | 展开 SHA256 |
| --- | ---: | ---: | --- | --- |
| knight.gsp.task.cmainmissioninfo.xml | 2460 | 2026233 | 3f7ab7b3 | ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706 |
| knight.gsp.role.createroleconfig.xml | 10 | 13107 | 0758d770 | 770da32d88784144e453c386c9cce05de03746943eb6004158d3cc53c9428132 |

执行 `research_task_reward_variants.py`：Unicorn 运行原 `0x17c5950..0x17c5aaa` 整个选择循环，原 `0x1129490` getter 也执行原指令；只将 `0x15ff710` 容器追加替换为捕获原传入 ID/Num 并等价返回，不替换条件判断。输入为六条原配置 × 十形象 × 三颜色，外加空 selector、0、-1、11、不匹配形象五种边界，共 **185 个原生用例通过**。另断言原 30 个颜色模型的余数对应原建角行 ID。

本 probe 证明该奖励展示路径的过滤与尾部保留行为，未执行完整 UI 构造/renderer，也未验证其他奖励窗口或真实服务器到账。服务器生产修改、重复结算审计、形象变更时固定发奖选择的凭据设计，由任务主模块处理；本批未部署或操作当前客户端。
