"""Exact private-story union over live wild-auto; preserve unrelated BASE assets."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'runtime/deployments/wild-auto-20261023T181143Z'
SOCIAL = ROOT/'evidence/reviews/social-scene-delivery-20261023T135356Z/source'
CHECKS = [
    'verify_runtime_private_map_factory.py', 'verify_runtime_map_address_identity.py',
    'verify_runtime_private_role.py', 'verify_runtime_private_role_guards.py',
    'verify_runtime_story_lifecycle.py', 'verify_runtime_story_pins.py',
    'verify_world_runtime_story_pins.py', 'verify_scene_delivery_terminals.py',
    'research_world_scene_delivery_abandonment.py', 'verify_story_maintenance_recovery.py',
    'verify_story_cleanup_retry.py', 'verify_story_gc_isolation.py',
    'verify_scene_cleanup_recovery.py', 'verify_private_transfer_disconnect.py',
    'verify_prologue_touch_runtime.py', 'verify_prologue_touch_two_roles.py',
    'verify_task_prologue_touch.py', 'verify_world_story_instance_directory.py',
    'verify_world_story_lifecycle.py', 'verify_world_legacy_intro_entry.py',
    'verify_npc_static_cell_candidate.py', 'verify_world_newbie_interaction_policy.py',
    'verify_social_scene_delivery.py', 'verify_social_scene_scope.py',
    'verify_newbie_runtime.py', 'verify_newbie_cart_runtime.py',
    'verify_wild_auto_runtime.py', 'verify_battle_damage_presentation.py',
    'verify_jiaxing_pending_recovery.py',
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_function(text, name, replacement):
    anchor = 'def '+name+'('
    start = text.index(anchor)
    end = text.find('\ndef ', start+len(anchor))
    if end == -1:
        end = len(text)
    return text[:start]+replacement.rstrip()+'\n\n'+text[end:].lstrip('\n')


def function(text, name):
    start = text.index('def '+name+'(')
    end = text.find('\ndef ', start+4)
    return text[start:end if end != -1 else len(text)]


def harness_bytes(path):
    data = path.read_text(encoding='utf-8')
    # Two-level roots refer to the installed original archives, not reports.
    data = re.sub(r'^ROOT\s*=\s*Path\(__file__\)(?:\.resolve\(\))?\.parent\.parent\s*$',
                  'from inspect_client import ROOT', data, flags=re.MULTILINE)
    data = re.sub(r'^ROOT\s*=\s*Path\(__file__\)(?:\.resolve\(\))?\.parent\s*$',
                  "ROOT=Path(__file__).parent/'workspace'", data, flags=re.MULTILINE)
    if path.name == 'verify_jiaxing_pending_recovery.py':
        data = data.replace('root=Path(__file__).resolve().parent',
                            "root=Path(__file__).resolve().parent/'workspace'")
    if path.name == 'verify_jiaxing_pending_release.py':
        data = data.replace('inspect_client.ROOT=Path(__file__).resolve().parents[1]',
                            'inspect_client.ROOT=Path('+repr(str(ROOT.parent))+')')
    return data.encode('utf-8')


def main():
    for name in CHECKS:
        if not (ROOT/name).is_file():
            raise ValueError('Acceptance script missing before staging: '+name)
    before = json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    for name, expected in before['sha256'].items():
        if digest(BASE/'source'/name) != expected:
            raise ValueError('Live BASE changed: '+name)
    if digest(BASE/'run_release.py') != before['runner_sha256']:
        raise ValueError('BASE runner changed')
    fixed = {}
    fixed.update(json.loads((ROOT/'evidence/npc-interaction-v2-ready.json').read_text(encoding='utf-8'))['minimal_static_runtime_files'])
    fixed.update(json.loads((ROOT/'evidence/task-prologue-touch-delivery.json').read_text(encoding='utf-8'))['policy_files'])
    fixed.update({
        'world_owner.py':'3a893ec87feab966adf4f07f1917779296669f143177cb78da580758c3ef4d5b',
        'world_story_instances.py':'f8a817fb68aed25df3cfec580fe5731ce9659743aa252bdff538b2d0eb8b6268',
        'world_story_projection_pool.py':'3fdedb540a7c1157c1e3b1984d0242fc96e22848903ef4f3897ee87fa5c2bd9b',
        'world_newbie.py':'68128b455a789c33adbceda460a923b796ee909e0f35c16a6742f9ed32e46df4',
        'task_prologue_touch.py':'e7d6a0629c874f494a3afb38a5f881d7d6a772fcb1e1d142f90fa5629d0def2a',
        'task_conversation.py':'2dc3874c35d88f62841666fafe1f4ec3f3250ec23739552433f3a7b88844a536',
    })
    patch = {}
    origins = {}
    for name, expected in fixed.items():
        if digest(ROOT/name) != expected:
            raise ValueError('Reviewed owned input changed: '+name)
        patch[name] = (ROOT/name).read_bytes()
        origins[name] = str(ROOT/name)
    for name, expected in {
        'social_owner.py':'dfa8b2e44492e58cd446733358f84719c282507580eebf04ddeef22c7f9d7f6e',
        'social_runtime.py':'7fd13b5e64a469b43e593043d4ff2c60ce15b47c4692ae21895f088626a2a082',
    }.items():
        if digest(SOCIAL/name) != expected:
            raise ValueError('Clean social snapshot changed')
        patch[name] = (SOCIAL/name).read_bytes()
        origins[name] = str(SOCIAL/name)
    domain = ROOT/'evidence/reviews/task-prologue-puzzle-formal-20261023T132126Z/source/task_domain.py'
    if digest(domain) != 'f0c6225ad621de5ebdd5befa57adb0cfb2e5eac808669be8c9dea893b63a7328':
        raise ValueError('Reviewed touch task domain changed')
    patch['task_domain.py'] = domain.read_bytes()
    origins['task_domain.py'] = str(domain)
    for name in ('game_runtime.py', 'runtime_story_maps.py'):
        patch[name] = (ROOT/name).read_bytes()
        origins[name] = str(ROOT/name)
    # Keep BASE receipt/resource contracts: the unrelated care/repair source
    # work is deliberately not part of this private-story release.
    storage = (ROOT/'runtime_storage.py').read_text(encoding='utf-8')
    base_storage = (BASE/'source/runtime_storage.py').read_text(encoding='utf-8')
    for name in ('repair_role_equipment', 'npc_recover_resources'):
        storage = replace_function(storage, name, function(base_storage, name))
    newline = '\r\n' if b'\r\n' in (ROOT/'runtime_storage.py').read_bytes() else '\n'
    patch['runtime_storage.py'] = storage.replace('\n', newline).encode('utf-8')
    origins['runtime_storage.py'] = 'workspace private hunks; unrelated two care functions restored byte-semantically from BASE'
    serve = (BASE/'source/serve.py').read_bytes()
    anchor = b'GameRuntime(store,prepared,logger=logger,training=training_battle)'
    if serve.count(anchor) != 1:
        raise ValueError('Production feature admission seam changed')
    patch['serve.py'] = serve.replace(anchor, anchor[:-1]+b',prologue_touch=True)', 1)
    origins['serve.py'] = 'BASE one explicit touch activation argument'
    now = datetime.now(timezone.utc)
    release = ROOT/'runtime/deployments'/('private-story-'+now.strftime('%Y%m%dT%H%M%SZ'))
    source = release/'source'
    source.mkdir(parents=True, exist_ok=False)
    for name in before['sha256']:
        target = source/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BASE/'source'/name, target)
    changes = []
    for name, data in patch.items():
        target = source/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        old = BASE/'source'/name
        changes.extend(difflib.unified_diff(
            old.read_text(encoding='utf-8').splitlines(True) if old.exists() else [],
            target.read_text(encoding='utf-8').splitlines(True),
            fromfile='live-base/'+name, tofile='private-story/'+name))
    hashes = {str(path.relative_to(source)).replace('\\','/'):digest(path)
              for path in source.rglob('*') if path.is_file()}
    changed = {name:value for name,value in hashes.items() if before['sha256'].get(name) != value}
    if set(changed)-set(patch):
        raise ValueError('Changes escaped the explicit private union')
    shutil.copy2(BASE/'run_release.py', release/'run_release.py')
    manifest = dict(created_utc=now.isoformat(), base_release=str(BASE), sha256=hashes,
        changed_modules=changed, runner_sha256=digest(release/'run_release.py'),
        scope='completed storyteller recovery -> original bloodmark -> bounded private1501, no battle advancement')
    (release/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (release/'changes.diff').write_text(''.join(changes), encoding='utf-8')
    harness = release/'harness'
    (harness/'evidence').mkdir(parents=True)
    shutil.copy2(source/'evidence/native-image.bin', harness/'evidence/native-image.bin')
    for path in ROOT.glob('*.py'):
        if path.name.startswith(('verify_', 'research_')):
            (harness/path.name).write_bytes(harness_bytes(path))
    for name in CHECKS:
        if not (harness/name).exists():
            raise ValueError('Requested acceptance harness missing: '+name)
    # Report/hash paths may read workspace copies; those copies never enter
    # the production import path. Mutable reports cannot alter frozen source.
    workspace = harness/'workspace'
    workspace.mkdir()
    for name in hashes:
        target = workspace/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source/name, target)
    for path in harness.glob('*.py'):
        shutil.copy2(path, workspace/path.name)
    extra_fixtures={}
    for name in ('evidence/npc-client-visit-root-red.json', 'evidence/npc-interaction-compatibility-audit.json'):
        shutil.copy2(ROOT/name, workspace/name)
        extra_fixtures[name]=digest(workspace/name)
    harness_hashes = {path.name:digest(path) for path in harness.glob('*.py')}
    workspace_hashes = {name:value for name,value in hashes.items()
        if not name.startswith('evidence/') or name.endswith('.bin')
        or name=='evidence/newbie-birth-sites-audit.json'}
    workspace_hashes.update(harness_hashes)
    workspace_hashes.update(extra_fixtures)
    record = dict(release=str(release), base_release=str(BASE), base_pid_at_staging=12336,
        file_count=len(hashes), changed_modules=changed, production_origins=origins,
        started=False, checks_required=CHECKS,
        new_empty_tables=['world_story_instances', 'task_prologue_touches'],
        verification_name='private-story', scope=manifest['scope'],
        harness_sha256=harness_hashes, harness_sources={name:str(harness/name) for name in harness_hashes},
        harness_resource_sha256={'evidence/native-image.bin':digest(harness/'evidence/native-image.bin')},
        workspace_sha256=workspace_hashes,
        workspace_reference_overrides={name:value for name,value in harness_hashes.items() if hashes.get(name)!=value},
        check_arguments={'verify_jiaxing_pending_recovery.py':['--source',str(BASE/'source')]},
        harness_adaptation='ROOT report/hash paths point to workspace copy; gameplay imports only frozen source',
        excludes='workspace inventory/pet evolution/care/organizations/NPC lifecycle/identification/dream-return/puzzle runtime',
        native_gui_verified=False, formal_story_battle_started=False)
    bundle=dict(production=manifest['sha256'],runner=manifest['runner_sha256'],
        harness=record['harness_sha256'],resources=record['harness_resource_sha256'],
        workspace=record['workspace_sha256'],checks=record['checks_required'],arguments=record['check_arguments'])
    record['acceptance_input_sha256']=hashlib.sha256(
        json.dumps(bundle,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    data = json.dumps(record, indent=2)
    (release/'candidate.json').write_text(data, encoding='utf-8')
    (ROOT/'staging/private-story-candidate.json').write_text(data, encoding='utf-8')
    print(json.dumps({key:value for key,value in record.items() if not key.startswith('harness')}))


if __name__ == '__main__':
    main()
