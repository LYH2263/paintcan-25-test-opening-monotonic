# 开洞单调性与扣洞上界测例说明

对应测例文件：`backend/app/tests/test_openings_monotonic.py`
被测引擎：`backend/app/engines/wall_area.py`（`wall_area`）、
`backend/app/engines/estimate.py`（`estimate_room` 组合层）

## 背景

墙面计算的核心恒等式为：

```
gross_m2     = 2 × (长 + 宽) × 高
openings_m2  = Σ(洞宽 × 洞高)
net_m2       = max(0, gross_m2 − openings_m2)
```

围绕该恒等式存在三类典型回归，本测例逐一钉死。

## 固定房几何

全文件统一使用 长 6m × 宽 4m × 高 2.5m 的固定房间，毛面积恒为 50.0m²。
固定几何后，追加开洞引起的净面积变化只可能来自扣除逻辑本身，便于断言单调性。

## 覆盖场景

| 测例 | 验证点 |
| --- | --- |
| `test_no_openings_net_equals_gross` | 无开洞：净面积 == 毛面积，扣除为 0 |
| `test_net_does_not_rise_after_window` | 追加一扇窗后净面积 ≤ 追加前，且必须严格下降 |
| `test_deduction_equals_gross_minus_net` | 触底前 `openings_m2 == gross_m2 − net_m2` |
| `test_monotonic_along_each_added_window` | 连续追加 5 扇窗（每扇 12m²），逐步不回升；触底前逐步校验扣除口径 |
| `test_net_floors_at_zero_when_deduction_exceeds_gross` | 两扇各 30m²（合计 60 > 50），净面积触底为 0 |
| `test_single_giant_opening_floors_at_zero` | 单扇洞即超过毛面积，同样触底为 0 |
| `test_single_door_single_window` | 单门单窗三种尺寸组合（常规、高门小窗、宽扁大窗） |
| `test_varied_opening_geometries` | 多种洞几何种子：方洞、窄高洞、宽扁洞、三者混合、混合后累计超毛面积（50.30 > 50）触底 |
| `test_estimate_engine_same_monotonic_floor` | 经 `estimate_room` 组合层复验：升数不回升、净面积触底后升数为 0 |

## 失败消息口径

为便于一眼定位回归，断言失败消息点名缺陷类别：

- **净面积回升**：追加开洞后 `net_m2` 反而增大，消息以「净面积回升」开头；
- **扣除口径**：`openings_m2` 不等于 `gross_m2 − net_m2`，消息以「扣除口径失败」开头；
- **触底失败**：扣除超过毛面积后 `net_m2` 未归零（甚至为负），消息以「触底失败」开头。

三类消息均带上实际值与期望值，无需再翻代码定位。

## 与既有测例的关系

`backend/app/tests/test_calc.py` 中的客厅净面积（50.4 / 46.41）与升数（11.6L）
数字测例保持原样、未做任何改动；本文件为新增独立模块，二者互不依赖。

## 运行

```bash
cd backend
pytest app/tests/
```

## 设计说明（为何这样断言）

- 浮点比较一律使用 `pytest.approx`，避免 round 后二进制尾数造成的偶发失败。
- 触底后不再校验 `openings_m2 == gross − net`：触底时引擎记录的是**原始扣除量**
  （可大于毛面积），该恒等式只在触底前成立，测例显式按 `net > 0` 分支处理。
- 单调断言同时要求「严格下降」而非仅「不增」，防止追加非零窗洞被静默忽略的缺陷漏网。
