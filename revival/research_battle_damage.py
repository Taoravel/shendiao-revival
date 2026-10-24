"""Offline original round-result consumption; never opens a game or socket."""
from research_battle import NativeBattleDecoder


def consumed_target_hp(payload, *, item_index=0, target_index=0):
    """Run the original result-map dispatch, capturing its HP-change local.

    The input is an actual SSendRoundScript body. The original decoder builds
    its containers; original instructions 11910df..1191821 then iterate the
    selected target's result map. Logging is disabled exactly as in normal play.
    This is a protocol-consumer probe, not rendered-animation verification.
    """
    from unicorn.x86_const import UC_X86_REG_EBX
    n=NativeBattleDecoder().decode('SSendRoundScript',payload)
    item=n.list_items(n.obj+8)[item_index]
    target=n.list_items(item+0x38)[target_index]
    stack=n.stack
    n.u.mem_write(stack,bytes(0x500))
    n.write(stack+0x50,target-8)
    n.u.reg_write(n.sp,stack)
    n.u.reg_write(UC_X86_REG_EBX,item-8)
    n.u.emu_start(0x11910df,0x1191821,count=10000)
    if n.u.reg_read(n.ip)!=0x1191821:
        raise AssertionError('Original target-result consumer did not finish')
    value=n.read(stack+0x348)
    return value-0x100000000 if value&0x80000000 else value
