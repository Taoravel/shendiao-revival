"""NPC service proof -> prepared guild command -> fenced role transaction."""
from pathlib import Path
from contextlib import closing
from dataclasses import replace
import tempfile,struct,json
from inspect_client import OUT,write_json
from verify_guild_offices import setup
from npc_services import NpcServices,ServiceBinding
from world_npcs import NpcInteraction
from world_owner import MapAddress,Location
import role_practice as p
import practice_protocol as wire
import practice_npc as npc
from inventory import Inventory,AssetChange,BAG_INFO


def main():
    passed=[];rules=p.load_rules()
    with tempfile.TemporaryDirectory() as directory:
        f,_,_,guild=setup(Path(directory)/'npc-practice.db')
        f.tx(1,lambda db:p.initialize(db,1111,1,f.epochs[1],tuple(p.PracticeState(s,0,0,0) for s in rules.skills),'explicit_migration',rules))
        services=NpcServices({1023:'我要修炼技能'},(ServiceBinding(10077,1023,'guild_practice','designed','isolated coach fixture'),))
        location=Location(1,f.epochs[1],MapAddress(1007,1,0),7,1680,5311)
        proof=NpcInteraction('practice-1',1,f.epochs[1],location.address,7,123,10077,1)
        command=services.plan(struct.pack('>qi',123,1023),proof,location,request_id=proof.source_id,now_ms=f.now(),deadline_ms=f.now()+5000)
        messages=f.tx(1,lambda db:npc.open_panel(db,1111,command,location,f.now(),rules))
        assert [kind for kind,_ in messages]==[wire.UPDATE_ASSIST_SKILL]*7+[wire.FACTION_PRACTICE]
        assert messages[-1][1]==wire.open_types(())
        passed.append('authorized original service exposes current seven known skills and original open-type map without zero-filling unknown role/guild data')
        with closing(f.accounts.connect()) as db,db:
            db.execute('UPDATE family_members SET joined_ms=?',(f.now()-rules.tenure_ms,))
            db.execute('UPDATE guild_families SET joined_ms=?',(f.now()-rules.tenure_ms,))
            db.execute('UPDATE guild_member_state SET prestige=500 WHERE role_id=1')
            db.execute('UPDATE guild_assets SET funds=6000000 WHERE guild=?',(guild,))
            db.execute('UPDATE guild_practice_materials SET available=6 WHERE guild=?',(guild,))
        f.org.execute(f.cmd(1,guild,'set_practice_open',(360001,True)),f.now())
        def service(request_id):
            return services.plan(struct.pack('>qi',123,1023),replace(proof,source_id=request_id),location,
                request_id=request_id,now_ms=f.now(),deadline_ms=f.now()+5000)
        fresh=service('purchase-1')
        body=struct.pack('>QiB',123,360001,0)
        prepared=f.tx(1,lambda db:npc.prepare_purchase(db,1111,fresh,location,body,f.now(),rules))
        assert prepared.command.organization==guild and prepared.command.args==(360001,0)
        assert prepared.command.operation=='reserve_practice' and prepared.command.request_id=='purchase-1'
        f.org.execute(prepared.command,f.now())
        passed.append('verified NPC packet prepares an immutable guild reservation using role membership, never treating NPC Q as guild ID')
        cash=f.cash(1)
        result=f.tx(1,lambda db:npc.finish_purchase(db,1111,prepared,fresh,location,f.now(),rules,currency_rules=f.rules))
        assert result.receipt.state==p.PracticeState(360001,0,10,1) and f.cash(1)==cash-30000
        assert result.messages[0]==(wire.UPDATE_ASSIST_SKILL,wire.update(result.receipt.state))
        f.org.execute(f.cmd(1,guild,'resolve_practice',(prepared.command.request_id,)),f.now())
        assert f.tx(1,lambda db:npc.finish_purchase(db,1111,prepared,fresh,location,f.now(),rules,currency_rules=f.rules))==result
        passed.append('fresh NPC finish atomically settles cash and returns current native skill/wallet packets; replay remains current and single-charge')
        for invalid in (replace(fresh,handler='unrelated'),replace(fresh,service_id=121),
            replace(fresh,position_version=8),replace(fresh,login_epoch='old')):
            f.reject(lambda:f.tx(1,lambda db:npc.open_panel(db,1111,invalid,location,f.now(),rules)),'invalid_practice_npc_scope')
        for bad_body in (struct.pack('>QiB',124,360001,0),struct.pack('>QiB',123,380001,0),
            struct.pack('>QiB',123,360001,2)):
            f.reject(lambda:f.tx(1,lambda db:npc.prepare_purchase(db,1111,fresh,location,bad_body,f.now(),rules)),
                'unsupported_or_foreign_practice_request')
        changing=service('purchase-moving')
        waiting=f.tx(1,lambda db:npc.prepare_purchase(db,1111,changing,location,body,f.now(),rules));f.org.execute(waiting.command,f.now())
        moved=replace(location,version=8)
        f.reject(lambda:f.tx(1,lambda db:npc.finish_purchase(db,1111,waiting,replace(changing,position_version=8),moved,
            f.now(),rules,currency_rules=f.rules)),'practice_prepared_scope_changed')
        f.reject(lambda:f.tx(1,lambda db:npc.finish_purchase(db,1111,waiting,changing,location,changing.deadline_ms,
            rules,currency_rules=f.rules)),'invalid_practice_npc_scope')
        assert f.cash(1)==cash-30000
        f.org.execute(f.cmd(1,guild,'resolve_practice',(waiting.command.request_id,)),f.now())
        passed.append('foreign NPC/type/mode, stale lease/service/position, moved-after-prepare and expired finish reject without spending')
        f.accounts.inventory_config=Inventory.prepare(f.accounts)
        inv=Inventory(f.accounts,1111,1,epoch=f.epochs[1],currency_rules=f.rules)
        f.tx(1,lambda db:inv.apply_settlement(db,AssetChange('fixture-npc-pill',grants=((36747,1,1),))))
        pill=service('purchase-pill')
        ready=f.tx(1,lambda db:npc.prepare_purchase(db,1111,pill,location,struct.pack('>QiB',123,360001,1),f.now(),rules))
        assert ready.command.operation=='reserve_pill_practice';f.org.execute(ready.command,f.now())
        f.reject(lambda:f.tx(1,lambda db:npc.finish_purchase(db,1111,ready,pill,location,f.now(),rules,inventory=inv)),
            'practice_inventory_projection_required')
        project=lambda db,inventory,snapshot,**kw:tuple(inventory.equipment_bag_messages(db,f.epochs[1]))
        result=f.tx(1,lambda db:npc.finish_purchase(db,1111,ready,pill,location,f.now(),rules,inventory=inv,precommit=project))
        assert result.receipt.state==p.PracticeState(360001,0,30,2) and not result.receipt.inventory.items
        assert [kind for kind,_ in result.messages]==[wire.UPDATE_ASSIST_SKILL,BAG_INFO,BAG_INFO]
        assert f.cash(1)==cash-30000
        f.org.execute(f.cmd(1,guild,'resolve_practice',(ready.command.request_id,)),f.now())
        assert f.tx(1,lambda db:npc.finish_purchase(db,1111,ready,pill,location,f.now(),rules,inventory=inv,precommit=project))==result
        passed.append('NPC pill finish requires precommit inventory/source projection and returns current skill/bag replies in the same transaction')
    result=dict(passed=passed,native_gui_verified=False,live_npc_registry_changed=False,live_store_changed=False)
    write_json(OUT/'evidence/practice-npc-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
