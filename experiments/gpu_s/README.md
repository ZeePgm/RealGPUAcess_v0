# S0—S3 实验入口

此目录实现 `docs/GPU_S_SERIES_PLAN.md` 的S0—S3；S4及以后尚未实现。
公共 Host、Device、Session、TensorAccessBridge 和 llama.cpp 源码保持复用。

## 构建

当前入口在 Windows/MSVC 上验证，链接本工作区已经封存的依赖构建，默认目录为
`build-portability-model`，可用 `-DBASE_BUILD=...` 指定其他经过身份校验的构建。
依赖 CUDA Runtime、CUPTI、CMake、Ninja、Python、NumPy 和 PyTorch CPU 运算。
先按仓库构建文档准备依赖，并在 VS 开发者 PowerShell 中运行：

```powershell
python tools/integrated_build_identity.py verify --build-dir build-portability-model
cmake -S experiments/gpu_s -B build-s0-s2 -G Ninja -DCMAKE_BUILD_TYPE=Release -DCUDAToolkit_ROOT="$env:CUDA_PATH"
cmake --build build-s0-s2 --parallel 4
```

Python 入口当前使用 `build-portability-model` 和 `build-s0-s2` 两个工作区相对目录；
若另设构建目录，需要同步调整 `study.py` 的 BASE/BUILD。
工具路径和运行环境由现有 `platform_environment` 层解析。
实验数值参照当前限定为已验证的 Qwen3 F16/F32 GGUF，不能直接用于其他架构。

## 执行

每次使用新的 study 目录。S0/S1 必须依次通过，然后才执行 S2：

```powershell
$study = 'output/gpu-s/<new-study-id>'
python experiments/gpu_s/study.py S0 --study $study --model '<model.gguf>' --conversion '<conversion.json>'
python experiments/gpu_s/study.py S1 --study $study
python experiments/gpu_s/s2.py --study $study
python experiments/gpu_s/report.py --study $study
```

S0 仅分词、查询资源和解析后端配置。它预登记独立校准输入及精度目标，并复制
实验源码、二进制和 CMakeCache，保存模型、转换、依赖构建的身份。
S1 的公式检查使用合成事件；实际桥接案例另外调用真实增量后端，独立审计全部
320 个读片段地址、父子完成关系、背压、失败和排空。

S2 的 GPU 入口使用 F16 权重、每个 MUL_MAT 显式 F32 精度、F16 原生 KV，
关闭 flash attention；依赖构建须关闭 CUDA graphs。每个算子由 scheduler 单独
发射并同步，CUPTI 记录实际 kernel。该执行变体需在后续 HBF 对照中保持一致。
`verify` 导出 hidden/QKV/有效 KV/完整 logits；`timing` 仅用于同路径一致性检查，
此阶段尚不采集正式性能结果。预发射中止 fixture 只验证执行器边界。

CPU 参照独立使用 PyTorch CPU 方程和 GGUF 实际张量值，覆盖 prefill/decode、
全部层、RoPE 和 F16 KV 发布。精度目标为预先声明的工程目标，并非全网络误差定理。
两组分离校准输入必须全部通过后才能形成合格数值合同；失败保留逐数组误差，
S2 标记 blocked，停止进入 S3。主输入原生运行可继续提供边界诊断。

## S3：单区域真实GPU/HBF

S3使用同一份 `native.cpp` 构建 `gpu_s_joint`，在算子发射前调用
`hbf_gate.hpp`，读取已冻结H0有效INI和区域清单。全部公共后端代码继续复用。
每例通过普通写初始化，所有模拟计算段为0，token相对t0时长仅由HBF等待组成。
M1=4H字节norm，M8=8192字节down，分别在新Session中运行。

```powershell
cmake -S experiments/gpu_s -B build-s3 -G Ninja -DCMAKE_BUILD_TYPE=Release -DCUDAToolkit_ROOT="$env:CUDA_PATH"
cmake --build build-s3 --target gpu_s_joint --parallel 4
python experiments/gpu_s/s3.py --prior-study 'output/gpu-s/<S0-S2-study>' --study 'output/gpu-s/<new-S3-study>'
```

入口默认要求S2状态为pass。若用户在B2尚未合格时明确要求继续功能诊断，
才使用 `--diagnostic-with-unqualified-cpu`；此标志不改变精度判据，不产生S3验收通过，
也不开放S4。诊断记录仍计算独立CPU对主输入的完整误差，保留blocked总状态。

`s3_audit.py` 独立核对原始源范围→区域→Global、64B片段地址和content、
父完成=max子完成、普通写初始化和最终排空，并用CUPTI证明确实在依赖成功后发射。
native/M1/M8的完整logits和全部有效快照必须逐位相同；KV填充不参与比较。
新入口另外复验原S2的1/2输出事件序列与数值，历史S2源码保留在其运行快照中。

负例包含持续program-fail初始化失败（预期进程码87）和运行时间限额（88）。
后者把独立正常初始化案例的t0+1ps显式登记为绝对限额；消费者前中止，保存未决Global。
限额不自动上调，未排空状态如实报告。负例返回预期退出码仍需通过独立审计。

进程退出 0 表示记录流程完成；**以每阶段 `stage-result.json` 验收状态为准**。
原始事件时钟、GPU kernel 时间戳、程序墙钟均不作为正式 HBF 模拟 TTFT/TPOT。
原始快照和模型不进入源码发布清单；结果目录位于被忽略的 `output/`。
