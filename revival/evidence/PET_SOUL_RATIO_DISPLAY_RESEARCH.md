# 宠物五项元魂比例的原生显示路径

状态：completed，2026-10-24。按已读 research Skill 后台有界调查；只写本文，不修改生产/政策/旧封签资料/真实数据库，不启动服务或客户端。

目标：原Pet属性UI或tooltip是否消费740/1550/1560/1580/1590，以及整数存储到显示格式的确切scale。既有证据仅证明c32c9通用float map消费者截为int；本批不据习惯猜×100、百分数或万分比单位，不将未找到引用当不存在。

## 已确认：原魂珠tooltip按原配置曲线显示百分数

原映像：`native-image.bin` SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`，50675712字节，BASE0x400000。原Soul配置仍为先前直接复核的`artres/config.pfs::autoconfig/knight.gsp.pet.cpetsoulattrcfg.xml`（SHA256 `da015cfbf873037ea91541fc17699654031d888a49f8520c0db70f929590f690`）。本批重点执行显示消费者，不重复把属性映射当新数学证据。

原`15993b0`接受**魂珠对象**与0-based等级指针：

1. `15993b3`经`89e380`的原CPetSoulAttrCfg表按对象+c模板ID查row；验证row存在、等级0..14。
2. `15993da`读row+44的`shuzitype`。type1从row+64的原double vector取项并经19191e0转int；type2在`15993fa..159940b`取同一原double项，乘原常量`2473e98=100.0`，再经原19191e0转int。
3. type2在`1599410..1599413`执行`cdq; xor eax,edx; sub eax,edx`取绝对值。负向减免曲线只在这条**显示**路径取正；服务端原负Fraction不能因此反号。
4. 原`1599140`同样查对象模板row+44：type2选择UTF16地址`22a6768`，确切内容`%d%%`；其它分支`224bdc4`为`%d`。本批执行原format选择，宿主仅观察string构造终端入参，得到type1→`%d`，type2→`%d%%`。
5. 有名字的原renderer`15a0d60`已由原ChatItemTips魂珠分支定位：在`15a111a`/`15a1209`调用1599140，在`15a113c`/`15a121d`调用15993b0，再把原integer与原format传入809e90格式化。它分别用于前一档/当前档能力文字。该函数前后也读XP和魂技等魂珠字段；不是Pet属性合计函数。

实际执行10种珠×15档共150项原15993b0、内部原1078780 vector取项与原乘法/int/abs：

| 模板 | 对应modifier | 原曲线首/末项 | 原helper首/末integer | 配原format得到的表示 |
| --- | --- | --- | --- | --- |
| 31290/31292 天相/天机 | 1551/1561 | 0.01 / 0.15 | 1 / 15 | 1% / 15% |
| 31291/31293 高级 | 1551/1561 | 0.03 / 0.20 | 3 / 20 | 3% / 20% |
| 31294/31296/31298 三减免 | 741/1581/1591 | −0.01 / −0.15 | 1 / 15 | 1% / 15% |
| 31295/31297/31299 高级 | 741/1581/1591 | −0.03 / −0.20 | 3 / 20 | 3% / 20% |

普通完整integer向量为1..15；高级为`3,4,6,7,8,9,10,11,12,13,14,15,17,18,20`。这里“得到的表示”由实际原integer+实际原format确定；未执行完整CRT文字排版或GUI绘制。只以原PFS浮点向量作为查表Adapter，未替换数值计算。

## 与最终Pet core整数scale的严格区别

**这条路径不读取Pet.GetAttribute(740/1550/1560/1580/1590)。** 它读取魂珠对象+c的template ID，随后按等级从原CPetSoulAttrCfg double向量取值。helper没有Pet对象参数、当前角色基线、其它珠子合计、整数属性map或最终战斗比例。因此证据只支持“魂珠自身能力tooltip以配置ratio×100的整数百分数显示”；不能推出“Pet aggregate core存储ratio×100”，更不能推出×10000。

先前已执行的c32c9→Pet attr通用分支仍截float到int；本批没有找到从五项**聚合core整数**到真实显示控件的可证链路。因此维持native aggregate ratio投影pending，保留server exact Fraction与明确完整来源。已经存在的完整元魂map/逐珠tooltip渠道能表达珠子的自身效果，但本批未执行登录到实际tooltip的整条GUI链，不将它冒称五项合计已经显示。

## 原布局与Pet UI定位范围

本批直接读取原`artres/ui.pfs`，长度/CRC通过：

| 路径 | 字节 / CRC32 | SHA256 |
| --- | --- | --- |
| layouts/petproperty.layout | 60385 / 4f05e6f3 | 517ef2551036d743368ad3d4d44ddb7e001ecb97b289884eba389d02e200e681 |
| layouts/petinfodialog.layout | 80487 / 9574b900 | 338ee34ebcdceb0686209c5a61c0b65a919ed59c41156396362b25c949b7aa43 |
| layouts/petsoul.layout | 11704 / db944048 | 959f9ade38a52f3c6a81d64453a7bfc5e42d14f8dc4f0c84e85e2a7f59282abf |

PetProperty/PetInfo的原布局含生命/真气、内外攻防、速度、五维等明确控件。原绑定`1426f02..1426f36`查`PetPropertyDlg/damage`；`140ee6c..140eead`查`PetInfoDialog/damage`并存成员+a0。后者对应实际刷新`141164b..141166b`以core80查询4e8e00，把原integer经4901c0转文字再送该控件。相邻刷新同理读取core100/130/810/820等。这里只定位了真实普通数值控件，**没有完成全Pet UI所有消费者的穷尽证明**。

原`PetSoul`布局有“元魂效果”及RichEditbox `PetSoul/Back/Name6`，但本批未将其动态绑定与五项aggregate GetAttribute闭合。`cattrtipsconfig`仅为十个人物门派五维加点说明，不是五项Pet ratio scale定义。局部搜索未找到五项core直接消费，不据此断言“客户端根本不展示”或“不需发包”。

## 可复现：原150项计算与格式选择

项目根以已有Python执行；先native_inspect再Unicorn。查表Adapter只提供原配置行，string Adapter只记录原literal，所有算术/分支/索引/返回均原码。没有写文件或访问进程。

```python
import sys,struct
sys.path.insert(0,'revival')
from native_inspect import DATA,BASE,u32
from pfs import PfsArchive
from bxml import decode
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
rows=list(decode(PfsArchive('artres/config.pfs').read('autoconfig/knight.gsp.pet.cpetsoulattrcfg.xml')))
u=Uc(UC_ARCH_X86,UC_MODE_32)
u.mem_map(BASE,(len(DATA)+4095)&~4095);u.mem_write(BASE,DATA);u.mem_map(0x5000000,0x20000)
obj,cache,vt,row,values,index,out,stack,stop,lookup=(0x5000000,0x5001000,0x5002000,0x5003000,
    0x5004000,0x5005000,0x5006000,0x5010000,0x500f000,0x500f100)
