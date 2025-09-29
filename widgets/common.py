import time
import traceback
import os
import pyautogui
from pyautogui import ImageNotFoundException
import pygetwindow as gw
from typing import Optional, Union, Callable, Any, Dict, List
from PyQt5.QtCore import pyqtSignal
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QTextEdit
import keyboard
import json
import types
import cv2

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
            "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x",
            "м": "m", "т": "t", "н": "h", "в": "b", "к": "k",
        }
        normalized = "".join(replacements.get(ch, ch) for ch in active.title.casefold())
        return "multi" in normalized
        
    @staticmethod
    def _make_label(text: str, size: int) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setStyleSheet(f"background:none;color:white;font-size:{size}px;")
        return lbl
        
    @staticmethod
    def create_log_field(layout):
        log_field = QtWidgets.QTextEdit()
        log_field.setReadOnly(True)
        log_field.setObjectName("logField")
        log_field.setStyleSheet("background-color: black; color: white; font-family: monospace;")
        log_field.setMinimumHeight(100)
        layout.addWidget(log_field)
        return log_field
    
    @staticmethod
    def create_slider_row(title: str, minimum: int, maximum: int, default: float, suffix: str = "сек", step: float = 0.1):
        layout = QtWidgets.QHBoxLayout()
        layout.setSpacing(5)

        factor = int(1 / step)

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

        return layout, slider, value_label

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
        CommonLogger.log(f"Автонажатие E: {state}", self.log_signal)
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