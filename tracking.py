import json
import time
import collections

import cv2
import numpy as np
import mediapipe as mp
import pyautogui

from touch_interpreter import TouchInterpreter


class TrackingEngine:
    def __init__(self, calibration_path="calibration.json", camera_source=0):
        pyautogui.PAUSE = 0
        pyautogui.FAILSAFE = False
        with open(calibration_path, "r") as f:
            cal = json.load(f)

        self._matrix = np.array(cal["matrix"], dtype=np.float32)
        self._screen_w = cal["screen_width"]
        self._screen_h = cal["screen_height"]

        if isinstance(camera_source, int):
            self._cap = cv2.VideoCapture(camera_source)
        else:
            self._cap = cv2.VideoCapture(camera_source)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open camera source: {camera_source}")
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self._cam_w = 640
        self._cam_h = 480

        self._mp_hands = mp.solutions.hands
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._mp_draw = mp.solutions.drawing_utils

        self._window_name = "Touch TV — Tracking"
        self._show_debug = True

        self._buf_size = 2
        self._buf = collections.deque(maxlen=self._buf_size)

        self._interpreter = TouchInterpreter()

        self._running = True
        self._no_hand_frames = 0
        self._max_no_hand = 30
        self._last_valid_screen = None

    def _warp(self, cam_x, cam_y):
        pt = np.array([[[cam_x, cam_y]]], dtype=np.float32)
        warped = cv2.perspectiveTransform(pt, self._matrix)
        return (int(warped[0, 0, 0]), int(warped[0, 0, 1]))

    def _running_avg(self, pt):
        self._buf.append(pt)
        xs = [p[0] for p in self._buf]
        ys = [p[1] for p in self._buf]
        return (int(np.mean(xs)), int(np.mean(ys)))

    def run(self):
        if self._show_debug:
            cv2.namedWindow(self._window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(self._window_name, 480, 360)

        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self._hands.process(rgb)

            tip_cam = None
            thumb_idx_dist = None

            if results.multi_hand_landmarks:
                self._no_hand_frames = 0
                lm = results.multi_hand_landmarks[0]
                h, w, _ = frame.shape

                tx = int(lm.landmark[8].x * w)
                ty = int(lm.landmark[8].y * h)
                tip_cam = (tx, ty)

                t4x = lm.landmark[4].x
                t4y = lm.landmark[4].y
                t8x = lm.landmark[8].x
                t8y = lm.landmark[8].y
                thumb_idx_dist = ((t4x - t8x) ** 2 + (t4y - t8y) ** 2) ** 0.5

                if self._show_debug:
                    self._mp_draw.draw_landmarks(
                        frame, lm, self._mp_hands.HAND_CONNECTIONS,
                        self._mp_draw.DrawingSpec(color=(0, 255, 0), thickness=1),
                        self._mp_draw.DrawingSpec(color=(0, 0, 255), thickness=1),
                    )
                    cv2.circle(frame, tip_cam, 6, (0, 255, 255), -1)
            else:
                self._no_hand_frames += 1

            screen_pt = None
            if tip_cam is not None:
                raw_screen = self._warp(*tip_cam)
                screen_pt = self._running_avg(raw_screen)
                self._last_valid_screen = screen_pt

                if screen_pt[0] < 0:
                    screen_pt = (0, screen_pt[1])
                if screen_pt[1] < 0:
                    screen_pt = (screen_pt[0], 0)
                if screen_pt[0] > self._screen_w:
                    screen_pt = (self._screen_w, screen_pt[1])
                if screen_pt[1] > self._screen_h:
                    screen_pt = (screen_pt[0], self._screen_h)

                pyautogui.moveTo(screen_pt[0], screen_pt[1])
                self._interpreter.update(screen_pt[0], screen_pt[1], thumb_idx_dist)
            elif self._no_hand_frames > self._max_no_hand:
                self._interpreter.reset()

            if self._show_debug:
                if screen_pt and self._last_valid_screen:
                    cw, ch = 320, 240
                    debug = cv2.resize(frame, (cw, ch))
                    cv2.putText(
                        debug,
                        f"Screen: {self._last_valid_screen}",
                        (10, 20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
                        (0, 255, 0),
                        1,
                    )
                    cv2.putText(
                        debug,
                        f"Drag: {self._interpreter.is_dragging()}",
                        (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
                        (255, 0, 255) if self._interpreter.is_dragging() else (0, 255, 0),
                        1,
                    )
                    cv2.imshow(self._window_name, debug)

            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                self.stop()
                break

        self._cleanup()

    def stop(self):
        self._running = False

    def _cleanup(self):
        self._interpreter.reset()
        if self._cap is not None and self._cap.isOpened():
            self._cap.release()
        cv2.destroyAllWindows()


def run_tracking(camera_source=0):
    engine = TrackingEngine(camera_source=camera_source)
    engine.run()
