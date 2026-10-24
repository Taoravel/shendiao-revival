# 元魂背包基础 Item 与详情来源补证

状态：completed（本批有界来源研究），2026-10-24。research 后台研究；唯一修改本文，未修改生产、既有封签报告、共享入口、真实数据库或服务。

已读 research Skill、AGENTS、ARCHITECTURE、DESIGN_AUTHORITY。按原映像指令/原编解码追实际参数类型，旧报告只作地址线索。问题是旧 `PET_SOUL_ITEM_SOURCE_RESEARCH.md` 将 `107fe20` 称为背包工厂并把其输入+0x10称为附加Octets，而实际基础 Item 的+0x10已独立证明为位置；两者不可混用。

## 核心更正与可实施消息顺序

**client_verified：普通背包 Item 不包含元魂四字段Octets。** 原 `Item@gsp@knight@@` vtable `0x224d4fc`，其marshal `0x822040` / unmarshal `0x81a590`的完整wire为9项scalar：`BE32 template, BE32 flags, BE32 key, BE32 position, BE64 scalar5, BE32 quantity, BE64 scalar7, BE32 scalar8, BE64 scalar9`，共48字节。基础Item内存+0x10是position，附加四项不能插入其中。基础Item其余未命名scalar的业务含义本批不猜；现有恢复编码为0的历史状态也不证明原服总为0。

**client_verified：107fe20 输入是 TradeItem，不是上述 Item。** 本文 supersedes `PET_SOUL_ITEM_SOURCE_RESEARCH.md` 中“原背包对象工厂107fe20、Item+0x10附加Octets”的归类措辞；旧报告保持封签历史，其已执行四字段codec、CYuanHunZhuObject parser、六→四转换与SItemTips证据不因此失效。

可实施顺序是：先发送普通 `SGetBagInfo` 基础Item记录建立容器1/key的当前对象；再发送该实例 `SItemTips(column1,key,16-byte orb tips)` 补充四项；穿戴宠物完整map另发 `SendPetSouls`。这是已核验编码和消费者支持的实施选择，不是本批执行了全登录或服务器准入。已存在的ItemRef更新由SItemTips精确容器/key定位；不存在时不创建、不跨列兜底。不能用TradeItem/GivenItem的布局替换普通背包Item，不能将元魂四项塞入48字节基础记录，也不能给元魂详情套普通装备116字节结构。

## 两种工厂的直接原参数证据

- `107fe20` 为以ItemRef为this的展示/交易物品构造路径，结束 `108063e ret 0xc`，三个栈参数分别来自调用方的UI指针、TradeItem指针及显示选项。本函数 `107fe53`检查第1参数非零；`107fe66`将第2参数送ESI，`107fe6d`用 `[ESI+8]`查模板，`107ff32`将 `[ESI+0x10]`作为Octets流。`1080427..1080489`再从ESI+8模板/+c数量构造本地基础Item并调用81a760；+18的word和+20/+24的qword为额外交易字段。因此不是读取完整背包Item。
- 调用点 `1367359 call80ddc0 → 136736d/7371`写模板、数量 → `136737d..7388`传入结构指针和UI指针。原 `80ddc0` 将结构vtable设为 `0x224c168`，RTTI准确为 `TradeItem@trade@gsp@knight@@`；+4子对象vtable `0x224c108`，RTTI为 `GivenItem@item@gsp@knight@@`。TradeItem的+8是模板、+c数量、+10 Octets（其数据指针+14）、+18 word、+20 qword。GivenItem子对象本身只含模板/数量两项；**Octets属于TradeItem，不是GivenItem本体**。
- 原TradeItem ctor80ddc0 / marshal80ed10 / decoder80e640已执行非空往返：模板31277、数量1、16字节四项 `(120,10002,-205,204)`、word1、qword123456789，精确35字节：`00007a2d00000001100000007800002712ffffff33000000cc000100000000075bcd15`。原80ed10先虚调用GivenItem子对象marshal80ec80写两i32，再写Octets、word及qword。
- 普通背包路径是 `1081790`：栈第1参数column、第2参数基础Item指针EBX；`1081795`取EBX+4模板，`108179e..17a2`调用 `1080720(template,column)`；后者 `108075a`取第1参数模板、`1080899..08b4`按type145分配/构造CYuanHunZhuObject，**不读取Item的+10作Octets**。返回后 `10817b1..17b7`把完整基础Item复制到Object+8，`10817bc..17c9`赋真实column和position。全factory包含图标/UI资源，本批只执行其CYuanHunZhuObject原构造及随后原copy/位置片段，未运行完整factory。

## 原SItemTips消费者与实际非空验证

原 `SItemTips Process107a080`：`107a0b5..0cf`从消息+14取得Octets数据并准备局部流；`107a0d7..0f2`从消息+8/+c取column/key，调用完整原1091670。后者在物品管理器+0xa4的外层原map按column、其节点+0x10内层map按key查ItemRef。`107a13c..148`取现存ItemRef指向的Object，其vtable+8真实为元魂parser107a020，再用局部OctetsStream补四项。直到 `107a14a`停在GUI观察者之前。

