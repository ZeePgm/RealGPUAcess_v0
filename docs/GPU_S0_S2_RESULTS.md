# S0—S2 执行结果

日期：2026-10-31。正式记录批次：`20261031-s0-s2-002`。
**S0通过，S1通过，S2已执行但未通过进入S3的标准。**

后续：用户明确要求继续S3，已另外完成[S3功能诊断](GPU_S3_RESULTS.md)，其总状态仍受B2阻断；本文件保留原S0—S2记录。

[完整本地报告](../output/gpu-s/20261031-s0-s2-002/report.md)与[结构化摘要](validation/gpu-s0-s2.json)保留各项证据。
原始事件、快照和二进制位于被忽略的 `output/`，源码仓库保留实验入口和摘要。

## 实际条件与实现

- 本机 RTX 5070 / capability 12.0 / 驱动616.56；Qwen3-0.6B-F16，28层、H=1024、F=3072、16个Q头和8个KV头、head_dim=128。
- GGUF SHA256：`74878aba1d10648eae3d6cfef822f8c59ce3217b3808b35fce2dd02d975952a2`。主prompt实际44 tokens；两组预登记独立校准输入分别44、45 tokens。
- 单请求、单序列、greedy，context/batch/ubatch=512/256/256，8个CPU线程，F16原生KV。CUDA graphs和flash attention关闭。
- 新增独立实验入口 `experiments/gpu_s/`，链接已验证身份的本工作区依赖构建；公共Host/Device/Session/桥和llama.cpp源码未修改。
- 显式设置每个MUL_MAT为F32精度、cuBLAS F32和禁用TF32。仅设置cuBLAS环境变量不足以控制自定义MMVF的累加精度，诊断后已通过公开GGML精度接口补齐。
- 每个算子单独发射并同步，真实消费者前后回调与CUPTI kernel关联。该算子拆分和精度变体须在后续native/HBF对照中共同保留；当前结果不代表默认融合执行性能。

S0保存源码与二进制快照、依赖seal验证结果、构建缓存、GPU/运行时/编译器版本、模型/conversion和输入哈希。编译工具报告CUDA 13.0.88，实际CUDA runtime/driver API均返回13040，两者分别记录。源模型、CUDA与MSVC路径属于本机配置，模型权重和工具链不进入源码包。

## 各步验收

| 阶段 | 状态 | 已取得的结果 |
|---|---|---|
| S0 | pass | GGUF/conversion、分词和容量、资源、依赖构建身份、H0 resolver检查通过；没有运行推理 |
| S1 | pass | 合成TTFT=35μs、ITL/TPOT=12μs；N=0/1、EOS、表缺项/重复/错序/身份错配等检查通过 |
| S1真实桥 | pass | 有效登记16KiB、唯一触达12KiB、累计读20KiB，3个父读/5个读Global；320个64B逻辑读片段地址和父完成=max子完成逐项核对通过 |
| S1边界 | pass | 非零偏移、跨区/别名/填充、非法映射拒绝；resident=64发生3次背压拒绝后完成；持续program-fail按失败返回并排空 |
| S2 B1 | pass | 主输入1/2输出、消费者/kernel前后配对、范围覆盖、KV发布、终止边界和模式一致性通过 |
| S2 B2 | not_qualified | 独立CPU校准超出预登记误差目标，尚不能冻结合格数值合同 |

真实桥三次父读等待分别为323910ps、214010ps、217222ps；这些来自未校准H0，不是GPU请求TTFT。S1-a的35μs/12μs仅用于公式验收。

主输入输出token IDs分别为 `[32]`、`[32,6366]`，实际处理位置分别44、45，均以length结束。两输出运行包含prefill和一次decode，2258对算子边界、1882条kernel记录，无CUPTI丢失。M1/M2/M8及必做down非零偏移范围均被实际消费者的完整输入源覆盖。访问合同为每次真实消费者调用一次完整源范围，再与选区求交；不按prefill行数扩增流量，不解释为物理load次数。

跨两组校准和主输入1/2输出共392个有效F16 KV发布数组，与GPU自身生成值的F16舍入逐位一致。1/2输出的首步完整logits相同，verify/timing的完整logits相同，最后输出后没有额外预测步。预发射中止fixture确认消费者未发射、无token产生；这项证据限定为执行器中止边界，不冒充HBF故障门控。

## 数值合同阻断

CPU参照独立使用PyTorch CPU数学方程读取GGUF实际权重值，包括Qwen3 QK norm、GQA、NEOX RoPE、因果attention、greedy/EOS和F16 KV舍入，不调用llama推理或CUDA计算。

校准前预登记的工程保真目标：

- `RMS(error)/RMS(reference) ≤ 2^-11 = 0.00048828125`。
- `max(|error|/max(|reference|, RMS(reference))) ≤ 2^-10 = 0.0009765625`。
- token/raw EOS/结束原因/位置一致，数组形状一致且数值有限。

两个误差目标分别以一个F16单位舍入预算和两个预算为设计依据，**不是完整网络误差上界**，须经分离校准检验。最终复跑使用的目标文件与最初诊断批次逐字节相同，没有根据失败误差放宽。

| 校准输入 | 比较数组 | 超标数组 | token/边界 | 最大相对RMS | 最大归一化元素误差 |
|---|---:|---:|---|---:|---:|
| calibration-a | 343 | 198 | 精确一致 | 0.000531049424 | 0.005931683689 |
| calibration-b | 343 | 202 | 精确一致 | 0.000523298561 | 0.006722683782 |

比较涵盖全部28层hidden/QKV及有效F16 KV、选中层前后hidden、最终norm和两个输出的完整logits。两组最大相对RMS均出现在prefill的Vstore-27，最大归一化元素误差均出现在prefill的Kstore-20；完整logits也未通过元素误差目标。

已有证据支持GPU KV发布及token行为正确，尚未完成跨CPU/GPU数值差异的归因。不能仅凭这些误差断言模型实现错误，也不能以token相同代替逐数组验收。B2未成立，主输入CPU正式数值验收没有开展，S2总状态为blocked；S3未启动，正式计算表和性能主图没有采集。

## 复现与下一步

运行步骤见[实验入口说明](../experiments/gpu_s/README.md)。新批次不得覆盖旧目录。完整产物SHA256索引为 `output/gpu-s/20261031-s0-s2-002/artifact-index.json`；最初诊断批次001保留用于分析，不作为最终版本验收记录。

下一步应定位归约、RoPE和F16 KV舍入等边界的数值差异，核查参照与被测执行精度。若需修订CPU参照或精度合同，必须给出独立依据，建立新实验版本并重新进行分离校准和主输入数值验收。B2及主输入验收通过前不进入S3。
