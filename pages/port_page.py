from PyQt5 import QtWidgets, QtCore
from widgets.switch_button import SwitchButton
import time
import keyboard
import pygetwindow as gw
import pyautogui
from widgets.logger import CommonLogger


class PortPage(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.worker: PortWorker | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        switch_layout = QtWidgets.QHBoxLayout()
        self.switch = SwitchButton()
        self.switch.clicked.connect(self.toggle_script)

        switch_layout.addWidget(CommonLogger._make_label("Порт", 16))
        switch_layout.addStretch()
        switch_layout.addWidget(self.switch)
        layout.addLayout(switch_layout)
        
        self.counter_label = QtWidgets.QLabel("Счётчик: 0")
        self.counter_label.setObjectName("counter_label")

        hotkey_layout = QtWidgets.QHBoxLayout()
        hotkey_layout.setContentsMargins(0, 0, 0, 0)
        hotkey_layout.setSpacing(5)
        
        input_group = QtWidgets.QHBoxLayout()
        input_group.setSpacing(5)
        input_group.setContentsMargins(0, 0, 0, 0)
        
        self.hotkey_input = QtWidgets.QLineEdit("f5")
        self.hotkey_input.setMaxLength(20)
        self.hotkey_input.setFixedWidth(50)
        self.hotkey_input.setAlignment(QtCore.Qt.AlignCenter)
        self.hotkey_input.setStyleSheet("""
            background-color: #222; 
            color: white;
            font-size: 12px;
        """)
        
        hotkey_description = QtWidgets.QLabel("— вкл/выкл автонажатие Shift+W")
        hotkey_description.setObjectName("hotkey_description")
        
        input_group.addWidget(self.hotkey_input)
        input_group.addWidget(hotkey_description)
        
        hotkey_layout.addWidget(CommonLogger._make_label("Горячая клавиша:", 14))
        hotkey_layout.addLayout(input_group)
        
        layout.addLayout(hotkey_layout)
        layout.addWidget(self.counter_label)
        layout.addStretch()
        
        self.log_output = CommonLogger.create_log_field(layout)

    def toggle_script(self, checked: bool):
        if checked:
            self.log_output.clear()
            self.worker = PortWorker(self.hotkey_input.text())
            self.worker.log_signal.connect(self._append_log)
            self.worker.counter_signal.connect(self._update_counter)
            self.worker.start()
        else:
            self._stop_worker()

    def _stop_worker(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait()
            self.worker = None
            self._append_log("[■] Скрипт остановлен.")
            self.switch.setChecked(False)

    def _append_log(self, text: str):
        self.log_output.append(text)

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

                screenshot = pyautogui.screenshot()
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
