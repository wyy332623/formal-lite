# 工作区配置验证记录

日期：2026-11-12（Asia/Shanghai）。

- 主机目录：D:/PersonalPrograms/calab/formal-lite，与原实验目录并列。
- 运行环境：WSL 发行版 Ubuntu-22.04，使用 /usr/bin/python3 调用隔离工具链。
- 工具包：OSS CAD Suite 2026-11-12 Linux x64；归档大小750616226字节，SHA-256为346499255e3e5e6e9bf67e1d378a4e6bc249abd3de3b0caf5b57604bc8ba1752，与官方GitHub资产元数据一致。
- doctor：ready=true；Yosys 0.70+385（098e46a36），SBY v0.70-9-g79fc9ed，Z3 4.15.5。

最终自检使用更新后的 run.py/worker.py，结果如下：

| 任务 | 结果 | 结果目录 |
| --- | --- | --- |
| smoke bmc | BMC_PASS，20步 | results/smoke/20261112-230239-bmc-28d92b |
| smoke prove | PROVED | results/smoke/20261112-230243-prove-b40740 |
| smoke cover | COVER_REACHED，生成VCD | results/smoke/20261112-230244-cover-03c34f |
| smoke fault | 按预期FAIL，生成反例VCD | results/smoke/20261112-230245-fault-6b80f2 |

每个目录包含源码快照、SHA-256、生成的SBY配置、工具版本、假设、日志及结果JSON。整体SELF-TEST PASS，最新索引见 results/self-test-latest.json。

另外确认：所有配置JSON可解析，PowerShell入口可列出用例，未配置的exp15被NEEDS_CONFIGURATION阻止且返回码为2。exp15目前只有输入/协议/任务模板，没有接入真实转接桥，因此没有其验证结论。

原实验仓库的tracked文件状态保持操作前已有的README.md、myCPU/stage3_ex.v修改；本次没有修改或提交实验RTL。
