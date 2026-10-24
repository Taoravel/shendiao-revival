"""Independently replay the frozen pure notice codecs, with owned outputs."""
import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    review = args.review.resolve(strict=True)
    source = review / 'source'
    output = args.output.resolve()
    root = Path(__file__).resolve().parents[1]
    if output.is_relative_to(review) or output == root:
        raise ValueError('Independent output directory required')
    output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((review / 'candidate.json').read_text(encoding='utf-8'))
    before = {str(p.relative_to(review)): sha(p) for p in review.rglob('*') if p.is_file()}
    image = root / 'evidence/native-image.bin'
    image_sha = sha(image)
    if image_sha != manifest['native_image_sha256']:
        raise ValueError('Original image differs from reviewed image')

    def verify():
        for name, expected in manifest['dependency_source_sha256'].items():
            if sha(source / name) != expected:
                raise ValueError('Frozen source changed: ' + name)
        if sha(image) != image_sha:
            raise ValueError('Original native image changed')

    verify()
    sys.path[:] = [str(source)] + [p for p in sys.path if p and not Path(p).resolve().is_relative_to(root)]
    import inspect_client
    inspect_client.ROOT = root.parent
    inspect_client.OUT = root
    # Read the checked original image before changing the report destination.
    import native_inspect
    if hashlib.sha256(native_inspect.DATA).hexdigest() != image_sha:
        raise ValueError('Loaded original image differs')
    inspect_client.OUT = output
    import verify_visible_notice_native
    capture = io.StringIO()
    with redirect_stdout(capture):
        verify_visible_notice_native.main()
    (output / 'stdout.txt').write_text(capture.getvalue(), encoding='utf-8')
    report = output / 'evidence/visible-notice-native-verification.json'
    result = json.loads(report.read_text(encoding='utf-8'))
    if len(result.get('passed', [])) != 4 or not result.get('original_unmarshal_verified'):
        raise ValueError('Expected four original codec/consumer groups')
    origins = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if path.is_relative_to(root):
            if not path.is_relative_to(source) and path != Path(__file__).resolve():
                raise ValueError('Unfrozen workspace import: ' + str(path))
            origins[name] = {'path': str(path), 'sha256': sha(path)}
    verify()
    after = {str(p.relative_to(review)): sha(p) for p in review.rglob('*') if p.is_file()}
    if after != before:
        raise ValueError('Review snapshot changed during replay')
    final = dict(passed=True, groups=4, review=str(review), review_sha256=before,
        image_sha256=image_sha, actual_import_origins=origins,
        parent_runner_sha256=sha(Path(__file__)), child_report_sha256=sha(report),
        frozen_inputs_stable=True, output_adapter='Only inspect_client.OUT changed to owned reports; write_json unchanged',
        original_marshal_unmarshal_process_ingress_verified=True,
        native_gui_verified=False, live_database=False, live_socket=False, service_changed=False,
        shared_runtime_wired=False, native_system_popup_implemented=False)
    (output / 'verification.json').write_text(json.dumps(final, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: final[k] for k in ('passed','groups','frozen_inputs_stable','native_gui_verified')}))


if __name__ == '__main__':
    main()
