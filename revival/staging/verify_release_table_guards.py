"""Exercise deployment preservation gates using actual SQLite table states."""
import sqlite3
from master_ready_preflight import table_state,verify_preserved_tables

with sqlite3.connect(':memory:') as db:
    db.execute('CREATE TABLE roles(id INTEGER PRIMARY KEY,name TEXT)')
    db.execute("INSERT INTO roles VALUES(1,'preserved')")
    before=table_state(db)
    policy={'new_empty_tables':['npc_role_healing_receipts']}
    db.execute('CREATE TABLE npc_role_healing_receipts(role_id INTEGER PRIMARY KEY)')
    assert verify_preserved_tables(before,table_state(db),policy)==['npc_role_healing_receipts']
    def refused():
        try:verify_preserved_tables(before,table_state(db),policy)
        except ValueError:return
        raise AssertionError('Unsafe deployment table change was admitted')
    db.execute('INSERT INTO npc_role_healing_receipts VALUES(1)');refused()
    db.execute('DELETE FROM npc_role_healing_receipts')
    db.execute('CREATE TABLE unexpected(id INTEGER)');refused()
    db.execute('DROP TABLE unexpected')
    db.execute("UPDATE roles SET name='changed' WHERE id=1");refused()
    db.execute("UPDATE roles SET name='preserved' WHERE id=1")
    db.execute('DROP TABLE roles');refused()
print('Passed: declared empty addition; populated/undeclared addition, existing row change and table removal reject')
