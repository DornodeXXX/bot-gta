import time
import traceback
import os
import pyautogui
from pyautogui import ImageNotFoundException
import pygetwindow as gw
from typing import Optional, Union, Callable, Any
from PyQt5.QtCore import pyqtSignal
from PyQt5 import QtWidgets, QtCore

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
        log_field.setStyleSheet("background-color: black; color: white; font-family: monospace;")
        log_field.setFixedHeight(240)
        layout.addWidget(log_field)
        return log_field
