"""Read-only actual role4 checkpoint/task and immutable-release NPC distances."""
from pathlib import Path
import json,sqlite3,sys
ROOT=Path(__file__).resolve().parents[1]
release=ROOT/'runtime/deployments/npc-role-healing-20261023T125539Z'
sys.path.insert(0,str(release/'source'))
import inspect_client
inspect_client.ROOT=ROOT.parent;inspect_client.OUT=release/'source'
from world_npcs import load_placements
with sqlite3.connect((ROOT/'runtime/accounts.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
    db.execute('BEGIN')
    role=db.execute('SELECT id,school,shape,level FROM roles WHERE id=4').fetchone()
    position=db.execute('SELECT map_id,x,y FROM role_positions WHERE role_id=4').fetchone()
    version=db.execute('SELECT version FROM position_versions WHERE role_id=4').fetchone()
    tasks=db.execute('SELECT task_id,state FROM task_journal WHERE role_id=4 ORDER BY task_id').fetchall()
placements=load_placements().get(position[0],()) if position else ()
nearest=sorted((dict(npc_id=p.npc_id,placement_id=p.placement_id,x=p.x,y=p.y,
    distance_squared=(p.x-position[1])**2+(p.y-position[2])**2,
    original_client_cell_squared=(p.x//16-position[1]//16)**2+(p.y//16-position[2]//16)**2)
    for p in placements),key=lambda row:row['distance_squared'])[:6]
report={'role':role,'durable_position':position,'position_version':version,'tasks':tasks,
    'nearest_original_npcs':nearest,'live_database_read_only':True,'process_or_client_changed':False}
target=ROOT/'evidence/live-role4-cart-checkpoint.json'
target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