本批先实际原Bag完整decoder `ef6220/ef62d0/ef6350`解析非空col1、cash10000、capacity40、模板31277、flags161、key333、position5、qty1；取得原Item64字节对象。随后在同一个离线原映像环境执行CYuanHunZhuObject原构造10743c0、原81a760复制及原10817bc..cc位置/容器赋值，再对SItemTips实际fresh decoder与上述完整原map查找和parser消费：

| 消息column/key | 原查找命中 | 最终元魂四项 | parser调用 | Octets消费 |
|---|---|---|---:|---:|
| 1/333 | 当前ItemRef | `(120,10002,-205,204)` | 1 | 16 |
| 4/333 | 未命中 | 原构造零值未变 | 0 | 0 |
| 1/334 | 未命中 | 原构造零值未变 | 0 | 0 |

三例中Object的模板31277、完整flags161、key333、position5和column1全部保持。未命中样例只是验证没有误投，不授权服务端使用不属于角色的key。原模板/flags来自实际Bag decoder和原Item copy，四项来自实际SItemTips decoder和原parser，不是Python向最终字段复制答案。

宿主Adapter：仅原XP等级函数1078b30隔离返回已独立认证的固定2，原89e380配置查表供应原31277的soulType2；lookup1091670及其108dca0/1090930两层STL查找真实执行，未替换返回值。原CRT内存分配/拷贝/引用计数使用既有 `native_gameplay_probe.probe` 的明确宿主适配。此批不重复认证XP公式，也不执行完整Process后续GUI刷新。

## 可直接复现的有界执行

工作目录 `D:/神雕侠侣/revival`，Python `C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`，`PYTHONUTF8=1`。先导入native_gameplay_probe/native_inspect以设置依赖。下方已实际运行；输出三例和原48字节基础Item结果均PASS。

fixture参数位置明确如下：`item`与`bag`是完整真实生产者报文可替换的输入；本例选定Item为template31277/flags161/key333/position5/qty1，`raw_items`取实际Bag decoder向量内容。`check(col,key)`的两个实参直接控制实际SItemTips目标，四项由其中`payload`指定，本例为`(120,10002,-205,204)`。完整map fixture只登记容器1/key333→当前ref。配置adapter的 `w(row,31277,2)`须随目标模板改为原模板与真实soulType，不得把高级type2套给普通31276。若Bag含多项，按实际解码Item的key选择目标64字节对象，而非假定向量唯一；若基础flags最高位为1，wire可用`>I`保留32位原pattern，内存读取仍按uint32核对，不因Python的signed打包范围裁剪。

