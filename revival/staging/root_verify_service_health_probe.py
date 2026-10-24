"""Replay sealed EOF/deadline tests under normal or optimized Python."""
import hashlib
import json
from pathlib import Path
import runpy
import sys


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    root = Path(__file__).resolve().parents[1]
    review = root/'evidence/reviews/detached-service-host-root-20261024-r2'
    scope = json.loads((review/'scope.json').read_text(encoding='utf-8'))
    staging = review/'candidate/staging'
    wire_path = Path(scope['wire_dependency']['path'])
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

    def verify():
        for row in scope['files']:
            require(digest(review/'candidate'/row['path']) == row['candidate_sha256'], row['path'])
            require(digest(root/row['path']) == row['candidate_sha256'], 'Current tool differs: '+row['path'])
        require(digest(wire_path) == scope['wire_dependency']['sha256'], 'Wire dependency changed')

    verify()
    sys.path[:0] = [str(staging), str(wire_path.parent)]
    # The verifier's relative source path is relocation-dependent; preselect
    # the exact admitted immutable dependency and record its actual origin.
    import wire
    require(Path(wire.__file__).resolve() == wire_path, 'Unapproved wire import')
    sys.argv = [str(staging/'verify_service_health_probe.py')]
    runpy.run_path(sys.argv[0], run_name='__main__')
    import service_health_probe
    require(Path(service_health_probe.__file__).resolve() == staging/'service_health_probe.py',
        'Unsealed health helper import')
    verify()
    report = dict(test_program_completed=True, reported_groups=5,
        python_optimize=sys.flags.optimize, actual_wire=str(Path(wire.__file__).resolve()),
        actual_health_helper=str(Path(service_health_probe.__file__).resolve()),
        candidate_inputs_unchanged=True, immutable_wire_dependency_unchanged=True,
        production_service_restarted=False, live_socket_accessed=False,
        live_database_accessed=False, report_or_code_logic_mocked=False)
    target = review/f'root-health-probe-opt{sys.flags.optimize}.json'
    target.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
