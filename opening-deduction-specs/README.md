# 开洞扣减测例说明（opening-deduction-specs）

本目录说明 `backend/app/tests/test_openings_clamp.py` 的设计。
选用题目特征目录名，与邻题的通用文档目录（如 `docs/`）错开，避免合并时撞名。

## 覆盖的三条不变式

固定房间长 5 m、宽 4 m、高 2.8 m，毛墙面积恒为 `2 × (5 + 4) × 2.8 = 50.4 m²`。

| 测例 | 推进过程 | 守住的性质 |
| --- | --- | --- |
| `test_no_openings_net_equals_gross` | 无开洞 | 净面积 == 毛面积，开洞扣除为 0 |
| `test_adding_window_is_monotonic_and_deduction_matches` | 追加一扇 1.5 × 1.4 窗（2.1 m²） | 追加后净面积 ≤ 追加前；`openings_m2 == gross_m2 − net_m2`（净 48.3） |
| `test_deduction_floors_net_at_zero` | 继续追加至总扣除 62.1 > 50.4 | 净面积触底为 0，不得为负 |
| `test_every_step_is_monotonic_until_floor` | 0 → 2.1 → 22.1 → 42.1 → 62.1 逐级追加 | 每一步净面积单调不增，末步触底 |

## 种子房几何

与 `backend/app/seed.py` 对齐，并外推一种多洞户型：

- **客厅（单门单窗）**：5 × 4 × 2.8；门 0.9 × 2.1、窗 1.5 × 1.4 → 毛 50.40、扣 3.99、净 46.41。
- **卧室（多种洞）**：4 × 3.2 × 2.8；一门 0.9 × 2.1 + 两窗 1.8 × 1.5、1.2 × 1.5 → 毛 40.32、扣 6.39、净 33.93。
- **两门三窗**：6 × 3 × 2.7 → 毛 48.60、扣 10.98、净 37.62。

`test_seeded_room_geometries` 断言毛/扣/净三个数及「净 == 毛 − 扣」口径；
`test_estimate_pipeline_preserves_seeded_net` 再经 `estimate_room` 组合引擎走一遍，
确认升数链路不改净面积口径。

## 失败消息点名规则

引擎回归时，消息前缀直接指出问题类别，便于定位：

- **净面积回升**：追加开洞后净面积不降反升；
- **扣除口径错误**：`openings_m2` 不等于「毛面积 − 净面积」；
- **触底失败**：开洞合计已超过毛面积，净面积却未归零（出现负值）。

## 运行

```bash
cd backend
python -m pytest app/tests/ -v
```

原有 `test_calc.py` 中客厅净面积（46.41）与升数（11.6 L）数字测例保持不动，
新测例独立放在 `test_openings_clamp.py`。
