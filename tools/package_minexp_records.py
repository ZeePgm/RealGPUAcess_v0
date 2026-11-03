"""Check original experiment indexes and pack deduplicated, byte-exact records."""
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIES = ['20261101-s6-001', '20261101-s6-minimum-acceptance-001',
           '20261101-s7-001', '20261101-s8-002', '20261101-s9-002',
           '20261103-snapshot-reproduction-001']


def digest(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    dest = ROOT/'artifacts/minexp-complete'; dest.mkdir(parents=True, exist_ok=False)
    files = {}; objects = {}; verified = []
    for name in STUDIES:
        folder = ROOT/'output/gpu-s'/name
        index = json.loads((folder/'artifact-index.json').read_text(encoding='utf-8'))
        expected = {r['path']:r for r in index['files']}
        actual = {p.relative_to(folder).as_posix():p for p in folder.rglob('*') if p.is_file()}
        assert expected.keys() <= actual.keys(), name+' missing indexed file'
        for rel, p in sorted(actual.items()):
            h = digest(p); size = p.stat().st_size
            if rel in expected:
                r = expected[rel]; assert size == r['bytes'] and h == r['sha256'], str(p)
            files[p.relative_to(ROOT).as_posix()] = {'sha256':h, 'bytes':size}
            objects.setdefault(h, p)
        verified.append({'study':name, 'indexed_files_verified':len(expected), 'available_files':len(actual), 'missing':0, 'hash_mismatch':0})
        print('Original index verified', name, len(expected), flush=True)
    common = ROOT/'output/gpu-s/20261101-s2-b2-v2-001'
    extra = [p for p in (common/'S0').iterdir() if p.is_file()]
    extra += list((common/'S0/inputs').glob('*.txt'))
    extra += [common/'S2'/n for n in ['access_semantics.json','numerical_contract.json']]
    extra += [ROOT/'output/gpu-s/20261101-s4-001/S4/M2-regions.json']
    for p in extra:
        if p.exists():
            h = digest(p); files[p.relative_to(ROOT).as_posix()] = {'sha256':h,'bytes':p.stat().st_size}; objects.setdefault(h,p)
    payload = ROOT/'output/minexp-complete-payload.zip'
    with zipfile.ZipFile(payload, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for i, (h, p) in enumerate(sorted(objects.items())):
            z.write(p, 'objects/'+h)
            if i % 250 == 0: print('Packing unique contents',i,'/',len(objects),flush=True)
    parts = []
    with payload.open('rb') as f:
        i = 1
        while data := f.read(2*1024*1024):
            name = f'payload.zip.part{i:03d}'; p = dest/name; p.write_bytes(data)
            parts.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                          'git_blob_sha1':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()}); i += 1
    with zipfile.ZipFile(payload) as z:
        assert z.testzip() is None
    manifest = {'schema':2,'date':'2026-11-03','base_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'scope':'S6 all 10 measured and 3 warm-up pairs plus verification; qualified table; S7 all replays; S8 native/full/two timing; S9 full delivery; recovered numerical snapshots and common identities.',
        'verified_original_indexes':verified,'missing_files':0,'file_count':len(files),'unique_contents':len(objects),
        'total_original_bytes':sum(r['bytes'] for r in files.values()), 'archive_bytes':payload.stat().st_size,
        'archive_sha256':digest(payload),'parts':parts,'files':files,
        'storage':'Deduplicated by SHA256; restore recreates every original file path with the original bytes. No numerical data removed or downsampled.'}
    (dest/'file-index.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Complete package:',len(files),'files,',len(objects),'unique,',len(parts),'parts,',payload.stat().st_size,'compressed bytes',flush=True)


if __name__ == '__main__': main()
