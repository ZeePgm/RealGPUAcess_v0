"""Migration settings must work without the original machine's paths."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from platform_environment import executable, runtime_environment
from package_source import sources


class EnvironmentTests(unittest.TestCase):
    def test_cache_runtime_discovery_and_device(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); build = root / 'build-new'; build.mkdir()
            cuda = root / 'toolkit with spaces'; (cuda / 'bin').mkdir(parents=True)
            (build / 'bin').mkdir()
            (build / 'CMakeCache.txt').write_text('CUDAToolkit_ROOT:PATH=' + str(cuda) + '\n')
            env = runtime_environment(build, root, gpu_device='2')
            self.assertEqual(env['CUDA_PATH'], str(cuda.resolve()))
            self.assertEqual(env['CUDA_VISIBLE_DEVICES'], '2')
            self.assertIn(str(cuda / 'bin'), env['PATH'].split(os.pathsep))
            override = root / 'override'; override.mkdir()
            self.assertEqual(runtime_environment(build, root, override)['CUDA_PATH'], str(override))

    def test_invalid_toolkit_fails_before_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                runtime_environment(folder, folder, Path(folder) / 'missing')

    def test_native_executable_name(self):
        self.assertEqual(executable('bin', 'runner').name,
                         'runner.exe' if os.name == 'nt' else 'runner')

    def test_local_machine_paths_are_not_packaged(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); config = root / 'configs'; config.mkdir()
            (config / 'machine.local.json').write_text('{}')
            (config / 'machine.example.json').write_text('{}')
            self.assertEqual([p.name for p in sources(root)], ['machine.example.json'])


if __name__ == '__main__':
    unittest.main()
