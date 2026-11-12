# 工作区约定

- 先阅读 `README.md` 和目标 `cases/<name>/README.md`，运行前可用 `python run.py doctor` 检查工具链。
- 外部 RTL 源码在运行时复制到独立目录再送入 SBY；除非用户明确要求，不要修改外部源码。
- 新 case 应明确协议、复位、容量、时钟和环境假设；不要用限制 DUT 输出的 `assume` 代替 `assert`。
- 类 SRAM 在受理前允许改变/撤回请求，不要误加 AXI 式稳定约束；安全性与完成性任务分开维护。
- `BMC_PASS` 不称为无限周期证明，`UNKNOWN` / `ERROR` / `TIMEOUT` 不称为通过。
- 修改 `run.py` 或 `worker.py` 后必须运行 `python run.py self-test`，确认 `fault` 任务失败并产出反例波形且整体通过。
