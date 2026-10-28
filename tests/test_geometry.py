import pytest

from arch_docs.geometry import Port, Shape, point_along

BOX = Shape("b", 10, 20, 100, 40)


@pytest.mark.parametrize(
    ("side", "expected"),
    [
        ("top", Port(60, 20, 0.5, 0.0)),
        ("bottom", Port(60, 60, 0.5, 1.0)),
        ("left", Port(10, 40, 0.0, 0.5)),
        ("right", Port(110, 40, 1.0, 0.5)),
    ],
)
def test_port_defaults_to_middle_of_side(side, expected):
    assert BOX.port(side) == expected


def test_port_fraction_runs_left_to_right_and_top_to_bottom():
    assert BOX.port("top", 0.25) == Port(35, 20, 0.25, 0.0)
    assert BOX.port("right", 0.75) == Port(110, 50, 1.0, 0.75)


@pytest.mark.parametrize("f", [0.0, 1.0])
def test_port_accepts_fraction_bounds(f):
    assert BOX.port("bottom", f).fx == f


@pytest.mark.parametrize("f", [-0.01, 1.01])
def test_port_rejects_fraction_outside_unit_range(f):
    with pytest.raises(ValueError, match="0..1"):
        BOX.port("left", f)


def test_cx_is_horizontal_centre():
    assert BOX.cx == 60


def test_point_along_endpoints():
    pts = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]
    assert point_along(pts, 0) == (0, 0)
    assert point_along(pts, 1) == (10, 10)


def test_point_along_measures_total_length_not_segment_count():
    # 30 long then 10 long: the midpoint (20) lies on the first segment.
    pts = [(0.0, 0.0), (30.0, 0.0), (30.0, 10.0)]
    assert point_along(pts, 0.5) == pytest.approx((20, 0))
    assert point_along(pts, 0.875) == pytest.approx((30, 5))


def test_point_along_zero_length_returns_first_point():
    assert point_along([(5.0, 5.0), (5.0, 5.0)], 0.5) == (5, 5)


def test_point_along_rejects_fewer_than_two_points():
    with pytest.raises(ValueError, match="two points"):
        point_along([(0.0, 0.0)], 0.5)


@pytest.mark.parametrize("t", [-0.1, 1.1])
def test_point_along_rejects_t_outside_unit_range(t):
    with pytest.raises(ValueError, match="0..1"):
        point_along([(0.0, 0.0), (1.0, 1.0)], t)
