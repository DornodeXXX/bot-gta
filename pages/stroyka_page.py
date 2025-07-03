from PyQt5 import QtWidgets, QtCore
from widgets.switch_button import SwitchButton
from widgets.logger import CommonLogger
import os
import time
import keyboard

class StroykaPage(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        lay = QtWidgets.QVBoxLayout(self)

        head = QtWidgets.QHBoxLayout()
        head.addWidget(CommonLogger._make_label("Стройка | Шахта", 16))
        head.addStretch()
        self.switch = SwitchButton()
        self.switch.clicked.connect(self._toggle)
        head.addWidget(self.switch)
        lay.addLayout(head)

        self.counter = CommonLogger._make_label("Счётчик: 0", 14)
        lay.addWidget(self.counter)
        lay.addStretch()

        self.log_field = CommonLogger.create_log_field(lay)

    def _toggle(self, checked: bool):
        if checked:
            self._start_worker()
        else:
            self._stop_worker()

    def _start_worker(self):
        self.log_field.clear()
        self.worker = StroykaWorker()
        self.worker.log_signal.connect(self.log_field.append)
        self.worker.counter_signal.connect(self._update_counter)
        self.worker.start()

    def _stop_worker(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait()
            self.worker = None
        self.log_field.append("[■] Скрипт остановлен.")
        self.switch.setChecked(False)

    def _update_counter(self, value: int):
        self.counter.setText(f"Счётчик: {value}")


class StroykaWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    counter_signal = QtCore.pyqtSignal(int)

    CONFIDENCE = 0.95

    def __init__(self):
        super().__init__()
        self.running = False
        self.count = 0
        self.img_key = self._load_image_mappings()
        self._shown = {p: False for p in self.img_key}
        self._visible = {p: False for p in self.img_key}


    def _load_image_mappings(self) -> dict:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return {
            os.path.join(base, "assets", "stroyka", "image1.png"): "e",
            os.path.join(base, "assets", "stroyka", "image2.png"): "y",
            os.path.join(base, "assets", "stroyka", "image3.png"): "f",
            os.path.join(base, "assets", "stroyka", "image4.png"): "h",
        }

    def log(self, message: str):
        CommonLogger.log(message, self.log_signal)

    def safe_locate(self, path: str):
        return CommonLogger.safe_locate(path, self.CONFIDENCE, self.log_signal)

    def stop(self):
        self.running = False

    def run(self):
        self.running = True
        self.log("Поиск начат.")

        try:
            while self.running:
                self._process_images()
                time.sleep(0.10)
        except Exception as e:
            self.log(f"[Критическая ошибка]\n{str(e)}")
        finally:
            self.running = False

    def _process_images(self):
        for path, key in self.img_key.items():
            name = os.path.basename(path)

            if self.safe_locate(path):
                self._handle_visible_image(path, key, name)
            else:
                self._handle_missing_image(path, name)

    def _handle_visible_image(self, path: str, key: str, name: str):
        if not self._visible[path]:
            self._visible[path] = True
            self._shown[path] = False
            self.count += 1
            self.counter_signal.emit(self.count)
            self.log(f"[✓] Найдено → спам '{key}'")

        while self.running and self.safe_locate(path):
            if key == "f":
                keyboard.send(key)
            else:
                keyboard.press_and_release(key)
                
            time.sleep(0.03)

        self._visible[path] = False

    def _handle_missing_image(self, path: str, name: str):
        self._visible[path] = False
        if not self._shown[path]:
            self._shown[path] = True