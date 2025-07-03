from PyQt5 import QtWidgets, QtCore
from widgets.switch_button import SwitchButton
import pygetwindow as gw
import pyautogui
import time
import keyboard
import os
from widgets.logger import CommonLogger

class GotovkaPage(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.worker: GotovkaWorker | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        switch_layout = QtWidgets.QHBoxLayout()
        self.switch = SwitchButton()
        self.switch.clicked.connect(self.toggle_script)

        switch_layout.addWidget(CommonLogger._make_label("Готовка", 16))
        switch_layout.addStretch()
        switch_layout.addWidget(self.switch)
        layout.addLayout(switch_layout)

        dish_layout = QtWidgets.QHBoxLayout()
        dish_label = QtWidgets.QLabel("Выберите блюдо:")
        dish_label.setStyleSheet("color: white; font-size: 14px; background: none;")

        self.dish_combo = QtWidgets.QComboBox()
        self.dish_combo.addItems(["Фруктовый смузи", "Фруктовый салат", "Овощной салат", "Овощной смузи"])
        self.dish_combo.setStyle(QtWidgets.QStyleFactory.create("Fusion"))
        self.dish_combo.setStyleSheet("""
            QComboBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                min-width: 120px;
            }

            QComboBox QAbstractItemView {
                background-color: #333;
                color: white;
            }
        """)

        dish_layout.addWidget(dish_label)
        dish_layout.addWidget(self.dish_combo)
        dish_layout.addStretch()
        layout.addLayout(dish_layout)

        layout.addStretch()
        self.log_output = CommonLogger.create_log_field(layout)

    def toggle_script(self, checked: bool):
        if checked:
            self.log_output.clear()
            selected_dish = self.dish_combo.currentText()
            self.worker = GotovkaWorker(selected_dish)
            self.worker.log_signal.connect(self._append_log)
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


class GotovkaWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)

    def __init__(self, dish_name: str):
        super().__init__()
        self._running = True
        self.dish_name = dish_name

    def stop(self):
        self._running = False

    def log(self, message: str):
        CommonLogger.log(message, self.log_signal)

    def _drag_image(self, image_path):
        try:
            location = pyautogui.locateCenterOnScreen(image_path, confidence=0.85)
            if location:
                self.log(f"[✓] Найдено изображение: {os.path.basename(image_path)}.")
                pyautogui.rightClick(location.x, location.y)
                return True
            return False
        except Exception as e:
            return False

    def _click_image(self, image_path):
        try:
            location = pyautogui.locateCenterOnScreen(image_path, confidence=0.85)
            if location:
                pyautogui.click(location)
                self.log(f"[✓] Клик по изображению: {os.path.basename(image_path)}.")
                return True
            return False
        except Exception as e:
            return False

    def _find_all_required_images(self):
        """Проверяет наличие всех необходимых изображений для текущего блюда"""
        required_images = []
        
        if self.dish_name == "Фруктовый смузи":
            required_images = [
                ("assets/cook/frukti.png", self._drag_image),
                ("assets/cook/voda2.png", self._drag_image),
                ("assets/cook/whisk2.png", self._drag_image),
                ("assets/cook/startCoocking.png", self._click_image)
            ]
        elif self.dish_name == "Фруктовый салат":
            required_images = [
                ("assets/cook/frukti.png", self._drag_image),
                ("assets/cook/knife2.png", self._drag_image),
                ("assets/cook/startCoocking.png", self._click_image)
            ]
        elif self.dish_name == "Овощной салат":
            required_images = [
                ("assets/cook/ovoshi.png", self._drag_image),
                ("assets/cook/knife2.png", self._drag_image),
                ("assets/cook/startCoocking.png", self._click_image)
            ]
        elif self.dish_name == "Овощной смузи":
            required_images = [
                ("assets/cook/ovoshi.png", self._drag_image),
                ("assets/cook/voda2.png", self._drag_image),
                ("assets/cook/whisk2.png", self._drag_image),
                ("assets/cook/startCoocking.png", self._click_image)
            ]

        # Проверяем все изображения
        all_found = True
        for img_path, action in required_images:
            try:
                location = pyautogui.locateCenterOnScreen(img_path, confidence=0.85)
                if not location:
                    all_found = False
                    break
            except:
                all_found = False
                break
                
        if not all_found:
            return False
            
        # Если все изображения найдены, выполняем действия
        for img_path, action in required_images:
            if not action(img_path):
                return False
                
        return True

    def run(self):
        self.log(f"[→] Скрипт готовки запущен для блюда: {self.dish_name}")
        rage_window_missing = True
        waiting_for_images = False
        
        try:
            while self._running:
                if not CommonLogger.is_rage_mp_active():
                    if rage_window_missing:
                        self.log("Окно RAGE Multiplayer не активно. Ожидание...")
                        rage_window_missing = False
                    time.sleep(1)
                    continue

                try:
                    if self._find_all_required_images():
                        waiting_for_images = False
                        self.log("[✓] Операция готовки завершена. Начинаем новую...")
                        time.sleep(5.5)
                    else:
                        if not waiting_for_images:
                            self.log("[!] Ожидание появления всех элементов...")
                            waiting_for_images = True
                        time.sleep(1.0)

                except Exception as e:
                    if not waiting_for_images:
                        self.log(f"[!] Временная ошибка: {str(e)}")
                        waiting_for_images = True
                    time.sleep(1.0)
                    continue

        except Exception as e:
            self.log(f"[Ошибка] {e}")
        finally:
            if self._running:
                self.log("[■] Скрипт готовки завершён.")