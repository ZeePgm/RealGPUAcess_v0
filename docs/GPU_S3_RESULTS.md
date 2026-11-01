# S3：单区域真实GPU/HBF功能诊断

日期：2026-10-31；记录批次：`20261031-s3-002`。
**功能检查通过；S3总验收仍为blocked，S4未启动。**

用户在[S2数值校准阻断](GPU_S0_S2_RESULTS.md)后明确要求继续S3。本轮通过显式诊断选项执行全部S3案例，保留原精度目标和B2未合格结论，未宣称满足原设计的三方数值验收条件。

[完整本地报告](../output/gpu-s/20261031-s3-002/S3/report.md)；[结构化摘要](validation/gpu-s3.json)；[执行入口](../experiments/gpu_s/README.md)。

## 条件与接入

沿用S0模型、44-token主prompt、单请求/单序列、greedy、context/batch/ubatch=512/256/256、F16原生KV、显式F32矩阵计算和关闭graphs/flash的条件。每例最多1枚输出，模拟计算段全部为0。

新增 `gpu_s_joint` 实验入口与 `hbf_gate.hpp`，使用原生消费者前回调同步等待：

`CUDA消费者 → TensorAccessBridge → SimulationSession → 原HostDriver → 原DeviceDriver → Global最终成功 → CUDA消费者发射`

每例使用新的Session，通过普通Global写完成选区初始化，随后取请求t0。选区真实字节始终留在GPU，HBF使用符号内容身份1；KV不进入本轮权重HBF空间。所有公共后端和llama.cpp源码均未修改。

新入口先重验原S2的1/2输出：完整logits、全部有效快照、所有原始事件结构与回调ID均与历史记录完全一致。此次native与HBF使用同一二进制和算子执行方式。

## 正向结果

| 案例 | 有效登记/唯一触达/累计读 | 读Global | 64B逻辑读片段 | token相对t0模拟时长 | TPOT |
|---|---|---:|---:|---:|---|
| M1：layer10 norm完整4KiB | 4096/4096/4096B | 1 | 64 | 217222ps | null |
| M8：layer10 down前8KiB | 8192/8192/8192B | 2 | 128 | 323910ps | null |

两例均实际输出token `[32]`，位置44，以length结束，没有额外预测步。每例451个有效快照及完整logits与native逐位一致，其中56个有效KV发布数组也与GPU自身F16舍入结果逐位一致；未用KV未使用区的填充字节参与比较。

独立审计从原始消费者源范围重新求交，核对源偏移→区域偏移→Global地址、全部64B片段、无未选区额外读、父完成=max子Global最终完成及所有final成功。CUPTI记录确认选中消费者的实际kernel全部在依赖成功返回后发射。普通初始化和最终close、Host/Device排空通过。

内容身份依据为：完整初始化写入content=1；封存版本TensorAccessBridge为读设置expected_content；原Host比较返回token与`token_for(expected_content, global_address)`，所有公开读attempt的host_success为true。统计中的read `StatWorkDefined.content`按定义为null，不能将该字段误当成读的expected_content。

模拟时长完全等于请求内HBF等待，compute=0，整数ps守恒残差=0。以上是功能诊断值，尚无实测计算表，不能解释为真实GPU TTFT或硬件性能预测。

## 真实故障与限额

- **持续program-fail初始化**：预期进程码87，原Host给出`RecoveryBudgetExhausted`；GPU执行节点=0，token=0。已登记工作最终排空，逻辑失败如实保留。
- **请求时间限额**：正常M1初始化t0为1586201ps，独立负例显式设置绝对max_tick=1586202ps。预期进程码88，在消费者node439发射前中止。原始回调和CUPTI共同确认没有失败依赖之后的kernel或token。
- **未决状态**：限额后1个Global尚未完成，Host/Device均未排空，next_event=1586535ps；保留限额和待完成项，没有上调预算后改报成功。

额外6项审计负控均按预期拒绝：偏移错误、丢失选区门控、消费者过早发射、Host内容核验失败、父子完成不符，以及未合格S2下不带诊断标志的默认入口。负控通过内存副本构造错误证据，不改原始实验记录。

## CPU数值验收与阻断

独立CPU主输入诊断比较172个数组，其中107个超过原判据；最大相对RMS为0.000527717611，最大归一化元素误差为0.004430923456，原目标分别为0.00048828125和0.0009765625。CPU/native/M1/M8的token、EOS/位置/结束原因一致，三条CUDA路径相对CPU的数值差异完全相同。

观察第一层及后层K/V表明，两端均精确发布自身F32值的F16舍入结果，但早期F32差异已经跨越部分F16舍入边界，差异随后传播。此证据说明一种传播机制，尚不足以完成全部差异归因或给出新的全网络误差界，原阈值未改动。

B2仍为not_qualified，三方数值验收未通过，故S3阶段总状态保持blocked。后续应定位数值差异、独立论证精度合同并重新分离校准，完成主输入验收后才能将后续结果作为正式递进实验。

## 复现与产物

运行命令：

```powershell
python experiments/gpu_s/s3.py --prior-study output/gpu-s/20261031-s0-s2-002 --study output/gpu-s/<new-study> --diagnostic-with-unqualified-cpu
```

默认不带诊断选项时要求S2为pass。数据目录保存实际配置、源码/二进制及构建缓存快照、依赖seal身份、CPU结果、GPU事件和完整logits、bridge/gates/Global统计、数值/覆盖/排空审计、命令和退出码。SHA256索引位于 `output/gpu-s/20261031-s3-002/artifact-index.json`。大型原始数据保留在本地output，不进入源码包。
