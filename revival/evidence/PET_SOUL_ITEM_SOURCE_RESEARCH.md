# 背包元魂珠实例与原穿戴入口研究

状态：completed（本批研究范围），2026-10-24。仅离线原始映像/资源研究；没有修改生产源码、共享入口、真实数据库或服务。

## 方法与范围

已读取 research Skill、项目 AGENTS、ARCHITECTURE 与 DESIGN_AUTHORITY。按 research 从原客户端映像和原包寻找直接证据，已有 PET_EQUIPMENT_SOURCE_RESEARCH 只作定位线索。本文是唯一研究产物，逐项落盘并保留 unknown，未确认字段不填零或猜义。

目标：背包 type145 元魂实例的原解析器与额外 wire 数据；其经验、魂技和 raw 字段怎样进入 worn PetSoul；原 CUseItem 穿戴分支及数量、槽位、重复、宠物资格约束；完整 tips 与旗标/绑定关系。已知原 c0804 为融合意图，不当作穿戴。

## 直接证据

本轮直接 RTTI/原指令已区分两类，不能把名字相近的对象混用：

- `PetSoulObject` RTTI `0x28ce714`、vtable `0x228c294`，构造 `0x1074110`。它在对象+0x58构造 `PetSoulTipsOctets`（`d98fc0`、vtable `0x2277340`），后者为字符串/Octets包装。
- 另一原对象vtable `0x228c2b4`，构造 `0x10743c0`，在+0x60内嵌 `PetSoulPerlItemTipsOctets`（vtable `0x227732c`），该bean原构造 `0xd98f90` 明确四个int字段（+4/+8/+c/+10）。原marshal `0xe4dc30` 与decoder `0xd994a0`各处理四个BE32，**不是 worn PetSoul 的六个BE32**。准确类型和映射见下方原解析器实际执行，不把四项硬补成六项。
- 原 `0x10a5310` 穿戴确认函数：无当前宠分支到`10a5494`返回；`10a5499`检查Pet+0xc4恰等于5；`10a55d5..55eb`把候选物品模板+0xc交给原`108d730`精确ID重复检查；通过后`10a56f3`动态转换到`0x28ce74c`目标类型，确认说明只调用经验/摘除数量/有效级格式函数。`10a58b8..58c6`捕获物品key(+0x14)和Pet首字段至全局`294ac24/294ac28`，随后145350确认的回调是`1089150`。当前检查段未发现普通/高级同属性额外互斥，但上游type145入口及服务端约束尚未确认，不能由此排除其他路径。

### 本轮实际原码执行：四字段与六字段的映射

已执行 `PetSoulPerlItemTipsOctets` 原构造 `d98f90`、marshal `e4dc30`、fresh decoder `d994a0`，fixture四项 `(61,10001,-205,204)` 得精确16字节 `0000003d00002711ffffff33000000cc`，fresh对象四项相等，负数原样保留。RTTI补证：上述vtable `0x228c2b4` 的准确类名是 **CYuanHunZhuObject**（descriptor`0x28ce74c`，名字位于+8），而非 PetSoulObject。

已执行原 `CYuanHunZhuObject` 构造 `10743c0` 与非空实例parser `107a020`，流内四项 `(120,10002,205,204)` 被原decoder完整消费16字节，最终对象+64/+68/+6c/+70逐项完全一致。parser还由物品基础flags（对象+10）取bit0到对象+5d；按原元魂配置soulType==2设置+5c。

已执行原 `1402f90`（将 worn PetSoul 转为 CYuanHunZhuObject 的构造）。输入六项 `(31277,120,10002,204,205,raw6)`，输出：

| worn bean来源 | 背包珠对象 / 四字段tips |
|---|---|
| item_id，第1项，bean+4 | 对象+0xc（不在四字段tips内） |
| 累计XP，第2项，bean+8 | 对象+0x64 / 四项第1项 |
| 魂技ID，第3项，bean+0xc | 对象+0x68 / 四项第2项 |
| raw4，第4项，bean+0x10 | 对象+0x70 / 四项第4项 |
| raw5，第5项，bean+0x14 | 对象+0x6c / 四项第3项 |
| raw6，第6项，bean+0x18 | 对象+0x5d，按 **raw6!=0** 变成0/1；不在四字段tips内 |

因此交换两种来源时后两项顺序必须交叉，不能直接拷贝六项尾部。raw4/raw5业务名字仍unknown，仍须原样保存。raw6已确认关联对象+5d显示标志，但其完整业务/服务端域仍需消费者语义；不能直接称“完整基础flags”。

