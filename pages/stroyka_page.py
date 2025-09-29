from PyQt5 import QtWidgets, QtCore
from widgets.switch_button import SwitchButton
import os
from pynput.keyboard import Controller
import time
from widgets.common import CommonLogger, ScriptController, load_images
import threading

class StroykaPage(QtWidgets.QWidget):
    statusChanged = QtCore.pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(20, 15, 20, 15)
        head = QtWidgets.QHBoxLayout()
        head.addWidget(CommonLogger._make_label("Стройка | Шахта", 16))
        head.addStretch()
        self.switch = SwitchButton()
        self.switch.clicked.connect(self.handle_toggle)
        self.switch.clicked.connect(self.statusChanged.emit)
        head.addWidget(self.switch)
        lay.addLayout(head)

        self.counter = CommonLogger._make_label("Счётчик: 0", 14)
        lay.addWidget(self.counter)
        lay.addStretch()

        self.log_output = CommonLogger.create_log_field(lay)

    def handle_toggle(self):
        ScriptController.toggle_script(
            widget=self,
            worker_factory=lambda: StroykaWorker(),
            log_output=self.log_output,
            extra_signals={
                "counter_signal": self._update_counter
            }
        )

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
        self.img_key = load_images("stroyka", mapping={
            "image1.png": {"en": "e", "ru": "у"},
            "image2.png": {"en": "y", "ru": "н"},
            "image3.png": {"en": "f", "ru": "а"},
            "image4.png": {"en": "h", "ru": "р"},
        })
        self._shown = {p: False for p in self.img_key}
        self._visible = {p: False for p in self.img_key}
        self._stop = threading.Event()
        self.keyboard_controller = Controller()
        self.last_detection_time = 0
        self.detection_cache = {}

    def log(self, message: str):
        CommonLogger.log(message, self.log_signal)

    def safe_locate(self, path: str):
        current_time = time.time()
        if path in self.detection_cache and current_time - self.detection_cache[path]['time'] < 0.1:
            return self.detection_cache[path]['result']
        
        result = CommonLogger.safe_locate(path, self.CONFIDENCE, self.log_signal)
        self.detection_cache[path] = {'result': result, 'time': current_time}
        return result

    def run(self):
        self.running = True
        self.log("Поиск начат.")

        try:
            while self.running:
                start_time = time.time()
                self._process_images()
                
                process_time = time.time() - start_time
                if process_time < 0.02:
                    time.sleep(0.01)
        except Exception as e:
            self.log(f"[Критическая ошибка]\n{str(e)}")
        finally:
            self.running = False

    def _process_images(self):
        for path, keys in self.img_key.items():
            if self.safe_locate(path):
                self._handle_visible_image(path, keys)
                break

    def _handle_visible_image(self, path: str, keys: dict):
        if not self._visible[path]:
            self._visible[path] = True
            self._shown[path] = False
            self.count += 1
            self.counter_signal.emit(self.count)
            self.log(f"[✓] Найдено → спам '{keys['en']}' и '{keys['ru']}'")

        press_count = 0
        max_presses = 45 
        
        while self.running and press_count < max_presses:
            self.keyboard_controller.tap(keys['en'])
            self.keyboard_controller.tap(keys['ru'])
            
            press_count += 1
            time.sleep(0.00002)

        if not self.safe_locate(path):
            self._visible[path] = False

    def _handle_missing_image(self, path: str):
        self._visible[path] = False
        if not self._shown[path]:
            self._shown[path] = True