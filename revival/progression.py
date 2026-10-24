"""Character experience credit, joining the role owner's transaction.

Credit uses existing role_progress. Explicitly initialized ordinary profiles may
apply the versioned growth policy; uninitialized roles keep their existing phase
and balance semantics. No account is initialized implicitly by receiving EXP.
"""
from dataclasses import dataclass
from role_growth import auto_credit_profile


@dataclass(frozen=True)
class ExperienceBalance:
    role_id: int
    level: int
    experience: int


def read_experience(db, account_id, role_id):
    if not db.in_transaction:
        raise ValueError('Experience requires an owner transaction')
    row = db.execute('SELECT level FROM roles WHERE id=? AND account_id=?', (role_id, account_id)).fetchone()
    if row is None:
        raise ValueError('Experience role ownership mismatch')
    balance = db.execute('SELECT experience FROM role_progress WHERE role_id=?', (role_id,)).fetchone()
    return ExperienceBalance(role_id, row[0], balance[0] if balance else 0)


def credit_experience(db, account_id, role_id, amount, growth_rules=None, attribute_rules=None, login_epoch=None,*,resource_context=None):
    before = read_experience(db, account_id, role_id)
    if type(amount) is not int or amount < 0 or not 0 <= before.experience <= 2**63 - 1 - amount:
        raise ValueError('Invalid or overflowing experience credit')
    grown = auto_credit_profile(db,account_id,role_id,amount,growth_rules,attribute_rules,login_epoch,
                               resource_context=resource_context)
    if grown is not None:
        return ExperienceBalance(role_id,grown.level,grown.experience)
    after = ExperienceBalance(role_id, before.level, before.experience + amount)
    db.execute('INSERT INTO role_progress(role_id,experience) VALUES(?,?) '
               'ON CONFLICT(role_id) DO UPDATE SET experience=excluded.experience',
               (role_id, after.experience))
    return after
