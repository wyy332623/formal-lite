# formal-lite：RTL 形式化验证平台

轻量级 RTL 形式化验证运行器，基于 Python 标准库（Windows 经 WSL 调用，Linux 直接运行）驱动隔离的 OSS CAD Suite（Yosys + SymbiYosys + Z3 / Bitwuzla / ABC PDR）。

## 目录结构

- `run.py`：统一 CLI 入口（`doctor` / `bootstrap` / `list` / `run` / `self-test`）
- `worker.py`：Linux/WSL 端执行器，负责工具链检查、安装与调用 `sby`
- `workspace.json`：WSL 发行版、工具链目录、默认求解器与深度/超时配置
- `toolchain.lock.json`：OSS CAD Suite 归档下载与 SHA-256 校验配置
- `fetch_sources.py` / `sources.lock.json`：按需拉取示例 RTL 上游仓库（`sources/`）
- `cases/`：形式化验证用例（内置 `smoke` 自检用例及 `mul`、`div`、`axi` 示例用例）
- `results/`：每次运行的独立快照、`.sby` 配置、日志、波形（`.vcd`）和 `result.json`（不入 Git）

## 快速开始

环境要求：Python 3.11+；Windows 上需配置 WSL（如 `Ubuntu-22.04`）且 WSL 内有 `/usr/bin/python3`。

```powershell
python run.py bootstrap      # 下载并安装隔离版 OSS CAD Suite 到 ~/.local/share/formal-lite/
python run.py doctor         # 检查 yosys / sby / solver 是否就绪
python run.py self-test      # 运行 smoke 自检（含预期失败的 fault 反例）
python run.py list           # 列出所有可用用例及任务
```

运行具体用例（如需运行 `mul` / `div` / `axi`，先执行 `python fetch_sources.py` 拉取 `sources/`）：

```powershell
python run.py run smoke --task prove
python run.py run mul --task small
python run.py run div --task control
python run.py run axi --task single_prove --depth 16 --timeout 90
python run.py run axi --task bmc --engine "smtbmc z3"
```

## 新增用例

在 `cases/<name>/` 下创建 `case.json` 和验证顶层（harness / properties / assumptions）：

```json
{
  "name": "my_module",
  "top": "my_module_formal",
  "files": [
    {"path": "../../path/to/dut.v", "dest": "rtl/dut.v"},
    {"path": "harness.sv", "dest": "formal/harness.sv"}
  ],
  "include_dirs": ["rtl", "formal"],
  "defines": [],
  "tasks": {
    "bmc": {"mode": "bmc", "depth": 32, "timeout_seconds": 60},
    "prove": {"mode": "prove", "depth": 16, "timeout_seconds": 60, "engine": "abc pdr"},
    "cover": {"mode": "cover", "depth": 32, "timeout_seconds": 60}
  }
}
```

- `files` 中的字符串或对象 `path` 均相对于 `case.json`；`dest` 指定暂存到 `src/` 下的相对路径；`read` 默认对 `.v` / `.sv` 为 `true`，头文件可设为 `false` 仅暂存供 `` `include ``。
- `tasks` 支持任意 SBY 引擎（如 `smtbmc z3`、`smtbmc bitwuzla`、`abc pdr` 等），命令行可通过 `--depth`、`--timeout`、`--engine` 临时覆盖。

## 结果状态说明

| 状态 | 含义 |
| --- | --- |
| `BMC_PASS` | 在指定深度内未发现反例（有界检查，不代表无限周期证明） |
| `PROVED` | 所列断言在当前假设与输入域下获得归纳/PDR 证明 |
| `COVER_REACHED` | 全部覆盖点可达 |
| `FAIL` | 触发断言反例（可在 `results/.../work/engine_0/*.vcd` 查看波形） |
| `COVER_NOT_REACHED_OR_ASSERT_FAILED` | 覆盖点未到达或 cover 过程中断言失败 |
| `UNKNOWN` / `ERROR` / `TIMEOUT` | 未能得出证明结论，不算通过 |
