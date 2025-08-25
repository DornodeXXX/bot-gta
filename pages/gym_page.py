from PyQt5 import QtWidgets, QtCore
from widgets.switch_button import SwitchButton
import time
import keyboard
import pyautogui
import cv2
import numpy as np
import mss
from widgets.logger import CommonLogger


class GymPage(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.worker: GymWorker | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        switch_layout = QtWidgets.QHBoxLayout()
        self.switch = SwitchButton()
        self.switch.clicked.connect(self.toggle_script)

        switch_layout.addWidget(CommonLogger._make_label("Качалка", 16))
        switch_layout.addStretch()
        switch_layout.addWidget(self.switch)
        layout.addLayout(switch_layout)
        
        self.counter_label = QtWidgets.QLabel("Счётчик: 0")
        self.counter_label.setObjectName("counter_label")
        layout.addWidget(self.counter_label)
        layout.addStretch()
        
        self.log_output = CommonLogger.create_log_field(layout)

    def toggle_script(self, checked: bool):
        if checked:
            self.log_output.clear()
            self.worker = GymWorker()
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
            self._append_log("[■] Скрипт качалки остановлен.")
            self.switch.setChecked(False)

    def _append_log(self, text: str):
        self.log_output.append(text)

    def _update_counter(self, value: int):
        self.counter_label.setText(f"Счётчик: {value}")

class GymWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    counter_signal = QtCore.pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self._running = True
        self._count = 0
        self.template = self._load_template()
        self.monitor = self._auto_detect_region()
        self.last_action_time = time.time()
        self.circle_pos = None

    def _load_template(self):
        template = cv2.imread('assets/gym/circle.png', cv2.IMREAD_UNCHANGED)
        if template is None:
            raise FileNotFoundError("Шаблон не найден!")
        return template[:, :, :3]

    def _auto_detect_region(self):
        screen_width, screen_height = pyautogui.size()
        region_width = int(screen_width * 0.5)
        region_height = int(screen_height * 0.6)
        vertical_position_ratio = 0.25
        return {
            'left': int((screen_width - region_width) / 2),
            'top': int(screen_height * vertical_position_ratio),
            'width': region_width,
            'height': region_height
        }

    def log(self, message: str):
        CommonLogger.log(message, self.log_signal)

    def stop(self):
        self._running = False

    def run(self):
        with mss.mss() as sct:
            self.log("Скрипт качалки запущен. Нажми ESC для остановки.")
            self.log(f"Область поиска: {self.monitor}")

            try:
                while self._running:
                    if keyboard.is_pressed("esc"):
                        self.log("Получен ESC. Останавливаемся...")
                        self.stop()
                        break

                    frame = np.array(sct.grab(self.monitor))
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                    res = cv2.matchTemplate(frame_rgb, self.template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, max_loc = cv2.minMaxLoc(res)
                    if max_val >= 0.94:
                        h, w = self.template.shape[:2]
                        self.circle_pos = (max_loc[0] + w // 2, max_loc[1] + h // 2, max(w, h) // 2)
                        #self.log(f"[+] Найден основной круг (score={max_val:.2f})")
                    else:
                        time.sleep(0.05)
                        continue

                    x, y, r = self.circle_pos
                    roi = frame_rgb[y-r-10:y+r+10, x-r-10:x+r+10]
                    if roi.size == 0:
                        continue

                    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                    _, mask = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY)

                    white_ratio = np.sum(mask > 0) / mask.size

                    if white_ratio > 0.05:
                        self._count += 1
                        self.log(f"[✓] Найдено совпадение -> SPACE (#{self._count})")
                        self.counter_signal.emit(self._count)
                        keyboard.press_and_release("space")
                        self.last_action_time = time.time()
                        time.sleep(0.3)

                    if time.time() - self.last_action_time >= 5:
                        self.log("[!] 5 секунд без действия - нажимаем E")
                        keyboard.press_and_release("e")
                        self.last_action_time = time.time()

                    time.sleep(0.01)

            except Exception as exc:
                self.log(f"[Ошибка потока] {str(exc)}")
            finally:
                self.stop()
