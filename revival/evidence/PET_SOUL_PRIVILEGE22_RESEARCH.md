# 元魂有效级别 flag22 的原始来源

状态：completed，2026-10-24。research 后台有界调查。仅写本文；不修改生产、政策、历史报告或真实角色数据，不启动服务/客户端。

已读取 research Skill、AGENTS、ARCHITECTURE、DESIGN_AUTHORITY。调查原108f3a0中影响元魂有效上限的22究竟为何种索引/位、由哪个客户端管理器/消息维护；旧报告仅作定位线索。未知来源不默认false/0，不把客户端显示资格视为服务器业务授权。

## 已直接确认的纠正

`client_verified`：原108f411从全局0x2945534取对象，push0x16后调用1546940，检测返回的16字节副本+0xc是否非零；非零加有效上限1。1546940把参数验证在1..vector_count之间，减1后调用15466f0取16字节元素，复制完整四dword。**22是1-based条目索引，不是bit22。**

该全局的原创建814a80→1547f80分配0x34字节；构造1547fb2写vtable22ba690。其MSVC RTTI：vtable[-1]=251cc18，COL.type_descriptor+8原字符串为`.?AVMedalManager@@`。因此对象可直接命名MedalManager；不能继续根据旧“特权”临时名猜VIP。

原1546440作为消息handler从消息+0x10的map调用1545e40更新MedalManager的16字节vector；1545e40按bean第一项1-based索引选entry，写三项原整数，并把bean第四项==1转成entry+0xc布尔。handler另读第二集合与两项scalar；已确认的协议类/配置身份与仍未知的业务字段见下文。

## 第一方配置、消息身份与更新路径

原映像：`revival/evidence/native-image.bin`，50675712字节，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。地址均原VA，基址0x400000。

`client_verified`：`89cf40`返回ConfigManager+0x1c0；构造`1547feb..154802b`经其GetAllID条数分配第一vector，每条16字节。原ConfigManager析构`c99691..c9969c`对+1c0调用`861390`；该函数写vtable2252eec，其RTTI为`knight_gsp_game_CMingwen_table_implement@XMLCONFIG`。这不是`cmedalconfig`表，不能把同ID22的“家族龙舟成就奖章”联查到元魂上限。

直接读取 `artres/config.pfs::autoconfig/knight.gsp.game.cmingwen.xml`，PfsArchive验证长度/CRC，BXML解码后全部22行attributes及lists与现catalog逐行一致。原条目24753字节，CRC32 `9a154608`，SHA256 `c02db7b48b4b8a67a6f6f08a7cc8cc7398d55c42e143aade7f9ac690848b528e`。ID完整为1..22。第22行：

- name=`铭文·简易`，maxlevel=1；原激活文本为“宠物可获得超出自身参战等级限制的一级元魂珠能力”。这与原108f3a0的+1分支直接吻合。
- 原配置还记录activeconditionid=[19,20,21]、对应level=[1,1,1]、levelinall=30、itemid首项61543、itemnum首项1。**这些只是原配置值，本批没有验证激活请求、条件的AND/OR组合、扣料或服务端授予规则。**

原消息vtable2285c90的RTTI为`.?AVSRspXunZhangAndMingWen@chengjiu@gsp@knight@@`；该vtable的handler指针在2285ca8，值1546440。其第一集合wrapper的RTTI（vtable2285cdc）明确为`std::map<int, MingWenDetail>`；bean vtable2285cb4的RTTI为`MingWenDetail@chengjiu@gsp@knight`。本批尚未追到外层协议type数值，不猜编号、不提供未验证的共享路由。

`client_verified`：bean constructor `f8dd50` / marshal `f8e5d0` / unmarshal `f8e030`表示四个BE32字段。完整响应ctor `f8db70`、marshal `f8e830`、unmarshal `f8e8f0`表示两个BE32 scalar、compact-count的`map(BE32 key, 四BE32 bean)`，再第二map。第一bean的四项传入vector时：

