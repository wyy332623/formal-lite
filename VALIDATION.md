# 验证记录

本轮按用户授权接续历史 exp15，为 div、mul、AXI 建立独立用例，并将工作区纳入 Git、保存到 GitHub。被测源码没有修改。

calab main 获取时为 `10d248abc6af8811e506909dd61cc3ddc498ccaf`；三个 RTL 的锁定哈希见 [sources.lock.json](sources.lock.json)。实际状态、深度、超时、引擎及精简原始证据见 [结果索引](reports/main-10d248a/INDEX.md) 和 [结果 JSON](reports/main-10d248a/results.json)。

| 对象 | 验证支持 | 结论边界 |
| --- | --- | --- |
| mul | 独立算术参考、所有有符号/无符号 8 位数值、128 个固定全位宽边界组合、覆盖及故障注入 | 局部通过不代表全部 32 位输入已证明；全域超时保持未完成 |
| div | 独立受理/32 次迭代/完成保持模型，取消、后续任意复位、重启，除法/取模算术参考，受限域与八组边界值 | 控制证明不含算术；40 步 BMC 不称为长期证明，也不覆盖两次完整除法 |
| AXI | 事务账本、载荷、数据、完成顺序、独立反压、单/双请求范围、响应排空与覆盖 | 单请求安全性证明不含一般完成性、组合依赖、地址相关读写阻塞或任意容量 |

AXI general BMC 复现写响应越过较早 MEM load 的错误；IF-only delivery BMC 找到连续两个取指 R 响应只产生一次完成通知的错误。两者都需要同端口两笔未完成请求。确定性测试台在 Yosys 导出网表上的 Icarus 回放再次确认，见 [回放日志](reports/main-10d248a/evidence/axi/replay/simulation.log)。该回放独立于 formal harness，但不证明原 RTL 可直接在 Icarus 编译：rd_busy 未声明，由 Yosys 推断为寄存器。

工具包为 OSS CAD Suite 2026-11-12，WSL Ubuntu-22.04；Yosys 0.70+385、SBY v0.70-9-g79fc9ed、Z3 4.15.5。实际使用的 ABC/Bitwuzla 版本在任务 result.json 中。doctor ready=true；公共自检的 bmc/prove/cover 及故意失败反例必须全部符合预期，最新索引见 [self-test.json](reports/main-10d248a/self-test.json)。

未修复、提交或推送 calab RTL，没有将 UNKNOWN/ERROR/TIMEOUT 计为通过。实际设计反例仍令 regress 返回非零退出码。历史记录见 [HANDOFF.md](HANDOFF.md)；原“exp15 未接入 RTL”的说法只适用于初始模板阶段，已不适用于当前状态。