实际执行共10个原parser/转换fixture：原bag flags和worn raw6分别取0/1/2/160/161。bag +5d结果为0/1/0/0/1（bit0）；worn +5d为0/1/1/1/1（非零）。这证明两个输入不可按相同整数旗标盲拷。**宿主Adapter**仅代替既有已独立验证的等级函数`1078b30`返回已知2，及`89e380`配置查表提供原31277的soulType2；此批测试目标为原字段赋值/16字节解析和旗标提取，不重复认证XP等级公式。原构造、四项decoder、全部赋值和原函数自然返回均执行；没有GUI。

追加6个负值fixture：输入-1、-2、-2147483648时，bag+5d依次1/0/0，而worn+5d均1。worn输入bean中的原raw6逐字仍是原负值，构造函数只归一化显示副本。因此 **raw6的完整整数必须继续保留**；可称“传入对象+5d的原始标志”，不能从bag bit0反推原raw6，也不能将既有2或负值改写成1。+5d与基础bit0一致的事实支持绑定显示关联，但本批未执行最终标签/GUI观察者，精确业务命名不升级为新服务端权限或完整原始flags。

### 原背包/tips与使用入口

本轮直接原包读取 `artres/config.pfs::autoconfig/knight.gsp.item.citemattr.xml`，PfsArchive已执行目录/本地头/长度/CRC一致性检查后BXML解码：解压4096369字节，CRC`a3add081`，SHA256`974a3b38049c5f5f7cdae418718ffadd2741d373a5846a40fb71289af25e726f`。type145恰28行31276..31303，全部 **maxNum=1、level=0、needLevel=1、outbattleuse=2**。没有实例bind/quality字段，不能从配置缺字段推实例旗标0。首行原usemethod明确右键对宠使用、使用后右键取出。

原背包对象工厂 `107fe20`：经citemattr类型后，`107ff11`明确比较type`0x91=145`，`107ff1b..107ff29`分配0x78并构造CYuanHunZhuObject；`107ff32..107ff5e`取原Item bean的+0x10 Octets构造流并调用对象vtable+8（`107a020`）。公共基础字段随后设置；`10805b5..10805f0`非空附加Octets再调用同一parser，故最终原基础模板/flags已在对象上。另一个原工厂`1080899..10808b4`同样按type145构造该类。此为静态原分支，不宣称本轮执行了整个背包工厂。

实际外层 `SItemTips` 原构造`d9c110`、marshal`e4e5c0`、fresh decoder`e0a240`往返通过：column1/key333、16字节四项 `(120,10002,205,204)`，body精确为 `000000010000014d100000007800002712000000cd000000cc`（两BE32+compact16+四BE32）。fresh对象容器/key及Octets内容逐字相等。它是普通SItemTips封套，**不能**给元魂详情套116字节普通装备详情，也不应在16字节中额外插入模板或worn raw6。是否请求详情的后续UI仍未执行。

上游实际type路由已追到原 `10acd90`：一般状态分支`10acde6..10ace27`、物品相关分支`10ace2e..10ace71`在前；`10ace9b`直接比较item type`0x91`，`10acea8`进入`10a5310`。其后`10aceb2`才有另一个通用物品检查，不能声称type145经过后面的所有通用条件。前置消息141174原文是“该道具只能在战斗中使用”，仅凭全局字段位置不能反推完整战斗/锁定准入模型。原确认函数只在缺当前宠、已有5颗、精确模板重复或动态类型失败时离开已追踪的正常路径；后续仅构造展示参数和确认，未见“高级与普通同属性”互斥或实际宠当前级比较。

原CUseItem发送回调`1089150`和`141b0b0`均明确 `count=1`，target为捕获petkey的符号扩展64位，type`0xc03ff`。原消息原包对照：145349=“已携带5颗，是否打开融合”；145350确认展示移魂符数量和受参战等级限制的有效级；145808=“没有设置参战宠物，是否打开融合”。这些UI约束不能代替服务器资产/战斗/技能权限验证。

## 最小复现（本轮实际运行的核心设置）

工作目录`D:/神雕侠侣/revival`，Python使用本项目已配置运行时，先import原native工具以加入依赖。bean与完整tips的直接复现：

实际运行时：`C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`，`PYTHONUTF8=1`。原镜像本轮重核50675712字节、SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。完成报告后已直接从本文提取并重新执行以下两个Python代码块，均PASS；后一个覆盖16个不同模式/旗标组合，未依赖持久化辅助脚本。

```python
import struct
from native_gameplay_probe import probe
values=(61,10001,-205,204)
body,raw=probe(0xd98f90,0xe4dc30,0xd994a0,
               {4:struct.pack('<4i',*values)})
assert body==struct.pack('>4i',*values)
assert struct.unpack_from('<4i',raw,4)==values
obj=0x5001000
detail=struct.pack('>4i',120,10002,205,204)
fields={8:struct.pack('<ii',1,333),
        16:struct.pack('<II',0x224c100,obj+0x200),
        0x1f4:struct.pack('<III',16,16,1),0x200:detail}
encoded,_=probe(0xd9c110,0xe4e5c0,0xe0a240,fields)
assert encoded.hex()=='000000010000014d100000007800002712000000cd000000cc'
```

