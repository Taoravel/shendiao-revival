"""Actual relationship history in original CourseInfo and FamilyData wire."""
from pathlib import Path
import hashlib,json,struct,tempfile
from verify_guild_offices import setup
from verify_family_guild_history import sources,consume
from verify_family_history_native import octets_vector
from verify_social_native import native_payload
from family_guild_history import FamilyGuildHistoryCommand
from native_inspect import DATA
from inspect_client import OUT,write_json
import faction_protocol as p


def main():
    with tempfile.TemporaryDirectory() as d:
        f,first,second,guild=setup(Path(d)/'native-history.db');consume(f,sources(f,first,second,guild))
        f.org.execute(f.cmd(16,guild,'leave',(second,)),f.now())
        event=f.org.family_guild_history_event(f.org.pending_family_guild_history(second%f.org.maintenance_rules.partitions)[0][1])
        command=FamilyGuildHistoryCommand(event,'native-delivery',f.now()+5000)
        f.org.consume_family_guild_history(command,f.now());f.org.ack_family_guild_history(command,f.now())
        token=dict(f.org.family_audience(second).members)[16]
        view=f.org.family_projection(16,f.epochs[16],second,token,()).view
        assert [course.template_id for course in view.history]==[1,5,6]
        records=[];nested=[]
        for index,course in enumerate(view.history):
            start=0x5080000+index*0x100
            vector,buffers=octets_vector(course.parameters,0x5090000+index*0x1000)
            if course.template_id in (5,6):
                one,one_buffers=octets_vector(course.parameters)
                actual=native_payload(0xed7910,scalars=[(4,course.template_id)],raw=[
                    (0xc,struct.pack('<III',0x5005000,0x5005000+len(one),0x5005000+len(one))),
                    (0x4000,one),*one_buffers])
                assert actual==p.family_course(course) and course.parameters[1]=='职位帮派'
            records.append(struct.pack('<6I',0x22838c8,course.template_id,0,start,start+len(vector),start+len(vector)))
            nested.extend([(start-0x5001000,vector),*buffers])
        end=0x5005000+len(records)*24
        fields=[(4,view.identity),(0x5c,view.level),(0x60,view.funds&0xffffffff),(0x64,view.funds>>32),
            (0x68,view.popularity),(0x6c,view.popularity_max),(0x70,view.construction),(0x74,view.construction_max),
            (0x78,view.family_scene_identity&0xffffffff),(0x7c,view.family_scene_identity>>32)]
        actual=native_payload(0xed7340,[(8,view.founder_name),(0x24,view.name),(0x40,view.aim)],fields,
            raw=[(0x84,struct.pack('<III',0x5005000,end,end)),(0x4000,b''.join(records)),*nested])
        assert actual==p.family_data(view)
    report=dict(passed=['real join/leave events populate original template5/6 with original two UTF16 parameters',
        'original full FamilyData marshal matches actual authorized family projection after durable consumption'],
        image_sha256=hashlib.sha256(DATA).hexdigest(),native_gui_verified=False,live_server_changed=False,
        server_date_format_source='existing designed family display policy')
    write_json(OUT/'evidence/family-guild-history-native-verification.json',report);print(json.dumps(report))


if __name__=='__main__':main()
