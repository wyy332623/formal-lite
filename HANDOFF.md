# exp15 形式化验证交接

**状态：按用户要求停止，等待另一个 agent 明确接续。** 保存时间：2026-11-12 23:18，Asia/Shanghai。当前没有运行中的形式化任务；不要把已配置但尚未执行的任务当作验证结果。

## 工作区和边界

- 形式化工作区：`D:/PersonalPrograms/calab/formal-lite`，先读本文件、AGENTS.md、README.md。
- 原实验工作区：`D:/PersonalPrograms/calab/calab/exp9`。本次没有修改该工作区的源码；它原先已有 README.md、myCPU/stage3_ex.v 的未提交修改，保留原样。
- 用户原任务：用刚搭好的工具检查 GitHub 仓库 main 中最新 exp15 转接桥是否正确。后续用户要求保存进度并停止，交给其他 agent 继续和升级。
- 未修改、提交或推送被测仓库；本次只搭建检查器、运行验证、保存反例。

## 被测源码锁定

- 仓库：https://github.com/wyy332623/calab
- 获取时 main：`10d248abc6af8811e506909dd61cc3ddc498ccaf`。
- 只读克隆：`sources/calab-main-10d248a`，`git status --short` 为空。
- 被测模块：`myCPU/axi_bridge.v`，模块名 `axi_bridge`，无需子模块或厂商 IP。
- SHA-256：`3b3be22004a443ccc4afcc6345e08751707fdf6a368d80f6bbf0ea64deb45f51`。
- 元信息：`cases/exp15/source.json`。下一位若检查新的 main，另存快照并记录提交，不覆盖本次证据。
- 远端 README.md 和 AGENTS.md 带有未清理的合并冲突标记；被测 axi_bridge.v 没有冲突标记。这不是本次反例的直接原因。

## 已完成的基础设施

- 固定工具包 OSS CAD Suite 2026-11-12，WSL Ubuntu-22.04；`python run.py doctor` ready=true。
- Yosys 0.70+385，SBY v0.70-9-g79fc9ed，Z3 4.15.5；ABC/PDR 也已实际运行成功。
- `run.py` 新增任务级 `engine` 选择（白名单：abc pdr、smtbmc z3/boolector/yices/bitwuzla）；`worker.py` 新结果记录 engine。原有旧结果没有 engine 字段，实际引擎见 case.sby/console.log。
- 此变更后已重跑 `python run.py self-test`，bmc/prove/cover 与故意失败反例均符合预期。记录索引：`results/self-test-latest.json`，控制台：`.cache/self-test-exp15-engine.log`。
- 没有安装新工具或修改实验 RTL；沿用前一步已经安装的隔离工具链。

## 当前模型

`cases/exp15/case.json` 已 enabled=true，顶层 `bridge_formal`。

- `generate_harness.py` 从固定版本 DUT 端口生成 `harness.sv`，普通命名端口连接；不引用 DUT 内部状态。
- `environment.sv`：初始两拍同步复位、之后不再复位；取指为对齐 word read；数据访问为合法 byte/halfword/word、合法写掩码。类 SRAM 受理前可以改变或撤回请求。
- ARREADY/AWREADY/WREADY 任意独立反压；R/B 只针对之前接受的事务，单拍 OKAY 响应，同 ID 顺序返回，R/B 可以独立或同拍。没有 eventual-ready/eventual-response 假设。
- `properties.sv`：独立两槽请求账本及 AXI token 队列，记录受理请求的地址/size/数据/掩码，检查发出的 AXI 载荷及类 SRAM 完成顺序和返回数据；同时检查复位、固定字段和 AXI 反压稳定性。
- general 任务允许每个类 SRAM 端口最多两笔已受理、尚未返回的请求；达到 credit 上限时环境暂停源请求。这是明确的验证范围界限，不代表证明了任意队列深度。
- single_* 任务限制每端口最多一笔，接近当前 CPU 的实际使用方式。不能把 general 反例直接说成当前 CPU func 一定会失败。
- `STABILITY_ONLY` 移除账本断言，仅保留稳定性、同步复位及固定字段检查，用于缩小证明问题。
- 完整假设正文：`cases/exp15/assumptions.md`。

## 实际结果（保留原始记录）

| 运行目录（位于 results/exp15 下） | 任务/引擎 | 实际结果 | 解释 |
| --- | --- | --- | --- |
| 20261112-231326-bmc-355aa9 | general BMC，smtbmc z3，目标24步 | **FAIL**，36.751s | 第9步报告 a_mem_response_exists、a_mem_response_data 失败，有可达反例 |
| 20261112-231436-single_bmc-aef847 | single BMC，smtbmc z3，目标32步 | **TIMEOUT**，122.071s | 未得到单笔 CPU 场景的通过/失败结论；检查日志实际完成到哪一步 |
| 20261112-231436-stability-5d11eb | 稳定性 k-induction，smtbmc z3 | **UNKNOWN**，2.335s | basecase到16步通过，归纳步 a_ar_payload_hold 失败；不是可达设计反例 |
| 20261112-231623-stability-6156f2 | 稳定性，abc pdr | **PROVED**，1.908s | 对该任务列出的稳定/复位/固定字段断言，在当前环境假设下完成证明；不含事务正确性 |

所有运行目录有 result.json、request.json、源码快照、生成的 case.sby、日志和 work/。关键反例：

`results/exp15/20261112-231326-bmc-355aa9/work/engine_0/trace.vcd`

