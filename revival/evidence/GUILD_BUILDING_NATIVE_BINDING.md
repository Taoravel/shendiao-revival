# 原生帮派建筑数据与计算

读取条件：发送建筑数据、改建筑公式或接原建设请求前。第24批verify_guild_buildings_native执行原映像；验收版本与最终审查状态查guild-buildings-current-review.json。原映像SHA256为2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791，未开启游戏。

| 消息/bean | 原证据 | 已绑定形状 |
| --- | --- | --- |
| CRequestFactionBuildData c5627 | 构造d6ddd0/d6dde0，marshal8373a0 | 空body；管理菜单148d4e0–148d4f8检查帮主6或副帮主5且mask32 |
| SRequestFactionBuildData c5628 | 构造e92630写type，vtable2282564；marshal e92d80 | selected i32、list<FactionBuildInfo> |
| FactionBuildInfo | vtable2282588；marshal e92c70 | type i32、level i32、construction i32 |
| CChooseBuildConstruct c5631 | 构造d6b630、marshal e44d10；按钮14ac980 | Q原样来自dialog+20/+24，类型来自选中行+c0；只证明上下文传递，不代替地图/NPC校验 |

完整原Process1495020遍历list，类型0..2写manager+338+8×type的等级及+33c+8×type的建设度，selected写+334，非法selected归-1。运行时把三组GUI全局设为0，完整返回；反序三行也能正确映射。空list只更新selected，不清旧等级/建设度，故新codec只编码完整已知三行，不用空表“清掉未知旧档”。实际GUI实例的刷新调用未执行。

GangConstruct/SlectList原六列为建筑名、当前等级、当前建设度、所需建设度、消耗帮派资金、消耗人气度。原名称查找14aa1b0按0/1/2查询cstringres819/820/821，分别为聚义厅、工坊所、练功房。类型是0..2，不能把原表图片行1..3直接当线包建筑ID。

| 原函数 | 原数值控件读取片段 | 已核用途/公式 |
| --- | --- | --- |
| 1486d70 | 14ad3a5→847450，后列3 | 当前等级L<20时建设需求(L+2)×50 |
| 1486d00 | 14ad4ca→490220，后列4 | (L+5)×[100000,300000,400000]帮派资金；原返回EAX/EDX |
| 1486d50 | 14ad581→490220，后列5 | 人气200 |

原三函数L>=20返回0。逐类型L=0/1/4/19/20共15行已执行并与服务器requirements比较，另以L1的150/600000、1800000、2400000/200固定字面例验证。三处原控件取值片段在格式化器入口截获，layout标签独立核对；完整原响应及缓存执行与之相接。测试不把20分支称原服绝对cap，采用范围由显式building_policy约束。

纯guild_building_protocol校验完整冻结三行、当前合法进度和selected，不持状态/连接/钱包。decode_choice保留完整unsigned64上下文但只接受0..2类型；没有注册该收费线包。c5627查询由组织运行时以当前租约、成员代次和bit5授权后响应，当前人物/NPC位置资格仍由main/地图集成。

服务端状态、费用时点、储备设计和真实源责任见GUILD_BUILDING_CONTRACT.md。原编解码/receiver/算术与UI切片通过不表示正式NPC或任务已接入，也不表示GUI、帮派小时维护或原服经济已经验收。
