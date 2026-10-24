"""Original pill practice through guild permits and real role inventory."""
from contextlib import closing
from pathlib import Path
import tempfile,json
from inspect_client import OUT,write_json
from verify_guild_offices import setup
from inventory import Inventory,AssetChange
from currency import CurrencyChange,apply_currency
import role_practice as p
import practice_protocol as wire


def main():
    passed=[];rules=p.load_rules()
    with tempfile.TemporaryDirectory() as directory:
        f,_,_,guild=setup(Path(directory)/'pill.db')
        f.accounts.inventory_config=Inventory.prepare(f.accounts)
        inv=Inventory(f.accounts,1111,1,epoch=f.epochs[1],currency_rules=f.rules)
        f.tx(1,lambda db:p.initialize(db,1111,1,f.epochs[1],tuple(p.PracticeState(s,0,0,0) for s in rules.skills),'explicit_migration',rules))
        with closing(f.accounts.connect()) as db,db:
            db.execute('UPDATE family_members SET joined_ms=?',(f.now()-rules.tenure_ms,))
            db.execute('UPDATE guild_families SET joined_ms=?',(f.now()-rules.tenure_ms,))
            db.execute('UPDATE guild_member_state SET prestige=500 WHERE role_id=1')
            db.execute('UPDATE guild_assets SET funds=6000000 WHERE guild=?',(guild,))
        f.org.execute(f.cmd(1,guild,'set_practice_open',(360001,True)),f.now())
        f.tx(1,lambda db:inv.apply_settlement(db,AssetChange('fixture-pill',grants=((36747,2,1),))))
        command=f.cmd(1,guild,'reserve_pill_practice',(360001,0))
        f.org.execute(command,f.now())
        grant=f.org.guild_practice_permit(1,f.epochs[1],guild,command.request_id)
        assert grant.mode==1 and grant.cash==grant.materials==0 and grant.gain==20 and grant.item_template==36747
        assert f.org.guild_practice_materials(guild).available==0
        passed.append('pill permit carries original item/experience recipe without requiring or reserving guild materials')
        cash=f.cash(1)
        result=f.tx(1,lambda db:p.settle_pill(db,1111,1,f.epochs[1],guild,command.request_id,f.now(),rules,inv))
        assert result.state==p.PracticeState(360001,0,20,1)
        assert result.inventory.items[0].quantity==1 and f.cash(1)==cash
        f.org.execute(f.cmd(1,guild,'resolve_practice',(command.request_id,)),f.now())
        again=f.tx(1,lambda db:p.settle_pill(db,1111,1,f.epochs[1],guild,command.request_id,f.now(),rules,inv))
        assert again.state==result.state and again.inventory==result.inventory and again.item_key==result.item_key
        passed.append('one original pill is consumed atomically with twenty XP; committed replay does not consume another pill or cash')
        f.reject(lambda:f.tx(1,lambda db:p.settle(db,1111,1,f.epochs[1],guild,command.request_id,f.now(),rules,f.rules)),
            'practice_cash_recipe_required')
        # The packet has no selected item key. Choose a bound pill even if an
        # unbound stack is in an earlier slot, then fall back after deletion.
        inv.move_item(result.item_key,3)
        f.tx(1,lambda db:inv.apply_settlement(db,AssetChange('fixture-unbound',grants=((36747,1,0),))))
        second=f.cmd(1,guild,'reserve_pill_practice',(360001,1));f.org.execute(second,f.now())
        used=f.tx(1,lambda db:p.settle_pill(db,1111,1,f.epochs[1],guild,second.request_id,f.now(),rules,inv))
        assert used.item_key==result.item_key and len(used.inventory.items)==1 and used.inventory.items[0].binding==0
        f.org.execute(f.cmd(1,guild,'resolve_practice',(second.request_id,)),f.now())
        third=f.cmd(1,guild,'reserve_pill_practice',(360001,2));f.org.execute(third,f.now())
        used=f.tx(1,lambda db:p.settle_pill(db,1111,1,f.epochs[1],guild,third.request_id,f.now(),rules,inv))
        assert used.state==p.PracticeState(360001,1,10,3) and not used.inventory.items
        f.org.execute(f.cmd(1,guild,'resolve_practice',(third.request_id,)),f.now())
        old=f.tx(1,lambda db:p.settle_pill(db,1111,1,f.epochs[1],guild,command.request_id,f.now(),rules,inv))
        assert old.state==used.state and old.item_key==result.item_key and not old.inventory.items
        passed.append('designed bound-first/current-slot selection deletes empty stacks; historical replay returns current absolute state')
        missing=f.cmd(1,guild,'reserve_pill_practice',(360001,3));f.org.execute(missing,f.now())
        f.reject(lambda:f.tx(1,lambda db:p.settle_pill(db,1111,1,f.epochs[1],guild,missing.request_id,f.now(),rules,inv)),
            'practice_pill_unavailable')
        f.org.execute(f.cmd(1,guild,'resolve_practice',(missing.request_id,)),f.now())
        f.tx(1,lambda db:inv.apply_settlement(db,AssetChange('fixture-late-pill',grants=((36747,2,0),))))
        failed=f.cmd(1,guild,'reserve_pill_practice',(360001,3));f.org.execute(failed,f.now())
        before=inv.immutable_snapshot()
        bad=lambda db,inventory,snapshot,**kw:((wire.UPDATE_ASSIST_SKILL,'not-bytes'),)
        f.reject(lambda:f.tx(1,lambda db:p.settle_pill(db,1111,1,f.epochs[1],guild,failed.request_id,f.now(),rules,inv,precommit=bad)),
            'NPC precommit must return immutable encoded logical messages')
        assert inv.immutable_snapshot()==before
        assert f.tx(1,lambda db:p.read(db,1111,1,f.epochs[1],rules))[0]==used.state
        seen=[]
        def encode(db,inventory,snapshot,*,replayed):
            state=p.read(db,1111,1,f.epochs[1],rules)[0];seen.append((snapshot.inventory_revision,replayed))
            return ((wire.UPDATE_ASSIST_SKILL,wire.update(state)),)
        actual=f.tx(1,lambda db:p.settle_pill(db,1111,1,f.epochs[1],guild,failed.request_id,f.now(),rules,inv,precommit=encode))
        again=f.tx(1,lambda db:p.settle_pill(db,1111,1,f.epochs[1],guild,failed.request_id,f.now(),rules,inv,precommit=encode))
        assert len(seen)==2 and seen[0][0]>before.inventory_revision and seen[0][1] is False and seen[1][1] is True
        assert again==actual and actual.messages==((wire.UPDATE_ASSIST_SKILL,wire.update(actual.state)),)
        f.org.execute(f.cmd(1,guild,'resolve_practice',(failed.request_id,)),f.now())
        passed.append('missing item refuses; final native-encoding failure rolls back pill, inventory revision and XP; current-snapshot retry commits once')
        # Every type uses the original 20/30 split. No cash balance is involved.
        f.tx(1,lambda db:inv.apply_settlement(db,AssetChange('fixture-all-types',grants=((36747,7,1),))))
        for skill in rules.skills:
            if skill!=360001:
                with closing(f.accounts.connect()) as db,db:db.execute('UPDATE guild_assets SET funds=6000000 WHERE guild=?',(guild,))
                f.org.execute(f.cmd(1,guild,'set_practice_open',(skill,True)),f.now())
            state=next(s for s in f.tx(1,lambda db:p.read(db,1111,1,f.epochs[1],rules)) if s.skill==skill)
            c=f.cmd(1,guild,'reserve_pill_practice',(skill,state.revision));f.org.execute(c,f.now())
            result=f.tx(1,lambda db:p.settle_pill(db,1111,1,f.epochs[1],guild,c.request_id,f.now(),rules,inv))
            if skill!=360001:
                assert result.state==p.PracticeState(skill,0,20 if skill<=360003 else 30,1)
                f.org.execute(f.cmd(1,guild,'set_practice_open',(skill,False)),f.now())
            f.org.execute(f.cmd(1,guild,'resolve_practice',(c.request_id,)),f.now())
        assert f.cash(1)==cash and f.org.guild_practice_materials(guild).available==0
        passed.append('all seven types receive the original twenty/thirty experience split without spending cash or guild materials')
        # A real role without a wallet or a known guild-material balance can
        # still consume its owned pill; neither missing baseline is zero-filled.
        inv18=Inventory(f.accounts,1111,18,epoch=f.epochs[18])
        f.tx(18,lambda db:p.initialize(db,1111,18,f.epochs[18],tuple(p.PracticeState(s,0,0,0) for s in rules.skills),'explicit_migration',rules))
        f.tx(18,lambda db:inv18.apply_settlement(db,AssetChange('fixture-role18-pill',grants=((36747,1,0),))))
        with closing(f.accounts.connect()) as db,db:
            db.execute('DELETE FROM role_wallet_balances WHERE role_id=18');db.execute('DELETE FROM role_wallet_profiles WHERE role_id=18')
            db.execute('DELETE FROM guild_practice_materials WHERE guild=?',(guild,))
            db.execute('UPDATE guild_member_state SET prestige=500 WHERE role_id=18')
        c=f.cmd(18,guild,'reserve_pill_practice',(360001,0));f.org.execute(c,f.now())
        result=f.tx(18,lambda db:p.settle_pill(db,1111,18,f.epochs[18],guild,c.request_id,f.now(),rules,inv18))
        assert result.state.experience==20 and not result.inventory.items
        f.org.execute(f.cmd(18,guild,'resolve_practice',(c.request_id,)),f.now())
        unpaid=f.cmd(18,guild,'reserve_pill_practice',(360001,1));f.org.execute(unpaid,f.now())
        f.org.execute(f.cmd(18,guild,'resolve_practice',(unpaid.request_id,)),f.now())
        assert f.org.guild_practice_permit(18,f.epochs[18],guild,unpaid.request_id).status=='cancelled'
        f.reject(lambda:f.org.guild_practice_materials(guild),'practice_materials_unknown')
        f.reject(lambda:f.cash(18),'Explicit wallet baseline required')
        passed.append('pill settlement and zero-resource cancellation work with unknown wallet/material baselines without inventing either balance')
        orphan=f.cmd(18,guild,'reserve_pill_practice',(360001,1));f.org.execute(orphan,f.now())
        child='practice:'+str(guild)+':'+orphan.request_id
        f.tx(18,lambda db:inv18.apply_settlement(db,AssetChange(child)))
        f.reject(lambda:f.tx(18,lambda db:p.settle_pill(db,1111,18,f.epochs[18],guild,orphan.request_id,f.now(),rules,inv18)),
            'practice_orphan_asset_receipt')
        resolution=f.cmd(18,guild,'resolve_practice',(orphan.request_id,))
        f.reject(lambda:f.org.execute(resolution,f.now()),'practice_outcome_unknown')
        assert f.org.guild_practice_permit(18,f.epochs[18],guild,orphan.request_id).status=='reserved'
        # A standalone child debit with no common receipt is deliberately
        # corrupted fixture history, not an authorized partial settlement.
        with closing(f.accounts.connect()) as db,db:
            db.execute('INSERT INTO guild_practice_materials VALUES(?,3,0,?)',(guild,'explicit_fixture'))
        state=f.tx(1,lambda db:p.read(db,1111,1,f.epochs[1],rules))[0]
        orphan_cash=f.cmd(1,guild,'reserve_practice',(360001,state.revision));f.org.execute(orphan_cash,f.now())
        child='practice:'+str(guild)+':'+orphan_cash.request_id
        f.tx(1,lambda db:apply_currency(db,1111,1,f.epochs[1],CurrencyChange(child,'skill_training',
            'guild-practice:'+str(guild)+':360001',(('cash',-30000),)),f.rules))
        balance=f.cash(1)
        f.reject(lambda:f.tx(1,lambda db:p.settle(db,1111,1,f.epochs[1],guild,orphan_cash.request_id,f.now(),rules,f.rules)),
            'practice_orphan_currency_receipt')
        assert f.cash(1)==balance and f.tx(1,lambda db:p.read(db,1111,1,f.epochs[1],rules))[0]==state
        f.reject(lambda:f.org.execute(f.cmd(1,guild,'resolve_practice',(orphan_cash.request_id,)),f.now()),'practice_outcome_unknown')
        assert f.org.guild_practice_materials(guild).available==0
        passed.append('orphan inventory/currency child proofs remain unresolved for explicit repair; neither extra XP nor false cancellation/refund is allowed')
    result=dict(passed=passed,native_gui_verified=False,live_store_changed=False)
    write_json(OUT/'evidence/role-pill-practice-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