| bean项 | 原消费者与可证语义 |
| --- | --- |
| 第1项（bean+4；树node+14） | 1545ea1检查1..条数，1545f06减1选vector位置；可命名铭文条目ID/index |
| 第2项（bean+8） | 原整数复制到entry+4；本批未证明完整业务名，保留raw2 |
| 第3项（bean+c） | 原整数复制到entry+8；本批未证明完整业务名，保留raw3 |
| 第4项（bean+10） | 1545ef0严格比较==1，转换bool写entry+c；该bool决定元魂+1，结合CMingwen22文案可命名激活状态投影 |

map外层key与bean第1项分别存在；该handler按bean第1项定位，不是按外层key直接选vector。本批测试二者都取22，不由此证明不相等时原服如何处理。更新只覆盖消息里出现的条目，**缺席条目保持既有vector值，不等于未激活**。第二集合与两项scalar另有用途，本批不猜其名称；完整角色铭文账本仍须独立可信基线、版本和持久来源。

## 实际离线执行结果

1. 原getter1546940及内部15466f0完整执行8项：索引0/−1/23及count21时索引22均返回`(-1,0,0,0)`；count22时索引1/2/21/22精确取对应16字节。无查表、getter或bounds替身。
2. 原108f411→108f430完整执行2项（含原getter），原EDI=6，entry22.active为0/1分别得6/7。这里刻意隔离已在旧来源确认的模板/魂技计算，仅验证真实铭文读取分支。
3. 原完整SRsp constructor→fresh decoder→remarshal，再执行原1546440/1545e40及STL迭代，bean第四项0/1/2分别写entry22.active=0/1/0。原向量写入实际为`(22,7,12345,active)`，不是宿主伪造getter结果。第二集合为空fixture；唯一新增宿主Adapter为角色对象查询11d5330返回None以隔离外观更新，UI管理器设缺席；不是完整GUI或服务器授权执行。

以上全部exit0。第2/3原整数7/12345是保真fixture，不宣称合法铭文等级或经验。不存在据此授予真实角色铭文的操作。

## 最小复现：getter与实际cap分支

在项目根以既有Python执行；仅内存原码与原资源，只写本文之外的零文件。先导入native_inspect再导入Unicorn。

```python
import sys, struct
sys.path.insert(0, 'revival')
from native_inspect import DATA, BASE
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import *
u = Uc(UC_ARCH_X86, UC_MODE_32)
u.mem_map(BASE, (len(DATA)+4095)&~4095); u.mem_write(BASE, DATA)
u.mem_map(0x5000000, 0x20000)
def w(a, *v):
    u.mem_write(a, struct.pack('<'+'I'*len(v), *(x&0xffffffff for x in v)))
manager, vector, out, stack, stop = 0x5000000, 0x5001000, 0x5002000, 0x5010000, 0x500f000
w(manager+8, vector, vector+22*16, vector+22*16)
for i in range(22): w(vector+i*16, i+1, 7, 12345, int(i==21))
def hook(uc, addr, size, _):
    if addr in (stop, 0x108f430): uc.emu_stop()
u.hook_add(UC_HOOK_CODE, hook)
for index, count in ((0,22),(1,22),(21,22),(22,22),(23,22),(22,21),(-1,22),(2,22)):
    w(manager+0xc, vector+count*16); w(stack, stop, out, index)
    u.reg_write(UC_X86_REG_ECX, manager); u.reg_write(UC_X86_REG_ESP, stack)
    u.emu_start(0x1546940, 0, count=500)
    got = struct.unpack('<4i', u.mem_read(out,16))
    want = (index,7,12345,int(index==22)) if 1<=index<=count else (-1,0,0,0)
    assert got == want
    assert u.reg_read(UC_X86_REG_ESP) == stack+12
w(manager+0xc, vector+22*16); w(0x2945534, manager)
for active in (0,1):
    w(vector+21*16+12, active)
    u.reg_write(UC_X86_REG_ESP, stack); u.reg_write(UC_X86_REG_EDI, 6)
    u.emu_start(0x108f411, 0, count=500)
    assert u.reg_read(UC_X86_REG_EDI) == 6+active
print('PASS eight original indexed getter cases and two original cap branches')
```

