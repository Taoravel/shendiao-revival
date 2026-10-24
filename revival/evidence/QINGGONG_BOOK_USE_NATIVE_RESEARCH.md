# 轻功教学三书：原右键分派、读条与CUseItem

2026-10-24，端游1.6.1/网络601。按research Skill后台原生研究；完整读取research、codebase-design、ARCHITECTURE及DESIGN_AUTHORITY。本批闭合206104/206204/206304所用50190/50191/50192的**普通物品使用分派→TaskRelative/readtime→本地kind2进度→CUseItem**。原15只证明float阈值15，不证明服务器15秒政策、学习资格、扣物或任务完成。没有写角色/任务/轻功授权或操作GUI、网络、数据库、正式战斗。

## 一手来源

`artres/config.pfs`直接PfsArchive读取并核长度/CRC：

| 原成员 | 字节 / CRC32 | SHA256 |
| --- | --- | --- |
| autoconfig/knight.gsp.item.citemattr.xml | 4096369 / a3add081 | 974a3b38049c5f5f7cdae418718ffadd2741d373a5846a40fb71289af25e726f |
| autoconfig/knight.gsp.item.ctaskrelative.xml | 24845 / 26e177d3 | f7fd09554140c4964a59fe59800d8da4a2a6630a5f29bc922a5d3ad7ff52b913 |

三书ItemAttr均itemtypeid73、needLevel1、outbattleuse1、battleuse0；TaskRelative.readtime15/usemap0。原任务/前缀/赠书另由root直接PFS核 `qinggong-book-original-sources.json` / `QINGGONG_BOOK_SOURCE_AND_GUIDE.md`；本研究不替代其服务器学习政策。

原映像 `evidence/native-image.bin`，base0x400000，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`，每次probe均核SHA。所有VA仅对应此映像；既有两个TASK_USE_ITEM研究作为定位索引，关键指令本批重新反汇编。

## 更正旧类关联：三书不是【师授】秘籍对象

旧报告N4/N3只找到QingGongMiJiObject（vtable228c2a4/ctor1074260），未证明与三教学书的对应。实际原工厂107fed3/1080819先比较**模板36843/0x8feb**，命中才在107fefc/1080847构造此类。原36843为【师授】轻功秘籍，itemtypeid2198，对徒弟使用；它不是50190..50192。保留这个名字不能作为三书的动态发送链依据。

本批改从实际原ItemAttr字段复制与消费追溯，不能只因73低4位为9便类比普通type25。

## 原配置字段→TaskObject→真实使用分派

1. 原工厂1080720在1080753取CItemAttr getter89d730，用模板ID查原行，108076f调用1072890，目的为wrapper+4。
2. 原1072890在1072896..107289f分别复制配置首两int：id→wrapper+4，itemtypeid→wrapper+8。因此三书原73真的进入下述判断，不是猜一个内部编码。
3. 模板特判之后，10808be..10808cf读取该实际type低4位，按108101c表分派。type73/0x49的第9分支为1080f2d，构TaskObject（1073fd0，vtable228c284），不是QingGongMiJiObject。
4. 1080f6d再次取CTaskRelative getter89da10，用原模板查行；1080f90/1080f9a把relative+0x24的readtime赋给TaskObject+0x74。文字分别从relative+4与+0x28复制到对象+0x58/+0x78。原getter1072f20通过wrapper的data指针读取data+0x74；1072f30返回data+0x78文字地址。
5. 通用右键入口10acd90的10ae7a1..10ae7be读取同wrapper+8，低4位为9，按wrapper+0x78 needLevel和人物等级getter1135590检查；通过在10ae87e真正调用10a5a80。该handler按原模板查CTaskRelative，10a5dd8读usemap；三书usemap0且不命中50081/50029/50204/50205等动态特判，走10a5e0f。
6. 10a5e0f→1072f20读到15，正值路径在10a5e5f..10a5e81转float、压kind2、实例key参数及对象文字，经8114a0取得进度对象再call16c4140。本地无静态map限制；这不是服务器任务在任意图可完成的授权。

通用入口前段还有战斗/来源容器/旗标/确认等原前置，沿用 `TASK_ITEM_USE_ADMISSION_RESEARCH.md` N1；本次没有把它们全部模拟或给未识别字段强命名。

## 原kind2尾部：教学呈现后发同一个使用请求

原16c4490完成分支在16c4509检查kind2；非特殊状态15路径经1091670以当前实例key取物品，16c4545开始显式比较50190、50191、50192。三者分别取资源10040/10041/10042，调用174cfc0呈现；该函数可见UI对象创建/清理与虚函数调用，不是本研究已证的持久技能写者。

随后三个分支均汇合16c4627：主角色虚函数+0x38取得完整64位角色ID；16c4637..16c463f压入kind0、当前物品实例key、roleID并调用原CUseItem constructor10729f0，后经813860取得连接、16c4779..16c478a向连接虚函数+0x3c发包。无taskID、数量、技能ID、学习等级、坐标或服务器计时凭据。

原constructor写type0xc03ff；原marshal e4d740按i32 key、i32 kind、u64 roleID写body。三书共用此原布局，不需要新猜协议。

## 可复用有界probe与实际结果

新增独立 `staging/research_qinggong_book_use_native.py`，公开：

```python
native_qinggong_book_use(item_id, instance_key=123,
    role_id=0x1122334455667788) -> dict
