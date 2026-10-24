"""Original research bean->cache and GUI field readers; never opens game."""
from pathlib import Path
from dataclasses import replace
import hashlib,json,struct,tempfile
import xml.etree.ElementTree as ET
from inspect_client import OUT,write_json
from native_inspect import DATA
from verify_family_donation_native import Native
from unicorn.x86_const import UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_ESP
from verify_guild_research import make
from verify_guild_details_native import original_detail,detail_fixture
from guild_detail_protocol import GuildSceneIDs,guild_details
from guild_research import ResearchAward,native_skills


def original_fields(skill):
    n=Native();node,cache,head,created=0x5001000,0x5002000,0x5003000,0x5004000
    n.write(node+8,0x228253c,skill.skill_id,*skill.unbound_values)
    n.write(cache+4,head);n.write(head+4,head)
    n.uc.reg_write(UC_X86_REG_ESI,node);n.uc.reg_write(UC_X86_REG_EDI,cache)
    def copy(at):
        if at==0x1919178:n.ret(value=created)
        elif at==0x14a3c16:n.uc.emu_stop()
    n.run(0x14a3bbd,0,copy)
    actual=struct.unpack('<4iqq',bytes(n.uc.mem_read(created+8,32)))
    assert actual==(skill.skill_id,skill.unbound_values[0],skill.unbound_values[1],0,
        skill.unbound_values[2],skill.unbound_values[3])
    values=[]
    for address,formatter,wide in ((0x14e1be5,0x847450,False),(0x14e1d19,0x847450,False),
            (0x14e1e4d,0x490220,True),(0x14e1f09,0x490220,True)):
        n.write(n.stack+0x38,created);n.write(n.stack+0x2c,head)
        n.uc.reg_write(UC_X86_REG_EDI,created)
        def observe(at):
            if at==formatter:
                sp=n.uc.reg_read(UC_X86_REG_ESP)
                values.append(struct.unpack('<q' if wide else '<i',bytes(n.uc.mem_read(sp+8,8 if wide else 4)))[0])
                n.uc.emu_stop()
        n.run(address,0,observe)
    assert tuple(values)==skill.unbound_values
    return tuple(values)


def main():
    with tempfile.TemporaryDirectory() as d:
        f,guild=make(Path(d)/'research-native.db')
        f.org.execute(f.cmd(1,guild,'set_research',(300101,)),f.now())
        f.org.award_guild_research(ResearchAward(guild,'native-isolated-source',35,f.now()+5000),f.now())
        state=f.org.guild_research_snapshot(guild);rows=native_skills(state)
        assert rows[0].unbound_values==(2,3,5,30)
        for row in rows:original_fields(row)
        view=replace(detail_fixture(GuildSceneIDs(2**40+1393,2**41+1395,2**42+1394)),skills=rows)
        assert guild_details(view)==original_detail(view)==original_detail(view,wrapper=True)
    layout=ET.parse(OUT/'decoded/ui/layouts/gangskillsetting.layout').getroot()
    headers=next(w for w in layout.iter('Window') if w.attrib.get('Name')=='GangSkillSetting/SlectList')
    labels=[p.attrib['Value'].split(' width:')[0] for p in headers.findall('Property') if p.attrib['Name']=='ColumnHeader']
    assert labels==['text:技能名','text:当前等级','text:等级上限','text:当前经验','text:升级经验','text:技能简介']
    result=dict(passed=['original bean consumer and real cache-node constructor retain id/level/cap/xp/needed-xp',
        'four original numeric readers match current level, cap, xp and required xp; layout column labels independently match',
        'fourteen real persisted research states project into original full bean and c5624 wrapper without changing wire widths'],
        image_sha256=hashlib.sha256(DATA).hexdigest(),native_gui_verified=False,full_gui_consumer_executed=False,
        source_event_is_fixture=True,production_recipe_configured=False,full_guild_details_state_implemented=False,
        live_server_changed=False,scope='original consumer/constructor and numeric-reader slices, formatter/allocator edges stopped or adapted; no GUI rendering')
    write_json(OUT/'evidence/guild-research-native-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
