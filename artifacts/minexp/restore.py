"""Verify and restore the complete minexp record bundle using only stdlib."""
import argparse
import gzip
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path


def restore(bundle, destination=None):
    manifest_bytes = gzip.decompress((bundle/'file-index.json.gz').read_bytes())
    assert hashlib.sha256(manifest_bytes).hexdigest() == json.loads((bundle/'summary.json').read_text())['file_index_sha256']
    m = json.loads(manifest_bytes)
    targets = {}
    for rel, info in m['files'].items():
        assert not Path(rel).is_absolute() and '..' not in Path(rel).parts
        targets.setdefault(info['sha256'], []).append((rel, info['bytes']))
    restored = 0
    with tempfile.TemporaryFile() as combined:
        total = hashlib.sha256()
        for part in m['parts']:
            b = (bundle/part['path']).read_bytes()
            assert len(b) == part['bytes'] and hashlib.sha256(b).hexdigest() == part['sha256'], part['path']
            combined.write(b); total.update(b)
        assert total.hexdigest() == m['archive_sha256']
        combined.seek(0)
        with zipfile.ZipFile(combined) as z:
            assert set(z.namelist()) == {'objects/'+h for h in targets}
            for h, paths in targets.items():
                b = z.read('objects/'+h)
                assert hashlib.sha256(b).hexdigest() == h
                for rel, size in paths:
                    assert len(b) == size
                    if destination is not None:
                        path = (destination/rel).resolve()
                        assert path.is_relative_to(destination), rel
                        if path.exists():
                            with path.open('rb') as f:
                                assert hashlib.file_digest(f, 'sha256').hexdigest() == h, 'Conflicting existing file: '+str(path)
                        else:
                            path.parent.mkdir(parents=True, exist_ok=True)
                            with path.open('xb') as f: f.write(b)
                    restored += 1
    assert restored == m['file_count'] and m['missing_files'] == 0
    print(('Verified ' if destination is None else 'Verified/restored ')+str(restored)+' original files; all hashes match.')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--bundle', type=Path, default=Path(__file__).resolve().parent)
    p.add_argument('--destination', type=Path)
    p.add_argument('--verify-only', action='store_true')
    a = p.parse_args()
    if not a.verify_only and a.destination is None: p.error('Use --verify-only or specify --destination')
    restore(a.bundle.resolve(), None if a.verify_only else a.destination.resolve())
