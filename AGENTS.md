# 工作区约定

- 当前 exp15 工作已由用户要求停止并交接。先读 HANDOFF.md；收到明确接续任务后再启动新的验证或升级。

- 先阅读 README.md 和目标 cases/<name>/README.md，运行前用 `python run.py doctor` 检查固定工具链。
- 实验 RTL 是外部输入，运行时复制快照；只有用户明确要求修改实验设计时才编辑外部源码。
- 新 case 应先明确协议、复位、容量、时钟和环境假设；不要用限制 DUT 输出的 assume 代替 assert。
- 类 SRAM 在受理前允许改变/撤回请求；不能误加 AXI 式稳定约束。安全性与完成性任务分别维护。
- 报告保留工具版本、输入 SHA-256、假设、深度与超时。BMC_PASS 不称为无限周期证明，UNKNOWN/ERROR/TIMEOUT 不称为通过。
- 工具入口或结果解释变更后运行 `python run.py self-test`；其中故意损坏任务必须 FAIL 且产生反例波形，整体自检才通过。
- exp15 模板在 RTL、harness、协议假设和性质未完成前保持 enabled=false。
