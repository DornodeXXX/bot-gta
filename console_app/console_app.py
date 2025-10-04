import random
import threading
import os
import sys
import time
import pyautogui
import keyboard
import vgamepad as vg
import json
from typing import Optional, Tuple, Callable
from colorama import init, Fore, Style
import requests

CONFIG_FILE = "config.json"
os.system(f"mode con: cols=60 lines=20")

def resource_path(relative_path: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

BASE_ASSETS_PATH = resource_path("assets/spin/")

def draw_menu():
    os.system("cls" if os.name == "nt" else "clear")
    init(autoreset=True)
    GREEN = Fore.GREEN
    CYAN = Fore.CYAN
    YELLOW = Fore.YELLOW
    RESET = Style.RESET_ALL
    BOLD = Style.BRIGHT
    width = os.get_terminal_size().columns
    title = "Анти-АФК"
    items = [
        f"[{GREEN}{BOLD}1{RESET}] - Вкл/Выкл анти-АФК",
        f"[{GREEN}{BOLD}2{RESET}] - Вкл/Выкл авто-колесо",
        f"[{YELLOW}{BOLD}q{RESET}] - Выход"
    ]
    
    inner_len = len(title) + 2  
    top = f"╔{'═' * inner_len}╗"
    bot = f"╚{'═' * inner_len}╝"
    
    left_pad = (width - (inner_len + 2)) // 2
    mid = " " * left_pad + f"║ {BOLD}{CYAN}{title}{RESET} ║"

    print(top.center(width))
    print(mid)
    print(bot.center(width))
    print(f"{GREEN}https://github.com/DornodeXXX/bot-gta".center(width))
    print()
    
    for item in items:
        print(f"  {item}")

    print()
    print(f"{CYAN}{'─' * 60}{RESET}".center(width))
draw_menu()


def safe_log(msg: str):
    print(msg, flush=True)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            safe_log("[!] Ошибка чтения config.json, загружаем настройки по умолчанию.")
    return {
        "anti_afk_enabled": False,
        "auto_wheel_enabled": False,
        "min_delay": 0.5,
        "max_delay": 2.0,
        "min_pause": 2.5,
        "max_pause": 4.0,
    }

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        safe_log(f"[Ошибка сохранения настроек] {e}")


requests.get('https://dornode.ru/online_con.php')

class AntiAfkWorker(threading.Thread):
    def __init__(self, min_delay=1.0, max_delay=3.5, min_pause=0.5, max_pause=2.0, checkwheel=False):
        super().__init__(daemon=True)
        self.running = False
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.min_pause = min_pause
        self.max_pause = max_pause
        self.checkwheel = checkwheel
        self.stop_event = threading.Event()
        self.last_roulette_spin_time = time.time()

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

        try:
            self.gamepad = vg.VX360Gamepad()
            self.gamepad.reset()
            self.gamepad.update()
        except Exception as e:
            self.gamepad = None
            safe_log(f"[Ошибка] не удалось создать виртуальный геймпад: {e}")

    def close(self):
        if self.gamepad:
            try:
                self.gamepad.reset()
                self.gamepad.update()
            except Exception:
                pass
            self.gamepad = None

    def click_image_in_region(self,image_filename: str,region: Optional[Tuple[int, int, int, int]] = None,confidence: float = 0.85,click: Optional[Callable[[int, int], None]] = pyautogui.click) -> bool:
        full_image_path = os.path.join(BASE_ASSETS_PATH, image_filename)
        if not os.path.exists(full_image_path):
            print(f"Ошибка: Файл изображения '{full_image_path}' не найден.")
            return False
        try:
            location = pyautogui.locateOnScreen(full_image_path, region=region, confidence=confidence)
            if location:
                if click is not None:
                    center_x, center_y = pyautogui.center(location)
                    click(center_x, center_y)
                    print(f"Изображение '{image_filename}' найдено и был выполнен клик по координатам ({center_x}, {center_y}).")
                else:
                    print(f"Изображение '{image_filename}' найдено, но клик не выполнялся (click=None).")
                return True
            else:
                print(f"Изображение '{image_filename}' не найдено.")
                return False
        except Exception:
            return False

    def perform_roulette_spin(self):
        screen_width, screen_height = pyautogui.size()
        left_half_region = (0, 0, screen_width // 2, screen_height)
        right_half_region = (screen_width // 2, 0, screen_width // 2, screen_height)
        top_half_region = (0, 0, screen_width, screen_height // 2)
        bottom_half_region = (0, screen_height // 2, screen_width, screen_height // 2)

        pos = self.click_image_in_region("cols.jpg", region=top_half_region, click=None)
        if pos:
            safe_log(f"[✓] Открываю телефон.")
            keyboard.press_and_release('up')
            time.sleep(2)

            if self.click_image_in_region("casinoIcon.png", region=right_half_region,confidence=0.55):
                safe_log(f"[✓] Открыл казино.")
                time.sleep(2)
            else: 
                return

            if self.click_image_in_region('kasspin.jpg', region=left_half_region):
                safe_log(f"[✓] Открываю колесо удачи.")
                time.sleep(2)
            else:
                return

            if self.click_image_in_region("spinbutton.jpg", region=bottom_half_region):
                safe_log(f"[✓] Кручу.")
                time.sleep(2)
            else: 
                return

            time.sleep(0.5)
            keyboard.press_and_release('esc')
            time.sleep(0.5)
            keyboard.press_and_release('esc')
            time.sleep(0.5)
            keyboard.press_and_release('backspace')
        else:
            safe_log("[→] пропускаем колесо")

    def run(self):
        self.running = True
        safe_log("[→] Скрипт анти-АФК запущен.")
        try:
            while self.running and not self.stop_event.is_set():
                direction = random.choice(list(self.DIRECTIONS.keys()))
                hold_time = random.uniform(self.min_delay, self.max_delay)
                pause_time = random.uniform(self.min_pause, self.max_pause)
                x, y = self.DIRECTIONS[direction]

                safe_log(f"[•] Направление: {direction}, зажатие: {hold_time:.2f} сек.")
                try:
                    if self.gamepad:
                        self.gamepad.left_joystick(x_value=x, y_value=y)
                        self.gamepad.update()
                except Exception as e:
                    safe_log(f"[Ошибка gamepad] {e}")

                if self.stop_event.wait(hold_time):
                    break

                try:
                    if self.gamepad:
                        self.gamepad.left_joystick(x_value=0, y_value=0)
                        self.gamepad.update()
                except Exception:
                    pass

                safe_log(f"[…] Пауза: {pause_time:.2f} сек.")
                if self.stop_event.wait(pause_time):
                    break

                if self.checkwheel and (time.time() - self.last_roulette_spin_time >= 300):
                    self.perform_roulette_spin()
                    self.last_roulette_spin_time = time.time()
        finally:
            try:
                if self.gamepad:
                    self.gamepad.left_joystick(x_value=0, y_value=0)
                    self.gamepad.update()
            except Exception:
                pass
            self.close()
            safe_log("[×] Скрипт остановлен.")

    def stop(self):
        self.running = False
        self.stop_event.set()


def main():
    config = load_config()
    worker = None
    anti_afk_enabled = config["anti_afk_enabled"]
    auto_wheel_enabled = config["auto_wheel_enabled"]
    state_lock = threading.Lock()
    exit_event = threading.Event()
   
    def save_state():
        config["anti_afk_enabled"] = anti_afk_enabled
        config["auto_wheel_enabled"] = auto_wheel_enabled
        save_config(config)

    def toggle_afk():
        nonlocal worker, anti_afk_enabled
        with state_lock:
            if worker and worker.is_alive():
                worker.stop()
                worker.join(timeout=2.0)
                worker = None
                anti_afk_enabled = False
            else:
                worker = AntiAfkWorker(
                    min_delay=config["min_delay"],
                    max_delay=config["max_delay"],
                    min_pause=config["min_pause"],
                    max_pause=config["max_pause"],
                    checkwheel=auto_wheel_enabled
                )
                worker.start()
                anti_afk_enabled = True
            save_state()

    def toggle_wheel():
        nonlocal auto_wheel_enabled, worker
        with state_lock:
            auto_wheel_enabled = not auto_wheel_enabled
            if worker and worker.is_alive():
                worker.checkwheel = auto_wheel_enabled
            safe_log(f"[i] Авто-колесо: {'ВКЛ' if auto_wheel_enabled else 'ВЫКЛ'}")
            save_state()

    def quit_app():
        safe_log("[!] Завершение работы...")
        with state_lock:
            if worker and worker.is_alive():
                worker.stop()
                worker.join(timeout=2.0)
        save_state()
        exit_event.set()
        try:
            keyboard.unhook_all()
        except Exception:
            pass

    keyboard.add_hotkey("1", toggle_afk)
    keyboard.add_hotkey("2", toggle_wheel)
    keyboard.add_hotkey("q", quit_app)

    if anti_afk_enabled:
        toggle_afk()

    try:
        exit_event.wait()
    except KeyboardInterrupt:
        safe_log("\n[!] Прервано пользователем (Ctrl+C)")
        quit_app()

    with state_lock:
        if worker and worker.is_alive():
            worker.stop()
            worker.join(timeout=2.0)

if __name__ == "__main__":
    main()
