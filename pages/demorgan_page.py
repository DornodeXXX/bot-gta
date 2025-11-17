import time
import pyautogui
import cv2
import numpy as np
import mss
from widgets.common import CommonLogger, ScriptController, auto_detect_region, load_images, SettingsManager, OverlayWindow, CheckWithTooltip,CommonUI
import threading
import time, threading
from PyQt5 import QtWidgets, QtCore
import os, time, sys
from PyQt5 import QtMultimedia

def resource_path(relative_path: str) -> str:
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, relative_path)

def play_beep(self):
    timer_path = resource_path(os.path.join("assets", "beep.wav"))
    if os.path.exists(timer_path):
        self.sound_player = QtMultimedia.QMediaPlayer() 
        self.sound_player.setMedia(QtMultimedia.QMediaContent(QtCore.QUrl.fromLocalFile(timer_path)))
        self.sound_player.setVolume(100)
        self.sound_player.play()
    else:
        print(f"[⚠️] Файл {timer_path} не найден.")

class DemorganPage(QtWidgets.QWidget):
    statusChanged = QtCore.pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.worker: DemorganWorker | None = None
        self.settings = SettingsManager()
        self._init_ui()
        self._load_settings()
        self.hud = OverlayWindow(
            title="Деморган",
            fields={"Действий": 0},
            f_keys="F1",
            auto_monitor=False
        )

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)

        header, self.switch = CommonUI.create_switch_header("Деморган", "⛓")
        self.switch.clicked.connect(self.handle_toggle)
        self.switch.clicked.connect(self.statusChanged.emit)
        layout.addLayout(header)

        settings_group, settings_layout = CommonUI.create_settings_group()

        tokar_layout, self.tokar_pause_slider, self.get_tokar_pause = CommonUI.create_slider_row("Время сигнала токаря:", minimum=30, maximum=80, default=65, suffix="сек", step=1)
        shveika_layout, self.shveika_pause_slider, self.get_shveika_pause = CommonUI.create_slider_row("Время сигнала швейки:", minimum=60, maximum=100, default=85, suffix="сек", step=1)
        shveika_exe_layout, self.shveika_exe_slider, self.get_tokar_pause = CommonUI.create_slider_row("Время между действиями:", minimum=0, maximum=4, default=0, suffix="сек", step=0.1)

        self.checkoverlay = CheckWithTooltip("Оверлей - BETA", "Оверлей показывает интерфейс поверх всех окон игры.")

        settings_layout.addLayout(tokar_layout)
        settings_layout.addLayout(shveika_layout)
        settings_layout.addLayout(shveika_exe_layout)
        settings_layout.addWidget(self.checkoverlay)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        layout.addStretch()

        self.log_output = CommonUI.add_log_field(layout)
        
    def _load_settings(self):
        self.tokar_pause_slider.setValue(self.settings.get("demorgan", "tokar_pause", 65))
        self.shveika_pause_slider.setValue(self.settings.get("demorgan", "shveika_pause", 85))
        self.shveika_exe_slider.setValue(int(self.settings.get("demorgan", "shveika_exe", 0)*10))

    def _save_settings(self):
        self.settings.save_group("demorgan", {
            "tokar_pause": self.tokar_pause_slider.value(),
            "shveika_pause": self.shveika_pause_slider.value(),
            "shveika_exe": self.get_tokar_pause(),
        })



    def handle_toggle(self):
        self._save_settings()
        is_starting = self.switch.isChecked()

        ScriptController.toggle_script(
            widget=self,
            worker_factory=DemorganWorker,
            log_output=self.log_output,
            worker_kwargs={"tokar_pause": self.tokar_pause_slider.value(), 
                           "shveika_pause": self.shveika_pause_slider.value(), 
                           "shveika_exe": self.get_tokar_pause()},
            extra_signals = {
                "hud_update_signal": lambda data: self.hud.update_values(**data)
            }
        )

        if is_starting:
            if self.checkoverlay.isChecked():
                self.hud.start_monitor()
                self.hud.show()
            else:
                self.hud.stop_monitor()
                self.hud.close()
        else:
            self.hud.stop_monitor()
            self.hud.close()

class TimerWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    finished_signal = QtCore.pyqtSignal()
    hud_update_signal = QtCore.pyqtSignal(dict)

    def __init__(self, seconds: int, label: str):
        super().__init__()
        self.seconds = seconds
        self.label = label
        self.running = True

    def run(self):
        start = time.time()
        while self.running and (time.time() - start) < self.seconds:
            left = self.seconds - int(time.time() - start)
            mins, secs = divmod(left, 60)
            self.log_signal.emit(f"[⏳] Таймер: осталось {mins:02d}:{secs:02d}")
            self.hud_update_signal.emit({
                "Сдавать через": f"{mins:02d}:{secs:02d}"
            })
            time.sleep(1)
        if self.running:
            self.log_signal.emit(f"[✔] {self.label} таймер завершён!")
            self.hud_update_signal.emit({"Сдавать через": None})
            play_beep(self)
            self.finished_signal.emit()

    def stop(self):
        self.running = False

class DemorganWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    counter_signal = QtCore.pyqtSignal(int)
    hud_update_signal = QtCore.pyqtSignal(dict)
    
    CONFIDENCE = 0.95

    def start_timer(self, seconds: int, label: str):
        self.timer_thread = TimerWorker(seconds, label)
        self.timer_thread.log_signal.connect(self.log)
        self.timer_thread.hud_update_signal.connect(self.hud_update_signal)
        self.timer_thread.start()

    def __init__(self, width_ratio=0.5, height_ratio=0.6, top_ratio=0.25, tokar_pause: float = 0.0, shveika_pause: float = 0.0, shveika_exe: float = 0.0):
        super().__init__()
        self.running = True
        self.timer_thread = None
        self._count = 0
        self.tokar_pause = tokar_pause
        self.shveika_pause = shveika_pause
        self.shveika_exe = shveika_exe
        self.last_known_position = None
        self.template = self._load_template()
        self.monitor = auto_detect_region(width_ratio, height_ratio, top_ratio)
        self.monitor2 = auto_detect_region(0.5, 0.8, 0.1)
        self._stop = threading.Event()
        self.image_paths = load_images("shveika", count=20)
        self.shveika_templates = self._load_shveika_templates(self.image_paths)
        self.sentinel_idx = 0
        self.sentinel_threshold = 0.92
        self.is_tokar_found = False

    def _load_template(self):
        t = cv2.imread("assets/tokar/i3.png", cv2.IMREAD_UNCHANGED)
        if t is None:
            raise FileNotFoundError("Не найден шаблон токаря")
        return t[:, :, :3]

    def _load_shveika_templates(self, paths):
        templates = []
        for p in paths:
            img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise FileNotFoundError(f"Не найден шаблон: {p}")
            if img.shape[2] == 4:
                img = img[:, :, :3]
            templates.append(img)
        return templates

    def log(self, message: str):
        CommonLogger.log(message, self.log_signal)

    def run(self):
        self.log(f"[→] Скрипт Деморган запущен")
        tokar_thread = threading.Thread(target=self.run_tokar, args=(self.template, self.monitor))
        script_thread = threading.Thread(target=self.run_shveika) 
        tokar_thread.start()
        script_thread.start()
        tokar_thread.join()
        script_thread.join()

    def _locate_one(self, image_bgr, templ_bgr, threshold):
        res = cv2.matchTemplate(image_bgr, templ_bgr, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        if max_val >= threshold:
            h, w = templ_bgr.shape[:2]
            center = (max_loc[0] + w // 2 + self.monitor2["left"],
                      max_loc[1] + h // 2 + self.monitor2["top"])
            return center, max_val
        return None, max_val
        
    def _locate_all_20(self, image_bgr, threshold):
        coords = []
        for templ in self.shveika_templates:
            c, score = self._locate_one(image_bgr, templ, threshold)
            coords.append(c)
        return coords

    def run_shveika(self):
        last_wait_logged = 0.0
        sentinel_tem = self.shveika_templates[self.sentinel_idx]
        try:
            with mss.mss() as sct:
                while self.running:
                    if self.is_tokar_found:
                        self._stop.wait(0.05)
                        continue

                    frame = np.array(sct.grab(self.monitor2))
                    image_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    sentinel_center, sentinel_score = self._locate_one(image_bgr, sentinel_tem, self.sentinel_threshold)

                    if sentinel_center is None:
                        now = time.time()
                        if now - last_wait_logged > 1.5:
                            last_wait_logged = now
                        self._stop.wait(0.01)
                        continue

                    coords = self._locate_all_20(image_bgr, self.CONFIDENCE)

                    if all(coords):
                        self.start_timer(self.shveika_pause, "Швейка")
                        self._count += 1
                        self.counter_signal.emit(self._count)
                        self.log(f"[✓] Все 20 точек найдены. Начинаю клик.")
                        self.current_actions = self._count
                        self.hud_update_signal.emit({
                            "Действий": self.current_actions,
                            "Сейчас": "Швейка",
                        })
                        for i, pos in enumerate(coords):
                            if not self.running:
                                break
                            if i == 0:
                                pyautogui.click(pos)
                                self.log(f"[Клик] {i+1}/20: {pos} (1 раз)")
                            else:
                                pyautogui.click(pos)
                                self._stop.wait(self.shveika_exe)
                                pyautogui.click(pos)
                                self.log(f"[Клик] {i+1}/20: {pos} (2 раза)")
                        self._stop.wait(0.03)
                    else:
                        now = time.time()
                        if now - last_wait_logged > 1.5:
                            missing = [i+1 for i, c in enumerate(coords) if c is None]
                            self.log(f"[~] Ожидание элементов... отсутствуют: {missing[:6]}{'...' if len(missing) > 6 else ''}")
                            last_wait_logged = now
                        self._stop.wait(0.03)
        except Exception as exc:
            self.log(f"[Ошибка потока Швейки] {str(exc)}")
        finally:
            self.running = False


    def _search_in_region(self, sct, region):
        h, w = self.template.shape[:2]
        screenshot = np.array(sct.grab(region))
        screenshot_bgr = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

        result = cv2.matchTemplate(screenshot_bgr, self.template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > 0.9:
            found_x = region["left"] + max_loc[0] + w // 2
            found_y_bottom = region["top"] + max_loc[1] + h
            self.last_known_position = (found_x, found_y_bottom)
            self.is_tokar_found = True
            pyautogui.moveTo(found_x, found_y_bottom + 30)
            self.log(f"[✓] токарь найден (#{self._count})")
            self._stop.wait(0.01)
            self.is_tokar_found = False
            return True

        return False

    def run_tokar(self, template, monitor):
        h, w = template.shape[:2]
        self.template = template
        self.monitor = monitor
        self.last_known_position = None
        self.is_tracking = False

        with mss.mss() as sct:
            try:
                while self.running:
                    found = False

                    if self.last_known_position:
                        cx, cy_bottom = self.last_known_position
                        small_monitor = {
                            "left": max(cx - 100, self.monitor["left"]),
                            "top": max(cy_bottom - 100 - h // 2, self.monitor["top"]),
                            "width": min(cx + 100, self.monitor["left"] + self.monitor["width"]) - max(cx - 100, self.monitor["left"]),
                            "height": min(cy_bottom + 100 - h // 2, self.monitor["top"] + self.monitor["height"]) - max(cy_bottom - 100 - h // 2, self.monitor["top"]),
                        }
                        found = self._search_in_region(sct, small_monitor)

                    if not found:
                        found = self._search_in_region(sct, self.monitor)

                    if found and not self.is_tracking:
                        print("Элемент найден. Работа начата!")
                        self.start_timer(self.tokar_pause, "Токарь")
                        self.is_tracking = True

                    if not found:
                        self.last_known_position = None
                        if self.is_tracking:
                            print("Элемент потерян. Отслеживание остановлено.")
                            self.is_tracking = False
                        self._stop.wait(0.05)
                            
            except Exception as exc:
                self.log(f"[Ошибка потока токаря] {str(exc)}")
            finally:
                self.running = False
