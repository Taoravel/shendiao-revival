# 元魂最终宠物属性与资源来源研究

状态：completed，2026-10-24。按已读 research Skill 作为后台有界调查；只写本文，不改生产/政策/旧报告/shared/真实数据库，不启动服务或客户端。

目标：从原PFS属性定义、元魂配置和实际消费者区分7项固定修正、命中/躲闪比例与5项战斗比例的含义和可证计算顺序；确定未知命中/躲闪/比例基线及HPMP上限调整规则的证据界限。既有 `inventory_pet_growth.state` 保持单一资源来源，本文不设计第二HPMP记录，也不默认缺失基线0。

## 第一方来源与已确认映射

直接重读 `artres/config.pfs`，PfsArchive验证原长度/CRC，BXML解码后逐行attributes/lists与现catalog比对，全部一致。原映像50675712字节，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`；所有地址为基址0x400000的原VA。

| 原配置路径后缀（均autoconfig/knight.gsp.） | 行数/字节 | CRC32 | 原内容SHA256 |
| --- | --- | --- | --- |
| item.cattributedesconfig.xml | 195 / 19508 | 56e2ca7e | 5c68180582cf6252696d0bd61cd9ea9c11119beab2b473e96aa27bf0da358a79 |
| pet.cpetsoulattrcfg.xml | 28 / 11689 | f3a6c6c3 | da015cfbf873037ea91541fc17699654031d888a49f8520c0db70f929590f690 |
| pet.cpetattr.xml | 158 / 76736 | 9fc172d4 | 89d947b24d2e61cfe38f8e0ff24ea8ae6ad12410e8ae73e95256a1f1de9b00c8 |

`client_verified`为**属性定义字段的关系**，不是原服务器数学公式：

| 两类珠模板 | 元魂modifier ID | 所属core ID / 原名字 | 显式关系 | 原shuzitype |
| --- | --- | --- | --- | --- |
| 31276/31277 七杀 | 81 | 80 外功伤害值 | core.numid | 1 |
| 31278/31279 破军 | 811 | 810 内功伤害 | core.numid | 1 |
| 31280/31281 武曲 | 101 | 100 外功防御值 | core.numid | 1 |
| 31282/31283 贪狼 | 821 | 820 内功防御 | core.numid | 1 |
| 31284/31285 太阴 | 151 | 150 真气最大值 | core.numid | 1 |
| 31286/31287 太阳 | 141 | 140 生命最大值 | core.numid | 1 |
| 31288/31289 紫薇 | 131 | 130 速度值 | core.numid | 1 |
| 31290/31291 天相 | 1551 | 1550 外防穿透 | core.numid | 2 |
| 31292/31293 天机 | 1561 | 1560 内防穿透 | core.numid | 2 |
| 31294/31295 天梁 | 741 | 740 物理被动伤害修正 | core.numid | 2 |
| 31296/31297 天府 | 1581 | 1580 内伤减免 | core.numid | 2 |
| 31298/31299 天同 | 1591 | 1590 毒伤减免 | core.numid | 2 |
| 31300/31301 巨门 | 112 | 110 命中值 | core.percentid | 2 |
| 31302/31303 廉贞 | 122 | 120 躲闪值 | core.percentid | 2 |

应按表中numid/percentid联查，不按ID减1猜映射。最后7类shuzitype都是2，但前5类仍为各core的**numid**，只有112/122为percentid；把所有type2一律解释为`core*(1+ratio)`没有来源支持。原740/1580/1590各负Fraction完整保留；“减免”文字不授权先取绝对值或反号。原描述本身也有百分号显示；这只证明显示类别，尚不证明服务端单位或叠乘顺序。

## 原普通Pet刷新消费服务器绝对值

原 `pet::SRefreshPetData` ctor/marshal/unmarshal为`f9d7b0/f9d840/f9d880`；其内Pet由`f89ba0/f5df70/f5f1f0`编码。原刷新消费段`1135096..113517a`直接从服务器消息字段写Pet+34属性map：level490及HP60/maxHP140/MP70/maxMP150/外攻80/外防100/速度130/内攻810/内防820。该段每项为mov写入，没有读取元魂map、相加或按百分比重算。

本批用原Pet/SRefresh fresh codec后实际执行上述10个原写入：level10与`(70,203,40,99,31,32,33,34,35)`精确进入对应属性单元。仅map选单元的终端函数4e8e00由宿主提供可观察单元；原取字段、key和写入都执行，未运行完整GUI/STL属性容器。已穿元魂map仍是独立Pet+bc来源（既有184bf70来源）；普通绝对属性包与元魂列表不能互相替代。

结论限于客户端消费：服务器可投影当前最终绝对值；**这不是原服务器把元魂、血脉、成长、技能组合的公式证据**。命中/躲闪和5比例基线未出现在上述9整数基本字段中。原cpetattr所有158行只有已知五资质方向等字段，未找到可直接当作7项缺失当前基线的完整列；不能从“没有列”推0。

## 重要原生限制：float map不等于可直接传Fraction

原`attr::SRefreshPetData`，type0xc32c9，ctor/marshal/unmarshal=`ec30c0/ec3250/ec32f0`，wire为column/petkey+float map。原完整handler113daa0遍历这个map；除了少量特殊字段分支（例如ID600写特定float成员），普通通用分支`113e023..113e04c`执行：取float→`19191e0`转换整数→写Pet+34单元。

本批实际执行原fresh decoder、完整113daa0循环到UI前113e24d，结果：

| wire float | 客户端普通属性实际整数 |
| --- | --- |
| 110=123.75 | 123 |
| 120=456.5 | 456 |
| 740=−0.15 | 0 |
| 1550=0.15 | 0 |
| 1560=0.20 | 0 |
| 1580=−0.20 | 0 |
| 1590=−0.01 | 0 |

原codec往返通过，仍会在消费者截为0。故不能只把精确Fraction转float塞0xc32c9便宣称原生投影成功。比例服务端battle快照可保持精确Fraction；客户端整数比例的scale/显示路径须另证或显式设计，**本批没有证明×100或×10000**，也未证明这些core一定应由此增量包展示。命中/躲闪最终整数也需要明确舍入及有效上限政策。

## 官方端游定向检索

直接检索官方端游域，排除手游和《神雕侠侣2》；本轮查询含“元魂 命中 公式”“元魂 穿透 叠加”“元魂 摘除 生命 真气”。后3项针对精确公式/摘除规则未得到匹配结果。

- [官方端游元魂介绍，2013-02-27](https://sdxl.wanmei.com/news/gamenews/20130227/140652.shtml)：确认14类、5颗，以及攻击/防御/资源上限/速度、穿透/三类减免、命中/闪避的用途。它为`guide_supported`的历史方向旁证；没有给最终数值的加乘/取整/stack顺序，也没给穿脱HPMP保存规则。文章早于本客户端完整铭文/魂技来源，不覆盖后续规则。
- [官方端游宠物资质，2012-07-29](https://sdxl.wanmei.com/info/qita/pet/20120729/133549.shtml)：确认五资质方向及一些技能会影响命中、躲闪等；未给七项当前基础值/统一合计公式，不能忽略技能来源把基线填0。
- [官方端游战斗规则，2012-07-29](https://sdxl.wanmei.com/info/qita/fight/20120729/133541.shtml)：宠物HP≤0判死亡的一般说明，不是“穿脱提高上限时是否回血”的证据。未知该历史规则与1.6.1精确对应范围。后期2021/2022怀旧公告只描述礼包，未作公式依据。

## 供实施明确裁定的缺口

客户端直接证明原修正向量、numid/percentid对应、原正负比例和绝对值消费。仍需标`designed`的部分：7flat是否直接加最终裸身属性、命中/躲闪percent如何与明确基线及技能/其它percent组合、5个ratio是否加到各core原比例、取整/溢出/允许区间、多个来源先后及战斗消费。不能仅完成flat后把剩余7个修正丢弃并称完整元魂属性。

HP/MP必须继续由现有`inventory_pet_growth.state`一份记录持有。穿脱保持绝对当前值、下降裁剪、死亡不复活可作为明确本地政策，但本批无原服证据可将它标client_verified。成长保缺失量与装备穿脱绝对值保持是不同cause，实际组合必须按cause裁定；读档/paid重试不能隐式改资源。新policy要同时覆盖实际read、成长/消耗/战斗结算、native绝对投影与battle入场快照，防旧消费者按未加元魂的caps拒绝或覆盖真实当前资源。

## 可复现：原资源与显式映射

```python
import sys,json,hashlib
from fractions import Fraction
sys.path.insert(0,'revival')
from pfs import PfsArchive
from bxml import decode
arc=PfsArchive('artres/config.pfs');tables={}
for name in ('item.cattributedesconfig','pet.cpetsoulattrcfg','pet.cpetattr'):
    path='autoconfig/knight.gsp.'+name+'.xml';raw=arc.read(path);rows=list(decode(raw))
    with open('revival/catalogs/knight.gsp.'+name+'.json',encoding='utf-8') as f:cached=json.load(f)
    assert len(rows)==len(cached)
    for row,saved in zip(rows,cached):
        assert row.attrib==saved['attributes']
        assert {c.tag:[x.text for x in c] for c in row if len(c)}==saved['lists']
    tables[name]={int(r.attrib['id']):r for r in rows}
