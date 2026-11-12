# exp15 验证设置

当前已接入 `sources/calab-main-10d248a/myCPU/axi_bridge.v`，`enabled=true`。用户已要求停止，接续前先读工作区根目录 HANDOFF.md。工具链自检通过不代表整个转接桥正确。

下列接入步骤已经完成；验证覆盖尚不完整，具体状态见交接文档：

1. 被测 RTL 锁定为 main@10d248a 的 axi_bridge，具体文件清单见 case.json、版本及哈希见 source.json。
2. 明确顶层端口、时钟/复位极性、位宽、读写 ID、单拍传输约束，以及每个接口允许的未完成事务数。
3. 写 environment.sv：只约束外部合法协议行为，允许任意反压。类 SRAM 请求在受理前可以改变/撤回，AXI AW/W 必须允许独立握手。
4. 写 properties.sv：独立记录 req && addr_ok 接受的事务，检查 AXI 载荷、计数、响应归属、反压稳定和写后读阻塞。
5. 写 harness.sv：顶层命名 bridge_formal，实例化 DUT、环境与检查器。使用普通模块连接和时钟块内立即断言，适配开源前端。
6. 更新 assumptions.md，把设计边界和完成性假设写清楚；添加覆盖点检查读写请求和竞争场景确实可达。

建议的第一版任务：

| 类别 | 检查内容 |
| --- | --- |
| Safety | AR/AW/W 在 VALID && !READY 后保持 VALID 和全部载荷；事务不重复、内容正确、响应归属正确；容量边界与写后读阻塞 |
| Cover | 两端同时请求；AW先/W先；长反压后完成；旧响应与新请求同拍；读写并行 |
| Progress（后续单独加入） | 明确外部响应、公平仲裁/竞争流量假设后，证明已接受事务最终完成 |

`case.json` 的 `files` 是输入清单。字符串项默认以 basename 暂存；对象项可指定 `dest`，以保留 include 目录结构；头文件自动仅暂存、不单独 read。顶层是形式化 harness，不是 SoC 顶层。

命令：

```powershell
python run.py run exp15 --task bmc --depth 64
python run.py run exp15 --task prove --timeout 300
python run.py run exp15 --task cover --depth 80
```

本工具没有把“VALID/READY 没有组合依赖”、四态 X/Z 或实现时序自动等同于上述功能证明。前者需另加网表依赖检查，后两者保留仿真/Vivado 检查。

教材定位：§8.4.2，PDF230～231页（书内204～205页）；§8.4.3，PDF232页（书内206页）；§8.5.2，PDF236～237页（书内210～211页）。
