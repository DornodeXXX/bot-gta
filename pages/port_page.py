from PyQt5 import QtWidgets, QtCore
from widgets.switch_button import SwitchButton
import time
import keyboard
import pygetwindow as gw
import pyautogui
from widgets.logger import CommonLogger, ScriptController
import numpy as np

class PortPage(QtWidgets.QWidget):
    statusChanged = QtCore.pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        self.worker: PortWorker | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        switch_layout = QtWidgets.QHBoxLayout()
        self.switch = SwitchButton()
        self.switch.clicked.connect(self.handle_toggle)
        self.switch.clicked.connect(self.statusChanged.emit)
        
        switch_layout.addWidget(CommonLogger._make_label("Порт", 16))
        switch_layout.addStretch()
        switch_layout.addWidget(self.switch)
        layout.addLayout(switch_layout)
        
        self.counter_label = QtWidgets.QLabel("Счётчик: 0")
        self.counter_label.setObjectName("counter_label")

        hotkey_layout, self.hotkey_input = CommonLogger.create_hotkey_input(
            default="f5", description="— вкл/выкл автонажатие Shift+W"
        )
        
        layout.addLayout(hotkey_layout)
        layout.addWidget(self.counter_label)
        layout.addStretch()
        
        self.log_output = CommonLogger.create_log_field(layout)

    def handle_toggle(self):
        ScriptController.toggle_script(
            widget=self,
            worker_factory=lambda: PortWorker(self.hotkey_input.text()),
            log_output=self.log_output,
            extra_signals={
                "counter_signal": self._update_counter
            }
        )

    def _update_counter(self, value: int):
        self.counter_label.setText(f"Счётчик: {value}")


class PortWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    counter_signal = QtCore.pyqtSignal(int)

    GREEN = (126, 211, 33)
    RED = (231, 33, 57)
    TOLERANCE = 20
    STEP_X = 4
    STEP_Y = 10
    SEARCH_DELAY = 0.01

    def __init__(self, hotkey: str = "f5"):
        super().__init__()
        self._running = True
        self._count = 0
        self._move_enabled = False
        self._toggle_requested = False
        self.hotkey = hotkey or "f5"
        self.monitor = self._auto_detect_region()

        keyboard.add_hotkey(self.hotkey, self._request_toggle_move)

    def log(self, message: str):
        CommonLogger.log(message, self.log_signal)

    def stop(self):
        self._running = False
        keyboard.unhook_all_hotkeys()
        if self._move_enabled:
            keyboard.release("shift")
            keyboard.release("w")
            self._move_enabled = False
            self.log("[■] Движение отключено (Shift+W отпущены)")

    def _auto_detect_region(self):
        screen_width, screen_height = pyautogui.size()
        region_width = int(screen_width * 0.5)
        region_height = int(screen_height * 0.7)
        vertical_position_ratio = 0.25
        return {
            'left': int((screen_width - region_width) / 2),
            'top': int(screen_height * vertical_position_ratio),
            'width': region_width,
            'height': region_height
        }

    def _request_toggle_move(self):
        self._toggle_requested = True

    @staticmethod
    def _is_color_close(c1: tuple[int, int, int], c2: tuple[int, int, int], tol: int) -> bool:
        return all(abs(a - b) <= tol for a, b in zip(c1, c2))

    def run(self):
        self.log("Скрипт запущен. Нажми ESC для остановки или используй переключатель.")
        rage_window_missing = True
        try:
            while self._running:
                if not CommonLogger.is_rage_mp_active():
                    if self._move_enabled:
                        keyboard.release("shift")
                        keyboard.release("w")
                        self._move_enabled = False
                        self.log("[■] Движение отключено (Shift+W отпущены)")
                    if rage_window_missing:
                        self.log("Окно RAGE Multiplayer не активно. Ожидание...")
                        rage_window_missing = False
                    time.sleep(1.0)
                    continue

                if not rage_window_missing:
                    self.log("Окно RAGE Multiplayer найдено.")
                    rage_window_missing = True

                if keyboard.is_pressed("esc"):
                    self.log("Получен ESC. Останавливаемся…")
                    self.stop()
                    break

                if self._toggle_requested:
                    self._move_enabled = not self._move_enabled
                    if self._move_enabled:
                        keyboard.press("shift")
                        keyboard.press("w")
                        self.log("[→] Движение включено (Shift+W зажаты)")
                    else:
                        keyboard.release("shift")
                        keyboard.release("w")
                        self.log("[■] Движение отключено (Shift+W отпущены)")
                    self._toggle_requested = False

                screenshot = pyautogui.screenshot(region=tuple(self.monitor.values()))
                pixels = screenshot.load()
                width, height = screenshot.size
                found = False

                for y in range(0, height, self.STEP_Y):
                    for x in range(0, width, self.STEP_X):
                        if self._is_color_close(pixels[x, y], self.RED, self.TOLERANCE):
                            for dx in range(-10, 11):
                                nx = x + dx
                                if 0 <= nx < width and self._is_color_close(pixels[nx, y], self.GREEN, self.TOLERANCE):
                                    found = True
                                    break
                        if found:
                            break
                    if found:
                        break

                if found:
                    self._count += 1
                    self.log(f"[✓] Найдена мини-игра — нажимаем E (#{self._count})")
                    self.counter_signal.emit(self._count)
                    keyboard.press_and_release("e")
                    time.sleep(0.5)

                time.sleep(self.SEARCH_DELAY)

        except Exception as exc:
            self.log(f"[Ошибка потока] {exc}")
            self.stop()