```

返回`packet_type`、原marshal产生的`body:bytes`、实际捕获progress_kind/threshold_raw、教学资源ID，并显式`completed_timer_is_fixture=True`、`server_completion_authorized=False`。可供root把真实原包交当前只读任务检查Interface；不导入生产TaskItemUse/Inventory，运行入口只打印JSON。helper每次直接核原两表字段与映像SHA，不接受其他物品。

实际执行三例均通过（一次main，约1.26秒）：

| 原模板 | 原factory/dispatch结果 | 捕获kind/raw阈值/key | 原尾部提示 | 原包body |
| --- | --- | --- | --- | --- |
| 50190 | TaskObject→10a5a80 | 2 / 15.0 / 123 | 10040 | 0000007b000000001122334455667788 |
| 50191 | TaskObject→10a5a80 | 2 / 15.0 / 123 | 10041 | 0000007b000000001122334455667788 |
| 50192 | TaskObject→10a5a80 | 2 / 15.0 / 123 | 10042 | 0000007b000000001122334455667788 |

body均16字节、type0xc03ff；roleID完整0x1122334455667788保留。body来自捕获的原constructor字段再由原marshal执行，不用Python自写wire encoder替代；Python struct只作独立期望断言。

执行范围精确分段：实际1072890前两字段复制；实际10808be分派至TaskObject case；原TaskObject ctor及1080f6d相对表readtime赋值；实际10ae7a1右键分派尾→10a5a80全handler至16c4140入口，直接捕获kind/raw threshold/key。然后明确构造“本地kind2已完成”的暂态fixture，执行原16c4490到发送捕获；**未执行真实经过15个时间单位的timer，也未执行完整GUI启动前置**。

系统Adapter仅配置manager查找、空字符串copy/析构、人物等级70/完整ID、已存在UI状态对象、物品启用呈现/角色动画UI调用和网络发送捕获。TaskRelative判断、原type分派、浮点转换、kind、模板分支、CUseItem constructor及marshal均由原指令执行。未替换它们为Python条件。174cfc0实际GUI呈现被Adapter截住；未宣称其渲染或交互已验。

初次三例实际执行的脚本SHA为 `e30477bad37b39b466b9110daa1b0dd9963092ff71c704632c057c2e5615a1b8`。收尾按root建议仅把PFS定位从脚本parents改为原项目 `inspect_client.ROOT`，便于冻结副本复用；当前正常位置两者同指原项目，布局/原分支未改。最终脚本SHA256 `992210f4dfa834c1edaeecee8d2959ff4415cb8369eb9022e11a34a1a9a7beba`；最终接口的root统一包→只读检查桥接另有root报告，不冒称本研究重跑了新字节。依赖`research_battle.py` SHA `4aa276ece9ea4a9f13d9c4f9a0de2900f97cf77ff3783aeecc92e7d5f3a47b45`，`verify_social_native.py` SHA `a5e85ff5ec786c461a55af075b5ecd5c6d40b57da41c6f84bf9116596cae1a80`。原helper都只作离线映像/系统Adapter，无main副作用。

## 结论和未验范围

`client_verified`：三书真实字段进入原普通任务物品handler、TaskRelative.usemap0/readtime15、local kind2阈值和三教学呈现分支、原CUseItem16字节意图。旧“type73_native_use_unconfirmed”可对**这三个精确q/item**收敛；不能把一切type73或2198【师授】秘籍都变成此规则。

`unknown`：服务端实际学习/已有轻功等级或路线资格、扣几件/何时扣、计时许可、任务完成时序/原奖励和后继结算、重连/重复使用、角色权威轻功状态ID或学习同步消息。本批没有找到可确认为这些教学书写入持久轻功的状态授予者；UI提示不等于学习成功。既有class6的100007九阴白骨爪/100009凝神静气不是轻功，未把三书接进100008首次技能账本或普通移动权限。

codebase-design实际影响决定：把原生“使用意图”与角色/世界“学习及移动授权”作为不同Seam，公开一个可注入真实key/roleID的小probe Interface，隐藏Unicorn和暂态配置；root仍应通过当前公开Inventory/TaskSnapshot观察，不能由此研究直接建完成证据。research在原PFS/原映像闭合已问的发送链后收敛；官方版本和设计参数由root另外集中。本批仅新增本报告和独立probe，未改任何生产Module、中央政策或原资源。未验完整右键GUI、自然读条、实际学习、服务器/DB/网络/战斗/真实角色或部署。
