"""Create or verify a complete, portable source archive using SHA-256 records."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
MANIFEST='release-manifest.json'
EXCLUDED_ROOT_DIRS={'build','output','dist','models','.venv','.git','.pytest_cache'}

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def sources(root):
    result=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(root)
        if rel.as_posix()==MANIFEST:continue
        if any(part in {'.git','__pycache__','.venv','.pytest_cache'} for part in rel.parts):continue
        if p.suffix=='.pyc':continue
        first=root/rel.parts[0]
        if first.is_dir() and (rel.parts[0] in EXCLUDED_ROOT_DIRS or rel.parts[0].startswith('build-')):continue
        if rel.parts[:2]==('configs','integrated') and p.suffix=='.json':continue
        if rel.as_posix()=='configs/machine.local.json':continue
        result.append(p)
    return result

def verify(archive):
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise RuntimeError('Archive CRC verification failed')
        manifest=json.loads(z.read(MANIFEST))
        expected={x['path'] for x in manifest['files']}|{MANIFEST}
        if len(z.namelist())!=len(expected) or set(z.namelist())!=expected:raise RuntimeError('Archive membership differs from manifest')
        for item in manifest['files']:
            p=Path(item['path'])
            if p.is_absolute() or '..' in p.parts:raise RuntimeError('Non-relative source member')
            content=z.read(item['path'])
            if len(content)!=item['bytes'] or hashlib.sha256(content).hexdigest()!=item['sha256']:raise RuntimeError('Changed archive member: '+item['path'])
        for name in ['third_party/llama.cpp-integrated/cmake/build-info.cmake',
                     'third_party/llama.cpp-integrated/common/build-info.h',
                     'third_party/HBF-EventLab/include/hbf_eventlab/runtime/simulation_session.hpp']:
            if name not in expected:raise RuntimeError('Required source missing: '+name)
    return manifest

def package(archive):
    archive=archive.resolve()
    if archive.is_relative_to(ROOT):raise ValueError('Choose an archive path outside the source tree')
    origin=json.loads((ROOT/'third_party/hbf-eventlab-origin.json').read_text(encoding='utf-8'))
    files=sources(ROOT)
    manifest={'schema':2,'release':'RealGPUAcess_v0','revision':'incremental-host-72e0745',
              'backend_upstream_commit':origin['upstream_commit'],
              'backend_overlay_files':len(origin['local_changes']),
              'framework_commit':'b3fa69955ea81c3b60e77e3c1e2224c4a826ffb9',
              'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]}
    (ROOT/MANIFEST).write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    archive.parent.mkdir(parents=True,exist_ok=True)
    temporary=archive.with_name(archive.name+'.partial')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
        z.write(ROOT/MANIFEST,MANIFEST)
    verify(temporary)
    temporary.replace(archive)
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['create','verify'])
    parser.add_argument('--archive',type=Path,default=ROOT.parent/'RealGPUAcess_v0-source.zip')
    a=parser.parse_args();m=package(a.archive) if a.action=='create' else verify(a.archive)
    print(json.dumps({'status':'pass','files':len(m['files'])+1,'archive_sha256':sha(a.archive)},indent=2))
