from PyQt5 import QtWidgets, QtCore
import time
import cv2
import numpy as np
from pynput.keyboard import Key, Controller
import mss
from widgets.common import CommonLogger, ScriptController, HotkeyManager, SettingsManager, auto_detect_region,CommonUI

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

        header, self.switch = CommonUI.create_switch_header("Качалка", "🏋️")
        self.switch.clicked.connect(self.handle_toggle)
        self.switch.clicked.connect(self.statusChanged.emit)
        layout.addLayout(header)

        settings_group, settings_layout = CommonUI.create_settings_group()

        hotkey_layout, self.hotkey_input = CommonUI.create_hotkey_input(default="f5", description="— вкл/выкл автонажатие E")
        food_bind, self.food_bind = CommonUI.create_hotkey_input(default="k", description="— клавиша еды")
        food_pause_layout, self.pause_slider = CommonUI.create_slider_row("Время паузы еды:", 1, 3600, 50, step=1)

        self.counter_label = CommonUI.create_counter()

        settings_layout.addLayout(hotkey_layout)
        settings_layout.addLayout(food_bind)
        settings_layout.addLayout(food_pause_layout)
        settings_layout.addWidget(self.counter_label)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        layout.addStretch()

        self.log_output = CommonUI.add_log_field(layout)


    def _load_settings(self):
        self.hotkey_input.setText(self.settings.get("gym", "hotkey_port", "f5"))
        self.food_bind.setText(self.settings.get("gym", "food_bind", "k"))
        self.pause_slider.setValue(self.settings.get("gym", "pause", 1800))

    def _save_settings(self):
        self.settings.save_group("gym", {
            "pause": self.pause_slider.value(),
            "hotkey_port": self.hotkey_input.text(),
            "food_bind": self.food_bind.text()
        })

    def handle_toggle(self):
        self._save_settings()
        ScriptController.toggle_script(
            widget=self,
            worker_factory=GymWorker,
            log_output=self.log_output,
            extra_signals={"counter_signal": self._update_counter},
            worker_kwargs={"hotkey": self.hotkey_input.text().strip() or 'f5', "pause_delay": self.pause_slider.value(),"key_food": self.food_bind.text().strip() or 'k'}
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


    eng_to_rus = {
        'q': 'й', 'w': 'ц', 'e': 'у', 'r': 'к', 't': 'е', 'y': 'н', 'u': 'г',
        'i': 'ш', 'o': 'щ', 'p': 'з', '[': 'х', ']': 'ъ',
        'a': 'ф', 's': 'ы', 'd': 'в', 'f': 'а', 'g': 'п', 'h': 'р', 'j': 'о',
        'k': 'л', 'l': 'д', ';': 'ж', "'": 'э',
        'z': 'я', 'x': 'ч', 'c': 'с', 'v': 'м', 'b': 'и', 'n': 'т', 'm': 'ь',
        ',': 'б', '.': 'ю', '/': '.'
    }

    def __init__(self, monitor: dict = None, hotkey: str = 'f5', pause_delay: float = 0.0, key_food: str = 'k'):
        super().__init__()
        self.running = True
        self._count = 0
        self.pause_delay = pause_delay
        self.key_food = key_food
        lower = self.key_food.lower()
        self.rus_key = self.eng_to_rus.get(lower, self.key_food)
        if self.key_food.isupper():
            self.rus_key = self.rus_key.upper()
        self.monitor = monitor or auto_detect_region(reference_height=1440, reference_top=560)
        self._hotkey = (hotkey or 'f5').lower().strip()
        self._hotkey_id = None
        self._auto_e_enabled = False
        self._last_e_time = 0.0
        self.keyboard_controller = Controller()
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
                        self.keyboard_controller.tap(Key.space)

                    if not found:
                        now = time.time()
                        if now - getattr(self, "_last_k_time", 0) >= self.pause_delay:
                            self.keyboard_controller.tap(self.key_food)
                            self.keyboard_controller.tap(self.rus_key)
                            self._last_k_time = now
                            self.log(f"Нажата {self.key_food} (еда)")
                        if self._auto_e_enabled:
                            now = time.time()
                            if now - self._last_e_time >= 5.0:
                                self.keyboard_controller.tap('e')
                                self.keyboard_controller.tap('у')
                                self._last_e_time = now
                                self.log("Нажата 'E' (авто)")

                    was_found = found

        except Exception as exc:
            self.log(f"[Ошибка потока] {exc}")
        finally:
            self.hotkey_manager.unregister()
            self.running = False