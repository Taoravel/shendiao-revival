"""Audit existing organization/NPC/scene contracts; gaps are not acceptance."""
from pathlib import Path
from contextlib import closing
from dataclasses import fields,replace
import tempfile,struct,json,hashlib
from datetime import datetime,timezone
from inspect_client import OUT,write_json
from verify_guild_offices import setup
from social_owner import RoleSnapshot,RoleSocialOwner,SocialCommand,Publish
from world_owner import MapAddress,Location
from npc_services import NpcServiceCommand
import social_protocol as chat


def main():
    with tempfile.TemporaryDirectory() as directory:
        f,family,second,guild=setup(Path(directory)/'contract.db')
        before,members_before=f.org.snapshot(guild)
        first_scope=f.org.guild_scope(1,f.epochs[1])
        assert first_scope[0]==guild and len(first_scope)==3
        with closing(f.accounts.connect()) as db,db:
            db.execute("INSERT INTO roles(id,account_id,name,school,shape,level) VALUES(19,1111,'接口新成员',12,1010101,40)")
        f.epochs[19]=f.accounts.acquire_lease(1111,19)
        f.org.execute(f.cmd(19,second,'apply'),f.now());f.org.execute(f.cmd(16,second,'review',(19,True)),f.now())
        after,members_after=f.org.snapshot(guild)
        new_scope=f.org.guild_scope(19,f.epochs[19])
        assert new_scope[0]==guild and 19 not in members_before and 19 in members_after
        assert before['revision']==after['revision']
        # Hypothetical isolated locations, not live private-instance admission.
        # Old seven-argument callers still omit their full address by design.
        a=Location(1,f.epochs[1],MapAddress(1394,70001,0),8,382,622)
        b=Location(19,f.epochs[19],MapAddress(1394,70002,0),8,382,622)
        assert a.address!=b.address
        snapshots=[RoleSnapshot(loc.role_id,loc.login_epoch,'接口角色',40,12,1010101,loc.address.map_id) for loc in (a,b)]
        body=struct.pack('>i',chat.CURRENT_CHANNEL)+chat.text('实例接口核对')+chat.text('')+b'\0'
        effects=[]
        for snapshot in snapshots:
            owner=RoleSocialOwner(snapshot,None,200,256)
            result=owner.execute(SocialCommand(snapshot.role_id,snapshot.login_epoch,'contract-chat',f.now()+5000,chat.CHAT_SEND,body),{},f.now())
            assert not result.rejection and len(result.effects)==1 and isinstance(result.effects[0],Publish)
            effects.append(result.effects[0])
        assert [(e.scope,e.partition_key) for e in effects]==[('scene',1394),('scene',1394)]
        private_keys=[]
        for snapshot,location in zip(snapshots,(a,b)):
            address=location.address
            full=replace(snapshot,scene_scope=(address.map_id,address.instance_id,address.partition_id))
            result=RoleSocialOwner(full,None,200,256).execute(
                SocialCommand(full.role_id,full.login_epoch,'full-contract-chat',f.now()+5000,chat.CHAT_SEND,body),{},f.now())
            assert not result.rejection
            private_keys.append(result.effects[0].partition_key)
        assert private_keys==[(1394,70001,0),(1394,70002,0)]
        sources=['faction_domain.py','guild_projection.py','guild_offices.py','practice_npc.py','role_practice.py',
            'guild_practice.py','social_owner.py','social_runtime.py','game_runtime.py','world_owner.py','world_npcs.py','npc_services.py']
        report=dict(created_utc=datetime.now(timezone.utc).isoformat(),
            verified_existing_contracts=['guild_scope validates lease and returns guild/family token/member token',
                'snapshot returns a fresh organization dict and member tuple; it is not a frozen admission grant',
                'family-only member approval changes guild membership without changing guild organization revision',
                'legacy seven-argument callers retain public template route; explicit full scopes emit distinct instance keys'],
            organization_revision_before=before['revision'],organization_revision_after=after['revision'],
            member_counts=[len(members_before),len(members_after)],
            role_snapshot_fields=[f.name for f in fields(RoleSnapshot)],
            npc_service_command_fields=[f.name for f in fields(NpcServiceCommand)],
            current_channel_keys=[[e.scope,e.partition_key] for e in effects],
            explicit_scene_scope_keys=private_keys,scene_scope_planner_verified=True,
            full_organization_scene_authorization_verified=False,private_channel_instance_isolation_verified=False,
            scope='public storage and social-planner audit in disposable fixtures; no live private-instance admission/chat, no new policy/backend',
            source_sha256={n:hashlib.sha256((OUT/n).read_bytes()).hexdigest() for n in sources},
            live_server_changed=False,native_gui_verified=False)
    write_json(OUT/'evidence/organization-npc-contract-audit.json',report);print(json.dumps(report))


if __name__=='__main__':main()