## 最小复现：完整消息codec与原更新消费者

```python
import sys, struct
sys.path.insert(0, 'revival')
from native_inspect import DATA, BASE
from native_gameplay_probe import probe
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *
for flag in (0,1,2):
    payload = struct.pack('>iiB5iB',0,77,1,22,22,7,12345,flag,0)
    def observer(u, target):
        manager, vector, actor, stack, stop = 0x5300000,0x5301000,0x5302000,0x5330000,0x500f000
        def w(a, *v):
            u.mem_write(a, struct.pack('<'+'I'*len(v), *(x&0xffffffff for x in v)))
        def rd(a): return struct.unpack('<I',u.mem_read(a,4))[0]
        w(manager+8,vector,vector+22*16,vector+22*16)
        w(manager+0x18,0,0,0); w(0x2945534,manager)
        w(0x294ad74,0); w(0x2944550,actor)
        def hook(uc, addr, size, _):
            if addr == 0x11d5330:  # host role lookup only, isolate appearance update
                sp=uc.reg_read(UC_X86_REG_ESP); dest=rd(sp)
                uc.reg_write(UC_X86_REG_EAX,0)
                uc.reg_write(UC_X86_REG_ESP,sp+12); uc.reg_write(UC_X86_REG_EIP,dest)
        handle=u.hook_add(UC_HOOK_CODE,hook)
        w(stack,stop,0,0)
        u.reg_write(UC_X86_REG_ECX,target); u.reg_write(UC_X86_REG_ESP,stack)
        u.emu_start(0x1546440,0,count=10000)
        assert struct.unpack('<4i',u.mem_read(vector+21*16,16)) == (22,7,12345,int(flag==1))
        assert u.reg_read(UC_X86_REG_ESP) == stack+12
        u.hook_del(handle)
    result,_=probe(0xf8db70,0xf8e830,0xf8e8f0,payload=payload,observer=observer)
    assert result == payload
print('PASS three complete original response codecs and real Mingwen vector updates')
```

## 直接资源复核

```python
import sys, json, hashlib
sys.path.insert(0,'revival')
from pfs import PfsArchive
from bxml import decode
arc=PfsArchive('artres/config.pfs')
name='autoconfig/knight.gsp.game.cmingwen.xml'; raw=arc.read(name)
rows=list(decode(raw))
with open('revival/catalogs/knight.gsp.game.cmingwen.json',encoding='utf-8') as f: saved=json.load(f)
assert len(rows)==len(saved)==22
for row,cached in zip(rows,saved):
    assert row.attrib == cached['attributes']
    assert {c.tag:[x.text for x in c] for c in row if len(c)} == cached['lists']
assert hashlib.sha256(raw).hexdigest() == 'c02db7b48b4b8a67a6f6f08a7cc8cc7398d55c42e143aade7f9ac690848b528e'
print('PASS original CMingwen22 configuration attributes/lists and hash')
```

## 实施影响与未验证范围

当前 `known_flag22` 是历史临时 Interface 名，可解释为**当前角色已知铭文22激活投影**；本报告不改序列字段或已封签政策。真实provider应读取角色所有者下带版本、明确完整来源的铭文账本，取22激活状态，随后随其他权限/来源固定在受理命令并fresh重验。不能读VIP、bitmask22、普通技能缺档0或客户端构造vector默认0；也不能把缺席更新当false。false必须来自明确已知未激活状态。

本批方法实际决定：research要求回到原RTTI/构造/析构/消费者与PFS，遂将旧“特权22”纠正为CMingwen22“铭文·简易”，排除了同ID奖章误联查和bit22/VIP推断。产物仅本文，三个复现段实际运行exit0；原bound8+cap2+decoder/handler3共13受控离线案例、原22行配置全量比对通过。**未验证**：外层type数值与真实路由、两个scalar/第二集合完整业务名、bean raw2/raw3完整语义、铭文激活/升级/付费条件和授予权限、持久化ledger/provider、原服规则、GUI/部署；不因客户端默认未激活而设计真实角色默认0。
