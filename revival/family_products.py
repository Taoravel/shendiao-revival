"""Family-owned production settings. Caller supplies its organization transaction."""
from dataclasses import dataclass
import json
from inspect_client import OUT


@dataclass(frozen=True)
class ProductRules:
    revision: str
    initial_flags: tuple
    initial_stocks: tuple
    origin: str
    close_fee: int
    maintenance_costs: tuple


@dataclass(frozen=True)
class FamilyProducts:
    family: int
    drug_open: bool
    special_open: bool
    drug_stock: int
    special_stock: int
    revision: int
    origin: str


@dataclass(frozen=True)
class ProductPanel:
    state: FamilyProducts
    level: int
    drug_cost: int
    special_cost: int


def rules(policy):
    raw=policy['family_production']
    flags=tuple(raw['initial_flags']);stocks=tuple(raw['initial_stocks'])
    if (len(flags)!=2 or any(type(v) is not int or v not in (0,1) for v in flags)
            or len(stocks)!=2 or any(type(v) is not int or not 0<=v<2**31 for v in stocks)
            or type(raw['close_fee']) is not int or not 0<raw['close_fee']<2**63
            or not isinstance(raw['revision'],str) or not raw['revision']
            or not isinstance(raw['origin'],str) or not raw['origin']):
        raise ValueError('invalid_family_product_policy')
    rows=json.loads((OUT/'catalogs/knight.gsp.faction.cfamilymaintainconfig.json').read_text(encoding='utf-8'))
    costs={int(row['attributes']['id']):(int(row['attributes']['drugconsume']),
        int(row['attributes']['productconsume'])) for row in rows}
    if (len(rows)!=5 or set(costs)!={1,2,3,4,5}
            or any(not 0<=value<2**63 for pair in costs.values() for value in pair)):
        raise ValueError('invalid_family_product_cost_table')
    return ProductRules(raw['revision'],flags,stocks,raw['origin'],raw['close_fee'],tuple(costs[level] for level in range(1,6)))


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS family_products (
        family INTEGER PRIMARY KEY REFERENCES organizations(id),
        drug_open INTEGER NOT NULL CHECK(drug_open IN (0,1)),
        special_open INTEGER NOT NULL CHECK(special_open IN (0,1)),
        drug_stock INTEGER NOT NULL CHECK(drug_stock>=0 AND drug_stock<2147483648),
        special_stock INTEGER NOT NULL CHECK(special_stock>=0 AND special_stock<2147483648),
        revision INTEGER NOT NULL CHECK(revision>0),origin TEXT NOT NULL,recipe TEXT NOT NULL)''')


def new_family(db,family,policy):
    db.execute('INSERT INTO family_products VALUES(?,?,?,?,?,1,?,?)',
        (family,*policy.initial_flags,*policy.initial_stocks,policy.origin,policy.revision))


def snapshot(db,family):
    row=db.execute('''SELECT family,drug_open,special_open,drug_stock,special_stock,revision,origin
        FROM family_products WHERE family=?''',(family,)).fetchone()
    if not row:raise ValueError('family_products_unknown')
    return FamilyProducts(row[0],bool(row[1]),bool(row[2]),row[3],row[4],row[5],row[6])


def set_products(db,org,actor,choices,policy):
    """Return the closing charge; caller records it in this same transaction."""
    if (type(choices) is not tuple or len(choices)!=2
            or any(type(v) is not int or v not in (-1,0,1) for v in choices)
            or sum(v!=-1 for v in choices)!=1):
        raise ValueError('invalid_family_product_choice')
    member=db.execute('SELECT family FROM family_members WHERE role_id=?',(actor,)).fetchone()
    if org['leader']!=actor or not member or member[0]!=org['id']:
        raise ValueError('permission_denied')
    state=snapshot(db,org['id'])
    recipe=db.execute('SELECT recipe FROM family_products WHERE family=?',(org['id'],)).fetchone()[0]
    if recipe!=policy.revision:raise ValueError('family_product_recipe_mismatch')
    index=0 if choices[0]!=-1 else 1
    current=(state.drug_open,state.special_open)[index]
    desired=choices[index]
    if current==bool(desired):return 0
    field=('drug_open','special_open')[index]
    db.execute(f'UPDATE family_products SET {field}=?,revision=revision+1 WHERE family=?',
        (desired,org['id']))
    return policy.close_fee if not desired else 0


def panel(db,org,actor,epoch,policy):
    lease=db.execute('SELECT epoch,active FROM role_leases WHERE role_id=?',(actor,)).fetchone()
    if not lease or str(lease[0])!=str(epoch) or lease[1]!=1:raise ValueError('stale_epoch')
    member=db.execute('SELECT family FROM family_members WHERE role_id=?',(actor,)).fetchone()
    if actor!=org['leader'] or not member or member[0]!=org['id']:raise ValueError('permission_denied')
    if not 1<=org['level']<=len(policy.maintenance_costs):raise ValueError('family_level_unknown')
    return ProductPanel(snapshot(db,org['id']),org['level'],*policy.maintenance_costs[org['level']-1])
