import time
import traceback
import os
import pyautogui
from pyautogui import ImageNotFoundException
import pygetwindow as gw
from typing import Optional, Union, Callable, Any, Dict, List
from PyQt5.QtCore import pyqtSignal, QRect
from PyQt5 import QtWidgets, QtCore,QtGui
from PyQt5.QtWidgets import QTextEdit
import keyboard
import json
import types
import cv2
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QGraphicsDropShadowEffect, QFrame
)
from widgets.switch_button import SwitchButton

class CommonLogger:
    @staticmethod
    def log(message: str,log_target: Optional[Union[pyqtSignal, Callable, QTextEdit]] = None,log_file: str = "logs.txt") -> str:
        timestamp = time.strftime("[%H:%M:%S]")
        full_message = f"{timestamp} {message}"
        
        try:
            with open(log_file, "a", encoding="utf-8") as fp:
                fp.write(full_message + "\n")
        except OSError:
            pass

        if log_target:
            if hasattr(log_target, 'emit'): 
                log_target.emit(message)
            elif isinstance(log_target, QTextEdit):
                log_target.append(full_message)
            elif callable(log_target):
                log_target(full_message)
        
        return full_message

    @staticmethod
    def safe_locate(path: str, confidence: float = 0.95,log_signal: Optional[Union[pyqtSignal, Callable]] = None) -> Any:
        try:
            return pyautogui.locateOnScreen(path, confidence=confidence)
        except ImageNotFoundException:
            return None
        except Exception as e:
            CommonLogger.log(f"[Ошибка] locate {os.path.basename(path)}: {traceback.format_exc()}",log_signal)
            return None

    @staticmethod
    def is_rage_mp_active() -> bool:
        active = gw.getActiveWindow()
        if not active:
            return False
            
        replacements = {
            "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "м": "m", "т": "t", "н": "h", "в": "b", "к": "k",
        }
        normalized = "".join(replacements.get(ch, ch) for ch in active.title.casefold())
        return "multi" in normalized
        
class ScriptController:
    @staticmethod
    def toggle_script(widget, worker_factory, log_output, extra_signals=None, status_signal=None, worker_args=None, worker_kwargs=None):
        checked = widget.switch.isChecked()
        if checked:
            log_output.clear()
            worker_args = worker_args or ()
            worker_kwargs = worker_kwargs or {}
            widget.worker = worker_factory(*worker_args, **worker_kwargs)

            def stop(self):
                self.running = False
                if hasattr(self, "_stop"):
                    self._stop.set()
            widget.worker.stop = types.MethodType(stop, widget.worker)
            widget.worker.log_signal.connect(lambda text: CommonLogger.log(text, log_output))

            if extra_signals:
                for signal_name, slot in extra_signals.items():
                    signal = getattr(widget.worker, signal_name, None)
                    if signal:
                        signal.connect(slot)

            widget.worker.finished.connect(lambda: CommonLogger.log("[■] Скрипт остановлен.", log_output))
            widget.worker.start()
        else:
            if widget.worker:
                widget.worker.stop()

        if status_signal:
            status_signal.emit(checked)

class HotkeyManager:
    def __init__(self, hotkey: str, toggle_callback: Callable, log_signal=None):
        self.hotkey = (hotkey or 'f5').lower().strip()
        self._hotkey_id = None
        self._enabled = False
        self.log_signal = log_signal
        self.toggle_callback = toggle_callback

    def toggle(self):
        self._enabled = not self._enabled
        state = "включено" if self._enabled else "выключено"
        CommonLogger.log(f"Хоткей: {state}", self.log_signal)
        if self.toggle_callback:
            self.toggle_callback(self._enabled)

    def register(self):
        try:
            self._hotkey_id = keyboard.add_hotkey(self.hotkey, self.toggle)
        except Exception as exc:
            CommonLogger.log(f"Не удалось зарегистрировать горячую клавишу '{self.hotkey}': {exc}",self.log_signal)

    def unregister(self):
        if self._hotkey_id is not None:
            try:
                keyboard.remove_hotkey(self._hotkey_id)
            except Exception:
                pass
            self._hotkey_id = None

class SettingsManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance.filename = "settings.json"
            cls._instance.settings = {}
            cls._instance.load()
        return cls._instance

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
            except Exception:
                self.settings = {}
        else:
            self.settings = {}

    def save(self):
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)

    def get(self, section: str, key: str, default=None):
        return self.settings.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value):
        if section not in self.settings:
            self.settings[section] = {}
        self.settings[section][key] = value
        self.save()

    def save_group(self, section: str, values: dict):
        if section not in self.settings:
            self.settings[section] = {}
        self.settings[section].update(values)
        self.save()

