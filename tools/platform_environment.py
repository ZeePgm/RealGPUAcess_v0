"""Platform-dependent executable names and runtime library discovery."""
import os
from pathlib import Path


def executable(folder, name):
    return Path(folder) / (name + ('.exe' if os.name == 'nt' else ''))


def cache_value(build, name):
    cache = Path(build) / 'CMakeCache.txt'
    if cache.is_file():
        for line in cache.read_text(encoding='utf-8').splitlines():
            if line.startswith(name + ':') and '=' in line:
                return line.split('=', 1)[1]
    return None


def runtime_environment(build, source_root, cuda_root=None, gpu_device='0'):
    build, source_root = Path(build).resolve(), Path(source_root).resolve()
    root = cuda_root or cache_value(build, 'CUDAToolkit_ROOT') or os.environ.get('CUDA_PATH')
    env = dict(os.environ)
    inherited = [x for x in env.get('PATH', '').split(os.pathsep) if x and not
                 (Path(x).resolve().is_relative_to(source_root) and
                  any(part.startswith('build-') for part in Path(x).parts))]
    libraries = [build / 'bin']
    if root:
        cuda = Path(root).resolve()
        if not cuda.is_dir():
            raise ValueError('CUDA runtime root does not exist: ' + str(cuda))
        env['CUDA_PATH'] = str(cuda)
        libraries += [cuda / p for p in ('bin', 'bin/x64', 'lib', 'lib/x64',
                                         'lib64', 'extras/CUPTI/lib64', 'extras/CUPTI/lib/x64')]
    libraries = [str(p) for p in libraries if p.is_dir()]
    env['PATH'] = os.pathsep.join(libraries + inherited)
    if os.name != 'nt':
        env['LD_LIBRARY_PATH'] = os.pathsep.join(libraries + [env.get('LD_LIBRARY_PATH', '')])
    env['CUDA_VISIBLE_DEVICES'] = str(gpu_device)
    env['GGML_CUDA_DISABLE_GRAPHS'] = '1'
    for key in ('GGML_CUDA_CUBLAS_COMPUTE_TYPE', 'GGML_CUDA_DISABLE_FUSION',
                'HBFLAB_STORAGE_CONFIG', 'HBFLAB_M6_NORM'):
        env.pop(key, None)
    return env
