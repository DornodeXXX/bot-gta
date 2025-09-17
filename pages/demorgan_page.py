from PyQt5 import QtWidgets, QtCore
from widgets.switch_button import SwitchButton
import time
import pyautogui
import cv2
import numpy as np
import mss
from widgets.common import CommonLogger, ScriptController, auto_detect_region, load_images
import os
import threading

class DemorganPage(QtWidgets.QWidget):
    statusChanged = QtCore.pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        self.worker: DemorganWorker | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        switch_layout = QtWidgets.QHBoxLayout()
        self.switch = SwitchButton()
        self.switch.clicked.connect(self.handle_toggle)
        self.switch.clicked.connect(self.statusChanged.emit)
        
        switch_layout.addWidget(CommonLogger._make_label("Деморган", 16))
        switch_layout.addStretch()
        switch_layout.addWidget(self.switch)
        layout.addLayout(switch_layout)

        self.counter_label = CommonLogger._make_label("Счётчик: 0", 14)
        self.counter_label.setObjectName("counter_label")
        layout.addWidget(self.counter_label)
        layout.addStretch()

        self.log_output = CommonLogger.create_log_field(layout)

    def handle_toggle(self):
        ScriptController.toggle_script(
            widget=self,
            worker_factory=lambda: DemorganWorker(),
            log_output=self.log_output,
            extra_signals={
                "counter_signal": self._update_counter
            }
        )

    def _update_counter(self, value: int):
        self.counter_label.setText(f"Счётчик: {value}")

class DemorganWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    counter_signal = QtCore.pyqtSignal(int)
    CONFIDENCE = 0.95

    def __init__(self, width_ratio=0.5, height_ratio=0.6, top_ratio=0.25):
        super().__init__()
        self.running = True
        self._count = 0
        self.last_known_position = None
        self.template = self._load_template()
        self.monitor = auto_detect_region(width_ratio, height_ratio, top_ratio)
        self._stop = threading.Event()
        self.image_paths = load_images("shveika", count=20)
        self.shveika_templates = self._load_shveika_templates(self.image_paths)
        self.sentinel_idx = 0
        self.sentinel_threshold = 0.92
        self.is_tokar_found = False

    def _load_template(self):
        t = cv2.imread("assets/tokar/i3.png", cv2.IMREAD_UNCHANGED)
        if t is None:
            raise FileNotFoundError("Не найден шаблон токаря")
        return t[:, :, :3]

    def _load_shveika_templates(self, paths):
        templates = []
        for p in paths:
            img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise FileNotFoundError(f"Не найден шаблон: {p}")
            if img.shape[2] == 4:
                img = img[:, :, :3]
            templates.append(img)
        return templates

    def log(self, message: str):
        CommonLogger.log(message, self.log_signal)

    def _search_in_region(self, sct, region):
        h, w = self.template.shape[:2]
        screenshot = np.array(sct.grab(region))
        screenshot_bgr = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

        result = cv2.matchTemplate(screenshot_bgr, self.template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > 0.9:
            found_x = region["left"] + max_loc[0] + w // 2
            found_y_bottom = region["top"] + max_loc[1] + h
            self.last_known_position = (found_x, found_y_bottom)
            self.is_tokar_found = True
            pyautogui.moveTo(found_x, found_y_bottom + 30)
            self._count += 1
            self.counter_signal.emit(self._count)
            self.log(f"[✓] токарь найден (#{self._count})")
            self._stop.wait(0.01)
            self.is_tokar_found = False
            return True

        return False

    def run(self):
        self.log(f"[→] Скрипт Деморган запущен")
        tokar_thread = threading.Thread(target=self.run_tokar, args=(self.template, self.monitor))
        script_thread = threading.Thread(target=self.run_shveika) 
        tokar_thread.start()
        script_thread.start()
        tokar_thread.join()
        script_thread.join()

    def run_tokar(self, template, monitor):
        h, w = template.shape[:2]
        self.template = template
        self.monitor = monitor
        self.last_known_position = None

        with mss.mss() as sct:
            try:
                while self.running:
                    if self.last_known_position:
                        cx, cy_bottom = self.last_known_position
                        small_monitor = {
                            "left": max(cx - 100, self.monitor["left"]),
                            "top": max(cy_bottom - 100 - h // 2, self.monitor["top"]),
                            "width": min(cx + 100, self.monitor["left"] + self.monitor["width"]) - max(cx - 100, self.monitor["left"]),
                            "height": min(cy_bottom + 100 - h // 2, self.monitor["top"] + self.monitor["height"]) - max(cy_bottom - 100 - h // 2, self.monitor["top"]),
                        }
                        if self._search_in_region(sct, small_monitor):
                            continue

                    if not self._search_in_region(sct, self.monitor):
                        self.last_known_position = None
                        self._stop.wait(0.05)
            except Exception as exc:
                self.log(f"[Ошибка потока токаря] {str(exc)}")
            finally:
                self.running = False

    def _grab_bgr(self, sct, region):
        frame = np.array(sct.grab(region))
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    def _locate_one(self, image_bgr, templ_bgr, threshold):
        res = cv2.matchTemplate(image_bgr, templ_bgr, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        if max_val >= threshold:
            h, w = templ_bgr.shape[:2]
            center = (max_loc[0] + w // 2 + self.monitor["left"],
                      max_loc[1] + h // 2 + self.monitor["top"])
            return center, max_val
        return None, max_val

    def _locate_all_20(self, image_bgr, threshold):
        coords = []
        for templ in self.shveika_templates:
            c, score = self._locate_one(image_bgr, templ, threshold)
            coords.append(c)
        return coords

    def run_shveika(self):
        last_wait_logged = 0.0
        sentinel_tem = self.shveika_templates[self.sentinel_idx]

        idle_sleep = 0.12
        busy_sleep = 0.03
        wait_on_tokar = 0.05

        try:
            with mss.mss() as sct:
                while self.running:
                    if self.is_tokar_found:
                        self._stop.wait(wait_on_tokar)
                        continue

                    image_bgr = self._grab_bgr(sct, self.monitor)
                    sentinel_center, sentinel_score = self._locate_one(image_bgr, sentinel_tem, self.sentinel_threshold)

                    if sentinel_center is None:
                        now = time.time()
                        if now - last_wait_logged > 1.5:
                            last_wait_logged = now
                        self._stop.wait(idle_sleep)
                        continue

                    coords = self._locate_all_20(image_bgr, self.CONFIDENCE)

                    if all(coords):
                        self._count += 1
                        self.counter_signal.emit(self._count)
                        self.log(f"[✓] Все 20 точек найдены. Начинаю клик.")

                        for i, pos in enumerate(coords):
                            if not self.running:
                                break
                            if i == 0:
                                pyautogui.click(pos)
                                self.log(f"[Клик] {i+1}/20: {pos} (1 раз)")
                            else:
                                pyautogui.click(pos)
                                self._stop.wait(0.05)
                                pyautogui.click(pos)
                                self.log(f"[Клик] {i+1}/20: {pos} (2 раза)")
                        self._stop.wait(busy_sleep)
                    else:
                        now = time.time()
                        if now - last_wait_logged > 1.5:
                            missing = [i+1 for i, c in enumerate(coords) if c is None]
                            self.log(f"[~] Ожидание элементов... отсутствуют: {missing[:6]}{'...' if len(missing) > 6 else ''}")
                            last_wait_logged = now
                        self._stop.wait(busy_sleep)
        except Exception as exc:
            self.log(f"[Ошибка потока скрипта] {str(exc)}")
        finally:
            self.running = False