def auto_detect_region(width_ratio=None, height_ratio=None, top_ratio=None, reference_height=None, reference_top=None):
    screen_width, screen_height = pyautogui.size()

    if width_ratio is None:
        width_ratio = 0.5
    if height_ratio is None:
        height_ratio = 0.7
    if top_ratio is None:
        top_ratio = 0.25

    if reference_height is not None and reference_top is not None:
        top_ratio = reference_top / reference_height

    region_width = int(screen_width * width_ratio)
    region_height = int(screen_height * height_ratio)

    region = {
        "left": int((screen_width - region_width) / 2),
        "top": int(screen_height * top_ratio),
        "width": region_width,
        "height": region_height,
    }
    return region

def load_images(folder: str, mapping: Dict[str, str] = None, count: int = None, as_cv2: bool = False) -> Union[Dict[str, str], Dict[str, 'np.ndarray'], List[str]]:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder_path = os.path.join(base, "assets", folder)

    if mapping:
        if as_cv2:
            result = {}
            for filename, key in mapping.items():
                img = cv2.imread(os.path.join(folder_path, filename), cv2.IMREAD_UNCHANGED)
                if img is None:
                    raise FileNotFoundError(f"Файл {filename} не найден")
                result[key] = img[:, :, :3]
            return result
        else:
            return {os.path.join(folder_path, filename): value for filename, value in mapping.items()}

    if count:
        if as_cv2:
            result = []
            for i in range(1, count + 1):
                img = cv2.imread(os.path.join(folder_path, f"{i}.png"), cv2.IMREAD_UNCHANGED)
                if img is None:
                    raise FileNotFoundError(f"Файл {i}.png не найден")
                result.append(img[:, :, :3])
            return result
        else:
            return [os.path.join(folder_path, f"{i}.png") for i in range(1, count + 1)]

    raise ValueError("mapping count")

