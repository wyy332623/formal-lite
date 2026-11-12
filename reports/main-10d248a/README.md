# main@10d248a 验证报告

被测对象是 calab 最新 main 获取时的提交 `10d248abc6af8811e506909dd61cc3ddc498ccaf`，本轮结束前已再次核对远端 main 未变化。所有 DUT 均未修改。完整任务、深度、超时、引擎、用时见 [INDEX.md](INDEX.md) 和 [results.json](results.json)；各任务 evidence 中保留源码 SHA-256、工具版本、实际假设、SBY 配置、输入快照、日志与波形。文件完整性见 manifest.json。

| 模块 | 实际结果 | 解释 |
| --- | --- | --- |
| mul | small PROVED；corners PROVED；cover COVER_REACHED | small 为全体有符号/无符号 8 位数值；corners 仅 128 组固定的全 32 位边界输入，均不是全部 32 位输入 |
| mul | 全域 prove TIMEOUT（60秒） | Bitwuzla 未完成全域算术证明；不代表 RTL 通过或失败 |
| div | control PROVED | 初始同步复位后的完成时序、取消优先级、结果保持与稳定，后续复位可任意发生；不含算术正确性 |
| div | zero、unit、corners BMC_PASS（40步） | 分别为 y=0、y=1或0xffffffff，以及八组固定边界值；没有长期算术证明，也不覆盖两次完整计算 |
| div | cover、arithmetic_cover、corner_cover COVER_REACHED | 覆盖取消、完成保持、重启、除零、符号溢出等；八个边界向量的完成覆盖都在复位后实际到达，不依赖未初始化 complete |
| div | 全域 bmc TIMEOUT；prove UNKNOWN；small TIMEOUT | bmc 在检查第36步、首次算术完成附近超时；prove 的 basecase 只检查到第35步，归纳失败，因此没有算术证明，归纳波形不是可达设计反例 |
| AXI | single_prove、stability PROVED | single_prove 每端口最多一笔未完成请求，包含事务账本；stability 仅稳定、同步复位和固定字段，无事务账本断言 |
| AXI | bmc FAIL（第9步） | 每端口最多两笔；后发 MEM 写的 B 响应越过较早、尚未返回的 load，触发完成归属/数据断言 |
| AXI | delivery FAIL（第13步） | 只发 IF 请求，允许两笔；连续两个 RID=0 的 R 响应只交付一次 IF 完成，全部 AXI 响应已返回后仍无法排空 |
| AXI | cover COVER_REACHED | 合法环境下竞争、AW/W独立握手、反压、连续响应及R/B同拍等可达；该任务明确移除了事务正确性断言，不等于事务正确 |

两项 AXI 缺陷都需要同端口两笔未完成请求；不能据此声称当前 CPU 的单请求使用方式一定出错。single_prove 的结论也只覆盖当前假设下的所列安全性质，不是一般完成性、组合依赖或任意容量证明。

[确定性回放](evidence/axi/replay/simulation.log) 独立于 formal harness，确认了上述两类缺陷。回放基于 Yosys 从原始 RTL 导出的网表，再由 Icarus 执行端口测试台；原源码 rd_busy 未声明，Yosys 将其推断为寄存器，因此未声称原 RTL 可直接在 Icarus 编译。

mul/fault 和 div/fault 均按预期 FAIL 并产生 VCD，这是检查器敏感性测试，不是额外 DUT 缺陷。公共 [self-test](self-test.json) 四项全部符合预期。quick 回归整体非零是因为两项真实 AXI FAIL；arithmetic 整体非零是因为 TIMEOUT/UNKNOWN；checkers 整体通过。不把未完成任务或已知缺陷改标为设计通过。

仍未覆盖：乘除法完整 32 位域的长期算术正确性；AXI 一般完成性、组合依赖、地址相关写后读阻塞、错误响应/突发；四态 X/Z、异步复位电气行为、整核集成、Vivado时序和板卡。未运行的可选任务会在索引中明确显示 NOT_RUN_WITH_CURRENT_INPUTS。

源码恢复使用 sources.lock.json 显式的 CRLF 签出策略，分别记录工作树输入与 Git 原始内容哈希。Windows、WSL 的新克隆均校验成功；错误输入哈希会被拒绝且不修改原目录。formal-lite 自身禁用自动换行转换，以保持证据字节不变。
