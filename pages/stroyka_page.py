from PyQt5 import QtWidgets, QtCore
from widgets.common import CommonLogger, ScriptController, load_images, CommonUI, SettingsManager
from pynput.keyboard import Controller
import time
import threading
import keyboard

class StroykaPage(QtWidgets.QWidget):
    statusChanged = QtCore.pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.worker = None
        self.settings = SettingsManager()
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)

        header, self.switch = CommonUI.create_switch_header("Стройка | Шахта", "⛏️")
        self.switch.clicked.connect(self.handle_toggle)
        self.switch.clicked.connect(self.statusChanged.emit)
        layout.addLayout(header)

        settings_group, settings_layout = CommonUI.create_settings_group()
        hotkey_layout, self.hotkey_input = CommonUI.create_hotkey_input(default="f5", description="— вкл/выкл автонажатие Shift+W")
        self.counter = CommonUI.create_counter()

        settings_layout.addLayout(hotkey_layout)
        settings_layout.addWidget(self.counter)
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        layout.addStretch()

        self.log_output = CommonUI.add_log_field(layout)

    def _load_settings(self):
        self.hotkey_input.setText(self.settings.get("stroyka", "hotkey_stroyka", "f5"))

    def _save_settings(self):
        self.settings.save_group("stroyka", {
            "hotkey_stroyka": self.hotkey_input.text()
        })

    def handle_toggle(self):
        self._save_settings()
        worker_factory = lambda: StroykaWorker(self.hotkey_input.text())
        extra_signals = {
            "counter_signal": self._update_counter
        }
        ScriptController.toggle_script(
            widget=self,
            worker_factory=worker_factory,
            log_output=self.log_output,
            extra_signals=extra_signals
        )

    def _update_counter(self, value: int):
        self.counter.setText(f"Счётчик: {value}")

class StroykaWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    counter_signal = QtCore.pyqtSignal(int)
    CONFIDENCE = 0.95

    def __init__(self, hotkey: str = "f5"):
        super().__init__()
        self.running = False
        self.count = 0
        self.current_actions = 0
        self.img_key = load_images("stroyka", mapping={
            "image1.png": {"en": "e", "ru": "у"},
            "image2.png": {"en": "y", "ru": "н"},
            "image3.png": {"en": "f", "ru": "а"},
            "image4.png": {"en": "h", "ru": "р"},
        })
        self._stop = threading.Event()
        self._shown = {p: False for p in self.img_key}
        self._visible = {p: False for p in self.img_key}
        self.keyboard_controller = Controller()
        self.detection_cache = {}
        self._toggle_requested = False
        self._move_enabled = False
        self.hotkey = hotkey or "f5"

        keyboard.add_hotkey(self.hotkey, self._request_toggle_move)

    def log(self, message: str):
        self.log_signal.emit(message)

    def _request_toggle_move(self):
        self._toggle_requested = True

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
        rage_window_missing = True
        try:
            while self.running:
                if not CommonLogger.is_rage_mp_active():
                    if self._move_enabled:
                        keyboard.release("shift")
                        keyboard.release("w")
                        self._move_enabled = False
                        self.log("[■] Движение отключено (Shift+W отпущены)")
                    if rage_window_missing:
                        self.log("Окно RAGE Multiplayer не активно. Ожидание...")
                        rage_window_missing = False
                    self._stop.wait(1)
                    continue

                if not rage_window_missing:
                    self.log("Окно RAGE Multiplayer найдено.")
                    rage_window_missing = True

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
                start_time = time.time()
                for path, keys in self.img_key.items():
                    if self.safe_locate(path):
                        self._handle_visible_image(path, keys)
                        break
                
                elapsed = time.time() - start_time
                if elapsed < 0.02:
                    self._stop.wait(0.01)
        except Exception as e:
            self.log(f"[Критическая ошибка]\n{str(e)}")
        finally:
            self.running = False

    def _handle_visible_image(self, path: str, keys: dict):
        if not self._visible[path]:
            self._visible[path] = True
            self._shown[path] = False
            self.count += 1
            self.counter_signal.emit(self.count)
            self.log(f"[✓] Найдено → спам '{keys['en']}' и '{keys['ru']}'")
            
            self.current_actions = self.count

        press_count = 0
        max_presses = 45
        while self.running and press_count < max_presses:
            self.keyboard_controller.tap(keys['en'])
            self.keyboard_controller.tap(keys['ru'])
            press_count += 1
            if press_count % 5 == 0:
                self._stop.wait(0.001)


        if not self.safe_locate(path):
            self._visible[path] = False
            