import time

import pyautogui


class TouchInterpreter:
    def __init__(self):
        pyautogui.PAUSE = 0

        self._dwell_center = None
        self._dwell_start = None
        self._dwell_radius = 12
        self._dwell_time = 0.5
        self._clicked = False
        self._last_click_time = 0
        self._click_cooldown = 0.3

        self._dragging = False
        self._pinch_threshold = 0.05
        self._pinch_release = 0.07

    def update(self, screen_x, screen_y, thumb_idx_dist_norm):
        now = time.time()
        self._check_dwell(screen_x, screen_y, now)
        self._check_pinch(thumb_idx_dist_norm, screen_x, screen_y, now)

    def _check_dwell(self, sx, sy, now):
        if self._dragging:
            self._dwell_center = None
            self._dwell_start = None
            self._clicked = False
            return

        if self._dwell_center is None:
            self._dwell_center = (sx, sy)
            self._dwell_start = now
            self._clicked = False
            return

        dx = sx - self._dwell_center[0]
        dy = sy - self._dwell_center[1]
        dist = (dx * dx + dy * dy) ** 0.5

        if dist > self._dwell_radius:
            self._dwell_center = (sx, sy)
            self._dwell_start = now
            self._clicked = False
            return

        if not self._clicked and (now - self._dwell_start) >= self._dwell_time:
            if (now - self._last_click_time) >= self._click_cooldown:
                pyautogui.click()
                self._last_click_time = now
                self._clicked = True

    def _check_pinch(self, dist_norm, sx, sy, now):
        if dist_norm is None:
            if self._dragging:
                pyautogui.mouseUp()
                self._dragging = False
            self._dwell_center = None
            self._dwell_start = None
            self._clicked = False
            return

        if not self._dragging and dist_norm < self._pinch_threshold:
            self._dragging = True
            pyautogui.mouseDown()
            self._dwell_center = None
            self._dwell_start = None
            self._clicked = False
        elif self._dragging and dist_norm > self._pinch_release:
            pyautogui.mouseUp()
            self._dragging = False

    def is_dragging(self):
        return self._dragging

    def reset(self):
        if self._dragging:
            pyautogui.mouseUp()
            self._dragging = False
        self._dwell_center = None
        self._dwell_start = None
        self._clicked = False