class OverlayWindow(QWidget):
    def __init__(self, title="HUD", fields=None, f_keys=None, auto_monitor=True):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.fields = fields or {"Действий": 0}
        self.value_labels = {}

        self.setObjectName("root")
        self.setFixedSize(168, 78 + (len(self.fields) - 1) * 20)

        font_title = QFont("Arial", 12, QFont.Bold)
        font_labels = QFont("Arial", 10)
        font_values = QFont("Arial", 11, QFont.Bold)
        font_f = QFont("Arial", 8)

        header = QWidget()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 6, 10, 6)
        header_layout.setSpacing(6)

        status_dot = QLabel()
        status_dot.setFixedSize(QSize(7, 7))
        status_dot.setObjectName("statusDot")

        title_label = QLabel(title)
        title_label.setFont(font_title)
        title_label.setObjectName("titleLabel")

        f_keys_label = QLabel(f_keys or "")
        f_keys_label.setFont(font_f)
        f_keys_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f_keys_label.setObjectName("fKeys")

        left_header = QHBoxLayout()
        left_header.addWidget(status_dot)
        left_header.addWidget(title_label)

        header_layout.addLayout(left_header)
        header_layout.addStretch(1)
        header_layout.addWidget(f_keys_label)

        self.data_container = QWidget()
        self.data_container.setObjectName("body")
        self.data_layout = QGridLayout(self.data_container)
        self.data_layout.setContentsMargins(10, 6, 10, 6)
        self.data_layout.setSpacing(2)

        for i, (label_text, value) in enumerate(self.fields.items()):
            self._create_row(i, label_text, value, font_labels, font_values)

        self.data_layout.setColumnStretch(0, 1)
        self.data_layout.setColumnStretch(1, 1)

        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        main.addWidget(header)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setObjectName("separator")
        main.addWidget(sep)
        main.addWidget(self.data_container)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.setGraphicsEffect(shadow)

        self.setStyleSheet("""
            QWidget#root {
                background: transparent;
            }
            QWidget#header {
                background: rgba(0,0,0,0.38);
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
                border: 1px solid rgba(255,255,255,0.06);
                border-bottom: none;
                color: white;
            }
            QWidget#body {
                background: rgba(24,24,24,0.70);
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 16px;
                border: 1px solid rgba(255,255,255,0.06);
                border-top: none;
                color: white;
            }
            QLabel#statusDot {
                background-color: #2EE279;
                border-radius: 3px;
            }
            QLabel#fKeys {
                color: rgba(255,255,255,0.55);
            }
            QLabel#titleLabel {
                color: white;
            }
            QFrame#separator {
                background: rgba(255,255,255,0.08);
                margin-left: 10px;
                margin-right: 10px;
            }
            QLabel#dimLabel {
                color: rgba(255,255,255,0.60);
            }
            QLabel#valueLabel {
                color: #2EE279;
                font-weight: 700;
            }
            QLabel {
                background: transparent;
            }
        """)

        self.move_to_bottom_right()
        self._hud_timer = None
        if auto_monitor:
            self.start_monitor()

    def _create_row(self, row_index, label_text, value, font_labels, font_values):
        label = QLabel(label_text)
        label.setFont(font_labels)
        label.setObjectName("dimLabel")

        value_label = QLabel(str(value))
        value_label.setFont(font_values)
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value_label.setObjectName("valueLabel")

        self.data_layout.addWidget(label, row_index, 0)
        self.data_layout.addWidget(value_label, row_index, 1)
        self.value_labels[label_text] = value_label

    def add_field(self, label_text, value):
        if label_text in self.value_labels:
            self.value_labels[label_text].setText(str(value))
            return
        row = self.data_layout.rowCount()
        font_labels = QFont("Arial", 10)
        font_values = QFont("Arial", 11, QFont.Bold)
        self._create_row(row, label_text, value, font_labels, font_values)
        self._resize()

    def remove_field(self, label_text):
        if label_text not in self.value_labels:
            return

        value_label = self.value_labels.pop(label_text)

        for i in reversed(range(self.data_layout.count())):
            item = self.data_layout.itemAt(i)
            w = item.widget()
            if isinstance(w, QLabel) and (w.text() == label_text or w == value_label):
                self.data_layout.removeWidget(w)
                w.setParent(None)
                w.deleteLater()

        self.data_container.adjustSize()
        self._resize()
        self.data_container.repaint()
        self.repaint()
        QApplication.processEvents()


    def _resize(self):
        self.setFixedHeight(78 + (len(self.value_labels) - 1) * 20)

    def _rebuild_layout(self):
        while self.data_layout.count():
            item = self.data_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        font_labels = QFont("Arial", 10)
        font_values = QFont("Arial", 11, QFont.Bold)
        for i, (label_text, value_label) in enumerate(self.value_labels.items()):
            label = QLabel(label_text)
            label.setFont(font_labels)
            label.setObjectName("dimLabel")
            self.data_layout.addWidget(label, i, 0)
            self.data_layout.addWidget(value_label, i, 1)

    def update_values(self, **kwargs):
        for k, v in kwargs.items():
            if v is None:
                self.remove_field(k)
            else:
                if k in self.value_labels:
                    self.value_labels[k].setText(str(v))
                else:
                    self.add_field(k, v)


    def move_to_bottom_right(self):
        screen = QApplication.primaryScreen()
        geo = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
        x = geo.x() + geo.width() - self.width() - 10
        y = geo.y() + geo.height() - self.height() - 60
        self.move(x, y)

    def start_monitor(self):
        if self._hud_timer is not None:
            return
        self._hud_timer = QTimer(self)
        self._hud_timer.timeout.connect(self._check_game_focus)
        self._hud_timer.start(1000)

    def stop_monitor(self):
        if self._hud_timer is not None:
            self._hud_timer.stop()
            self._hud_timer = None
        self.close()

    def _check_game_focus(self):
        if CommonLogger.is_rage_mp_active():
            if not self.isVisible():
                self.show()
                self.move_to_bottom_right()
        else:
            if self.isVisible():
                self.close()

    def update_values_auto(self, **kwargs):
        self.update_values(**kwargs)

class ToolTipLabel(QtWidgets.QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent, QtCore.Qt.ToolTip)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.label = QtWidgets.QLabel(text, self)
        self.label.setStyleSheet("""
            background-color: rgba(40,40,45,0.9);
            color: white;
            padding: 6px 10px;
        """)
        self.label.adjustSize()
        self.setFixedSize(self.label.size())
        self.opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_anim = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_anim.setDuration(200)
        self.hide()

    def showTooltip(self, pos: QtCore.QPoint):
        self.move(pos)
        self.show()
        self.opacity_anim.stop()
        self.opacity_anim.setStartValue(self.opacity_effect.opacity())
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.start()

    def hideTooltip(self):
        self.opacity_anim.stop()
        self.opacity_anim.setStartValue(self.opacity_effect.opacity())
        self.opacity_anim.setEndValue(0.0)
        self.opacity_anim.start()
        self.opacity_anim.finished.connect(lambda: self.hide() if self.opacity_effect.opacity() == 0 else None)

