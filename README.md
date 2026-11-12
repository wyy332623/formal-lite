# formal-lite：多模块 RTL 形式化验证平台

公共 Python 运行器负责固定工具链、复制源码快照、调用验证工具、保存日志与反例；每个模块独立维护接口约定、环境假设和性质。无需启动完整 SoC、Vivado、func 或板卡。

当前支持 [calab](https://github.com/wyy332623/calab) main 获取时的固定提交 `10d248abc6af8811e506909dd61cc3ddc498ccaf`：

| 用例 | 对象与检查范围 |
| --- | --- |
| [mul](cases/mul/README.md) | 实际 CPU 组合乘法器：有符号/无符号 64 位乘积，全域任务、8 位数值域、128 个固定全位宽边界组合 |
| [div](cases/div/README.md) | 手写除法器：算术参考、32 次迭代时序、取消、完成保持、复位、重启及边界任务 |
| [axi](cases/axi/README.md) | 类 SRAM → AXI：事务内容、返回数据/顺序、独立反压、单/双请求范围及连续响应排空 |
| smoke | 公共工具链自检，包括必须失败并产生波形的故障任务 |
| [exp15](cases/exp15/README.md) | 历史用例；后续工作使用 axi，不覆盖原交接及证据 |

**接入支持不代表设计全部正确。** 结论与范围见 [VALIDATION.md](VALIDATION.md) 和 [版本化结果索引](reports/main-10d248a/INDEX.md)。AXI 双请求场景存在反例；全域算术超时不能用局部通过代替。

## 从云端恢复

Windows 主机需要 Python 3.11+、Git、WSL Ubuntu-22.04；WSL 的 /usr/bin/python3 也需 3.11+（本机为 3.12.3）。运行器仅使用 Python 标准库；Linux 也可直接使用 Python 和配置的隔离工具链。

```powershell
git clone https://github.com/wyy332623/formal-lite.git
cd formal-lite
python fetch_sources.py
python run.py bootstrap
python run.py doctor
python run.py self-test
python run.py list
```

`fetch_sources.py` 按 [sources.lock.json](sources.lock.json) 获取固定提交，显式使用 CRLF 签出以复现历史输入字节，并分别校验三个 RTL 的工作树及 Git 原始内容 SHA-256。现存目录若提交或哈希不匹配，会报错而不改写；不会自动跟踪新的 main。检查新版上游时应另建快照并更新锁定信息，旧证据保持不变。

`bootstrap` 校验并安装官方 OSS CAD Suite 2026-11-12 Linux x64（约716 MiB），归档大小和 SHA-256 见 toolchain.lock.json。工具安装到 WSL 用户目录 `~/.local/share/formal-lite/toolchains/2026-11-12/oss-cad-suite`，只在子进程中使用，不改系统 PATH；安装记录在父目录 installation.json。配置入口为 workspace.json。

## 运行与批量回归

```powershell
python run.py run mul --task small
python run.py run div --task control
python run.py run div --task corners
python run.py run axi --task single_prove
python run.py run axi --task bmc
python regress.py --profile quick
python regress.py --profile arithmetic
python regress.py --profile checkers
python replay_axi.py
```

任务清单见 regression.json。`quick` 包含局部算术、控制、覆盖和 AXI；`arithmetic` 尝试昂贵的全域/受限域算术；`checkers` 故意翻转检查器看到的结果，必须 FAIL 且有波形。回归继续收集所有任务结果，真实设计 FAIL、TIMEOUT、ERROR 会使整体退出非零；不会把已知设计错误改成“预期失败”使回归变绿。

`replay_axi.py` 使用独立、确定性的端口测试台重现两个 AXI 反例。先由 Yosys 从未修改的 RTL 导出网表，再由 Icarus 仿真；原 RTL 的 rd_busy 未声明，因此不能称为原源码在 Icarus 直接编译通过。命令成功表示重现了缺陷，不表示 DUT 正确。

也可使用 `./formal.ps1` 或 VS Code 的 formal-lite.code-workspace。

## 接入其他模块

每个 `cases/<name>/` 包含 README.md、case.json、assumptions.md 和形式化顶层；推荐 source.json 锁定仓库、提交、模块及哈希。先明确时钟、复位、受理/完成协议、容量、算术边界和环境假设，再写独立参考及断言。类 SRAM 请求受理前允许改变/撤回；不要用 assume 限制 DUT 输出来绕过错误。安全性、完成性分别维护，并用覆盖检查场景非空性。

case.json 指定 enabled、top、files、include_dirs、defines、assumptions_file、tasks；任务指定 mode、depth、timeout_seconds、defines 和可选 engine。支持 abc pdr 及 smtbmc z3/boolector/yices/bitwuzla。输入路径相对 case.json；文件对象的 dest 保留暂存结构，read=false 仅暂存。只复制输入，不修改实验 RTL。

## 结果及版本化证据

每次在 `results/<case>/<时间>-<task>-<后缀>/` 保存独立的源码快照/SHA-256、提交信息、宏、工具版本、引擎、假设、深度、超时、SBY、日志、结果及波形。source.json 存在时运行器会拒绝哈希不匹配的 DUT。doctor 检查固定工具包，实际运行额外检查所选引擎。WSL 启动诊断保存到 .cache/runtime-diagnostics.log。

| 状态 | 含义 |
| --- | --- |
| BMC_PASS | 所列深度内未找到反例，不称为无限周期证明 |
| PROVED | 所列性质在所列假设、输入域内获得证明 |
| COVER_REACHED | 全部所列覆盖点可达，不表示完整功能正确 |
| FAIL | 断言反例；故障注入任务必须单独识别 |
| COVER_NOT_REACHED_OR_ASSERT_FAILED | 覆盖未完成或覆盖中的断言失败，需查日志 |
| UNKNOWN / ERROR / TIMEOUT | 未获得证明，不算通过 |

`expected_result_observed=true` 仅表示符合任务预期。工具入口或结果解释变更后，必须运行 self-test；故意损坏任务必须 FAIL 并有 VCD，整体才算通过。

```powershell
python export_report.py
```

导出器仅收集匹配当前 RTL、harness、假设和任务设置的结果，缺失项显示 NOT_RUN_WITH_CURRENT_INPUTS。reports 保存精简原始记录、输入快照、波形、工具版本和文件哈希清单。大体积 results、工具缓存、上游 Git 克隆不进本项目 Git。历史 [HANDOFF.md](HANDOFF.md) 描述先前暂停时刻，不是当前任务状态。

## 版本管理

本工作区通过 .gitattributes 禁用 Git 自动换行转换，确保 harness、配置与证据的 SHA-256 在云端往返后不变。上游输入克隆另按 sources.lock.json 的显式签出策略复现历史字节。

本地 main 跟踪 [wyy332623/formal-lite](https://github.com/wyy332623/formal-lite) 的 main；被测 calab 是独立输入仓库。本项目的提交和推送不会修改被测 RTL 仓库。

## 官方参考

- [OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build)
- [SBY quickstart](https://yosyshq.readthedocs.io/projects/sby/en/latest/quickstart.html)
- [SBY reference](https://yosyshq.readthedocs.io/projects/sby/en/latest/reference.html)