ctor=u32(0x22443f0)
if not BASE<=ctor<BASE+len(DATA):u.mem_map(ctor&~4095,4096)
def w(a,*v):u.mem_write(a,struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v)))
def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
def ret(n,value):
    sp=u.reg_read(UC_X86_REG_ESP);dest=r(sp)
    u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_ESP,sp+4+n);u.reg_write(UC_X86_REG_EIP,dest)
formats=[]
def hook(uc,addr,size,_):
    if addr==0x89e380:ret(0,cache)
    elif addr==lookup:
        assert r(u.reg_read(UC_X86_REG_ESP)+4)==r(obj+0xc);ret(4,row)
    elif addr==ctor:
        ptr=r(u.reg_read(UC_X86_REG_ESP)+4);raw=bytearray()
        while bytes(u.mem_read(ptr+len(raw),2))!=bytes(2):raw.extend(u.mem_read(ptr+len(raw),2))
        formats.append(raw.decode('utf-16le'));ret(4,u.reg_read(UC_X86_REG_ECX))
    elif addr==stop:u.emu_stop()
u.hook_add(UC_HOOK_CODE,hook);w(cache,vt);w(vt+8,lookup)
assert struct.unpack_from('<d',DATA,0x2473e98-BASE)[0]==100.0
normal=tuple(range(1,16));advanced=(3,4,6,7,8,9,10,11,12,13,14,15,17,18,20)
tested=0
for original in rows:
    attr=original.attrib;template=int(attr['id'])
    if int(attr['attrid']) not in (741,1551,1561,1581,1591):continue
    w(obj+0xc,template);w(row,template);w(row+0x44,2)
    vector=[float(x.text) for x in original.find('attrvalue')]
    u.mem_write(values,struct.pack('<15d',*vector));w(row+0x68,values,values+120,values+120)
    got=[]
    for level in range(15):
        w(index,level);w(stack,stop,index)
        u.reg_write(UC_X86_REG_ECX,obj);u.reg_write(UC_X86_REG_ESP,stack)
        u.emu_start(0x15993b0,0,count=1000);got.append(u.reg_read(UC_X86_REG_EAX))
    assert tuple(got)==(normal if template%2==0 else advanced)
    tested+=15
for kind,want in ((1,'%d'),(2,'%d%%')):
    w(row+0x44,kind);w(stack,stop,out)
    u.reg_write(UC_X86_REG_ECX,obj);u.reg_write(UC_X86_REG_ESP,stack)
    u.emu_start(0x1599140,0,count=1000)
    assert formats[-1]==want
assert tested==150
print('PASS150 original soul ratio tooltip computations and two original format branches')
```

## 方法、决定与未验证

research按第一方控件/指令/表逐项追踪，使“×100”只归属于真正读取曲线的魂珠tooltip，不扩大到未知Pet core integer单位。产物仅本文；上面复现重新执行exit0。已读原布局、原常量/UTF16格式，原helper150项与两format分支通过；用户可见GUI、完整renderer/CRT排版、最终aggregate属性五项UI消费、整数scale/舍入、battle比例应用及共享/部署仍未验证。下一可执行定位是沿PetProperty/PetInfo完整刷新事件及元魂效果RichEditbox绑定逐个追GetAttribute调用与参数，不以原0xc32c9通用浮点载体猜单位。
