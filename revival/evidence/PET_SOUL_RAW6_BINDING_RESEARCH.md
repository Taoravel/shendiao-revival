# 元魂 raw6 与绑定显示消费者研究

状态：completed，2026-10-24。research 后台有界调查；本报告为唯一写入产物。已读取 research Skill、AGENTS、ARCHITECTURE 与 DESIGN_AUTHORITY。直接跟随原映像/第一方资源；旧报告仅作地址线索。未改生产、既有封签报告、政策、真实数据库、服务或活客户端。

目标：核明 CYuanHunZhuObject+0x5d 的真实消费者、与基础 Item.flags bit0 的区别，以及 worn raw6 是否可准确命名为绑定/锁定。未知2或负值不归一化、不反推原服逆转换；由证据决定后续策略，本文不改本地返还策略。

## 已验证与当前未验证

旧来源已给出定位：原1402f90把worn raw6按非零投影到对象+5d；原107a020从基础flags取bit0到同一位置。本文已独立核对原getter、有资源名字的tooltip绑定/锁定控件及必要原码分支；+5d的业务名称仍不升级为client_verified。

## 2026-10-24 已落盘的直接发现

原映像 SHA256（本批重新计算）：`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。地址均为该映像原VA，载入基址0x400000。通过`native_inspect`读取，随后才导入Capstone/Unicorn；`disasm`第二参数为字节数。

### client_verified：有名字的绑定显示路径读取基础flags，不读取+5d

- `0x159e131..0x159e180`：原UI初始化以字符串`0x22be5fc = "ChatItemTips/bind"`查找控件（调用`0x4552c0`），把返回控件写入UI对象`+0x40`。
- `0x15adcfd`取`ECX=[ESI+0x38]`（ItemRef）；`0x15add00`调用原getter`0x1072e70`。
- getter原码：`mov eax,[ecx]; mov eax,[eax+0x10]; and eax,1; ret`。确实是ItemRef所指基础Item的flags bit0。
- `0x15add05..0x15add12`：测试返回AL，把0或1传入控件`[ESI+0x40]`的`0x463580`。原`0x463580`在`0x4635a6..0x4635b2`比较并写入控件`+0x130`可见状态，继续发送UI通知。
- `0x15add17..0x15add47`：这一绑定显示分支之后，才检查ItemRef类型`0x91`，经RTTI`0x28ce74c`向CYuanHunZhuObject转换，调用魂珠专用renderer`0x15a0d60`。因此该路径确实覆盖元魂珠，且不是根据邻近地址猜测控件。
- 第二处同构路径`0x180029a..0x18002af`同样调用`0x1072e70`，控制UI`+0x30`，随后类型0x91转换并调用`0x17ee520`。本批尚未核第二控件的资源名字，不能单凭同构命名。

### client_verified：原绑定getter及分支的离线执行

执行区间`0x15adcfd -> 0x15add17`。原getter`0x1072e70`完整执行并自然`ret`；原条件分支完整执行。宿主Adapter仅截获UI函数`0x463580`，记录ECX和第一个参数，模拟其`ret 4`；并未执行整套GUI或声称真实窗口出现。所有8项均自然到达Adapter返回地址`0x15add17`，栈恢复到初始`0x31008000`。

| 基础flags | 独立对象+5d | 原getter返回 | bind控件可见参数 |
| --- | --- | --- | --- |
| 0 | 0 / 1 | 0 / 0 | 0 / 0 |
| 1 | 0 / 1 | 1 / 1 | 1 / 1 |
| 2 | 0 / 1 | 0 / 0 | 0 / 0 |
| 0xffffffff | 0 / 1 | 1 / 1 | 1 / 1 |

这里人为独立改变对象+5d以检测该分支依赖；不是把worn raw6写入flags，也不是原服逆转换试验。该结果证明**有名字的Bag聊天tooltip绑定控件依赖基础flags，不依赖对象+5d**；不能据此证明+5d在其它路径无业务意义。

### client_verified：+5d的生成和复制；实际业务读取仍unknown

独立重读原码：

- `0x1402f90`穿戴记录转对象，`0x1403067 cmp [edi+0x18],0; 0x140306a setne al; 0x140306d mov [esi+0x5d],al`。raw6非零仅投影成bool副本，未写回原raw6。
- `0x107a020`普通魂珠tips parser：`0x107a062 mov al,[esi+0x10]; and al,1; mov [esi+0x5d],al`，缺配置分支`0x107a073..0x107a078`亦相同。
- 原CYuanHun vtable`0x228c2b4`仅三个入口：destructor`0x10744c0`、clone`0x1077e00`、parser`0x107a020`；其后字节不是可继续枚举的方法。
- clone`0x1077e33..0x1077e36`、复制构造`0x184a8a0`等复制+5d；复制不证明绑定、锁定或交易限制。
- `0x18498e0`是`mov al,[esp+4]; mov [ecx+0x5d],al; ret 4`setter；本批没有找到其直接E8调用或绝对地址引用，尚不能建立业务调用关系。
- `0x184b1a0`更新魂珠实例四字段，并从第五参数写+5d；`0x184d350`消费消息，通过物品key查对象并dynamic_cast CYuanHun，在`message+0x1c!=0`时向上述第五参数传1，否则0。这个消息也是非零投影来源，但消息原业务字段名/操作协议尚unknown。

有界代码扫描`0x1070000..0x1900000`中直接byte内存位移0x5d访问，逐项区分对象类型。当前定位出的CYuanHun读操作均为复制；两个专用renderer`0x15a0d60`、`0x17ee520`的已检查前段使用+5c（soulType==2）和+68（skill），未定位到+5d条件读取。扫描不能覆盖别名、内联宽读取、所有函数或服务器逻辑；**不宣称全客户端没有消费者**。

`0x17e2dd0`虽有`mov al,[ecx+0x5d]; ret`字节序列，但无已知调用/类型关联；本批不给它贴CYuanHun getter标签。基础flags getter`0x1074420`与ItemRef getter`0x1072e70`均不是+5d getter。

### client_verified：第一方标签文本与独立锁图标

直接解码原`artres/ui.pfs`的`layouts/chatitemtipsdlg.layout`，解压内容3862字节、SHA256 `d522ee9bdf78299fea6e9e949207414ac3e62a5adbd14cfc0f50bb4d1a81274c`：

- `Name="ChatItemTips/bind"`为`TaharezLook/StaticText`，`Text="已绑定"`。
- `Name="ChatItemTips/lockicon"`为`TaharezLook/StaticImage`，图像`set:MainControl5 image:Locked`。
- 原初始化`0x159e0d5`使用字符串`0x22be610="ChatItemTips/lockicon"`，`0x159e122`存控件至UI+0x3c。
- 原刷新`0x15adbf9..0x15adc0d`取ItemRef指向对象，`test byte [eax+0x10],0x20`，以该结果开关UI+0x3c；该有名字的锁图标也是基础flags路径，没有读取+5d。

因此，至少在这一个完整可定位的ChatItemTips UI里，“已绑定”与锁图标各有独立基础flags来源。**不能把raw6/+5d当作任一已知控件的授权标志**。这与“raw6最终业务含义unknown”并不冲突。

### client_verified：raw4/raw5已有可命名的客户端显示消费者

本批顺带直接读原码和原`artres/config.pfs`（未读或改服务器数值）：

- 原`0x1402f90`映射：worn raw4（记录+0x10）→对象+0x70；worn raw5（记录+0x14）→对象+0x6c。
- `0x15a1455`仅在魂技ID对象+0x68非零时进入魂技文字段。
- `0x15a14bf..0x15a14f7`以键`0x224bd64=UTF16 "parameter2"`，调用`0x1599040`产生显示值。`0x1599041`读取对象+0x6c（raw5），`0x1599049`加`0x23927=145703`，`0x1599058`调用文本查找`0x8370e0`。原message145704..145712依次为“一级”到“九级”。这条路径把raw5显示为**魂技等级**；不是由字段排序猜测。
- `0x15a1581`键`0x224bd34=UTF16 "parameter4"`；`0x15a1590`直接读取对象+0x70（raw4），`0x15a1593..0x15a15ad`以`0x224bdc4=UTF16 "%d"`格式写入parameter4。
- `0x15a15d0`取message145629（0x238dd），其原文包含“魂技等级：$parameter2$”与“当前还可点化$parameter4$次。”。故raw4在此被显示为**当前剩余可点化次数**。
- 无魂技分支`0x15a1618..`取message145630，只显示“附加魂技：无”。不能从该UI推导raw4/raw5可接受服务器范围、扣减公式或无魂技时的隐藏值规则。
- 原魂技效果helper`0x15a0ba0`还有raw5消费者：`0x15a0c20`读取+0x6c，要求>0且不超过技能效果列表长度；`0x15a0c62..0x15a0c78`用raw5-1选择描述项。与等级显示一致，但服务器技能效果和升级规则仍未恢复。
- 原`0x1854bb0`读取魂珠对象+0x6c，传给`0x1854a00`保存于选择UI的条目。这里只记录消费者，不根据地址邻近猜测操作协议名称。

直接资源：`autoconfig/knight.gsp.message.cmessagetip.xml` SHA256 `d0cfc9cb4613442be0bb8ec9262bf6db7f2c7fcb5ad28df05e150c4b0503fa20`；`autoconfig/knight.gsp.skill.cpetsoulskill.xml` SHA256 `f8ee542e2aa053bdbac99b3811a05e738bbca90ce8e73360ea9e8158381709c2`。后者只是辅助确认配置内容，没有作为raw4/raw5范围或计算权威。读取`cstringres`未找到145629/145630，随后改读原`cmessagetip`定位，不混淆两表。

## 最小复现：原getter + 原绑定条件分支

在项目根目录用现有Python运行下列代码；只在内存中映射原映像，不创建文件，不连接服务。先导入native_inspect，再导入Unicorn。DATA由native_inspect读取既有原映像，不能换成当前模拟服务或任意本地对象实现。8项预期如上矩阵。

```python
import sys, struct
sys.path.insert(0, 'revival')
from native_inspect import DATA, BASE
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import *
p = lambda x: struct.pack('<I', x & 0xffffffff)
for flags in (0, 1, 2, 0xffffffff):
    for marker in (0, 1):
        u = Uc(UC_ARCH_X86, UC_MODE_32)
        u.mem_map(BASE, (len(DATA) + 4095) & ~4095)
        u.mem_write(BASE, DATA)
        u.mem_map(0x30000000, 0x10000)
        u.mem_map(0x31000000, 0x10000)
        ui, ref, obj, ctrl = (0x30000000, 0x30001000,
                              0x30002000, 0x30003000)
        u.mem_write(ui + 0x38, p(ref))
        u.mem_write(ui + 0x40, p(ctrl))
        u.mem_write(ref, p(obj))
        u.mem_write(obj + 0x10, p(flags))
        u.mem_write(obj + 0x5d, bytes([marker]))
        u.reg_write(UC_X86_REG_ESI, ui)
        u.reg_write(UC_X86_REG_ESP, 0x31008000)
        result, returned = [], []
        def hook(uc, va, size, _):
            if va == 0x15add05:
                returned.append(uc.reg_read(UC_X86_REG_EAX))
            if va == 0x463580:  # host UI adapter, not native GUI
                sp = uc.reg_read(UC_X86_REG_ESP)
                ret, arg = struct.unpack('<II', uc.mem_read(sp, 8))
                result.append((uc.reg_read(UC_X86_REG_ECX), arg, ret))
                uc.reg_write(UC_X86_REG_ESP, sp + 8)  # ret 4
                uc.reg_write(UC_X86_REG_EIP, ret)
            elif va == 0x15add17:
                uc.emu_stop()
        u.hook_add(UC_HOOK_CODE, hook)
        u.emu_start(0x15adcfd, 0, count=100)
        assert returned == [flags & 1]
        assert result == [(ctrl, flags & 1, 0x15add17)]
        assert u.reg_read(UC_X86_REG_EIP) == 0x15add17
        assert u.reg_read(UC_X86_REG_ESP) == 0x31008000
        print(flags, marker, returned, result)
