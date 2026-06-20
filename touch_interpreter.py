import time

import pyautogui


class GlassTap:
    def __init__(self):
        self._positions = []
        self._clicked = False
        self._cooldown = 0

    def update(self, sx, sy):
        if self._cooldown > 0:
            self._cooldown -= 1
            return False

        if self._clicked:
            max_dist = max(
                ((sx - px) ** 2 + (sy - py) ** 2) ** 0.5
                for px, py in self._positions[-4:]
            ) if len(self._positions) >= 4 else 0
            if max_dist > 40:
                self._clicked = False
                self._positions.clear()
            return False

        self._positions.append((sx, sy))
        if len(self._positions) > 8:
            self._positions.pop(0)

        if len(self._positions) >= 6:
            max_dist = max(
                ((sx - px) ** 2 + (sy - py) ** 2) ** 0.5
                for px, py in self._positions[-6:]
            )
            if max_dist < 12:
                self._clicked = True
                self._cooldown = 10
                return True

        return False

    def reset(self):
        self._positions.clear()
        self._clicked = False
        self._cooldown = 0


class TouchInterpreter:
    def __init__(self):
        self._pinch_threshold = 0.05
        self._pinch_release = 0.07
        self._was_pinching = False

        self._glass_tap = GlassTap()

    def update(self, screen_x, screen_y, thumb_idx_dist_norm):
        if self._glass_tap.update(screen_x, screen_y):
            pyautogui.click()

        self._check_pinch(thumb_idx_dist_norm)

    def _check_pinch(self, dist_norm):
        if dist_norm is None:
            if self._was_pinching:
                pyautogui.mouseUp()
                self._was_pinching = False
            return

        if not self._was_pinching and dist_norm < self._pinch_threshold:
            self._was_pinching = True
            pyautogui.mouseDown()
        elif self._was_pinching and dist_norm > self._pinch_release:
            pyautogui.mouseUp()
            self._was_pinching = False

    def is_dragging(self):
        return self._was_pinching

    def reset(self):
        if self._was_pinching:
            pyautogui.mouseUp()
            self._was_pinching = False
        self._glass_tap.reset()
