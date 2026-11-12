# 形式化任务结果索引

源码提交：`10d248abc6af8811e506909dd61cc3ddc498ccaf`。

BMC_PASS 仅限所列深度；PROVED 仅限任务性质与假设；故障注入 FAIL 不表示 DUT 错误；TIMEOUT/NOT_RUN 均未获得证明。

| 模块 | 任务 | 结果 | 深度 | 超时/秒 | 引擎 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| mul | prove | TIMEOUT | 1 | 60 | smtbmc bitwuzla | [记录](evidence/mul/prove/result.json) |
| mul | bmc | NOT_RUN_WITH_CURRENT_INPUTS | — | — | — | — |
| mul | small | PROVED | 1 | 60 | smtbmc z3 | [记录](evidence/mul/small/result.json) |
| mul | corners | PROVED | 1 | 60 | abc pdr | [记录](evidence/mul/corners/result.json) |
| mul | cover | COVER_REACHED | 2 | 60 | smtbmc z3 | [记录](evidence/mul/cover/result.json) |
| mul | fault | FAIL | 2 | 30 | smtbmc z3 | [记录](evidence/mul/fault/result.json) |
| div | control | PROVED | 36 | 90 | abc pdr | [记录](evidence/div/control/result.json) |
| div | bmc | TIMEOUT | 40 | 90 | smtbmc z3 | [记录](evidence/div/bmc/result.json) |
| div | prove | UNKNOWN | 36 | 90 | smtbmc z3 | [记录](evidence/div/prove/result.json) |
| div | small | TIMEOUT | 40 | 90 | smtbmc z3 | [记录](evidence/div/small/result.json) |
| div | zero | BMC_PASS | 40 | 60 | smtbmc z3 | [记录](evidence/div/zero/result.json) |
| div | unit | BMC_PASS | 40 | 150 | smtbmc z3 | [记录](evidence/div/unit/result.json) |
| div | cover | COVER_REACHED | 72 | 90 | smtbmc z3 | [记录](evidence/div/cover/result.json) |
| div | arithmetic_cover | COVER_REACHED | 40 | 90 | smtbmc z3 | [记录](evidence/div/arithmetic_cover/result.json) |
| div | fault | FAIL | 40 | 60 | smtbmc z3 | [记录](evidence/div/fault/result.json) |
| div | corners | BMC_PASS | 40 | 90 | smtbmc z3 | [记录](evidence/div/corners/result.json) |
| div | corner_cover | COVER_REACHED | 40 | 90 | smtbmc z3 | [记录](evidence/div/corner_cover/result.json) |
| axi | bmc | FAIL | 12 | 90 | smtbmc z3 | [记录](evidence/axi/bmc/result.json) |
| axi | single_bmc | NOT_RUN_WITH_CURRENT_INPUTS | — | — | — | — |
| axi | single_prove | PROVED | 16 | 90 | abc pdr | [记录](evidence/axi/single_prove/result.json) |
| axi | stability | PROVED | 16 | 60 | abc pdr | [记录](evidence/axi/stability/result.json) |
| axi | cover | COVER_REACHED | 16 | 90 | smtbmc z3 | [记录](evidence/axi/cover/result.json) |
| axi | delivery | FAIL | 18 | 90 | smtbmc z3 | [记录](evidence/axi/delivery/result.json) |
