# div 形式化用例

验证手写 32 位迭代除法器，独立建模受理、32 次迭代、完成保持、撤请求、取消、复位及重新启动；不修改或引用 DUT 内部状态。完整约定见 assumptions.md。

```powershell
python run.py doctor
python run.py run div --task control
python run.py run div --task corners
python run.py run div --task corner_cover
python run.py run div --task bmc
python run.py run div --task zero
python run.py run div --task unit
python run.py run div --task small
python run.py run div --task cover
```

`control` 不含算术正确性。`bmc` 深度必须覆盖启动后的 32 次迭代，默认 40 步；较浅结果可能根本没有检查到完成。`prove` 尝试全域算术证明；`zero`、`unit`、`small`、`corners` 仅检查各自说明的受限输入域。`corners` 是八组明确输入/结果，BMC 检查 40 步；`corner_cover` 要求八组都能在复位后真正完成。40 步不覆盖两次完整除法，不应视为长期算术证明。除零及 INT_MIN/-1 的结果按当前 RTL 明确写入约定。
