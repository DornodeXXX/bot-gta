from PyQt5 import QtWidgets, QtCore
from widgets.switch_button import SwitchButton
import time
import keyboard
import cv2
import numpy as np
import mss
import os
from pynput.keyboard import Controller
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
            "Время паузы:", minimum=0.07, maximum=5, default=0.07, suffix="сек", step=0.01
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

    def __init__(self, pause_delay=0, hotkey: str = 'f5'):
        super().__init__()
        self.running = True
        self._count = 0
        try:
            cv2.setUseOptimized(True)
            cv2.setNumThreads(max(1, os.cpu_count() - 1))
        except Exception:
            pass
        self.templates = load_images("cow", mapping={"1.png": "1", "2.png": "2"}, as_cv2=True)
        self.monitor = auto_detect_region(width_ratio=1.0, height_ratio=0.65, top_ratio=0.35)
        self.pause_delay = 0.04
        self._stop = threading.Event()
        self._auto_e_enabled = False
        self.min_press_interval = 0
        self._last_press_time = 0.0
        self.ui_update_every = 5
        self.keyboard_controller = Controller()
        self.hotkey_manager = HotkeyManager(
            hotkey=hotkey,
            toggle_callback=self._on_toggle_auto_e,
            log_signal=self.log_signal
        )

    def _on_toggle_auto_e(self, enabled: bool):
        self._auto_e_enabled = enabled

    def log(self, message: str):
        CommonLogger.log(message, self.log_signal)

    def _tap(self, key: str):
        keyboard.press_and_release(key)

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
                    for key, template in self.templates.items():
                        res = cv2.matchTemplate(frame_rgb, template, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, _ = cv2.minMaxLoc(res)
                        if max_val >= 0.91:
                            scores[key] = max_val

                    found = bool(scores)

                    if found:
                        now = time.time()
                        if now - self._last_press_time >= self.min_press_interval:
                            if scores.get("1", -1) >= scores.get("2", -1):
                                self.keyboard_controller.tap('a')
                                self.keyboard_controller.tap('ф')
                            else:
                                self.keyboard_controller.tap('d')
                                self.keyboard_controller.tap('в')

                            self._last_press_time = now
                            if self._count % self.ui_update_every == 0:
                                self.counter_signal.emit(self._count)

                    elif self._auto_e_enabled:
                        self.keyboard_controller.tap('e')
                        self.keyboard_controller.tap('у')

                    if self.pause_delay > 0:
                        if self._stop.wait(self.pause_delay):
                            break

            except Exception as exc:
                self.log(f"[Ошибка потока] {str(exc)}")
            finally:
                self.hotkey_manager.unregister()
                self.stop()