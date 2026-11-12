# formal-lite：个人形式化验证工作区

**当前任务已按用户要求停止。接续 exp15 验证前先读 [HANDOFF.md](HANDOFF.md)。**

位置：`D:/PersonalPrograms/calab/formal-lite`，与 `exp5`～`exp14` 等实验目录并列。

这是独立的命令行工作区，不依赖实验 SoC、func、golden trace、Vivado 或板卡。输入为 RTL 文件清单、形式化顶层和明确的验证约定；Python 只做配置、暂存、调用及结果汇总。

## 打开与运行

用 VS Code 打开 `formal-lite.code-workspace`，终端进入本目录。Windows 主机只需 Python 标准库和现有 WSL；固定使用 `Ubuntu-22.04` 发行版。

```powershell
python run.py doctor
python run.py list
python run.py self-test
python run.py run smoke --task bmc --depth 64
python run.py run smoke --task prove
python run.py run smoke --task cover
```

也可使用 `./formal.ps1 doctor`。VS Code 的“运行任务”已配置 doctor、自检和 smoke 的 prove/cover。

## 工具链

`workspace.json` 配置发行版、求解器、默认深度/超时及实验 RTL 根路径。`toolchain.lock.json` 锁定官方 OSS CAD Suite 2026-11-12 Linux x64 归档、大小和 GitHub 提供的 SHA-256。

`python run.py bootstrap` 下载并校验归档，然后安装到 WSL 用户目录 `~/.local/share/formal-lite/toolchains/2026-11-12/oss-cad-suite`。工具只在子进程中使用该路径，不修改系统 Yosys 或全局 PATH；下载缓存在本目录 `.cache/`。归档约716 MiB，安装后可删除下载缓存以节省主机磁盘；再次 bootstrap 时会重新下载。

安装与验证记录位于 WSL 工具链父目录的 installation.json。Windows/WSL 之间通过 argv 传路径，不使用拼接 shell 命令。

## 输入

每个 `cases/<name>/case.json` 包含：enabled、top、files、include_dirs、defines、tasks、assumptions_file。各任务配置 mode、depth、timeout_seconds 和可选 defines。输入文件路径相对 case.json 所在目录，支持引用工作区外的 RTL；只复制输入进行验证。

每次运行在 `results/<case>/<时间>-<task>-<随机后缀>/` 创建独立结果目录，保存源文件快照/SHA-256、生成的 .sby、工具版本、假设清单、日志、result.json、summary.md 及 SBY 波形。旧结果不被覆盖。

WSL 启动诊断保存到 `.cache/runtime-diagnostics.log`；执行失败时也显示在终端。常规命令输出采用 UTF-8。

## 结果含义

| 状态 | 含义 |
| --- | --- |
| BMC_PASS | 配置深度内未找到反例，不是无限周期证明 |
| PROVED | 配置的性质在所列假设下获得证明 |
| COVER_REACHED | 在配置深度内到达全部覆盖点 |
| FAIL | 找到断言反例 |
| COVER_NOT_REACHED_OR_ASSERT_FAILED | 覆盖未完成或覆盖任务中的断言失败，查看日志 |
| UNKNOWN / ERROR / TIMEOUT | 没有获得证明，不作为通过 |

`self-test` 包含 bmc、prove、cover 和一个故意损坏的 fault 用例。fault 必须显示 FAIL 并生成 VCD，整体自检才通过。`expected_result_observed=true` 只表示符合任务预期，不能把预期的 FAIL 解释为设计通过。

## exp15

`cases/exp15` 已接入固定版本 main@10d248a 的 axi_bridge。当前已有两笔未完成请求场景的 BMC 反例、部分稳定性性质的 PDR 证明，以及一次单笔场景超时；不能宣称整个模块正确。具体证据、范围和待办见 HANDOFF.md。

## 官方参考

- https://github.com/YosysHQ/oss-cad-suite-build
- https://yosyshq.readthedocs.io/projects/sby/en/latest/quickstart.html
- https://yosyshq.readthedocs.io/projects/sby/en/latest/reference.html
- https://yosyshq.readthedocs.io/projects/sby/en/latest/verilog.html
