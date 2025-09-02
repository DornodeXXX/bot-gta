from widgets.switch_button import SwitchButton
from PyQt5 import QtWidgets, QtCore
import random
import time
import vgamepad as vg
from widgets.logger import CommonLogger, ScriptController
import threading

class AntiAfkPage(QtWidgets.QWidget):
    statusChanged = QtCore.pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        self.worker = None
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        self.switch = SwitchButton()
        self.switch.clicked.connect(self.handle_toggle)
        self.switch.clicked.connect(self.statusChanged.emit)

        switch_layout = QtWidgets.QHBoxLayout()
        switch_layout.addWidget(CommonLogger._make_label("Анти-АФК", 16))
        switch_layout.addStretch()
        switch_layout.addWidget(self.switch)

        self.min_delay_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.max_delay_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.min_pause_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.max_pause_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)

        for slider in [self.min_delay_slider, self.max_delay_slider, self.min_pause_slider, self.max_pause_slider]:
            slider.setMinimum(5)
            slider.setMaximum(100)
            slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.min_delay_slider.setValue(10)
        self.max_delay_slider.setValue(35)
        self.min_pause_slider.setValue(5)
        self.max_pause_slider.setValue(20)

        self.min_delay_slider.valueChanged.connect(self.update_min_label)
        self.max_delay_slider.valueChanged.connect(self.update_max_label)
        self.min_pause_slider.valueChanged.connect(self.update_min_pause_label)
        self.max_pause_slider.valueChanged.connect(self.update_max_pause_label)

        self.min_label = QtWidgets.QLabel("1.0 сек")
        self.max_label = QtWidgets.QLabel("3.5 сек")
        self.min_pause_label = QtWidgets.QLabel("0.5 сек")
        self.max_pause_label = QtWidgets.QLabel("2.0 сек")

        for lbl in [self.min_label, self.max_label, self.min_pause_label, self.max_pause_label]:
            lbl.setStyleSheet("color: white;")

        settings_group = QtWidgets.QGroupBox("")
        settings_group.setStyleSheet("QGroupBox { color: white; font-weight: bold; background: none; }")
        settings_layout = QtWidgets.QVBoxLayout()
        settings_layout.setSpacing(10)
        settings_layout.setContentsMargins(10, 10, 10, 10)

        settings_layout.addWidget(CommonLogger._make_label("Время зажатия:", 17))
        settings_layout.addLayout(self.create_slider_row("Мин. зажатие:", self.min_delay_slider, self.min_label))
        settings_layout.addLayout(self.create_slider_row("Макс. зажатие:", self.max_delay_slider, self.max_label))

        settings_layout.addWidget(CommonLogger._make_label("Пауза между движениями:", 17))
        settings_layout.addLayout(self.create_slider_row("Мин. пауза:", self.min_pause_slider, self.min_pause_label))
        settings_layout.addLayout(self.create_slider_row("Макс. пауза:", self.max_pause_slider, self.max_pause_label))
        settings_group.setStyleSheet("background: none;")
        settings_group.setLayout(settings_layout)

        layout.addLayout(switch_layout)
        layout.addWidget(settings_group)
        layout.addStretch()
        self.log_output = CommonLogger.create_log_field(layout)

        self.setLayout(layout)

    def create_slider_row(self, label_text, slider, value_label):
        row = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel(label_text)
        label.setStyleSheet("color: white;")
        row.addWidget(label)
        row.addWidget(slider)
        row.addWidget(value_label)
        return row

    def update_min_label(self, value):
        self.min_label.setText(f"{value / 10.0:.1f} сек")

    def update_max_label(self, value):
        self.max_label.setText(f"{value / 10.0:.1f} сек")

    def update_min_pause_label(self, value):
        self.min_pause_label.setText(f"{value / 10.0:.1f} сек")

    def update_max_pause_label(self, value):
        self.max_pause_label.setText(f"{value / 10.0:.1f} сек")

    def handle_toggle(self):
        ScriptController.toggle_script(widget=self,
            worker_factory=lambda: AntiAfkWorker(
                self.min_delay_slider.value() / 10.0,
                self.max_delay_slider.value() / 10.0,
                self.min_pause_slider.value() / 10.0,
                self.max_pause_slider.value() / 10.0
            ),
            log_output=self.log_output,
            status_signal=self.statusChanged
        )

class AntiAfkWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)

    def __init__(self, min_delay=1.0, max_delay=3.5, min_pause=0.5, max_pause=2.0):
        super().__init__()
        self.running = True
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.min_pause = min_pause
        self.max_pause = max_pause
        self.gamepad = vg.VX360Gamepad()
        self._stop = threading.Event()

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
        except Exception as e:
            self.log(f"[Ошибка] {e}")
        finally:
            self.gamepad.left_joystick(x_value=0, y_value=0)
            self.gamepad.update()