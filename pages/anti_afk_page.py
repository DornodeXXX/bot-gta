from widgets.switch_button import SwitchButton
from PyQt5 import QtWidgets, QtCore
import random
import vgamepad as vg
from widgets.logger import CommonLogger, ScriptController
import threading
import os
import pyautogui
import keyboard
from typing import Optional, Tuple, Callable
import time

BASE_ASSETS_PATH = "assets/spin/"

class AntiAfkPage(QtWidgets.QWidget):
    statusChanged = QtCore.pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)

        self.switch = SwitchButton()
        self.switch.clicked.connect(self.handle_toggle)
        self.switch.clicked.connect(self.statusChanged.emit)

        self.checkwheel = QtWidgets.QCheckBox('Авто Колесо — раз в 5 мин', self)
        self.checkwheel.setGeometry(20, 85, 200, 20)
        self.checkwheel.setStyleSheet("""
            QCheckBox {
                color: white;
            }

            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #ffffff;
                border-radius: 9px;
                background: transparent;
            }

            QCheckBox::indicator:checked {
                border: 1px solid #0A84FF;
                background-color: #0A84FF;
                image: url(assets/check.png);
            }
        """)

        switch_layout = QtWidgets.QHBoxLayout()
        switch_layout.addWidget(CommonLogger._make_label("Анти-АФК", 16))
        switch_layout.addStretch()
        switch_layout.addWidget(self.checkwheel)
        switch_layout.addWidget(self.switch)
        layout.addLayout(switch_layout)

        settings_group = QtWidgets.QGroupBox("")
        settings_group.setStyleSheet("QGroupBox { color: white; font-weight: bold; background: none; }")
        settings_layout = QtWidgets.QVBoxLayout()
        settings_layout.setSpacing(10)
        settings_layout.setContentsMargins(10, 10, 10, 10)

        settings_layout.addWidget(CommonLogger._make_label("Время зажатия:", 17))
        min_delay_row, self.min_delay_slider, self.min_label = CommonLogger.create_slider_row(
            "Мин. зажатие:", minimum=5, maximum=100, default=10, step=0.1
        )
        max_delay_row, self.max_delay_slider, self.max_label = CommonLogger.create_slider_row(
            "Макс. зажатие:", minimum=5, maximum=100, default=35, step=0.1
        )
        settings_layout.addLayout(min_delay_row)
        settings_layout.addLayout(max_delay_row)

        settings_layout.addWidget(CommonLogger._make_label("Пауза между движениями:", 17))
        min_pause_row, self.min_pause_slider, self.min_pause_label = CommonLogger.create_slider_row(
            "Мин. пауза:", minimum=5, maximum=100, default=5, step=0.1
        )
        max_pause_row, self.max_pause_slider, self.max_pause_label = CommonLogger.create_slider_row(
            "Макс. пауза:", minimum=5, maximum=100, default=20, step=0.1
        )
        settings_layout.addLayout(min_pause_row)
        settings_layout.addLayout(max_pause_row)

        settings_group.setLayout(settings_layout)

        layout.addWidget(settings_group)
        layout.addStretch()

        self.log_output = CommonLogger.create_log_field(layout)
        self.setLayout(layout)

    def handle_toggle(self):
        ScriptController.toggle_script(widget=self,
            worker_factory=lambda: AntiAfkWorker(
                self.min_delay_slider.value() / 10.0,
                self.max_delay_slider.value() / 10.0,
                self.min_pause_slider.value() / 10.0,
                self.max_pause_slider.value() / 10.0,
                self.checkwheel.isChecked()
            ),
            log_output=self.log_output,
            status_signal=self.statusChanged
        )

class AntiAfkWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)

    def __init__(self, min_delay=1.0, max_delay=3.5, min_pause=0.5, max_pause=2.0, checkwheel=False):
        super().__init__()
        self.running = True
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.min_pause = min_pause
        self.max_pause = max_pause
        self.checkwheel = checkwheel
        self.gamepad = vg.VX360Gamepad()
        self._stop = threading.Event()
        self.confidence = 0.85
        self.last_roulette_spin_time = time.time()

        self.DIRECTIONS = {
            'up': (0, 32767),
            'down': (0, -32767),
            'left': (-32767, 0),
            'right': (32767, 0),
            'up_right': (20000, 20000),
            'up_left': (-20000, 20000),
            'down_right': (20000, -20000),
            'down_left': (-20000, -20000),
            'center': (0, 0)
        }

    def stop(self):
        self.running = False
        self._stop.set()

    def log(self, message: str):
        CommonLogger.log(message, self.log_signal)

    def click_image_in_region(self,image_filename: str,region: Optional[Tuple[int, int, int, int]] = None,confidence: float = 0.85,click: Optional[Callable[[int, int], None]] = pyautogui.click) -> bool:
        full_image_path = os.path.join(BASE_ASSETS_PATH, image_filename)
        if not os.path.exists(full_image_path):
            print(f"Ошибка: Файл изображения '{full_image_path}' не найден.")
            return False
        try:
            location = pyautogui.locateOnScreen(full_image_path, region=region, confidence=confidence)

            if location:
                if click is not None:
                    center_x, center_y = pyautogui.center(location)
                    click(center_x, center_y)
                    print(f"Изображение '{image_filename}' найдено и был выполнен клик по координатам ({center_x}, {center_y}).")
                else:
                    print(f"Изображение '{image_filename}' найдено, но клик не выполнялся (click=None).")
                return True
            else:
                print(f"Изображение '{image_filename}' не найдено.")
                return False
        except Exception as e:
            return False

    def perform_roulette_spin(self):
        screen_width, screen_height = pyautogui.size()
        left_half_region = (0, 0, screen_width // 2, screen_height)
        right_half_region = (screen_width // 2, 0, screen_width // 2, screen_height)
        top_half_region = (0, 0, screen_width, screen_height // 2)
        bottom_half_region = (0, screen_height // 2, screen_width, screen_height // 2)

        pos = self.click_image_in_region("cols.jpg", region=top_half_region, click=None)
        if pos:
            self.log(f"[✓] Открываю телефон.")
            keyboard.press_and_release('up')
            self._stop.wait(2)

            if self.click_image_in_region("casinoIcon.png", region=right_half_region):
                self.log(f"[✓] Открыл казино.")
                self._stop.wait(2)
            else: 
                return

            if self.click_image_in_region('kasspin.jpg', region=left_half_region):
                self.log(f"[✓] Открываю колесо удачи.")
                self._stop.wait(2)
            else:
                return

            if self.click_image_in_region("spinbutton.jpg", region=bottom_half_region):
                self.log(f"[✓] Кручу.")
                self._stop.wait(3)
            else: 
                return

            self._stop.wait(0.5)
            keyboard.press_and_release('esc')
            self._stop.wait(0.5)
            keyboard.press_and_release('esc')
            self._stop.wait(0.5)
            keyboard.press_and_release('backspace')
        else:
            self.log("[→] пропускаем колесо")

    def run(self):
        self.log("[→] Скрипт анти-АФК запущен.")
        try:
            while self.running and not self._stop.is_set():
                direction = random.choice(list(self.DIRECTIONS.keys()))
                hold_time = random.uniform(self.min_delay, self.max_delay)
                pause_time = random.uniform(self.min_pause, self.max_pause)
                x, y = self.DIRECTIONS[direction]

                self.log(f"[•] Направление: {direction}, зажатие: {hold_time:.2f} сек.")
                self.gamepad.left_joystick(x_value=x, y_value=y)
                self.gamepad.update()

                if self._stop.wait(hold_time):
                    break

                self.gamepad.left_joystick(x_value=0, y_value=0)
                self.gamepad.update()

                self.log(f"[…] Пауза между: {pause_time:.2f} сек.")
                if self._stop.wait(pause_time):
                    break

                current_time = time.time()
                if self.checkwheel and (current_time - self.last_roulette_spin_time >= 300):
                    self.perform_roulette_spin()
                    self.last_roulette_spin_time = current_time

        except Exception as e:
            self.log(f"[Ошибка] {e}")
        finally:
            self.gamepad.left_joystick(x_value=0, y_value=0)
            self.gamepad.update()