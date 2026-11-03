# S6/S8缺失数值快照重现与恢复

日期：2026-11-03。新批次`output/gpu-s/20261103-snapshot-reproduction-001/`。**全部10825个缺失文件已重现，与旧实验索引逐文件SHA256完全一致，并补回原路径。**

| 原实验案例 | 重现文件 | 旧索引哈希一致 |
|---|---:|---:|
| S6 reference-verification | 3608个GPU `.bin` | 3608/3608 |
| S8 native-verify | 3608个GPU `.bin` | 3608/3608 |
| S8 G3-full | 3608个GPU `.bin` | 3608/3608 |
| S8 cpu-8 | 1个CPU `snapshots.npz` | 1/1 |

使用旧执行器、原配置、模型及输入重新执行核验，未重新选择S6计时样本，也未更换S7/S8的固定表。S6/S8可执行文件、CPU参照源码和模型哈希与旧身份一致，依赖构建seal验证通过。

重跑的三组GPU案例各1369个数组通过原B2分类判据；token、完整logits、事件结构与旧记录一致，KV发布核验通过。新运行之间的有效GPU快照逐位一致。S8真实G3依赖、内容、排空及与S7的配对时间守恒重新通过。

所有10825个原始数组文件的**整个文件**与旧索引SHA256一致，强于只比较有效KV区域；本次没有原始字节差异。新GPU时间戳、内存地址和程序墙钟仍属于新运行，仅保存在新目录，不当成旧运行记录覆盖。

恢复操作只补原目录中缺失且已匹配旧哈希的路径，不覆盖现有文件，不改写旧`artifact-index.json`、协议、数值判据、计算表或S9图表。恢复后重新验证：

- 原S6批次`20261101-s6-001`：3931个原索引条目全部存在且大小/SHA256匹配。
- 原S8批次`20261101-s8-002`：7381个原索引条目全部存在且大小/SHA256匹配。

新批次保留重跑命令/日志、完整新快照、`conditions.json`、`file-comparison.json`、`restoration-log.json`、数值/因果/配对审计、`stage-result.json`及自身哈希索引。仓库内摘要：[验证记录](validation/gpu-snapshot-reproduction-20261103.json)。

复现入口（须使用新的输出目录）：

```powershell
python experiments/gpu_s/reproduce_snapshots.py --study output/gpu-s/<new-reproduction-id>
```

该入口生成新数据并比较旧索引，不自动覆盖旧目录；本轮补回路径的操作记录单列于`restoration-log.json`。

恢复完成时上传曾暂停。用户随后授权再次核查并上传；现已按完整数据重新打包，旧缺失状态草稿作废。完整数据与恢复入口见[发布清单](GPU_MINEXP_DATA_MANIFEST.md)。
