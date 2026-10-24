"""Independent frozen World member replay; no live DB/socket/service access."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_set(directory):
    return {str(p.relative_to(directory)): sha(p) for p in directory.rglob('*') if p.is_file()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--review', type=Path, required=True)
    p.add_argument('--base-source', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--expected-groups', type=int, default=13)
    p.add_argument('--domain-source', type=Path)
    args = p.parse_args()
    review = args.review.resolve(strict=True)
    source = args.base_source.resolve(strict=True)
    domain_source = args.domain_source.resolve(strict=True) if args.domain_source else None
    if args.expected_groups < 1:
        raise ValueError('Positive expected group count required')
    domain_before = {n: sha(domain_source/n) for n in ('world_owner.py', 'world_roles.py')} if domain_source else {}
    manifest = json.loads((review/'manifest.json').read_text(encoding='utf-8'))
    for section in ('base', 'final', 'reference'):
        for name, expected in manifest[section].items():
            if sha(review/section/name) != expected:
                raise ValueError(f'Frozen {section} mismatch: {name}')
    if sha(review/'SPEC.md') != manifest['spec_sha256']:
        raise ValueError('Frozen spec mismatch')
    before_review, before_source = file_set(review), file_set(source)
    application = Path(__file__).resolve().parents[2]
    sys.path = [str(review/'final'), str(review/'reference'), str(source)] + [s for s in sys.path
        if s and not Path(s).resolve().is_relative_to(application)]
    import inspect_client
    inspect_client.ROOT = application
    inspect_client.OUT = source
    child = args.report.with_name(args.report.stem+'-module.json')
    sys.argv = [str(review/'final/verify_world_member_metadata.py'), '--report', str(child)]
    if domain_source:
        sys.argv += ['--domain-source', str(domain_source)]
    passed, error = False, None
    try:
        runpy.run_path(sys.argv[0], run_name='__main__')
        result = json.loads(child.read_text(encoding='utf-8'))
        passed = result['all_passed'] and result['inputs_stable'] and len(result['passed']) == args.expected_groups
    except BaseException as exc:
        error = repr(exc)
    origins = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(application):
                own_harness = name == '__main__' and path == Path(__file__).resolve()
                allowed = (review/'final', review/'reference', source) + ((domain_source,) if domain_source else ())
                if not own_harness and not any(path.is_relative_to(d) for d in allowed):
                    passed = False
                    error = f'Unapproved application import: {path}'
                origins[name] = dict(path=str(path), sha256=sha(path))
    after_review, after_source = file_set(review), file_set(source)
    domain_after = {n: sha(domain_source/n) for n in domain_before} if domain_source else {}
    stable = before_review == after_review and before_source == after_source and domain_before == domain_after
    result = dict(passed=bool(passed and stable), error=error,
        frozen_review=str(review), frozen_base_source=str(source),
        selected_domain_source=str(domain_source) if domain_source else None,
        selected_domain_sha256=domain_before, expected_group_count=args.expected_groups,
        review_file_count=len(before_review), base_source_file_count=len(before_source),
        inputs_stable=stable, review_sha256=before_review, base_source_sha256=before_source,
        actual_import_origins=origins, module_report=str(child),
        module_report_sha256=sha(child) if child.is_file() else None,
        root_probe_sha256=sha(Path(__file__)), live_socket=False, live_database=False,
        service_changed=False, shared_runtime_verified=False, gui_verified=False)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in result.items() if k not in
        ('review_sha256', 'base_source_sha256', 'actual_import_origins')}, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