mapping=((81,80,'numid'),(811,810,'numid'),(101,100,'numid'),(821,820,'numid'),
         (151,150,'numid'),(141,140,'numid'),(131,130,'numid'),
         (1551,1550,'numid'),(1561,1560,'numid'),(741,740,'numid'),
         (1581,1580,'numid'),(1591,1590,'numid'),(112,110,'percentid'),(122,120,'percentid'))
for i,(modifier,core,relation) in enumerate(mapping):
    assert int(tables['item.cattributedesconfig'][core].attrib[relation])==modifier
    for template in (31276+2*i,31277+2*i):
        row=tables['pet.cpetsoulattrcfg'][template]
        assert int(row.attrib['attrid'])==modifier
        values=[Fraction(x.text) for x in row.find('attrvalue')]
        assert len(values)==15
        if modifier in (741,1581,1591):assert all(v<0 for v in values)
print('PASS original195/28/158 rows, 14 explicit relations and420 exact signed values')
```

## 可复现：原完整float-map消费者截断

```python
import sys,struct
sys.path.insert(0,'revival')
from native_inspect import DATA,BASE
from native_gameplay_probe import probe
from wire import compact
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *
pairs=((110,123.75),(120,456.5),(740,-.15),(1550,.15),(1560,.2),(1580,-.2),(1590,-.01))
payload=struct.pack('>ii',1,7)+compact(len(pairs))+b''.join(struct.pack('>if',*x) for x in pairs)
def observer(u,msg):
    pet,manager,stack=0x5300000,0x5302000,0x5330000
    cells={key:0x5304000+4*i for i,(key,_) in enumerate(pairs)};calls=[]
    def w(a,*v):u.mem_write(a,struct.pack('<'+'I'*len(v),*v))
    def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
    def ret(n,value):
        sp=u.reg_read(UC_X86_REG_ESP);dest=r(sp)
        u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_ESP,sp+4+n);u.reg_write(UC_X86_REG_EIP,dest)
    def hook(uc,addr,size,_):
        sp=uc.reg_read(UC_X86_REG_ESP)
        if addr==0x112ffd0:
            assert (r(sp+4),r(sp+8))==(7,1);ret(8,pet)
        elif addr==0x4e8e00:
            key=r(r(sp+4));assert key in cells;calls.append(key);ret(4,cells[key])
    w(0x2944550,manager);w(0x29455cc,1);w(0x29b8ef8,1)
    for cell in cells.values():w(cell,12345)
    handle=u.hook_add(UC_HOOK_CODE,hook)
    w(stack,0x500f000,0,0);u.reg_write(UC_X86_REG_ESP,stack);u.reg_write(UC_X86_REG_ECX,msg)
    u.emu_start(0x113daa0,0x113e24d,count=100000)
    assert tuple(calls)==tuple(k for k,_ in pairs)
    assert {k:r(c) for k,c in cells.items()}=={110:123,120:456,740:0,1550:0,1560:0,1580:0,1590:0}
    u.hook_del(handle)