```

`native_inspect.disasm`复核位置：`(0x1072e70,16)`、`(0x159e131,96)`、`(0x15adcfd,96)`、`(0x15adbf9,32)`、`(0x1599040,40)`、`(0x15a1581,176)`。两个renderer从入口线性解码至第一个自然ret分别为`0x15a1833 ret 4`、`0x17eeff3 ret 4`；函数体直接对象字段访问中无+5d，但这不是跨所有被调用函数的完备性证明。

## 判定、方法记录与未验证范围

- **client_verified**：raw6非零投影+5d；Bag tips从flags bit0投影+5d；有名字的“已绑定”标签实际使用基础flags bit0；独立锁图标用基础flags0x20；raw4=显示剩余可点化次数，raw5=显示魂技等级。
- **inferred**：+5d像是为穿戴/背包两来源保留的布尔影子。来源相似不足以命名为绑定、交易限制或锁定授权，本报告不据此修改恢复实现。
- **unknown**：raw6的原始业务名、非零各值是否另有服务器含义；真正用+5d做业务决策的消费者；原穿戴→卸下时如何生成基础flags；184d350消息类/协议type；原服对raw4/raw5的修改公式；交易投递/摊位/赠送/销毁/锁定全链的raw6授权规则。

research方法实际影响：把**来源投影、UI字段依赖、业务权限**分别建立证据；通过原控件字符串/PFS文字反向核对getter，再用flags×+5d独立矩阵排除该显示路径的假依赖。由此不把旧raw6=0与新Bag binding1显示不一致视作客户端故障，也不擅自把2/-2归一化为1。当前本地设计仍应标designed；原raw6保真继续有必要，因为bool投影不可逆。

产物仅本报告。验证完成：原映像重哈希；3个相关原资源内容哈希；原getter自然返回及8项原分支执行；原UI路径和raw4/raw5消费者静态追踪。未验证：全GUI、真实账号或数据库、真实网络、原服务器行为、所有+5d别名读取。旧研究仅用于地址线索；检索时一次泛化rg意外枚举到归档文件名，结果未作为新事实或证据，随后改为只枚举revival顶层py。无需为保留unknown继续无限追协议。
