# S8：实测固定表驱动的真实GPU/HBF联合实验G3

批次`output/gpu-s/20261101-s8-002/`。**S8通过，S9尚未执行。** 结论限定于S6批准的`minimum_fixed_trace_mechanism_experiment`范围，继承短段测量精度、GPU活动并集口径及未校准H0参数的限制。

## 条件与真实执行路径

使用S7绑定的同一sample-3计算表、主输入44 tokens、8输出、M2选区与H0；表SHA256与S7完全一致。权重保留于GPU，原生F16 KV、每个MUL_MAT显式F32及其他算法条件沿用S5/S6。独立应用目标`gpu_s_s8`读取固定表；原S6二进制及Host／Device核心实现不变。

每例创建新的Session，经普通写初始化完整12288B注册范围后取t0。真实CUDA执行每个节点；选区消费者之前经`TensorAccessBridge → SimulationSession → HostDriver → DeviceDriver`等待父访问及全部子Global最终成功，再发射消费者。固定表时长在相应GPU工作完成后推进，实际GPU墙钟、HBF程序墙钟、验证快照均不推进模型时间。

执行器逐段核对表ID、kind、node、step与非空GPU活动覆盖，完整消耗18072个生产窗口（5880个非零段）；验证快照单独记录并不消耗表条目。表头、段数、ID顺序和整数时长不合法则拒绝。本轮实际执行native完整核验，以及G3完整核验一次、timing两次，未用离线重放代替G3。

## G2/G3配对结果

下表为模拟时钟结果，单位ms；差值来自本次真实提交的符号HBF访问。不是原生请求墙钟或真实HBF硬件预测。

| 指标 | S7 G2 | S8 G3 | G3−G2 |
|---|---:|---:|---:|
| TTFT | 10.040304 | 10.040791788 | 0.000487788 |
| 平均TPOT | 5.118493 | 5.118760988 | 0.000267988 |
| 最后token相对t0时刻 | 45.869755 | 45.872118704 | 0.002363704 |

首输出区间HBF等待为487788ps，之后7个区间各267988ps，累计2363704ps（2.363704µs）。每枚token均满足`T_G3−T_G2=此前累计实际HBF等待`，每个ITL差等于其区间等待。TPOT差以整数分子及分母7核验，避免浮点比较掩盖误差。逐段、逐token、配对区间的整数ps残差均为0。

输出IDs为`[32,6366,5711,4938,311,3553,323,17179]`；达到上限结束，无额外预测步。三次G3的tokens、模拟时刻、桥事件、完整统计逐字节相同；Session的全部模型字段和访问结果也相同。主机`before_ns/after_ns`只作观测证据，不要求不同进程取值相同。

## 数值、映射与因果审计

- 最终表驱动执行器的native完整logits、有效快照和事件与S5已验收native一致，生产CUDA操作与S6选定轨迹一致；新执行器没有改变被测数学计算。
- 重新执行8输出独立CPU参照，native及G3-full各1369个比较数组通过冻结B2判据。native/G3有效快照与完整logits逐位一致，GPU有效KV发布舍入核验通过。
- timing不导出逐层快照，完整logits、token、事件与full一致；两次timing同样执行全部真实GPU节点和HBF访问。full/lean指核验导出的差别，timing仍保留本轮因果审计所需CUPTI记录，并非无插桩原生性能测量。
- M2有效登记/唯一触达10240B、注册12288B、填充2048B；8步累计读81920B，16次父访问、24个读Global、1280个64B逻辑片段及读尝试。独立交集、地址/content、父完成=max子完成、全部成功和无未选区额外提交均通过。
- 各消费者的CUDA提交均在成功依赖之后；CUPTI API关联和全设备同步证明先前工作已完成、HBF等待期间没有GPU提交穿越依赖。GPU活动分段覆盖输入gap、节点工作及每token输出tail；无遗漏、重复或CUPTI丢失。
- 所有Session完成并关闭输入，Host/Device均排空，无依赖失败或未决项。初始化写单列，不计入请求延迟或累计读流量。

固定GPU工作进一步分解为互斥kernel-only、transfer-only及kernel/transfer重叠类别，本轨迹重叠类别为0。`G2-G3-decomposition.csv`逐步给出GPU计算、必要memcpy/memset及HBF等待，分解和严格等于固定表及G3区间时长，不重复计费。

## 表拒绝与中止记录

对真实S8二进制提供错误模型表头、缺段、段ID错序、小数时长4类副本，均在模型加载及GPU/HBF请求前退出，未产生正常输出。记录见`negative-table-validation.json`；原表及既有S7的11类拒绝测试保留。

先行批次`20261101-s8-001`完整G3已通过；第一次timing的后处理将Session.accesses中的主机观测`before_ns/after_ns`也要求逐字节相同，导致审计中止。差异核查确认只有这两个观测字段，未发现模拟状态差异。修正后仅从Session比较中排除这些主机时间戳，所有模拟Tick、访问结果和后端状态仍严格相同；本轮以新批次重新运行全部案例。旧源码、运行数据及inconclusive记录保留。

## 产物与复现

`G3/`保存条件、表/输入/有效H0、构建身份及源码/二进制快照；各执行子目录保存实际GPU活动、提交API、段推进、门控结果、token、后端统计、数值和独立审计。汇总文件为：

- `stage-result.json`、`G2-G3-paired.csv`、`G2-G3-decomposition.csv`。
- `decomposition-audit.json`、`negative-table-validation.json`及各例`paired-audit.json`、`segment-audit.json`。
- 批次根目录的`artifact-index.json`；仓库摘要[gpu-s8.json](validation/gpu-s8.json)。

复现须使用新的输出目录：

```powershell
python experiments/gpu_s/s8.py --study output/gpu-s/<new-S8-study-id>
python experiments/gpu_s/s8_validate.py --study output/gpu-s/<new-S8-study-id>
python experiments/gpu_s/s8_decomposition.py --study output/gpu-s/<new-S8-study-id>
```

当前S8已满足进入S9的固定轨迹数值/行为和配对要求。S9图表尚未生成；本次结果不证明微小模拟差异在真实硬件上可观测，不代表真实NAND字节搬运或权重卸载。


2026-11-03恢复说明：本地缺失的数值数组已使用原执行器与原输入重新生成，逐文件旧SHA256全部匹配后补回缺失路径，原实验索引再次通过。旧计时记录未覆盖，见[快照恢复报告](GPU_SNAPSHOT_REPRODUCTION_20261103.md)。
