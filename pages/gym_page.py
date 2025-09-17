from PyQt5 import QtWidgets, QtCore
from widgets.switch_button import SwitchButton
import time
import keyboard
import pyautogui
import cv2
import numpy as np
import mss
from widgets.common import CommonLogger, ScriptController, HotkeyManager, SettingsManager, auto_detect_region

class GymPage(QtWidgets.QWidget):
    statusChanged = QtCore.pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.worker: GymWorker | None = None
        self.settings = SettingsManager()
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        switch_layout = QtWidgets.QHBoxLayout()
        self.switch = SwitchButton()
        self.switch.clicked.connect(self.handle_toggle)
        self.switch.clicked.connect(self.statusChanged.emit)

        switch_layout.addWidget(CommonLogger._make_label("Качалка", 16))
        switch_layout.addStretch()
        switch_layout.addWidget(self.switch)
        layout.addLayout(switch_layout)

        self.counter_label = CommonLogger._make_label("Счётчик: 0", 14)
        
        hotkey_layout, self.hotkey_input = CommonLogger.create_hotkey_input(
            default="f5", description="— вкл/выкл автонажатие E"
        )
        
        layout.addLayout(hotkey_layout)
        
        layout.addWidget(self.counter_label)
        layout.addStretch()

        self.log_output = CommonLogger.create_log_field(layout)

    def _load_settings(self):
        self.hotkey_input.setText(self.settings.get("gym", "hotkey_port", "f5"))

    def _save_settings(self):
        self.settings.save_group("gym", {
            "hotkey_port": self.hotkey_input.text()
        })

    def handle_toggle(self):
        self._save_settings()
        ScriptController.toggle_script(
            widget=self,
            worker_factory=GymWorker,
            log_output=self.log_output,
            extra_signals={"counter_signal": self._update_counter},
            worker_kwargs={"hotkey": self.hotkey_input.text().strip() or 'f5'}
        )

    def _update_counter(self, value: int):
        self.counter_label.setText(f"Счётчик: {value}")

class GymWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    counter_signal = QtCore.pyqtSignal(int)

    TARGET_RGB = (120, 255, 166)

    H_TOL = 0   #оттенок 10
    S_TOL = 0   #насыщенность 15
    V_TOL = 0   #яркость

    MIN_AREA = 50
    
    def __init__(self, monitor: dict = None, hotkey: str = 'f5'):
        super().__init__()
        self.running = True
        self._count = 0
        self.monitor = monitor or auto_detect_region(reference_height=1440, reference_top=560)
        self._hotkey = (hotkey or 'f5').lower().strip()
        self._hotkey_id = None
        self._auto_e_enabled = False
        self._last_e_time = 0.0
        self.hotkey_manager = HotkeyManager(
            hotkey=hotkey,
            toggle_callback=self._on_toggle_auto_e,
            log_signal=self.log_signal
        )
     
    def _on_toggle_auto_e(self, enabled: bool):
        self._auto_e_enabled = enabled
        
    def rgb_to_hsv_bounds(self, rgb, h_tol, s_tol, v_tol):
        bgr = np.uint8([[[rgb[2], rgb[1], rgb[0]]]])
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[0, 0]
        h, s, v = int(hsv[0]), int(hsv[1]), int(hsv[2])

        lower = np.array([max(0,   h - h_tol), max(0,   s - s_tol), max(0,   v - v_tol)], dtype=np.uint8)
        upper = np.array([min(179, h + h_tol), min(255, s + s_tol), min(255, v + v_tol)], dtype=np.uint8)
        return lower, upper

    def found_circle_by_color(self, frame_bgr, lower, upper):
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower, upper)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.MIN_AREA:
                continue

            perim = cv2.arcLength(cnt, True)
            if perim == 0:
                continue

            '''circularity = 4 * math.pi * area / (perim * perim)
            if circularity < MIN_CIRCULARITY:
                continue'''

            return True
        return False

    def log(self, message: str):
        CommonLogger.log(message, self.log_signal)

    def run(self):
        lower, upper = self.rgb_to_hsv_bounds(self.TARGET_RGB, self.H_TOL, self.S_TOL, self.V_TOL)
        was_found = False
        self._last_e_time = time.time()

        self.log(f"Запуск. Область поиска: {self.monitor}")
        self.hotkey_manager.register()
        try:
            with mss.mss() as sct:
                while self.running:
                    img = np.array(sct.grab(self.monitor))
                    frame_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                    found = self.found_circle_by_color(frame_bgr, lower, upper)

                    if found and not was_found:
                        self.log(f"Круг найден, нажимаем пробел")
                        keyboard.press_and_release('space')

                    if not found and self._auto_e_enabled:
                        now = time.time()
                        if now - self._last_e_time >= 5.0:
                            keyboard.press_and_release('e')
                            self._last_e_time = now
                            self.log("Нажата 'E' (авто)")

                    was_found = found

        except Exception as exc:
            self.log(f"[Ошибка потока] {exc}")
        finally:
            self.hotkey_manager.unregister()
            self.running = False