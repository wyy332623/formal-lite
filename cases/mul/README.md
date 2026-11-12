# mul 形式化用例

验证当前 CPU 实际实例化的组合 `mul`，不包含备用厂商 IP。接口、输入域及独立算术参考见 assumptions.md；版本见 source.json。

```powershell
python run.py doctor
python run.py run mul --task prove
python run.py run mul --task small
python run.py run mul --task corners
python run.py run mul --task cover
```

`prove` 检查完整 32 位输入域；`small` 检查所有有符号/无符号 8 位数值；`corners` 是 128 个固定的全位宽边界输入组合。后两者不能替代全域证明。`fault` 故意翻转检查器看到的结果位，验证断言可触发并产生反例。采样断言需要一拍寄存，所以 BMC/fault/cover 深度至少为 2。
