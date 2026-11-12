# AXI bridge 形式化用例

验证最新 main 固定快照中的 `axi_bridge`。这是从历史 exp15 接续的独立用例；原 cases/exp15 及其结果不覆盖、不改写。

- 类 SRAM 受理前允许改变或撤回请求；IF 为对齐 word read，MEM 为合法 byte/halfword/word 读写。
- AXI 单拍、OKAY 响应，同 ID 按序；AR/AW/W 任意独立反压，R/B 可同拍。账本检查受理请求、AXI 载荷、返回数据及类 SRAM 完成顺序，不引用 DUT 内部状态。
- general 每端口最多两笔未完成请求；single_* 每端口最多一笔。安全性无 eventual-ready / eventual-response 假设，不证明任意容量或整核行为。
- `delivery` 单独检查 IF 连续响应后的有界排空：没有新受理、待发送请求、AXI token 或通道活动连续三拍后，已返回响应必须全部交付。它不是任意内存延迟下的完成性证明。
- `cover` 启用 STABILITY_ONLY：保留稳定/复位/固定字段断言，移除事务正确性断言，检查合法环境场景是否可达；覆盖通过不等于事务正确。
- 尚不包含自动组合依赖、写后读地址相关阻塞、AXI 错误响应/突发、异步复位及任意队列容量证明。详细输入合同见 assumptions.md。

```powershell
python run.py doctor
python run.py run axi --task bmc
python run.py run axi --task single_prove
python run.py run axi --task stability
python run.py run axi --task delivery
python run.py run axi --task cover
```

`bmc` 的预期仍为 PASS，因此真实设计反例返回非零退出码，不会作为“预期错误”被回归吞掉。STABILITY_ONLY 的证明不含事务内容和响应账本。
