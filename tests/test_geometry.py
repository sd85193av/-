import unittest
from types import SimpleNamespace

from gesture_mouse.geometry import analyze_landmarks


def landmark_set():
    return [SimpleNamespace(x=0.5, y=0.7) for _ in range(21)]


def set_finger(points, mcp, pip, tip, mcp_xy, pip_xy, tip_xy):
    points[mcp] = SimpleNamespace(x=mcp_xy[0], y=mcp_xy[1])
    points[pip] = SimpleNamespace(x=pip_xy[0], y=pip_xy[1])
    points[tip] = SimpleNamespace(x=tip_xy[0], y=tip_xy[1])


class GeometryTests(unittest.TestCase):
    def test_two_finger_pose_is_detected(self):
        points = landmark_set()
        points[0] = SimpleNamespace(x=0.5, y=0.85)
        points[4] = SimpleNamespace(x=0.34, y=0.65)
        set_finger(points, 5, 6, 8, (0.42, 0.65), (0.40, 0.50), (0.38, 0.25))
        set_finger(points, 9, 10, 12, (0.50, 0.62), (0.50, 0.45), (0.50, 0.20))
        set_finger(points, 13, 14, 16, (0.58, 0.65), (0.59, 0.55), (0.55, 0.68))
        set_finger(points, 17, 18, 20, (0.65, 0.68), (0.66, 0.59), (0.62, 0.72))

        result = analyze_landmarks(points)

        self.assertTrue(result.two_finger_gesture)
        self.assertFalse(result.closed_fist)
        self.assertAlmostEqual(result.motion_point[0], 0.44)
        self.assertAlmostEqual(result.motion_point[1], 0.225)

    def test_compact_curled_fingers_are_detected_as_fist(self):
        points = landmark_set()
        points[0] = SimpleNamespace(x=0.5, y=0.85)
        points[4] = SimpleNamespace(x=0.40, y=0.70)
        set_finger(points, 5, 6, 8, (0.42, 0.65), (0.41, 0.55), (0.46, 0.68))
        set_finger(points, 9, 10, 12, (0.50, 0.62), (0.50, 0.52), (0.52, 0.66))
        set_finger(points, 13, 14, 16, (0.58, 0.65), (0.59, 0.55), (0.56, 0.68))
        set_finger(points, 17, 18, 20, (0.65, 0.68), (0.66, 0.59), (0.62, 0.72))

        result = analyze_landmarks(points)

        self.assertTrue(result.closed_fist)
        self.assertFalse(result.two_finger_gesture)

    def test_outward_thumb_has_larger_open_ratio(self):
        tucked = landmark_set()
        outward = landmark_set()
        for points in (tucked, outward):
            points[0] = SimpleNamespace(x=0.5, y=0.85)
            set_finger(
                points,
                5,
                6,
                8,
                (0.42, 0.65),
                (0.40, 0.50),
                (0.38, 0.25),
            )
            points[9] = SimpleNamespace(x=0.50, y=0.62)
            points[17] = SimpleNamespace(x=0.65, y=0.68)
        tucked[4] = SimpleNamespace(x=0.47, y=0.68)
        outward[4] = SimpleNamespace(x=0.28, y=0.62)

        tucked_result = analyze_landmarks(tucked)
        outward_result = analyze_landmarks(outward)

        self.assertLess(tucked_result.thumb_open_ratio, 1.05)
        self.assertGreater(outward_result.thumb_open_ratio, 1.20)


if __name__ == "__main__":
    unittest.main()
