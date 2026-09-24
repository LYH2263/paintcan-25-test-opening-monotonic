"""开洞单调、扣除口径与净面积触底测例。

固定房间长宽高，沿「无洞 → 一扇窗 → 扣除超毛面积」推进，
分别守住三条不变式：
  1. 单调：追加开洞后净面积不得回升；
  2. 扣除口径：openings_m2 必须等于 gross_m2 - net_m2；
  3. 触底：扣除超过毛面积时净面积必须为 0。
另覆盖 seed.py 中单门单窗（客厅）与多种洞（卧室）种子房几何。
"""

import pytest

from app.engines.estimate import estimate_room
from app.engines.wall_area import wall_area

# 固定房间：5m x 4m x 2.8m，毛墙面积 = 2*(5+4)*2.8 = 50.4
L, W, H = 5.0, 4.0, 2.8
GROSS = 50.4
WINDOW = {"w": 1.5, "h": 1.4}  # 一扇窗 2.1 m2


def _deducted(gross, net):
    """从毛/净面积反推开洞扣除量。"""
    return gross - net


def test_no_openings_net_equals_gross():
    a = wall_area(L, W, H, [])
    assert a["gross_m2"] == GROSS
    assert a["net_m2"] == a["gross_m2"], "无开洞时净面积必须等于毛面积"
    assert a["openings_m2"] == 0.0


def test_adding_window_is_monotonic_and_deduction_matches():
    before = wall_area(L, W, H, [])
    after = wall_area(L, W, H, [WINDOW])

    # 净面积不得大于追加前
    assert after["net_m2"] <= before["net_m2"], (
        f"净面积回升：追加窗户前净面积 {before['net_m2']}，"
        f"追加后反而为 {after['net_m2']}"
    )

    # 开洞扣除须等于毛面积减净面积
    assert after["openings_m2"] == pytest.approx(
        _deducted(after["gross_m2"], after["net_m2"]), abs=0.01
    ), (
        f"扣除口径错误：引擎报开洞 {after['openings_m2']}，"
        f"但毛面积 {after['gross_m2']} − 净面积 {after['net_m2']} = "
        f"{_deducted(after['gross_m2'], after['net_m2'])}"
    )

    assert after["net_m2"] == 48.3


def test_deduction_floors_net_at_zero():
    # 在一扇窗之后继续追加，使总扣除 62.1 > 毛面积 50.4
    huge = [WINDOW, {"w": 4.0, "h": 5.0}, {"w": 4.0, "h": 5.0}, {"w": 4.0, "h": 5.0}]
    bottomed = wall_area(L, W, H, huge)

    # 确认确实是「扣除超过毛面积」的场景，而不是数据没构造够
    assert bottomed["openings_m2"] > bottomed["gross_m2"]
    assert bottomed["net_m2"] == 0.0, (
        f"触底失败：开洞合计 {bottomed['openings_m2']} 已超过毛面积 "
        f"{bottomed['gross_m2']}，净面积却为 {bottomed['net_m2']}，必须为 0"
    )


def test_every_step_is_monotonic_until_floor():
    # 逐级追加，确认每一步净面积都不回升；最后一步触底
    steps = [
        [],
        [WINDOW],
        [WINDOW, {"w": 4.0, "h": 5.0}],                 # 22.1，净 28.3
        [WINDOW, {"w": 4.0, "h": 5.0}, {"w": 4.0, "h": 5.0}],  # 42.1，净 8.3
        [WINDOW, {"w": 4.0, "h": 5.0}, {"w": 4.0, "h": 5.0}, {"w": 4.0, "h": 5.0}],  # 62.1，触底
    ]
    prev_net = wall_area(L, W, H, steps[0])["net_m2"]
    for i, openings in enumerate(steps[1:], start=1):
        a = wall_area(L, W, H, openings)
        assert a["net_m2"] <= prev_net, (
            f"净面积回升：第 {i} 次追加开洞后净面积由 {prev_net} 变为 {a['net_m2']}"
        )
        prev_net = a["net_m2"]

    assert prev_net == 0.0, f"触底失败：逐级扣除超过毛面积后净面积为 {prev_net}，应为 0"


# seed.py 中的种子房几何：（长, 宽, 高, 开洞, 期望毛面积, 期望扣除, 期望净面积）
SEEDED_GEOMETRIES = [
    pytest.param(
        5.0, 4.0, 2.8,
        [{"w": 0.9, "h": 2.1}, {"w": 1.5, "h": 1.4}],  # 客厅：单门单窗
        50.4, 3.99, 46.41,
        id="single-door-single-window-living-room",
    ),
    pytest.param(
        4.0, 3.2, 2.8,
        [{"w": 0.9, "h": 2.1}, {"w": 1.8, "h": 1.5}, {"w": 1.2, "h": 1.5}],  # 卧室(多种洞)
        40.32, 6.39, 33.93,
        id="multi-opening-bedroom",
    ),
    pytest.param(
        6.0, 3.0, 2.7,
        [{"w": 0.9, "h": 2.1}, {"w": 0.9, "h": 2.1},
         {"w": 2.0, "h": 1.5}, {"w": 2.0, "h": 1.5}, {"w": 1.0, "h": 1.2}],  # 两门三窗
        48.6, 10.98, 37.62,
        id="multi-opening-two-doors-three-windows",
    ),
]


@pytest.mark.parametrize("length,width,height,openings,gross,hole,net", SEEDED_GEOMETRIES)
def test_seeded_room_geometries(length, width, height, openings, gross, hole, net):
    a = wall_area(length, width, height, openings)

    assert a["gross_m2"] == gross
    assert a["openings_m2"] == pytest.approx(hole, abs=0.01), (
        f"扣除口径错误：种子房 {a['gross_m2']} m2 毛面积，"
        f"期望扣除 {hole}，引擎报 {a['openings_m2']}"
    )
    assert a["net_m2"] == pytest.approx(net, abs=0.01)
    assert a["net_m2"] == pytest.approx(
        _deducted(a["gross_m2"], a["openings_m2"]), abs=0.01
    ), (
        f"扣除口径错误：毛面积 {a['gross_m2']} − 开洞 {a['openings_m2']} "
        f"应等于净面积，实际净面积 {a['net_m2']}"
    )
    assert a["net_m2"] >= 0.0, f"触底失败：净面积 {a['net_m2']} 不应为负"


@pytest.mark.parametrize("length,width,height,openings,gross,hole,net", SEEDED_GEOMETRIES[:2])
def test_estimate_pipeline_preserves_seeded_net(length, width, height, openings, gross, hole, net):
    # 经 estimate_room 组合引擎走一遍，种子房净面积在升数链路中不被改口径
    e = estimate_room(length, width, height, openings, coverage=8, coats=2)
    assert e["gross_m2"] == gross
    assert e["net_m2"] == pytest.approx(net, abs=0.01), (
        f"扣除口径错误：estimate 链路净面积 {e['net_m2']} 与墙面积引擎 {net} 不一致"
    )
    assert e["liters"] == round(net * 2 / 8, 2)
