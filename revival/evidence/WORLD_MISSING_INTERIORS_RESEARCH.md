# 1302/1307缺失内景：原资源候选与仍有效引用

后续原Scene→World→资源请求的5项可执行验证已由父任务独立通过，见 `WORLD_MISSING_MAP_LOAD_RESEARCH.md`：两缺图原目录打开失败，无第二候选请求；本地可选分段资源配置也缺失。候选仍不能改标完整原图，未复制资源或激活别名。

2026-10-23。research使用原PFS目录、CRC校验读取、BXML结构解码和原RMP头，不以地图名称相似决定资源替代。此次只读调查，没有写任何源码、目录别名、配置、存档或客户端文件；部署冻结保持。

## 原配置与资源事实

原config.pfs/autoconfig/knight.gsp.map.cmapconfig.xml中：

| 地图 | 原resdir | 配置尺寸 | 当前同目录map.rmp |
|---|---|---|---|
| 1302 全真教真武殿 | quanzhenjiaozhenwudian | 1920×1536 | 缺失 |
| 1307 桃花岛玄机堂 | taohuadaoxuanjitang | 1664×1216 | 缺失 |
| 1593 全真教重阳宫 | map_1593_quanzhenjiaozhenwudian | 1920×1536 | 存在，原RMP头同尺寸 |
| 1422 浪漫屋 | map_1422_changshengdian | 1664×1216 | 存在，原RMP头同尺寸 |

已扫描原map.pfs的全部308份map.rmp：1920×1536仅1593；1664×1216为1422和1654圣诞屋。尺寸只是候选筛选，不证明几何、交互或场景身份相同。

1593/map.rmp包含UTF16LE的quanzhenjiaozhenwudian资源路径（字节偏移4953），原归档也存在elements/quanzhenjiaozhenwudian/ground/quanzhenjiaozhenwudian.img及该目录architecture图元。1422/map.rmp包含UTF16LE的changshengdian（3485）和taohuadaoxuanjitang（3529），对应原图元elements/map_1422_changshengdian/ground/taohuadaoxuanjitang.img。由此确认旧内景的美术资源在新地图中有复用痕迹；不能因此说旧1302/1307的完整原地图已找回。

两份候选均有原maze.dat，均无goto.xml。1593/npc.xml有14处摆放，1422只有NPC12667一处；不能把这些候选图的NPC列表自动作为旧门派内景摆放。两份RMP的SHA256分别为：

- 1593：a3045a88bdff73824b51296ea3ed7aa362cadcb517e2959f754ebf5b0d78ec78
- 1422：df51c13d2c5c403f9acd088a35b3cbaec9a95d3a8e55a01605e1e581a37cf510

原map配置1302与1593仍有safemap、findpathin、xjPos/yjPos等不同；1307与1422的用途、战场背景和入口值也不同。未核实原加载器存在这些别名/回退分支，未修改world_catalog把缺失标成可用。

## 旧地图仍被引用

已读取catalogs/knight.gsp.*.json所有顶层attributes，筛选字段名含map且值精确等于1302/1307；找到以下4处。此扫描不覆盖列表内容、脚本文本或原native调用，不能作为“只有4个全客户端引用”的证明。

| 原表与行 | 字段 | 值 | 对恢复的影响 |
|---|---|---|---|
| role.schoolinfo 16 全真教 | innermapid | 1302 | 门派内景引用仍存在 |
| role.schoolinfo 17 桃花岛 | innermapid | 1307 | 门派内景引用仍存在 |
| task.cmainmissioninfo 316702 | ActiveInfoMapID | 1302 | type10尊师重道，目标NPC10163 |
| task.cmainmissioninfo 316802 | ActiveInfoMapID | 1307 | type10尊师重道，目标NPC10051 |

还逐份读取原map.pfs/goto.xml，未发现destmap1302或1307；这只说明当前静态门户没有进入它们，不能排除菜单、任务、服务端传送或客户端寻路使用上述引用。

为排除旧catalog过时，已重新从原config.pfs读取以下三表，核PFS长度/CRC、解码，并将上述全部8个相关原行与catalog逐属性比较一致：

| 原路径（均autoconfig/前缀） | 原BXML字节数 | SHA256 |
|---|---:|---|
| knight.gsp.map.cmapconfig.xml | 91110 | 374d400f933a74e83d402c8da948fef47823e7f92344ccb660414edfb87a1814 |
| knight.gsp.role.schoolinfo.xml | 4075 | 3ed66a6f40f615b6d89372a1775246a33c644b9d612df7794532edb656332a2d |
| knight.gsp.task.cmainmissioninfo.xml | 2026233 | ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706 |

## 接下来如何恢复

1. 先核原地图加载器有无按ID/resdir转换或可验证回退。若有，按原规则恢复，重验RMP、maze、NPC、景物和传送坐标。
2. 若确无原路径，交主策划裁定是否以1593/1422资源制作明确designed的旧内景兼容策略；地图身份、safemap、任务目标、NPC摆放和出入口必须分别指定，不能靠复制目录一并继承候选地图玩法。
3. 完成后用原客户端进入这两张地图，验证地面/景物、目标NPC、可走与不可走处、进入和返回。只有这些完成，才能将缺图统计由302/304改为完整可用。

本批证明了可用于继续恢复的原美术/尺寸候选和仍有效的任务引用；没有恢复旧地图本身，也没有编写兼容补丁。没有部署、重启、GUI或改真实角色。
