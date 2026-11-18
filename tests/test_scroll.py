"""Pure helpers of the side-scrolling levels (floor segments, camera, pits)."""
from game.config import W, FLOOR
from game.scroll import floor_segments, make_platforms, camera_target, pit_ahead, over_pit


def test_floor_segments_split_around_pits():
    assert floor_segments(1000, []) == [(0, 1000)]
    assert floor_segments(1000, [(300, 360), (700, 780)]) == [(0, 300), (360, 340), (780, 220)]
    assert floor_segments(1000, [(0, 50)]) == [(50, 950)]
    assert floor_segments(1000, [(950, 1000)]) == [(0, 950)]
    assert floor_segments(1000, [(300, 360), (340, 400)]) == [(0, 300), (400, 600)]      # overlapping pits merge


def test_platform_list_has_floor_pieces_first():
    pl = make_platforms(1000, [(300, 360)], [(100, 170, 80)])
    assert pl == [(0, FLOOR, 300), (360, FLOOR, 640), (100, 170, 80)]


def test_camera_follows_leader_and_clamps():
    assert camera_target(0, 2000) == 0
    assert camera_target(500, 2000) == 500 - W * 0.55
    assert camera_target(1990, 2000) == 2000 - W
    assert camera_target(900, 2000, lock_x0=1520) == 1520.0       # locked boss room ignores the leader


def test_pit_detection():
    pits = [(300, 360)]
    assert pit_ahead(pits, 270, 1) and not pit_ahead(pits, 200, 1) and not pit_ahead(pits, 270, -1)
    assert pit_ahead(pits, 380, -1) and not pit_ahead(pits, 380, 1)
    assert over_pit(pits, 330) and not over_pit(pits, 301) and not over_pit(pits, 361)
