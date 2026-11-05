# Dependencies

| Component | Version / identity | Distribution |
|---|---|---|
| HBF-EventLab | main, 8ccb1f353630f893f761b017d621812b7b9d5bf2, unmodified upstream | Complete 212-file source tree in ../third_party/HBF-EventLab |
| llama.cpp | b3fa69955ea81c3b60e77e3c1e2224c4a826ffb9 plus existing private overlay | Complete source in ../third_party/llama.cpp-integrated |
| Detours | Existing accepted frontend dependency | Source and license in ../third_party/detours |
| CUDA | Toolkit 13.0, CUPTI, cuBLAS and runtime DLLs | External installation |
| Compiler | Visual Studio 2022 C++ Build Tools | External installation |
| Build tools | CMake >= 3.24 and Ninja | Located by ../build.ps1 |
| Python | 3.12 validated; runtime packages in ../requirements.txt | External environment |

The backend commit, tree and all upstream source hashes are recorded in
[the origin record](../third_party/hbf-eventlab-origin.json). The former local
backend overlay is integrated upstream and has been removed.

GGUF parsing uses the bundled framework gguf-py package. No installed runtime
source path depends on the development workspace. Model GGUF files, conversion
records and generated local profiles are caller-supplied inputs.

Third-party source, notices and license files retain their original content and
languages. Release-authored documentation is English.
