"""Compare raw quest reward coordinates with map-owned bounds/collision.

This produces candidate evidence, never authorizes travel or defines policy.
"""
import hashlib
import json
from inspect_client import OUT,ROOT
from pfs import PfsArchive
from bxml import decode
from world_catalog import maps,maze_grids,valid_position
from world_collision import maze_clear

TASK_IDS=(100104,100203,100303,100403,100503,100603,100703,100803,100903,103204)


def main():
    raw=PfsArchive(ROOT/'artres/config.pfs').read('autoconfig/knight.gsp.task.cmainmissioninfo.xml')
    originals={int(x.get('id')):x for x in decode(raw)}
    catalog=maps();grids=maze_grids();rows=[]
    for task_id in TASK_IDS:
        task=originals[task_id]
        target=tuple(int(task.get(k)) for k in ('RewardMapID','RewardMapXPos','RewardMapYPos'))
        assert int(task.get('RewardMapJumpType'))==1 and target[0]==1006
        candidates=[]
        for factor in (1,16):
            position=(target[0],target[1]*factor,target[2]*factor)
            candidates.append(dict(factor=factor,position=position,in_bounds=valid_position(position,catalog),
                clear_mask1=maze_clear(grids[position[0]],*position[1:],mask=1),
                clear_mask8=maze_clear(grids[position[0]],*position[1:],mask=8)))
        rows.append(dict(task_id=task_id,raw_reward_position=target,candidates=candidates))
    result=dict(config_entry_sha256=hashlib.sha256(raw).hexdigest(),tasks=rows,
        conclusion='raw positions blocked for masks1/8; x16 candidates clear for normal mask1 but blocked for mask8',
        provenance='original config and map-owned collision Interface; conversion remains inferred, not verified original server policy',
        authorization=False,live_state_changed=False)
    assert all(not c['clear_mask1'] and not c['clear_mask8'] if c['factor']==1
               else c['in_bounds'] and c['clear_mask1'] and not c['clear_mask8']
               for row in rows for c in row['candidates'])
    (OUT/'evidence/task-cart-target-candidates.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='tasks'},ensure_ascii=False))


if __name__=='__main__':main()
