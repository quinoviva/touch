import json
import time
import threading
import cv2
import numpy as np
import mediapipe as mp
import customtkinter as ctk
from PIL import Image, ImageTk


class CalibrationApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Touch TV Calibration")
        self.root.attributes("-fullscreen", True)
        self.root.configure(fg_color="#000000")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        inset = 50
        self.corner_pts = [
            (inset, inset),
            (self.screen_w - inset, inset),
            (self.screen_w - inset, self.screen_h - inset),
            (inset, self.screen_h - inset),
        ]
        self.corner_labels = [
            "Top-Left",
            "Top-Right",
            "Bottom-Right",
            "Bottom-Left",
        ]

        self._corner_idx = 0
        self._camera_pts = []
        self._screen_pts = []
        self._finger_stable_since = None
        self._last_finger_pt = None
        self._phase = "preview"

        self._cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self._cap.isOpened():
            raise RuntimeError("Could not open webcam (index 0)")
        self._cam_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._cam_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if self._cam_w == 0 or self._cam_h == 0:
            self._cam_w, self._cam_h = 640, 480
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self._mp_hands = mp.solutions.hands
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        self._mp_draw = mp.solutions.drawing_utils

        self._running = True
        self._frame = None
        self._fingertip = None
        self._lock = threading.Lock()
        self._cal_done = threading.Event()

        self._setup_ui()
        self._start_capture()
        self.root.bind("<Escape>", lambda e: self._on_close())
        self.root.after(30, self._tick)

    def _setup_ui(self):
        self._canvas = ctk.CTkCanvas(
            self.root,
            width=self.screen_w,
            height=self.screen_h,
            highlightthickness=0,
            bg="black",
        )
        self._canvas.pack(fill="both", expand=True)

    def _start_capture(self):
        self._cap_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._cap_thread.start()

    def _capture_loop(self):
        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self._hands.process(rgb)

            tip = None
            if results.multi_hand_landmarks:
                h, w, _ = frame.shape
                lm = results.multi_hand_landmarks[0]
                tip = (
                    int(lm.landmark[8].x * w),
                    int(lm.landmark[8].y * h),
                )
                self._mp_draw.draw_landmarks(
                    frame, lm, self._mp_hands.HAND_CONNECTIONS,
                    self._mp_draw.DrawingSpec(color=(0, 255, 0), thickness=1),
                    self._mp_draw.DrawingSpec(color=(0, 0, 255), thickness=1),
                )

            with self._lock:
                self._frame = frame
                self._fingertip = tip

    def _tick(self):
        if not self._running:
            return

        with self._lock:
            frame = self._frame.copy() if self._frame is not None else None
            tip = self._fingertip

        self._canvas.delete("all")

        if frame is not None:
            preview_w = self.screen_w
            preview_h = int(preview_w * self._cam_h / self._cam_w)
            if preview_h > self.screen_h:
                preview_h = self.screen_h
                preview_w = int(preview_h * self._cam_w / self._cam_h)
            disp = cv2.resize(frame, (preview_w, preview_h))
            disp_rgb = cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(disp_rgb)
            self._photo = ImageTk.PhotoImage(pil_img)
            offset_x = (self.screen_w - preview_w) // 2
            offset_y = (self.screen_h - preview_h) // 2
            self._canvas.create_image(
                offset_x, offset_y, anchor="nw", image=self._photo
            )

            if tip is not None:
                tx = offset_x + int(tip[0] * preview_w / self._cam_w)
                ty = offset_y + int(tip[1] * preview_h / self._cam_h)
                self._canvas.create_oval(
                    tx - 6, ty - 6, tx + 6, ty + 6,
                    fill="#00ff00", outline="white", width=1,
                )

        self._draw_targets()

        if self._phase == "preview":
            txt = (
                "Make sure the entire TV screen is visible in the camera.\n"
                "Press SPACE to begin calibration."
            )
            self._canvas.create_text(
                self.screen_w // 2, self.screen_h - 80,
                text=txt, font=("Segoe UI", 22),
                fill="white", justify="center",
            )
        elif self._phase == "calibrating":
            self._handle_calibration_tick(tip)
        elif self._phase == "complete":
            self._canvas.delete("all")
            txt = "Calibration Complete!\nPress ESC to exit."
            self._canvas.create_text(
                self.screen_w // 2, self.screen_h // 2,
                text=txt, font=("Segoe UI", 48),
                fill="#00ff00", justify="center",
            )

        self.root.after(30, self._tick)

    def _draw_targets(self):
        if self._phase != "calibrating":
            return
        cx, cy = self.corner_pts[self._corner_idx]

        phase = time.time() * 4
        pulse = 30 + 10 * np.sin(phase)
        r = int(40 + pulse)

        self._canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            outline="red", width=5, tags="target",
        )
        self._canvas.create_oval(
            cx - 6, cy - 6, cx + 6, cy + 6,
            fill="red", tags="target",
        )

        idx = self._corner_idx + 1
        self._canvas.create_text(
            self.screen_w // 2, 30,
            text=f"Step {idx}/4: Touch the {self.corner_labels[self._corner_idx]} target on your TV",
            font=("Segoe UI", 28),
            fill="white", tags="target",
        )

    def _handle_calibration_tick(self, tip):
        if tip is None:
            self._finger_stable_since = None
            self._last_finger_pt = None
            return

        now = time.time()

        if self._last_finger_pt is None:
            self._last_finger_pt = tip
            self._finger_stable_since = now
            return

        dx = tip[0] - self._last_finger_pt[0]
        dy = tip[1] - self._last_finger_pt[1]
        moved = np.sqrt(dx * dx + dy * dy)

        if moved > 15:
            self._last_finger_pt = tip
            self._finger_stable_since = now
            return

        elapsed = now - self._finger_stable_since
        frac = min(elapsed / 1.5, 1.0)

        bw, bh = 300, 18
        bx = (self.screen_w - bw) // 2
        by = self.screen_h - 80
        self._canvas.create_rectangle(
            bx, by, bx + bw, by + bh,
            outline="white", width=2,
        )
        if frac > 0:
            self._canvas.create_rectangle(
                bx + 2, by + 2,
                bx + int((bw - 4) * frac), by + bh - 2,
                fill="#00cc00", outline="",
            )
        pct = f"{int(frac * 100)}%"
        self._canvas.create_text(
            self.screen_w // 2, by + bh // 2,
            text=pct, font=("Segoe UI", 11),
            fill="white",
        )

        if elapsed >= 1.5:
            self._record_point(tip)

    def _record_point(self, cam_pt):
        sx, sy = self.corner_pts[self._corner_idx]
        self._camera_pts.append([int(cam_pt[0]), int(cam_pt[1])])
        self._screen_pts.append([int(sx), int(sy)])

        self._corner_idx += 1
        self._finger_stable_since = None
        self._last_finger_pt = None

        if self._corner_idx >= 4:
            self._finish_calibration()

    def _finish_calibration(self):
        src = np.array(self._camera_pts, dtype=np.float32)
        dst = np.array(self._screen_pts, dtype=np.float32)
        matrix = cv2.getPerspectiveTransform(src, dst)

        data = {
            "camera_points": self._camera_pts,
            "screen_points": self._screen_pts,
            "matrix": matrix.tolist(),
            "screen_width": self.screen_w,
            "screen_height": self.screen_h,
        }
        with open("calibration.json", "w") as f:
            json.dump(data, f, indent=2)

        self._phase = "complete"
        self._cal_done.set()

    def start_calibration(self):
        self._phase = "calibrating"
        self._corner_idx = 0
        self._camera_pts = []
        self._screen_pts = []
        self._finger_stable_since = None
        self._last_finger_pt = None

    def _on_close(self):
        self._running = False
        if self._cap is not None and self._cap.isOpened():
            self._cap.release()
        self.root.destroy()

    def run(self):
        def _on_space(e):
            if self._phase == "preview":
                self.start_calibration()
        self.root.bind("<space>", _on_space)
        self.root.mainloop()


def run_calibration():
    app = CalibrationApp()
    app.run()
    return app._cal_done.is_set()
