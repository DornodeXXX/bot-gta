from PyQt5 import QtWidgets, QtCore
from widgets.switch_button import SwitchButton
import time
import keyboard
import pyautogui
import random
import ctypes
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

        hotkey_layout = QtWidgets.QHBoxLayout()
        self.hotkey_input = QtWidgets.QLineEdit("f6")
        self.hotkey_input.setMaxLength(20)
        self.hotkey_input.setFixedWidth(100)
        self.hotkey_input.setStyleSheet("background-color: #222; color: white;")

        hotkey_layout.addWidget(CommonLogger._make_label("Горячая клавиша:", 14))
        hotkey_layout.addWidget(self.hotkey_input)
        hotkey_layout.addStretch()
        layout.addLayout(hotkey_layout)

        hotkey_description = QtWidgets.QLabel("— вкл/выкл скрипта")
        hotkey_description.setStyleSheet("color: white; font-size: 12px; padding-right:150px;background: none;")
        hotkey_layout.addWidget(hotkey_description)

        self.counter_label = QtWidgets.QLabel("Счётчик: 0")
        self.counter_label.setStyleSheet("color: white; font-size: 14px;background: none;")
        layout.addWidget(self.counter_label)
        layout.addStretch()

        self.log_output = CommonLogger.create_log_field(layout)

    def toggle_script(self, checked: bool):
        if checked:
            self.log_output.clear()
            self.worker = CowWorker(self.hotkey_input.text())
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
            self._append_log("[■] Скрипт остановлен.")
            self.switch.setChecked(False)

    def _append_log(self, text: str):
        self.log_output.append(text)

    def _update_counter(self, value: int):
        self.counter_label.setText(f"Счётчик: {value}")


class CowWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    counter_signal = QtCore.pyqtSignal(int)

    def __init__(self, hotkey: str = "f6"):
        super().__init__()
        self._running = True
        self._count = 0
        self._active = False
        self._toggle_requested = False
        self.hotkey = hotkey.lower().strip() or "f6"
        
        self.target_colors = {
            'a': (255, 255, 255),
            'd': (255, 255, 255),
            'danger': (255, 105, 86)
        }
        self.color_tolerance = 5

        try:
            keyboard.add_hotkey(self.hotkey, self._request_toggle)
        except Exception as e:
            self.log(f"[!] Ошибка при назначении горячей клавиши '{self.hotkey}': {str(e)}")

    def log(self, message: str):
        CommonLogger.log(message, self.log_signal)

    def stop(self):
        self._running = False
        keyboard.unhook_all_hotkeys()
        self._active = False
        self.log("[■] Скрипт остановлен")

    def _request_toggle(self):
        self._toggle_requested = True

    #def colors_are_similar(self, color1, color2, tolerance):
    #    return all(abs(c1 - c2) <= tolerance for c1, c2 in zip(color1, color2))

    def safe_key_press(self, key):
        try:
            key_map = {'A': 0x41, 'D': 0x44, 'a': 0x41, 'd': 0x44}
            if key in key_map:
                ctypes.windll.user32.keybd_event(key_map[key], 0, 0, 0)
                time.sleep(0.05)
                ctypes.windll.user32.keybd_event(key_map[key], 0, 2, 0)
        except:
            pass

    def scan_screen_for_colors(self):
        try:
            # 1. Увеличиваем область поиска
            screenshot = pyautogui.screenshot()
            width, height = screenshot.size
            
            # 2. Центральная область (60% ширины и 50% высоты)
            start_x, end_x = int(width * 0.2), int(width * 0.8)
            start_y, end_y = int(height * 0.25), int(height * 0.75)
            
            # 3. Новые параметры цветов на основе ваших логов
            dark_blue = (15, 25, 35)  # Средний цвет из логов
            danger_color = (255, 105, 86)
            
            # 4. Увеличиваем допуск
            tolerance = 40  # Большой допуск для темных цветов
            
            for x in range(start_x, end_x, 5):  # Увеличиваем шаг для скорости
                for y in range(start_y, end_y, 5):
                    try:
                        pixel = screenshot.getpixel((x, y))
                        
                        # Проверка на опасный цвет (красный)
                        if all(abs(p - t) <= 15 for p, t in zip(pixel, danger_color)):
                            return 'danger', (x, y)
                        
                        # Проверка на темно-синий (фон)
                        if all(abs(p - t) <= tolerance for p, t in zip(pixel, dark_blue)):
                            # Проверяем область вокруг на белые пиксели (кнопки)
                            white_count = 0
                            for dx, dy in [(0,5), (5,0), (0,-5), (-5,0)]:
                                try:
                                    p = screenshot.getpixel((x+dx, y+dy))
                                    if all(c > 200 for c in p):  # Яркий пиксель
                                        white_count += 1
                                except:
                                    continue
                            
                            if white_count >= 2:  # Нашли кнопку
                                # Определяем A (левая часть) или D (правая часть)
                                if x < width // 2:
                                    return 'a', (x, y)
                                else:
                                    return 'd', (x, y)
                    
                    except:
                        continue
            
            return None, None
            
        except Exception as e:
            self.log(f"[ОШИБКА СКАНИРОВАНИЯ] {str(e)}")
            return None, None

    def colors_are_similar(self, color1, color2, tolerance):
        """Улучшенная проверка цветов с логированием"""
        result = all(abs(c1 - c2) <= tolerance for c1, c2 in zip(color1, color2))
        if not result:
            self.log(f"Цвет {color1} не совпадает с {color2} (допуск {tolerance})")
        return result
        
    def run(self):
        self.log("Скрипт коров запущен. Нажми ESC для остановки или используй переключатель.")
        rage_logged = False
        danger_pause_until = 0

        try:
            while self._running:
                try:
                    if not CommonLogger.is_rage_mp_active():
                        if self._active:
                            self._active = False
                            self.log("[■] Скрипт приостановлен (RAGE не активно)")
                        if not rage_logged:
                            self.log("Окно RAGE Multiplayer не активно. Ожидание...")
                            rage_logged = True
                        time.sleep(1.0)
                        continue
                    else:
                        if rage_logged:
                            self.log("Окно RAGE Multiplayer найдено.")
                            rage_logged = False
                except Exception as e:
                    self.log(f"[!] Ошибка при проверке окна RAGE: {e}")
                    time.sleep(1.0)
                    continue

                if keyboard.is_pressed("esc"):
                    self.log("Получен ESC. Останавливаемся...")
                    self.stop()
                    break

                if self._toggle_requested:
                    self._active = not self._active
                    self.log(f"[→] Скрипт {'активирован' if self._active else 'деактивирован'}")
                    self._toggle_requested = False

                if not self._active:
                    time.sleep(0.1)
                    continue

                if time.time() < danger_pause_until:
                    time.sleep(0.1)
                    continue

                color_type, _ = self.scan_screen_for_colors()
                
                if color_type == 'danger':
                    self.log("[!] Обнаружен опасный цвет - пауза на 5-15 секунд")
                    danger_pause_until = time.time() + random.uniform(5, 15)
                    continue
                elif color_type == 'a':
                    self.safe_key_press('A')
                    self._count += 1
                    self.log(f"[A] Нажата клавиша A (#{self._count})")
                    self.counter_signal.emit(self._count)
                    time.sleep(0.3 + random.uniform(0.0, 0.1))
                elif color_type == 'd':
                    self.safe_key_press('D')
                    self._count += 1
                    self.log(f"[D] Нажата клавиша D (#{self._count})")
                    self.counter_signal.emit(self._count)
                    time.sleep(0.3 + random.uniform(0.0, 0.1))
                else:
                    time.sleep(0.05)

        except Exception as exc:
            self.log(f"[Ошибка потока] {exc}")
            self.stop()