"""开洞单调性与扣洞上界测例。

固定房间长宽高，逐扇追加开洞，验证：
1. 无开洞时净面积 == 毛面积；
2. 追加一扇窗后净面积不回升（开洞单调不增）；
3. 开洞扣除口径：openings_m2 == gross_m2 - net_m2（触底前）；
4. 扣除总量超过毛面积时净面积触底为 0，不得为负。

另覆盖单门单窗组合与多种洞几何（方洞、窄高洞、宽扁洞）。
原有客厅净面积与升数数字测例见 test_calc.py，本文件不触碰。
"""
import pytest

from app.engines.estimate import estimate_room
from app.engines.wall_area import wall_area

# 固定房间：长 6m × 宽 4m × 高 2.5m，毛面积 = 2*(6+4)*2.5 = 50.0
L, W, H = 6.0, 4.0, 2.5
GROSS = 2 * (L + W) * H


def test_no_openings_net_equals_gross():
    """无开洞：净面积必须等于毛面积，扣除为 0。"""
    a = wall_area(L, W, H, [])
    assert a["gross_m2"] == pytest.approx(GROSS)
    assert a["openings_m2"] == pytest.approx(0.0)
    assert a["net_m2"] == pytest.approx(a["gross_m2"]), "无开洞时净面积不等于毛面积（扣除口径失败）"


def test_net_does_not_rise_after_window():
    """追加一扇窗后净面积不得大于追加前（开洞单调不增）。"""
    before = wall_area(L, W, H, [])
    after = wall_area(L, W, H, [{"w": 1.2, "h": 1.5}])
    assert after["net_m2"] <= before["net_m2"], (
        f"净面积回升：追加窗之前 {before['net_m2']}，追加后 {after['net_m2']}"
    )
    assert after["net_m2"] < before["net_m2"], "追加非零窗洞后净面积应下降，否则扣除未生效"


def test_deduction_equals_gross_minus_net():
    """追加一扇窗后，开洞扣除必须等于毛面积减净面积。"""
    window = {"w": 1.2, "h": 1.5}
    a = wall_area(L, W, H, [window])
    expected_hole = window["w"] * window["h"]
    assert a["openings_m2"] == pytest.approx(expected_hole)
    assert a["openings_m2"] == pytest.approx(a["gross_m2"] - a["net_m2"]), (
        f"扣除口径失败：openings_m2={a['openings_m2']} != "
        f"gross_m2({a['gross_m2']}) - net_m2({a['net_m2']})"
    )


def test_monotonic_along_each_added_window():
    """连续追加窗：每一步净面积都不得回升，且触底前扣除口径恒等。"""
    # 每扇 3m × 4m = 12m²；毛面积 50m²，第 5 扇后累计 60 > 50 触底
    window = {"w": 3.0, "h": 4.0}
    prev_net = wall_area(L, W, H, [])["net_m2"]
    for n in range(1, 6):
        a = wall_area(L, W, H, [window] * n)
        assert a["net_m2"] <= prev_net, (
            f"净面积回升：第 {n} 扇窗后 net_m2={a['net_m2']} > 上一步 {prev_net}"
        )
        if a["net_m2"] > 0:
            assert a["openings_m2"] == pytest.approx(a["gross_m2"] - a["net_m2"]), (
                f"扣除口径失败（第 {n} 扇窗）：openings_m2={a['openings_m2']} != "
                f"gross_m2({a['gross_m2']}) - net_m2({a['net_m2']})"
            )
        prev_net = a["net_m2"]


def test_net_floors_at_zero_when_deduction_exceeds_gross():
    """继续追加使扣除超过毛面积时，净面积必须为 0。"""
    # 单扇 6m × 5m = 30m²，两扇 60m² > 毛面积 50m²
    a = wall_area(L, W, H, [{"w": 6.0, "h": 5.0}, {"w": 6.0, "h": 5.0}])
    assert a["openings_m2"] > a["gross_m2"], (
        "前置条件不成立：本组开洞扣除未超过毛面积，无法验证触底"
    )
    assert a["net_m2"] == pytest.approx(0.0), (
        f"触底失败：扣除 {a['openings_m2']} 已超过毛面积 {a['gross_m2']}，"
        f"net_m2 应为 0，实际 {a['net_m2']}"
    )


