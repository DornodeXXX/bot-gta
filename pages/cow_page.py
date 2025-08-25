from PyQt5 import QtWidgets, QtCore
from widgets.switch_button import SwitchButton
import time
import keyboard
import pyautogui
import cv2
import numpy as np
import mss
from widgets.logger import CommonLogger


class CowPage(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.worker: CowWorker | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        switch_layout = QtWidgets.QHBoxLayout()
        self.switch = SwitchButton()
        self.switch.clicked.connect(self.toggle_script)

        switch_layout.addWidget(CommonLogger._make_label("Коровы", 16))
        switch_layout.addStretch()
        switch_layout.addWidget(self.switch)
        layout.addLayout(switch_layout)
        
        self.counter_label = QtWidgets.QLabel("Счётчик: 0")
        self.counter_label.setObjectName("counter_label")
        
        '''hotkey_layout = QtWidgets.QHBoxLayout()
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
        
        hotkey_description = QtWidgets.QLabel("— вкл/выкл автонажатие E")
        hotkey_description.setObjectName("hotkey_description")
            
        input_group.addWidget(self.hotkey_input)
        input_group.addWidget(hotkey_description)
        
        hotkey_layout.addWidget(CommonLogger._make_label("Горячая клавиша:", 14))
        hotkey_layout.addLayout(input_group)
        
        layout.addLayout(hotkey_layout)'''
        layout.addWidget(self.counter_label)
        layout.addStretch()
        
        self.log_output = CommonLogger.create_log_field(layout)
        
    def toggle_script(self, checked: bool):
        if checked:
            self.log_output.clear()
            self.worker = CowWorker()
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
            self._append_log("[■] Скрипт коровки остановлен.")
            self.switch.setChecked(False)

    def _append_log(self, text: str):
        self.log_output.append(text)

    def _update_counter(self, value: int):
        self.counter_label.setText(f"Счётчик: {value}")


class CowWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    counter_signal = QtCore.pyqtSignal(int)

    def __init__(self, hotkey: str = "f5"):
        super().__init__()
        self._running = True
        self._count = 0
        self.templates = self._load_templates()
        self.monitor = self._auto_detect_region()
        self._move_enabled = False
        self._toggle_requested = False
        self.hotkey = hotkey or "f5"
        
        keyboard.add_hotkey(self.hotkey, self._request_toggle_move)

    def _request_toggle_move(self):
        self._toggle_requested = True

    def _load_templates(self):
        t1 = cv2.imread("assets/cow/1.png", cv2.IMREAD_UNCHANGED)
        t2 = cv2.imread("assets/cow/2.png", cv2.IMREAD_UNCHANGED)
        if t1 is None or t2 is None:
            raise FileNotFoundError("Не найдены шаблоны")
        return {
            "1": t1[:, :, :3],
            "2": t2[:, :, :3]
        }

    def _auto_detect_region(self):
        screen_width, screen_height = pyautogui.size()
        region_height = int(screen_height * 0.65)
        return {
            "left": 0,
            "top": int(screen_height * 0.35),
            "width": screen_width,
            "height": region_height
        }

    def log(self, message: str):
        CommonLogger.log(message, self.log_signal)

    def stop(self):
        self._running = False

    def run(self):
        with mss.mss() as sct:
            self.log("Скрипт коровы запущен. Нажми ESC для остановки.")
            self.log(f"Область поиска: {self.monitor}")

            try:
                while self._running:
                    if keyboard.is_pressed("esc"):
                        self.log("Получен ESC. Останавливаемся...")
                        self.stop()
                        break
                    
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

                    if "1" in scores and "2" in scores:
                        brighter = max(scores, key=scores.get)
                        if brighter == "1":
                            keyboard.send("a")
                            self._count += 1
                            self.log(f"[✓] найдена → A (#{self._count})")
                        else:
                            keyboard.send("d")
                            self._count += 1
                            self.log(f"[✓] найдена → D (#{self._count})")
                        self.counter_signal.emit(self._count)

                    time.sleep(0.1)

            except Exception as exc:
                self.log(f"[Ошибка потока] {str(exc)}")
            finally:
                self.stop()