result,_=probe(0xec30c0,0xec3250,0xec32f0,payload=payload,observer=observer)
assert result==payload
print('PASS original float-map codec/whole pre-UI handler: fractions truncate to integer zero')
```

## 可复现：原普通Pet绝对值写入

```python
import sys,struct
sys.path.insert(0,'revival')
from native_inspect import DATA,BASE
from native_gameplay_probe import probe
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *
values=(70,203,40,99,31,32,33,34,35)
record,_=probe(0xf89ba0,0xf5df70,0xf5f1f0,{4:struct.pack('<i',500001),8:struct.pack('<i',7),
    0x28:struct.pack('<i',10),0x40:struct.pack('<9i',*values)})
def observer(uc,msg):
    stack,mapobj,cell=0x5330000,0x5301000,0x5302000;seen={};keys=[]
    def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
    def hook(u,address,size,_):
        if address==0x4e8e00:
            sp=u.reg_read(UC_X86_REG_ESP);key=r(r(sp+4));ptr=cell+4*len(keys)
            keys.append(key);seen[key]=ptr;dest=r(sp)
            u.reg_write(UC_X86_REG_EAX,ptr);u.reg_write(UC_X86_REG_ESP,sp+8);u.reg_write(UC_X86_REG_EIP,dest)
    handle=uc.hook_add(UC_HOOK_CODE,hook)
    uc.reg_write(UC_X86_REG_ESI,msg);uc.reg_write(UC_X86_REG_EDI,mapobj)
    uc.reg_write(UC_X86_REG_EAX,cell+0x100);uc.reg_write(UC_X86_REG_ESP,stack)
    uc.emu_start(0x1135096,0x113517c,count=500)
    assert keys==[60,140,70,150,80,100,130,810,820]
    assert tuple(r(seen[k]) for k in keys)==values and r(cell+0x100)==10
    uc.hook_del(handle)
probe(0xf9d7b0,0xf9d840,0xf9d880,payload=record,observer=observer)
print('PASS original Pet refresh writes level and9 absolute integer values unchanged')
```

## 方法、产物、验证与未验证

research实际决定：直接联查原numid/percentid而非猜ID差值；实际执行消费者后发现float-map丢弃小比例，因此拒绝把codec通过当比例UI成功；官方来源仅给方向，精确顺序与资源cause继续显式设计。唯一产物本文；三段复现已执行exit0，三个原表全行比对、420精确向量、一个7项floatmap原循环及10项绝对写入通过。宿主只隔离宠物查找/属性单元终端；不冒称完整GUI、原服务器公式或生产接线。未验证完整命中/躲闪/5比例基线、server加乘/取整/边界、显示整数scale、技能/铭文/成长组合、HPMP上限转换、battle消费者、持久化/旧policy迁移与shared/部署/容量。