class CheckWithTooltip(QtWidgets.QWidget):
    def __init__(self, text: str, tooltip_text: str = "", parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.Check = QtWidgets.QCheckBox(text, self)
        self.Check.setCursor(QtCore.Qt.PointingHandCursor)
        self.Check.setStyleSheet("""
            QCheckBox { color: white; font-size: 14px; }
            QCheckBox::indicator { width:15px; height:15px; border:1px solid #fff; border-radius:3px; background:transparent; }
            QCheckBox::indicator:checked { border:1px solid #0A84FF; background-color:#0A84FF; image: url(assets/check.png); }
        """)
        self.layout.addWidget(self.Check)
        self.layout.addStretch()

        self.tooltip = None
        if tooltip_text:
            self.tooltip = ToolTipLabel(tooltip_text)
            self.Check.installEventFilter(self)

    def eventFilter(self, source, event):
        if self.tooltip and source == self.Check:
            cursor_pos = QtGui.QCursor.pos()
            if event.type() == QtCore.QEvent.Enter:
                pos = self.Check.mapToGlobal(QtCore.QPoint(self.Check.width() + 10, 0))
                self.tooltip.showTooltip(pos)
            elif event.type() == QtCore.QEvent.Leave:
                if not self.Check.rect().contains(self.Check.mapFromGlobal(cursor_pos)):
                    self.tooltip.hideTooltip()
        return super().eventFilter(source, event)
    
    def setChecked(self, value: bool):
        self.Check.setChecked(value)

    def isChecked(self) -> bool:
        return self.Check.isChecked()
    
class CommonUI:
    @staticmethod
    def create_settings_group(title: str = "", spacing: int = 10, margins=(10, 10, 10, 10)):
        group = QtWidgets.QGroupBox(title)
        group.setAlignment(QtCore.Qt.AlignHCenter)
        group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                background: none;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 2px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                color: #ffcc66;
            }
        """)
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(spacing)
        layout.setContentsMargins(*margins)
        group.setLayout(layout)
        return group, layout


    @staticmethod
    def create_switch_header(label_text: str, icon: str = "", font_size: int = 16):
        layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel(f"{icon} {label_text}")
        label.setStyleSheet(f"color: white; font-size: {font_size}px; background: none;")

        switch = SwitchButton()
        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(switch)
        return layout, switch

    @staticmethod
    def create_counter(text="Счётчик: 0", font_size: int = 14):
        label = QtWidgets.QLabel(text)
        label.setStyleSheet(f"color: white; font-size: {font_size}px; background: none;")
        return label

    @staticmethod
    def create_combo(label_text: str, items: list[str]):
        layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel(label_text)
        label.setStyleSheet("color: white; font-size: 14px; background: none;")

        combo = QtWidgets.QComboBox()
        combo.addItems(items)
        layout.addWidget(label)
        layout.addWidget(combo)
        layout.addStretch()
        return layout, combo

    @staticmethod
    def add_log_field(parent_layout):
        log_field = QtWidgets.QTextEdit()
        log_field.setReadOnly(True)
        log_field.setObjectName("logField")
        log_field.setStyleSheet("background-color: black; color: white; font-family: monospace;")
        log_field.setMinimumHeight(100)
        parent_layout.addWidget(log_field)
        return log_field
    
    @staticmethod
    def _make_label(text: str, size: int) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setStyleSheet(f"background:none;color:white;font-size:{size}px;")
        return lbl
    
    @staticmethod
    def create_slider_row(title: str, minimum: float, maximum: float, default: float, suffix: str = "сек", step: float = 0.1):
        layout = QtWidgets.QHBoxLayout()
        layout.setSpacing(5)
        factor = 1 / step 

        label = QtWidgets.QLabel(title)
        label.setStyleSheet("color: white;")

        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setMinimum(int(minimum * factor))
        slider.setMaximum(int(maximum * factor))
        slider.setValue(int(default * factor))
        slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        value_label = QtWidgets.QLabel(f"{default:.2f} {suffix}")
        value_label.setStyleSheet("color: white;")

        def update_label(val):
            value_label.setText(f"{val / factor:.2f} {suffix}")

        slider.valueChanged.connect(update_label)

        layout.addWidget(label)
        layout.addWidget(slider)
        layout.addWidget(value_label)

        def get_value():
            return slider.value() / factor

        return layout, slider, get_value

    @staticmethod
    def create_hotkey_input(default: str = "f5", description: str = "— вкл/выкл автонажатие E"):
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        input_group = QtWidgets.QHBoxLayout()
        input_group.setSpacing(5)
        input_group.setContentsMargins(0, 0, 0, 0)

        hotkey_input = QtWidgets.QLineEdit(default)
        hotkey_input.setMaxLength(20)
        hotkey_input.setFixedWidth(50)
        hotkey_input.setAlignment(QtCore.Qt.AlignCenter)
        hotkey_input.setStyleSheet("""
            background-color: #222; 
            color: white;
            font-size: 12px;
        """)

        hotkey_description = QtWidgets.QLabel(description)
        hotkey_description.setObjectName("hotkey_description")

        input_group.addWidget(hotkey_input)
        input_group.addWidget(hotkey_description)

        layout.addWidget(QtWidgets.QLabel("Горячая клавиша:"))
        layout.addLayout(input_group)

        return layout, hotkey_input