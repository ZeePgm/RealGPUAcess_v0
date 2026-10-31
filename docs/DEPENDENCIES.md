# Dependencies

| Component | Version / identity | Distribution |
|---|---|---|
| HBF-EventLab | feat/incremental-host, 72e074508c462dceb7d42962c4885ecf17cc4d0d, six local patch files | Complete 205-file source tree in ../third_party/HBF-EventLab |
| llama.cpp | b3fa69955ea81c3b60e77e3c1e2224c4a826ffb9 plus existing private overlay | Complete source in ../third_party/llama.cpp-integrated |
| Detours | Existing accepted frontend dependency | Source and license in ../third_party/detours |
| CUDA | Toolkit 13.0, CUPTI, cuBLAS and runtime DLLs | External installation |
| Compiler | Visual Studio 2022 C++ Build Tools | External installation |
| Build tools | CMake >= 3.24 and Ninja | Located by ../build.ps1 |
| Python | 3.12 validated; runtime packages in ../requirements.txt | External environment |

The backend provenance and original/patched hashes are in
[the origin record](../third_party/hbf-eventlab-origin.json); the exact changes
are in [the overlay patch](../third_party/hbf-eventlab-overlay.patch).
The local changes provide guarded pre-start fault-model injection and Host
metadata/eligibility scan optimizations. They do not add another Host or Device.

requirements-dev.txt adds matplotlib and Pillow for architecture rendering.
GGUF parsing uses the bundled framework gguf-py package. No installed runtime
source path depends on the development workspace. Model GGUF files, conversion
records and generated local profiles are caller-supplied inputs.

Third-party source, notices and license files retain their original content and
languages. Release-authored documentation is English.
