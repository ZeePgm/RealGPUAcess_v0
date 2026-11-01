# S7：固定计算表的零等待对照G2

批次 `output/gpu-s/20261101-s7-001/`。**S7通过，S8尚未执行。** 继承S6的`minimum_fixed_trace_mechanism_experiment`限定验收及短段精度限制，未重新测量或改变计算表。

## 条件与操作

使用`20261101-s6-minimum-acceptance-001/compute-table.json`的sample-3完整轨迹、对应事件序列和M2区域清单。请求t0=0，纯记录回放，不启动CUDA、TensorAccessBridge、Session、Host或Device，不提交读写、不产生NAND命令，HBF等待恒为0。输出token来自已核验的源记录，不能声称本轮重新计算了logits。

按源窗口结束与源语义事件的先后顺序，将每个固定段的整数ps时长推进一次；源CPU时间戳仅用于重建顺序，其时间差不计入模拟时间。gap在消费者之前结算、node在node_after之前结算、每步tail在execution_end及token之前结算。未选区节点与空工作窗口均保留。

协议/模型/输入配置/事件哈希、S6限定验收及其表哈希在回放前检查；原表、事件、窗口和区域输入均复制进本批次。表未冻结、缺段、重复、错序、测得时长被改写或身份错配均拒绝，不用默认1000ps替代。

## 实际结果

| 指标 | 结果 |
|---|---:|
| 实际输出数 | 8 |
| 完整窗口／非零工作段 | 18072／5880 |
| 保留源语义事件 | 18091 |
| 保留M2选区回调 | 16 |
| G2 TTFT | 10.040304ms |
| G2平均TPOT | 5.118493ms |
| 请求至最后token的模拟总时长 | 45.869755ms |
| HBF访问、读写Global及NAND命令 | 全部0 |
| 每token及每段时间守恒残差 | 全部0ps |

逐token ITL（token2至8）为`[3.864877, 3.732482, 5.410031, 5.947936, 5.838706, 5.369777, 5.665642] ms`。输出序列为`[32,6366,5711,4938,311,3553,323,17179]`，与S6源记录一致；输出上限结束，没有额外执行步，也没有伪造自然EOS。

三次回放的tokens、segments、事件、选区记录、指标、零访问计数及审计文件SHA256全部一致。独立审计从原表按step求和并累积得到各token时刻；逐段检查起止Tick连续、增量等于表时长；额外逐事件检查18091个语义事件的时钟等于其前所有已闭合窗口的固定时长之和。所有残差为0。

选区审计独立从源回调及清单求交，核对16次回调的源偏移、长度、Global地址和身份，均标记`submitted=false`。这些是保留的逻辑候选访问，不计为已提交读或实际触达HBF存储。

11类修改副本均被拒绝：段缺失、段重复、段错序、模型哈希错误、prompt哈希错误、事件哈希错误、未限定验收的表、负时长、小数时长、改写实测时长、step归属错误。原S6表和历史记录未修改。

## 解释边界与后续

这些时刻是同一固定轨迹的G2模拟值；不是新一次GPU原生请求墙钟，也不证明短段测量达到微秒/亚微秒准确度。S6的波动、分辨率与观测扰动限制继续适用。这里只建立零等待对照，尚未得到G3的HBF等待影响结果。

进入S8时必须读取本批次绑定的相同计算表、事件、输入及M2；实际GPU消费者经同步桥成功等待后继续，并验证数值、依赖、排空及`(T_G3-T_G2)=累计HBF等待`。不能用此次纯记录回放替代S8的真实门控执行。

产物位于批次`G2/`：`tokens.jsonl`、`segments.csv`、`events.jsonl`、`metrics.json`、`selected-callbacks.json`、`zero-access.json`、`audit.json`、`event-clock-audit.json`、`negative-cases.json`、3个`replay-*`目录及`conditions.json`。批次根目录含SHA256索引；仓库内摘要见[验证记录](validation/gpu-s7.json)。

复现入口（使用新的输出目录）：

```powershell
python experiments/gpu_s/s7.py --study output/gpu-s/<new-S7-study-id>
```

逐事件补充核验结果保存于本批次`event-clock-audit.json`；主入口内的逐段、逐token、事件保留及选区审计在每次复现时执行。
