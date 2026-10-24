"""Pin the selected Task contracts and parent evidence, without activation."""
import difflib
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    evidence = root / 'evidence'
    review = evidence / 'reviews/task-growth-modules-root-20261024-r1'
    base = root / 'runtime/deployments/npc-repair-20261024T023920Z'
    selected = {
        'task_first_battle.py': ('task-first-battle-20261024-r1', 'b5557bd04227018b7d706849091373a0915c446b62cdb3e45ade7835036b51ad'),
        'role_skills.py': ('task-first-skill-20261024-r3', '7985e132239bffcda1c19fce63b3af724d3b48e1e92395f590a530b7e6038daf'),
        'task_first_skill.py': ('task-first-skill-20261024-r3', '40a15f95b47bf25088a2abff63aa84b246c612d5b91e76fdb50043bb71f0fcdb'),
        'task_domain.py': ('task-first-skill-20261024-r3', '11f93e8efbaf6059e6b51779691c310912bda5143fe630a0e625c5cadedf6c0b'),
        'task_battle.py': ('task-battle-terminal-recovery-20261024-r2', '8a78b9da2ce1cd144035c0b176c5485ef561d75afaa0ddf1bb033bdb6740d3f8'),
    }
    inputs = {}
    patch = []
    production = {}
    for name, (origin, expected) in selected.items():
        original = evidence / 'reviews' / origin / 'source' / name
        if sha(original) != expected:
            raise ValueError('Unexpected selected production source: ' + name)
        baseline = base / 'source' / name
        old = baseline.read_bytes() if baseline.exists() else b''
        for directory, data in (('source', original.read_bytes()), ('baseline', old)):
            target = review / directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and target.read_bytes() != data:
                raise ValueError('Pinned selection changed: ' + str(target))
            target.write_bytes(data)
        production[name] = dict(source_sha256=expected, original=str(original),
            baseline_sha256=sha(baseline) if baseline.exists() else None,
            baseline_absent=not baseline.exists())
        patch.extend(difflib.unified_diff(old.decode('utf-8-sig').splitlines(keepends=True),
            original.read_text(encoding='utf-8-sig').splitlines(keepends=True),
            fromfile='baseline/'+name, tofile='source/'+name))
    tests = {}
    for name, count in (('root-task-first-battle-gate-20261024', 5),
                        ('root-task-first-skill-r3-20261024', 8),
                        ('root-task-terminal-recovery-r2-20261024', 6)):
        path = evidence / name / 'verification.json'
        report = json.loads(path.read_text(encoding='utf-8'))
        groups = report.get('groups')
        if groups is None and isinstance(report.get('gate_groups'), list):
            groups = len(report['gate_groups'])
        if report.get('passed') is not True or groups != count:
            raise ValueError('Expected parent contract replay: ' + name)
        if report.get('base_input_counts') != [1442, 422, 1208]:
            raise ValueError('Different runtime baseline: ' + name)
        tests[name] = dict(path=str(path), sha256=sha(path), groups=count,
            actual_ai_victory_verified=False, shared_runtime_wired=False)
    paths = [base/'manifest.json', base/'candidate.json', root/'ARCHITECTURE.md', root/'DESIGN_AUTHORITY.md',
        evidence/'TASK_TERMINAL_RECOVERY_DECISION.md', evidence/'NEWBIE_FIRST_SKILL_DECISION.md',
        root/'design/task-pve-ai8001-v1.json', root/'design/newbie-first-skill-v1.json']
    for relative in ('task-first-battle-20261024-r1','task-first-skill-20261024-r3','task-battle-terminal-recovery-20261024-r2'):
        paths.append(evidence/'reviews'/relative/'manifest.json')
    for path in paths:
        inputs[str(path)] = sha(path)
    (review/'candidate.patch').write_text(''.join(patch), encoding='utf-8')
    record = dict(scope='Selected Task contracts only; not runtime integration or activation',
        baseline=str(base), production=production, parent_replays=tests, input_sha256=inputs,
        methods=['codebase-design: public caller-transaction Interfaces',
                 'code-review: independent Standards and Spec against exact byte baseline'],
        artificial_terminal_fixture=True, designed_local_compatibility_verified=False,
        actual_producer_source_cas_verified=False, native_gui_verified=False,
        service_changed=False, activation_authorized=False)
    (review/'manifest-root.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(pinned=True, production_files=len(production), parent_group_counts=[5,8,6])))


if __name__ == '__main__':
    main()