16个原parser/转换fixture的核心执行函数如下；等级和配置查找被明确隔离，全部字段赋值仍为原码，读数不是由Python复制原公式得到：

```python
import struct
from native_inspect import DATA,BASE
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
def run(mode,flags):
    uc=Uc(UC_ARCH_X86,UC_MODE_32)
    uc.mem_map(0,0x1000)
    uc.mem_map(BASE,(len(DATA)+4095)&~4095);uc.mem_write(BASE,DATA)
    uc.mem_map(0x5000000,0x400000)
    obj,bean,stream,buf=0x5001000,0x5002000,0x5003000,0x5004000
    cache,vtbl,row=0x5005000,0x5006000,0x5007000
    stack,stop,lookup=0x5100000,0x500f000,0x500f100
    def w(a,*v):
        uc.mem_write(a,struct.pack('<'+'I'*len(v),*[x&0xffffffff for x in v]))
    def rd(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
    def ret(value,count=0):
        sp=uc.reg_read(UC_X86_REG_ESP);dest=rd(sp)
        uc.reg_write(UC_X86_REG_EAX,value)
        uc.reg_write(UC_X86_REG_ESP,sp+4+count);uc.reg_write(UC_X86_REG_EIP,dest)
    w(cache,vtbl);w(vtbl+8,lookup);w(row,31277,2)
    def hook(uc,address,size,user):
        if address==0x1078b30:ret(2)
        elif address==0x89e380:ret(cache)
        elif address==lookup:ret(row,4)
    uc.hook_add(UC_HOOK_CODE,hook)
    if mode=='worn':
        w(bean,0x227b308,31277,120,10002,204,205,flags)
        w(stack,stop,bean)
        uc.reg_write(UC_X86_REG_ECX,obj);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0x1402f90,stop,count=100000)
        assert struct.unpack('<i',uc.mem_read(bean+24,4))[0]==flags
    else:
        w(stack,stop)
        uc.reg_write(UC_X86_REG_ECX,obj);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0x10743c0,stop,count=100000)
        w(obj+12,31277);w(obj+16,flags)
        w(stream,0x224c100,buf,0);w(buf-12,0x7000,16,1)
        uc.mem_write(buf,struct.pack('>4i',120,10002,205,204))
        w(stack,stop,stream)
        uc.reg_write(UC_X86_REG_ECX,obj);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0x107a020,stop,count=100000)
        assert rd(stream+8)==16
    assert uc.reg_read(UC_X86_REG_EIP)==stop
    assert rd(obj+12)==31277 and rd(obj+0x58)==2
    assert uc.mem_read(obj+0x5c,1)[0]==1
    assert struct.unpack('<4i',uc.mem_read(obj+0x64,16))==(120,10002,205,204)
    return uc.mem_read(obj+0x5d,1)[0]
for value in (0,1,2,160,161,-1,-2,-2147483648):
    assert run('bag',value)==value&1
    assert run('worn',value)==int(value!=0)
```

## 尚未知与实施影响

本批新增 `client_verified`：四字段bean16字节、原CYuanHunZhuObject解析、六→四交叉映射和原raw6非零提取、负raw保留、完整SItemTips封套、type145工厂及正常确认路由、原28珠maxNum1。业务范围仍unknown：raw4/raw5名字、raw6完整可用数值域与最终绑定标签语义、原服基础flags与worn第6项的精确逆转换、实际槽位开放/更多互斥/战斗锁定/过期等服务端准入、摘除绑定选择、融合消耗与经验守恒。未运行完整背包工厂或UI选宠/确认；不能从本批排除其他路径的额外限制。

实施建议：四项实例档案与穿戴六项档案分开持有；显式完整来源，非堆叠每实例独立，原始有符号raw4/raw5/raw6保留。存档四项命名可用XP、soul_skill_id、raw5、raw4；编码固定16字节。交换必须按已核映射，不把raw6归一化后的显示值回写历史来源。新实例如何取worn raw6若无明确原来源须另行设计标注，不能冒称原服；此报告不作数值设计或资产授权。

后续所有资产交换仍需角色所有者、有效租约、同一调用方事务和完整幂等凭据；离线解析通过不等于原 GUI 或服务端准入完成。方法实际影响：research迫使区分两个近名原对象及两种bean，避免了把背包四项误当六项、尾部顺序错误和丢失raw6负值；所有新增断言均有原码/原包或原码执行对应，不依赖次级攻略。
