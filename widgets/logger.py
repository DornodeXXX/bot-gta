import time
import traceback
import os
import pyautogui
from pyautogui import ImageNotFoundException
import pygetwindow as gw
from typing import Optional, Union, Callable, Any
from PyQt5.QtCore import pyqtSignal
from PyQt5 import QtWidgets, QtCore
import keyboard

class CommonLogger:
    @staticmethod
    def log(message: str,log_signal: Optional[Union[pyqtSignal, Callable]] = None, 
           log_file: str = "logs.txt") -> str:
        timestamp = time.strftime("[%H:%M:%S]")
        full_message = f"{timestamp} {message}"
        
        try:
            with open(log_file, "a", encoding="utf-8") as fp:
                fp.write(full_message + "\n")
        except OSError:
            pass
            
        if log_signal:
            if hasattr(log_signal, 'emit'):
                log_signal.emit(full_message)
            else:
                log_signal(full_message)
                
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
    def safe_locate_center(path: str, confidence: float = 0.95,log_signal: Optional[Union[pyqtSignal, Callable]] = None) -> Any:
        try:
            return pyautogui.locateCenterOnScreen(path, confidence=confidence)
        except ImageNotFoundException:
            return None
        except Exception as e:
            CommonLogger.log(f"[Ошибка] locate_center {os.path.basename(path)}: {traceback.format_exc()}",log_signal)
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
    def check_file_exists(file_path: str,log_signal: Optional[Union[pyqtSignal, Callable]] = None) -> bool:
        exists = os.path.exists(file_path)
        if not exists and log_signal:
            CommonLogger.log(f"[Ошибка] Файл не найден: {file_path}", log_signal)
        return exists
        
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
    def create_slider_row(title: str, minimum: int, maximum: int, default: int, suffix: str = "сек", step: float = 0.1):
        layout = QtWidgets.QHBoxLayout()
        layout.setSpacing(5)

        label = QtWidgets.QLabel(title)
        label.setStyleSheet("color: white;")
        
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setMinimum(minimum)
        slider.setMaximum(maximum)
        slider.setValue(default)
        slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        
        value_label = QtWidgets.QLabel(f"{default * step:.1f} {suffix}")
        value_label.setStyleSheet("color: white;")
        
        def update_label(val):
            value_label.setText(f"{val * step:.1f} {suffix}")
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
    def toggle_script(widget, worker_factory, log_output, extra_signals=None, status_signal=None,
                      worker_args=None, worker_kwargs=None):
        checked = widget.switch.isChecked()
        if checked:
            log_output.clear()
            worker_args = worker_args or ()
            worker_kwargs = worker_kwargs or {}
            widget.worker = worker_factory(*worker_args, **worker_kwargs)
            widget.worker.log_signal.connect(lambda text: ScriptController.append_log(log_output, text))

            if extra_signals:
                for signal_name, slot in extra_signals.items():
                    signal = getattr(widget.worker, signal_name, None)
                    if signal:
                        signal.connect(slot)

            widget.worker.finished.connect(lambda: ScriptController.on_worker_finished(widget, log_output))
            widget.worker.start()
        else:
            if widget.worker:
                widget.worker.stop()

        if status_signal:
            status_signal.emit(checked)

    @staticmethod
    def on_worker_finished(widget, log_output):
        ScriptController.append_log(log_output, "[■] Скрипт остановлен.")
        widget.worker = None

    @staticmethod
    def append_log(log_output, text):
        log_output.append(text)

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
            CommonLogger.log(f"Не удалось зарегистрировать горячую клавишу '{self.hotkey}': {exc}",
                             self.log_signal)

    def unregister(self):
        if self._hotkey_id is not None:
            try:
                keyboard.remove_hotkey(self._hotkey_id)
            except Exception:
                pass
            self._hotkey_id = None