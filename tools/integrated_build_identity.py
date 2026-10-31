"""Release-local build and source integrity, independent of the development workspace."""
import argparse,json
from pathlib import Path
from setup_llama_baseline import ROOT,sha
from platform_environment import executable
COMMIT='72e074508c462dceb7d42962c4885ecf17cc4d0d'
DEFAULT_BUILD=ROOT/'build-model'
def require(ok,message):
    if not ok:raise RuntimeError(message)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def records(paths):return [{'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(set(map(Path,paths))) if p.is_file()]
def verify_records(items):
    for i in items:require(sha(Path(i['path']))==i['sha256'],'changed file: '+i['path'])
def inputs():
    return records([p for name in ['include','src','cmake','adapters','third_party','tools'] for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts])
def seal(build):
    build=Path(build).resolve();require(not (build/'release-identity.json').exists(),'sealed build cannot be overwritten')
    v={'status':'sealed','backend':{'commit':COMMIT,'path':str(ROOT/'third_party/HBF-EventLab')},'build_directory':str(build),'sources':inputs(),'artifacts':records([*list((build/'bin').glob('*')),*list(build.glob('*.ptx')),build/'CMakeCache.txt'])}
    require(executable(build/'bin','realgpu_llama').exists(),'model executable missing');write(build/'release-identity.json',v);return v
def verify_build(build=DEFAULT_BUILD,expected=COMMIT):
    v=read(Path(build)/'release-identity.json');require(v['backend']['commit']==expected,'backend mismatch');require(Path(v['build_directory'])==Path(build).resolve(),'build location changed; rebuild required');verify_records(v['artifacts']);require(v['sources']==inputs(),'source inventory changed; rebuild required');return v
def add_build_arguments(p):
    p.add_argument('--cuda-root',type=Path);p.add_argument('--gpu-device',default='0');p.add_argument('--build-dir',type=Path,default=DEFAULT_BUILD);p.add_argument('--expected-backend',default=COMMIT)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['seal','verify']);add_build_arguments(p);a=p.parse_args();v=seal(a.build_dir) if a.action=='seal' else verify_build(a.build_dir,a.expected_backend);print(v['status'])
