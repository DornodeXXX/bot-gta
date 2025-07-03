from widgets.switch_button import SwitchButton
from PyQt5 import QtWidgets, QtCore
import random
import time
import vgamepad as vg
from widgets.logger import CommonLogger

class AntiAfkPage(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        self.switch = SwitchButton()
        self.switch.clicked.connect(self.toggle_script)

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
            slider.setStyleSheet(self.get_slider_style())
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



    def get_slider_style(self):
        return """
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #ccc;
                border-radius: 20px;
            }

            QSlider::sub-page:horizontal {
                background: #007aff;
                border-radius: 6px;
            }

            QSlider::add-page:horizontal {
                background: #ccc;
                border-radius: 6px;
            }

            QSlider::handle:horizontal {
                background: white;
                width: 20px;
                height: 20px;
                margin: -8px 0;
                border-radius: 10px;

            }
        """

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


    def toggle_script(self, checked):
        if checked:
            self.log_output.clear()
            min_delay = self.min_delay_slider.value() / 10.0
            max_delay = self.max_delay_slider.value() / 10.0
            min_pause = self.min_pause_slider.value() / 10.0
            max_pause = self.max_pause_slider.value() / 10.0

            self.worker = AntiAfkWorker(min_delay, max_delay, min_pause, max_pause)
            self.worker.log_signal.connect(self.append_log)
            self.worker.start()
        else:
            if self.worker:
                self.worker.stop()
                self.worker.wait()
                self.worker = None
                self.append_log("[■] Скрипт остановлен.")
                self.switch.setChecked(False)

    def append_log(self, text):
        self.log_output.append(text)


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
        self.quit()
        self.wait()

    def run(self):
        self.log("[→] Скрипт анти-АФК запущен.")
        try:
            while self.running:
                direction = random.choice(list(self.DIRECTIONS.keys()))
                hold_time = random.uniform(self.min_delay, self.max_delay)
                pause_time = random.uniform(self.min_pause, self.max_pause)
                x, y = self.DIRECTIONS[direction]

                self.log(f"[•] Направление: {direction}, зажатие: {hold_time:.2f} сек.")
                self.gamepad.left_joystick(x_value=x, y_value=y)
                self.gamepad.update()

                time.sleep(hold_time)

                self.gamepad.left_joystick(x_value=0, y_value=0)
                self.gamepad.update()

                self.log(f"[…] Пауза между: {pause_time:.2f} сек.")
                time.sleep(pause_time)
        except Exception as e:
            self.log(f"[Ошибка] {e}")
        finally:
            self.log("[■] Скрипт завершён.")
            self.gamepad.left_joystick(x_value=0, y_value=0)
            self.gamepad.update()

    def log(self, message: str):
        CommonLogger.log(message, self.log_signal)
