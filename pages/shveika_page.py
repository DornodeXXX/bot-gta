from PyQt5 import QtWidgets, QtCore
from widgets.switch_button import SwitchButton
import os
import time
import traceback
import pyautogui
from pyautogui import ImageNotFoundException
import keyboard
from widgets.logger import CommonLogger, ScriptController

class ShveikaPage(QtWidgets.QWidget):
    statusChanged = QtCore.pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        self.worker: ShveikaWorker | None = None
        self._init_ui()

    def _init_ui(self):
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(20, 15, 20, 15)
        head = QtWidgets.QHBoxLayout()
        head.addWidget(CommonLogger._make_label("Швейка Авто-Кликер", 16))
        head.addStretch()
        self.switch = SwitchButton()
        self.switch.clicked.connect(self.handle_toggle)
        self.switch.clicked.connect(self.statusChanged.emit)
        head.addWidget(self.switch)
        lay.addLayout(head)

        self.counter_label = CommonLogger._make_label("Цикл: 0", 14)
        lay.addWidget(self.counter_label)
        lay.addStretch()

        self.log_output = CommonLogger.create_log_field(lay)

    def handle_toggle(self):
        ScriptController.toggle_script(
            widget=self,
            worker_factory=lambda: ShveikaWorker(),
            log_output=self.log_output,
            extra_signals={
                "counter_signal": self._update_counter
            }
        )

    def _update_counter(self, value: int):
        self.counter_label.setText(f"Счётчик: {value}")

class ShveikaWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    counter_signal = QtCore.pyqtSignal(int)

    CONFIDENCE = 0.95

    def __init__(self):
        super().__init__()
        self.running = True
        self.count = 0

        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.image_paths = [
            os.path.join(base, "assets", "shveika", f"{i}.png") for i in range(1, 21)
        ]

    def log(self, message: str):
        CommonLogger.log(message, self.log_signal)

    def stop(self):
        self.running = False

    def safe_locate_center(self, path: str):
        return CommonLogger.safe_locate_center(path, self.CONFIDENCE, self.log_signal)

    def run(self):
        for path in self.image_paths:
            if not os.path.exists(path):
                self.log(f"[Ошибка] Файл не найден: {path}")
                return

        self.log("Скрипт запущен. Ожидание всех 20 элементов...")

        while self.running:
            coords = []
            missing_indices = []

            for i, path in enumerate(self.image_paths):
                center = self.safe_locate_center(path)
                coords.append(center)
                if center is None:
                    missing_indices.append(i + 1)
                    
            if all(coords):
                self.count += 1
                self.counter_signal.emit(self.count)
                self.log(f"[✓] Все 20 точек найдены. Начинаю клик.")
                for i, pos in enumerate(coords):
                    if not self.running:
                        break
                    if pos is None:
                        self.log(f"[⚠️] Пропуск {i+1} — координаты не найдены.")
                        continue
                    if i == 0:
                        pyautogui.click(pos)
                        self.log(f"[Клик] {i+1}/20: {pos} (1 раз)")
                    else:
                        pyautogui.click(pos)
                        time.sleep(0.05)
                        pyautogui.click(pos)
                        self.log(f"[Клик] {i+1}/20: {pos} (2 раза)")
            else:
                self.log(f"[~] Ожидание всех 20 элементов...")