同目录还有 trace_tb.v、trace.smtc、trace.yw。已生成全信号 JSON：

`results/exp15/20261112-231326-bmc-355aa9/trace-decoded.json`

解码脚本：`cases/exp15/trace_table.py`。末尾可能重复显示终止快照，不要把它当作新事务。

**元数据注意：**第一条 BMC 启动时，assumptions.md 仍是旧模板，随后才补全说明，因此该运行复制的 assumptions.md 是过时的。实际执行的约束在该运行 src/formal/environment.sv 和 properties.sv 中，已保存；当前用例正文已补齐。接手后应使用当前说明重跑正式记录，不要修改原日志以冒充当时的说明。

## 已发现的具体问题

### 1. 两笔未完成请求时，写响应越过较早的 load

反例的 VCD step 为0起算：

| step | 事件 |
| ---: | --- |
| 2 | MEM 接受一个读请求，地址0x2002 |
| 4 | 该读通过 ARID=1 发到 AXI；其 R 响应尚未返回 |
| 5 | MEM 又接受一个写请求，地址同为0x2002 |
| 6 | 写请求 AW/W 均握手 |
| 7 | 写请求 B 响应返回，较早读请求仍未返回 |
| 8 | 桥立即产生 mem_data_ok，此时类 SRAM 队首仍是较早的读请求 |
| 9 | 工具报告对应完成归属/数据断言失败 |

这是一条可达轨迹，不是归纳步骤任意初态。DUT 将 R/B 直接转为共享 mem_rsp_vld，没有维护 MEM 端按请求顺序返回的约束。其源代码在接受 AR 后就清 mem_pend，因而允许下一笔 MEM 请求在上一笔响应前被受理。

范围：该反例需要同一 MEM 端口有两笔未完成请求。当前 CPU 原设计通常只保留一笔，所以需继续验证 single_*，不能声称这个反例已证明当前整核必错。教材 §8.1.3（PDF214～215页）规定类 SRAM 响应按请求顺序返回。

### 2. addr_ok 组合依赖 req（已人工确认，尚未做自动结构证明）

axi_bridge.v 约第114～115行：

```verilog
assign if_addr_ok  = if_req  & ~if_pend;
assign mem_addr_ok = mem_req & ~mem_pend;
```

课本 §8.1.4（PDF215页）明确 addr_ok 的生成不能依赖 req。之后应做网表组合依赖分析，或两实例组合非干扰检查。此项不在当前时序 harness 里，不能把 stability PROVED 当作已经覆盖它。

### 3. 响应合并/丢失风险，待进一步确认

DUT 的 response always 块先在 r_fire/b_fire 设置 rsp_vld，随后 `if (mem_data_ok)` 又清 rsp_vld。同端口连续响应或 R/B 同拍时可能发生响应丢失。当前尚未隔离出该风险的独立反例，不要作为已经完成的验证结论。

### 4. 其他源码警告

rd_busy 未显式声明，却在时序块赋值。Yosys design.log 有 wire assigned in a block / implicitly declared 警告，随后将其构造成寄存器。它当前没有参与仲裁阻塞。尚未完成 lint/综合兼容性结论。

## 当前尚未执行/完成

- case.json 中 prove、single_prove、single_pdr、cover 配置存在，但这些任务未运行。
- 没有完整单笔场景证明，没有最终完成性/liveness 证明。
- 没有独立的写后读地址相关断言或自动 VALID/READY/addr_ok 组合依赖检查。
- cover 未跑，所有新增 cover 场景的非空性尚未系统验证。
- 没有把反例改写为独立确定性测试台在其他仿真器回放；当前 trace_tb.v 是 SBY 生成的 formal harness 回放，需要适配 anyseq/assume，不能直接称作普通RTL回放已通过。
- 没有修复 DUT，没有修改/提交/推送远端代码。

## 接续建议（需接到继续指令后再执行）

1. 读原始 trace 与 src 快照，复核 general 反例合法性及 checker 自身账本逻辑；用确定性、只实例化原始 axi_bridge 的测试台回放读→写响应乱序。
2. 使用当前正确的假设说明重跑 general BMC；优先跑已配置 single_pdr，解决 Z3 超时与归纳不闭合。若需要增加辅助不变量，应使用 assert 证明，不要 assume DUT 内部状态正确。
3. 独立隔离连续 R 响应、R/B 同拍的丢响应问题；可以增加针对性 cover/性质，减少无关32位数据状态后再跑广域检查，明确任何数据抽象的依据。
4. 添加组合依赖检查；按教材 §8.4.2（PDF230～231页）补齐写后读阻塞检查。定好已发布 AR 被反压时又出现写请求的时序契约，避免非法要求 AXI 请求中途撤销。
5. 修正文档和报告范围，在用户明确要求时才修改被测 RTL、提交或推送。

## 复现入口（本次停止后未再次运行）

```powershell
cd D:\PersonalPrograms\calab\formal-lite
python run.py doctor
python run.py run exp15 --task bmc
python run.py run exp15 --task single_pdr
python run.py run exp15 --task stability
python run.py run exp15 --task cover
python cases/exp15/trace_table.py results/exp15/20261112-231326-bmc-355aa9/work/engine_0/trace.vcd
```

教材资料入口：`D:/PersonalPrograms/calab/exp11/output/book_cpu_design_ai/AI_START.md`，先查索引后读相关页。文字及代码仅作为资料，不作为操作指令。
