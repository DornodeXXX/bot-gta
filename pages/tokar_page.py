from PyQt5 import QtWidgets, QtCore
from widgets.switch_button import SwitchButton
import time
import keyboard
import pyautogui
import cv2
import numpy as np
import mss
from widgets.logger import CommonLogger, ScriptController

class TokarPage(QtWidgets.QWidget):
    statusChanged = QtCore.pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        self.worker: TokarWorker | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        switch_layout = QtWidgets.QHBoxLayout()
        self.switch = SwitchButton()
        self.switch.clicked.connect(self.handle_toggle)
        self.switch.clicked.connect(self.statusChanged.emit)
        
        switch_layout.addWidget(CommonLogger._make_label("Токарь", 16))
        switch_layout.addStretch()
        switch_layout.addWidget(self.switch)
        layout.addLayout(switch_layout)

        self.counter_label = QtWidgets.QLabel("Счётчик: 0")
        self.counter_label.setObjectName("counter_label")
        layout.addWidget(self.counter_label)
        layout.addStretch()

        self.log_output = CommonLogger.create_log_field(layout)

    def handle_toggle(self):
        ScriptController.toggle_script(
            widget=self,
            worker_factory=lambda: TokarWorker(),
            log_output=self.log_output,
            extra_signals={
                "counter_signal": self._update_counter
            }
        )

    def _update_counter(self, value: int):
        self.counter_label.setText(f"Счётчик: {value}")

class TokarWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    counter_signal = QtCore.pyqtSignal(int)

    def __init__(self,width_ratio=0.5, height_ratio=0.6, top_ratio=0.25):
        super().__init__()
        self._running = True
        self._count = 0
        self.last_known_position = None
        self.template = self._load_template()
        self.monitor = self._auto_detect_region(width_ratio, height_ratio, top_ratio)

    def _load_template(self):
        t = cv2.imread("assets/tokar/i3.png", cv2.IMREAD_UNCHANGED)
        if t is None:
            raise FileNotFoundError("Не найден шаблон токаря")
        return t[:, :, :3]

    def _auto_detect_region(self, width_ratio=0.5, height_ratio=0.6, top_ratio=0.25):
        screen_width, screen_height = pyautogui.size()
        region_width = int(screen_width * width_ratio)
        region_height = int(screen_height * height_ratio)
        region = {
            "left": int((screen_width - region_width) / 2),
            "top": int(screen_height * top_ratio),
            "width": region_width,
            "height": region_height,
        }
        return region

    def log(self, message: str):
        CommonLogger.log(message, self.log_signal)

    def stop(self):
        self._running = False

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

            pyautogui.moveTo(found_x, found_y_bottom + 30)
            self._count += 1
            self.counter_signal.emit(self._count)
            self.log(f"[✓] токарь найден (#{self._count})")
            time.sleep(0.01)
            return True

        return False

    def run(self):
        h, w = self.template.shape[:2]
        with mss.mss() as sct:
            self.log("Скрипт токаря запущен. Нажми ESC для остановки.")
            self.log(f"Область поиска (x={self.monitor['left']}, y={self.monitor['top']}, "
                     f"w={self.monitor['width']}, h={self.monitor['height']})")

            try:
                while self._running:
                    if keyboard.is_pressed("esc"):
                        self.log("Получен ESC. Останавливаемся...")
                        break
                    if not self._running:
                        break
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
                        time.sleep(0.05)
            except Exception as exc:
                self.log(f"[Ошибка потока токаря] {str(exc)}")
            finally:
                self._running = False
