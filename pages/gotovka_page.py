from PyQt5 import QtWidgets, QtCore
import pyautogui
import os
from widgets.common import CommonLogger, ScriptController, CommonUI
import threading

BASE_ASSETS_PATH = "assets/cook/"
RECIPES = {
    "Фруктовый смузи": [
        ("frukti.png", "right"),
        ("voda2.png", "right"),
        ("whisk2.png", "right"),
        ("startCoocking.png", "left")
    ],
    "Фруктовый салат": [
        ("frukti.png", "right"),
        ("knife2.png", "right"),
        ("startCoocking.png", "left")
    ],
    "Овощной салат": [
        ("ovoshi.png", "right"),
        ("knife2.png", "right"),
        ("startCoocking.png", "left")
    ],
    "Овощной смузи": [
        ("ovoshi.png", "right"),
        ("voda2.png", "right"),
        ("whisk2.png", "right"),
        ("startCoocking.png", "left")
    ],
    "Рагу": [
        ("myaso.png", "right"),
        ("ovoshi.png", "right"),
        ("voda2.png", "right"),
        ("fire2.png", "right"),
        ("startCoocking.png", "left")
    ]
}

class GotovkaPage(QtWidgets.QWidget):
    statusChanged = QtCore.pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        self.worker: GotovkaWorker | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)

        header, self.switch = CommonUI.create_switch_header("Готовка", "🍜")
        self.switch.clicked.connect(self.handle_toggle)
        self.switch.clicked.connect(self.statusChanged.emit)
        layout.addLayout(header)

        settings_group, settings_layout = CommonUI.create_settings_group()

        dish_layout, self.dish_combo = CommonUI.create_combo("Выберите блюдо:", list(RECIPES.keys()))
        settings_layout.addLayout(dish_layout)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        layout.addStretch()

        self.log_output = CommonUI.add_log_field(layout)


    def handle_toggle(self):
        selected_dish = self.dish_combo.currentText()
        ScriptController.toggle_script(
            widget=self,
            worker_factory=lambda: GotovkaWorker(selected_dish),
            log_output=self.log_output
        )

class GotovkaWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)

    def __init__(self, dish_name: str):
        super().__init__()
        self._stop = threading.Event()
        self.running = True
        self.dish_name = dish_name
        self.confidence = 0.85
        self.cycles_count = 0

    def log(self, message: str):
        CommonLogger.log(message, self.log_signal)

    def _find_and_perform_action(self, image_filename: str, click_type: str) -> bool:
        full_image_path = os.path.join(BASE_ASSETS_PATH, image_filename)
        try:
            location = pyautogui.locateCenterOnScreen(full_image_path, confidence=self.confidence)
            if location:
                if click_type == "right":
                    pyautogui.rightClick(location)
                    self.log(f"[✓] Использован/перетащен: {image_filename}.")
                elif click_type == "left":
                    pyautogui.click(location)
                    self.log(f"[✓] Клик по кнопке: {image_filename}.")
                return True
            else:
                self.log(f"[!] Изображение не найдено: {image_filename}.")
                return False
        except Exception as e:
            return False

    def _execute_recipe(self) -> bool:
        recipe_steps = RECIPES.get(self.dish_name)
        for image_filename, action_type in recipe_steps:
            if not self.running:
                return False
            if not self._find_and_perform_action(image_filename, action_type):
                return False
            self._stop.wait(0.1)

        self.log(f"[✓] Все шаги для приготовления '{self.dish_name}' выполнены.")
        return True

    def run(self):
        self.log(f"[→] Скрипт готовки запущен для блюда: {self.dish_name}")
        rage_window_missing = True
        waiting_for_recipe_elements = False

        try:
            while self.running:
                if not CommonLogger.is_rage_mp_active():
                    if not rage_window_missing:
                        self.log("[!] Окно RAGE Multiplayer не активно. Ожидание...")
                        rage_window_missing = True
                    self._stop.wait(1)
                    continue
                else:
                    if rage_window_missing:
                        self.log("[✓] Окно RAGE Multiplayer активно.")
                        rage_window_missing = False

                if self._execute_recipe():
                    self.cycles_count += 1
                    self.log(f"[✓] Цикл готовки №{self.cycles_count} для '{self.dish_name}' завершён.")
                    self.log("Ожидание перезарядки (5.5 секунд)...")
                    waiting_for_recipe_elements = False
                    self._stop.wait(5.5)
                else:
                    if not waiting_for_recipe_elements:
                        self.log(f"[!] Ожидание появления всех элементов для '{self.dish_name}'...")
                        waiting_for_recipe_elements = True
                    self._stop.wait(1)

        except Exception as exc:
            self.log(f"[Ошибка потока] {exc}")
        finally:
            if self.running:
                self.log("[■] Скрипт готовки завершён.")

