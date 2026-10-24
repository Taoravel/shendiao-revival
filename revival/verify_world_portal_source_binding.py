"""Bind an exact runtime catalog to fresh original config and every goto row."""
import argparse
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys

import inspect_client


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def compare(expected, actual):
    assert len(expected) == len(actual), 'Map row count differs'
    assert len({int(row['attributes']['id']) for row in actual}) == len(actual), 'Duplicate map id'
    for expected_row, actual_row in zip(expected, actual):
        assert expected_row['attributes'] == actual_row['attributes'], 'Original map attributes differ'
        assert expected_row['portal_cells'] == actual_row['portal_cells'], 'Original goto rows differ'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-source', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    source = args.runtime_source.resolve(strict=True)
    sys.path.insert(0, str(source))
    for name in ('pfs', 'bxml'):
        sys.modules.pop(name, None)
    pfs, bxml = importlib.import_module('pfs'), importlib.import_module('bxml')
    assert all(Path(module.__file__).resolve() == source/(name+'.py')
               for name, module in (('pfs', pfs), ('bxml', bxml)))
    manifest_path = source.parent/'manifest.json'
    manifest_hash = digest(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding='utf8'))['sha256']
    assert all(digest(source/name) == value for name, value in manifest.items())
    catalog_path = source/'catalogs/world.json'
    catalog_hash = digest(catalog_path)
    catalog = json.loads(catalog_path.read_text(encoding='utf8'))
    assets = {str(path): digest(path) for path in
              (inspect_client.ROOT/'artres/map.pfs', inspect_client.ROOT/'artres/config.pfs')}
    map_archive = pfs.PfsArchive(inspect_client.ROOT/'artres/map.pfs')
    config_archive = pfs.PfsArchive(inspect_client.ROOT/'artres/config.pfs')
    names = {name.casefold(): name for name in map_archive.entries}
    assert len(names) == len(map_archive.entries), 'Ambiguous map resource names'
    config_name = 'autoconfig/knight.gsp.map.cmapconfig.xml'
    config_raw = config_archive.read(config_name)
    original_config = {int(row.attrib['id']): dict(row.attrib) for row in bxml.decode(config_raw)}
    assert len(original_config) == len(catalog) == 304
    expected, entries, pairs = [], [], set()
    for row in catalog:
        mid = int(row['attributes']['id'])
        attrs = original_config[mid]
        entry = names.get((attrs['resdir']+'/goto.xml').casefold())
        rows = []
        if entry:
            raw = map_archive.read(entry)
            rows = [dict(item.attrib) for item in bxml.decode(raw)]
            entries.append(dict(map_id=mid, entry=entry, configured_entry=attrs['resdir']+'/goto.xml', rows=len(rows),
                sha256=hashlib.sha256(raw).hexdigest(), crc_checked=True))
            pairs.update((mid, int(portal['destmap'])) for portal in rows)
        expected.append(dict(attributes=attrs, portal_cells=rows))
    compare(expected, catalog)
    # Preserve row counts but change an actual destination: this gate must fail.
    changed = copy.deepcopy(catalog)
    faulty = next(row for row in changed if row['portal_cells'])
    faulty['portal_cells'][0]['destx'] = str(int(faulty['portal_cells'][0]['destx'])+1)
    try:
        compare(expected, changed)
    except AssertionError as error:
        negative_control = str(error)
    else:
        raise AssertionError('Same-count portal corruption escaped original row binding')
    rows = sum(entry['rows'] for entry in entries)
    assert rows == 6275 and len(pairs) == 227 and len(entries) == 142, (rows, len(pairs), len(entries))
    stable = (manifest_hash == digest(manifest_path) and catalog_hash == digest(catalog_path)
        and assets == {path: digest(path) for path in assets}
        and all(digest(source/name) == value for name, value in manifest.items()))
    assert stable
    report = dict(all_original_rows_match=True, inputs_stable=stable, configured_maps=len(catalog),
        original_goto_rows=rows, directed_pairs=sorted(pairs), goto_entries=entries,
        manifest=str(manifest_path), manifest_sha256=manifest_hash, production_files=len(manifest),
        runtime_catalog=str(catalog_path), runtime_catalog_sha256=catalog_hash,
        asset_sha256=assets, config_entry=config_name,
        config_entry_sha256=hashlib.sha256(config_raw).hexdigest(),
        script_sha256=digest(__file__), same_count_negative_control_rejected=negative_control,
        parsers={name: dict(path=module.__file__, sha256=digest(module.__file__))
                 for name, module in (('pfs', pfs), ('bxml', bxml))},
        live_server_changed=False, gui_verified=False,
        scope='Original raw ordered map attributes/goto rows equal exact immutable runtime catalog; not destination-unit or gameplay proof')
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(dict(all_original_rows_match=True, maps=len(catalog), goto_rows=rows,
                         same_count_corruption_rejected=True)), flush=True)


if __name__ == '__main__':
    main()