def test_single_giant_opening_floors_at_zero():
    """单扇洞即超过毛面积时净面积同样触底为 0。"""
    a = wall_area(L, W, H, [{"w": 10.0, "h": 10.0}])
    assert a["net_m2"] == pytest.approx(0.0), (
        f"触底失败：单扇洞 {a['openings_m2']} 超过毛面积 {a['gross_m2']}，"
        f"net_m2 应为 0，实际 {a['net_m2']}"
    )


@pytest.mark.parametrize(
    "door,window",
    [
        ({"w": 0.9, "h": 2.1}, {"w": 1.5, "h": 1.4}),   # 常规单门单窗
        ({"w": 1.0, "h": 2.4}, {"w": 0.6, "h": 0.6}),   # 高门 + 小方窗
        ({"w": 0.8, "h": 2.0}, {"w": 4.0, "h": 1.8}),   # 普通门 + 宽扁大窗
    ],
)
def test_single_door_single_window(door, window):
    """单门单窗组合：净面积 = max(0, 毛面积 - 门 - 窗)。"""
    a = wall_area(L, W, H, [door, window])
    hole = door["w"] * door["h"] + window["w"] * window["h"]
    assert a["openings_m2"] == pytest.approx(round(hole, 2))
    expected_net = max(0.0, round(GROSS - hole, 2))
    assert a["net_m2"] == pytest.approx(expected_net), (
        f"单门单窗扣除口径失败：net_m2={a['net_m2']}，期望 {expected_net}"
    )


@pytest.mark.parametrize(
    "openings",
    [
        # 多种洞：方洞
        [{"w": 1.0, "h": 1.0}, {"w": 2.0, "h": 2.0}],
        # 多种洞：窄高洞（条形窗/高侧窗）
        [{"w": 0.3, "h": 2.0}, {"w": 0.5, "h": 2.5}],
        # 多种洞：宽扁洞（横长窗、推拉门洞）
        [{"w": 3.0, "h": 0.6}, {"w": 2.4, "h": 0.9}],
        # 多种洞混合：方 + 窄高 + 宽扁，累计仍小于毛面积
        [{"w": 1.2, "h": 1.2}, {"w": 0.4, "h": 2.2}, {"w": 2.5, "h": 0.8}],
        # 多种洞混合且累计超过毛面积 -> 触底：
        # 方洞 9+6.25，窄高 1.25+0.6，宽扁 10+13.2+10，合计 50.30 > 50
        [
            {"w": 3.0, "h": 3.0}, {"w": 2.5, "h": 2.5},
            {"w": 0.5, "h": 2.5}, {"w": 0.3, "h": 2.0},
            {"w": 5.0, "h": 2.0}, {"w": 5.5, "h": 2.4}, {"w": 5.0, "h": 2.0},
        ],
    ],
)
def test_varied_opening_geometries(openings):
    """多种洞种子几何下，扣除口径与触底约束同时成立。"""
    a = wall_area(L, W, H, openings)
    raw_hole = sum(o["w"] * o["h"] for o in openings)
    expected_net = max(0.0, round(GROSS - raw_hole, 2))
    assert a["net_m2"] >= 0, f"触底失败：net_m2={a['net_m2']} 为负"
    assert a["net_m2"] == pytest.approx(expected_net), (
        f"扣除口径失败：洞面积和 {round(raw_hole, 2)}、毛面积 {a['gross_m2']}，"
        f"净面积应为 {expected_net}，实际 {a['net_m2']}"
    )
    if expected_net > 0:
        assert a["openings_m2"] == pytest.approx(a["gross_m2"] - a["net_m2"]), (
            f"扣除口径失败：openings_m2={a['openings_m2']} != "
            f"gross_m2 - net_m2={a['gross_m2'] - a['net_m2']}"
        )


def test_estimate_engine_same_monotonic_floor():
    """经 estimate_room 服务组合层复验：追加开洞后升数不回升，触底后升数为 0。"""
    e0 = estimate_room(L, W, H, [], coverage=8, coats=2)
    assert e0["net_m2"] == pytest.approx(GROSS)
    e1 = estimate_room(L, W, H, [{"w": 6.0, "h": 5.0}], coverage=8, coats=2)
    assert e1["net_m2"] <= e0["net_m2"], "组合层净面积回升"
    e2 = estimate_room(L, W, H, [{"w": 6.0, "h": 5.0}, {"w": 6.0, "h": 5.0}], coverage=8, coats=2)
    assert e2["net_m2"] == pytest.approx(0.0), f"组合层触底失败：net_m2={e2['net_m2']}"
    assert e2["liters"] == pytest.approx(0.0), f"净面积触底后升数应为 0，实际 {e2['liters']}"
