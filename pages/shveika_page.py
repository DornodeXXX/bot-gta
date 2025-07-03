from PyQt5 import QtWidgets, QtCore
from widgets.switch_button import SwitchButton
import os
import time
import traceback
import pyautogui
from pyautogui import ImageNotFoundException
import keyboard
from widgets.logger import CommonLogger

class ShveikaPage(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.worker: ShveikaWorker | None = None
        self._init_ui()

    def _init_ui(self):
        lay = QtWidgets.QVBoxLayout(self)

        head = QtWidgets.QHBoxLayout()
        head.addWidget(CommonLogger._make_label("Швейка Авто-Кликер", 16))
        head.addStretch()
        self.switch = SwitchButton()
        self.switch.clicked.connect(self._toggle)
        head.addWidget(self.switch)
        lay.addLayout(head)

        self.counter = CommonLogger._make_label("Цикл: 0", 14)
        lay.addWidget(self.counter)
        lay.addStretch()

        self.log_field = CommonLogger.create_log_field(lay)

    def _toggle(self, checked: bool):
        if checked:
            self.log_field.clear()
            self.worker = ShveikaWorker()
            self.worker.log_signal.connect(self.log_field.append)
            self.worker.counter_signal.connect(lambda v: self.counter.setText(f"Цикл: {v}"))
            self.worker.start()
        else:
            if self.worker:
                self.worker.stop()
                self.worker.wait()
                self.worker = None
            self.log_field.append("[■] Скрипт остановлен.")
            self.switch.setChecked(False)


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
            if keyboard.is_pressed("f5"):
                self.log("[■] Остановлено по F5")
                self.stop()
                break

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
                    
                    time.sleep(0.5)
            else:
                self.log(f"[~] Ожидание всех 20 элементов...")
            time.sleep(0.5)
