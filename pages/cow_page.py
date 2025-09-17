from PyQt5 import QtWidgets, QtCore
from widgets.switch_button import SwitchButton
import time
import keyboard
import pyautogui
from pynput.keyboard import Controller, Key
import cv2
import numpy as np
import mss
from widgets.common import CommonLogger, ScriptController, HotkeyManager, SettingsManager, auto_detect_region, load_images
import threading

class CowPage(QtWidgets.QWidget):
    statusChanged = QtCore.pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        self.worker: CowWorker | None = None
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

        switch_layout.addWidget(CommonLogger._make_label("Коровы", 16))
        switch_layout.addStretch()
        switch_layout.addWidget(self.switch)
        layout.addLayout(switch_layout)
        
        self.counter_label = CommonLogger._make_label("Счётчик: 0", 14)
        
        hotkey_layout, self.hotkey_input = CommonLogger.create_hotkey_input(
            default="f5", description="— вкл/выкл автонажатие E"
        )

        settings_group = QtWidgets.QGroupBox("")
        settings_group.setStyleSheet("QGroupBox { color: white; font-weight: bold; background: none; }")

        settings_layout = QtWidgets.QVBoxLayout()
        settings_layout.setSpacing(10)
        settings_layout.setContentsMargins(10, 10, 10, 10)

        pause_layout, self.pause_slider, self.min_label = CommonLogger.create_slider_row(
            "Время паузы:", minimum=0, maximum=100, default=1, suffix="сек", step=0.1
        )

        settings_group.setStyleSheet("background: none;")
        settings_group.setLayout(settings_layout)

        settings_layout.addLayout(pause_layout)
        layout.addLayout(hotkey_layout)
        layout.addWidget(settings_group)
        layout.addWidget(self.counter_label)
        layout.addStretch()
        
        CommonLogger.create_slider_row

        self.log_output = CommonLogger.create_log_field(layout)
        
    def _load_settings(self):
        self.hotkey_input.setText(self.settings.get("cow", "hotkey_port", "f5"))
        self.pause_slider.setValue(self.settings.get("cow", "pause", 1))

    def _save_settings(self):
        self.settings.save_group("cow", {
            "pause": self.pause_slider.value(),
            "hotkey_port": self.hotkey_input.text()
        })

    def handle_toggle(self):
        self._save_settings()
        ScriptController.toggle_script(
            widget=self,
            worker_factory=CowWorker,
            log_output=self.log_output,
            extra_signals={"counter_signal": self._update_counter},
            worker_kwargs={"hotkey": self.hotkey_input.text().strip() or 'f5', "pause_delay": self.pause_slider.value() / 10.0}
        )

    def _update_counter(self, value: int):
        self.counter_label.setText(f"Счётчик: {value}")


class CowWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    counter_signal = QtCore.pyqtSignal(int)

    def __init__(self, pause_delay=0 ,hotkey: str = 'f5'):
        super().__init__()
        self.running = True
        self._count = 0
        self.templates = load_images("cow", mapping={"1.png": "1", "2.png": "2"}, as_cv2=True)
        self.monitor = auto_detect_region(width_ratio=1.0, height_ratio=0.65, top_ratio=0.35)
        self._move_enabled = False
        self._toggle_requested = False
        self.pause_delay = pause_delay
        self._stop = threading.Event()
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

    def log(self, message: str):
        CommonLogger.log(message, self.log_signal)
        
    def run(self):
        self.hotkey_manager.register()
        with mss.mss() as sct:
            self.log("Скрипт коровы запущен.")
            self.log(f"Область поиска: {self.monitor}")

            try:
                while self.running and not self._stop.is_set():
                    frame = np.array(sct.grab(self.monitor))
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                    scores = {}
                    locations = {}

                    for key, template in self.templates.items():
                        res = cv2.matchTemplate(frame_rgb, template, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, max_loc = cv2.minMaxLoc(res)
                        if max_val >= 0.91:
                            h, w = template.shape[:2]
                            roi = frame_rgb[max_loc[1]:max_loc[1]+h, max_loc[0]:max_loc[0]+w]
                            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                            brightness = np.mean(gray)
                            scores[key] = brightness
                            locations[key] = max_val

                    found = bool(scores)
                    
                    if "1" in scores and "2" in scores:
                        brighter = max(scores, key=scores.get)
                        if brighter == "1":
                            keyboard_controller = Controller()
                            keyboard_controller.press("a")
                            time.sleep(0.01)
                            keyboard_controller.release("a")
                            self._count += 1
                            self.log(f"[✓] найдена → A (#{self._count})")
                        else:
                            keyboard.send("d")
                            self._count += 1
                            self.log(f"[✓] найдена → D (#{self._count})")
                        self.counter_signal.emit(self._count)
                        
                    if not found and self._auto_e_enabled:
                        keyboard.press_and_release('e')
                        self.log("Нажата 'E' (авто)")
                            
                    if self._stop.wait(self.pause_delay):
                        break

            except Exception as exc:
                self.log(f"[Ошибка потока] {str(exc)}")
            finally:
                self.hotkey_manager.unregister()
                self.stop()