```python
import struct
from native_gameplay_probe import probe
from native_inspect import DATA,BASE
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *
item=struct.pack('>iiiiQiQiQ',31277,161,333,5,0,1,0,0,0)
raw_items=[]
def bag_observer(uc,target):
    rd=lambda a:struct.unpack('<I',uc.mem_read(a,4))[0]
    start,end=rd(target+0x28),rd(target+0x2c)
    assert end-start==64
    raw_items.append(bytes(uc.mem_read(start,64)))
    assert struct.unpack_from('<I',raw_items[-1])[0]==0x224d4fc
bag=struct.pack('>iQi',1,10000,40)+b'\1'+item+b'\0'
probe(0xef6220,0xef62d0,0xef6350,payload=bag,observer=bag_observer)
results=[]
def check(col,key):
    def observe(uc,msg):
        obj,ref,bean,mgr=0x5011000,0x5012000,0x5013000,0x5014000
        oh,on,ih,inn=0x5015000,0x5015100,0x5015200,0x5015300
        cache,vtbl,row,lookup=0x5016000,0x5016100,0x5016200,0x5016300
        stack,stop=0x5100000,0x500f000
        def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*[x&0xffffffff for x in v]))
        def rd(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
        def ret(v,n=0):
            sp=uc.reg_read(UC_X86_REG_ESP);dest=rd(sp)
            uc.reg_write(UC_X86_REG_EAX,v);uc.reg_write(UC_X86_REG_ESP,sp+4+n)
            uc.reg_write(UC_X86_REG_EIP,dest)
        phase=[None];calls=[]
        def hook(uc,a,s,u):
            if a==0x1078b30:ret(2)
            elif a==0x89e380:ret(cache)
            elif a==lookup:ret(row,4)
            elif a==0x107a020:calls.append(a)
            elif phase[0]=='lookup' and a==0x107a0f4:uc.emu_stop()
            elif phase[0]=='consume' and a==0x107a14a:uc.emu_stop()
        uc.hook_add(UC_HOOK_CODE,hook)
        def run(addr,this,args=()):
            w(stack,stop,*args);uc.reg_write(UC_X86_REG_ESP,stack)
            uc.reg_write(UC_X86_REG_ECX,this);uc.emu_start(addr,stop,count=100000)
            assert uc.reg_read(UC_X86_REG_EIP)==stop
        w(cache,vtbl);w(vtbl+8,lookup);w(row,31277,2)
        run(0x10743c0,obj);uc.mem_write(bean,raw_items[0]);run(0x81a760,obj+8,(bean,))
        w(ref,obj);w(ref+8,145);w(ref+0x28,0)
        uc.reg_write(UC_X86_REG_ESI,ref);uc.reg_write(UC_X86_REG_EBX,bean)
        uc.reg_write(UC_X86_REG_EDI,1);uc.emu_start(0x10817bc,0x10817cc,count=10000)
        before=tuple(struct.unpack('<4i',uc.mem_read(obj+0x64,16)));assert before==(0,0,0,0)
        w(0x2944628,mgr);w(mgr+0xa4,0,oh,1)
        w(oh,on,on,on);uc.mem_write(oh+0x1d,b'\1');w(on,oh,oh,oh,1,0,ih,1)
        w(ih,inn,inn,inn);uc.mem_write(ih+0x15,b'\1');w(inn,ih,ih,ih,333,ref)
        w(stack+0x10,0x224c100,rd(msg+0x14),0)
        uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_EBP,msg);phase[0]='lookup'
        uc.emu_start(0x107a0d7,0x107a0f4,count=100000)
        found=uc.reg_read(UC_X86_REG_ESI);assert found==(ref if col==1 and key==333 else 0)
        if found:
            phase[0]='consume';uc.emu_start(0x107a10c,0x107a14a,count=100000)
        after=tuple(struct.unpack('<4i',uc.mem_read(obj+0x64,16)))
        assert after==((120,10002,-205,204) if found else before)
        assert (rd(obj+12),rd(obj+16),rd(obj+20),rd(obj+0x48),rd(obj+0x4c))==(31277,161,333,5,1)
        assert calls==([0x107a020] if found else [])
        assert rd(stack+0x18)==(16 if found else 0)
        results.append((col,key,bool(found),after,rd(stack+0x18)))
    payload=struct.pack('>ii',col,key)+b'\x10'+struct.pack('>4i',120,10002,-205,204)
    probe(0xd9c110,0xe4e5c0,0xe0a240,payload=payload,observer=observe)
for col,key in ((1,333),(4,333),(1,334)):check(col,key)
fields={4:struct.pack('<iiii',31277,161,333,5),24:struct.pack('<q',123456),
        32:struct.pack('<i',1),40:struct.pack('<q',456789),48:struct.pack('<i',7),56:struct.pack('<q',987654)}
encoded,_=probe(0x8184f0,0x822040,0x81a590,fields)
assert encoded==struct.pack('>iiiiQiQiQ',31277,161,333,5,123456,1,456789,7,987654)
assert len(encoded)==48
print('PASS',results,'Item48/no Octets')
```

TradeItem/GivenItem类型及非空35字节wire复现（已实际执行）：

```python
import struct
from native_gameplay_probe import probe
from native_inspect import DATA,BASE,u32
def rtti_name(table):
    descriptor=u32(u32(table-4)+12);start=descriptor-BASE+8
    return DATA[start:DATA.find(b'\0',start)].decode('ascii')
assert rtti_name(0x224c168)=='.?AVTradeItem@trade@gsp@knight@@'
assert rtti_name(0x224c108)=='.?AVGivenItem@item@gsp@knight@@'
assert rtti_name(0x224d4fc)=='.?AVItem@gsp@knight@@'
obj=0x5001000;detail=struct.pack('>4i',120,10002,-205,204)
fields={8:struct.pack('<ii',31277,1),16:struct.pack('<II',0x224c100,obj+0x200),
        0x1f4:struct.pack('<III',16,16,1),0x200:detail,
        24:struct.pack('<H',1),32:struct.pack('<q',123456789)}
encoded,raw=probe(0x80ddc0,0x80ed10,0x80e640,fields)
assert encoded==struct.pack('>ii',31277,1)+b'\x10'+detail+struct.pack('>Hq',1,123456789)
assert len(encoded)==35 and struct.unpack_from('<ii',raw,8)==(31277,1)
assert struct.unpack_from('<H',raw,24)==(1,) and struct.unpack_from('<q',raw,32)==(123456789,)
print('PASS TradeItem35/GivenItem2i32 != Item48')
```

## 未验证与实际影响

未执行完整UI图标/对象工厂和完整Bag/详情Process观察者、真实登录/返回珠GUI、服务端物品/宠物所有权、元魂穿戴/摘除/融合费用与幂等、原完整bagflags其他位语义。基础scalar中高位flags在wire仍是32位bit pattern，服务端编码器不得只接受非负signed31而截掉合法显式uint32来源；位语义与操作权限需另证。

方法实际影响：research将相同“+0x10”的类型上下文拆开，纠正了TradeItem/Item混淆，避免破坏原48字节基础Item协议；完整原map查找和现有对象parser证明可以按Bag→逐珠SItemTips的顺序补全实例四项。原始完整raw6仍仅属于穿戴记录/独立来源，不能从基础绑定位或显示副本倒推。
