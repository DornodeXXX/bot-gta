from PyQt5 import QtCore, QtGui, QtWidgets
from widgets.styles import COLORS
from widgets.module_button import ModuleButton
from widgets.titlebar import TitleBar
from pages.index_page import IndexPage
from pages.port_page import PortPage
from pages.anti_afk_page import AntiAfkPage
from pages.stroyka_page import StroykaPage
from pages.shveika_page import ShveikaPage
from pages.gotovka_page import GotovkaPage
from pages.cow_page import CowPage
from pages.gym_page import GymPage
from pages.tokar_page import TokarPage
from widgets.status_dot import StatusPulseDot
from widgets.switch_button import SwitchButton
import urllib.request
import urllib.error
import webbrowser

class ModernWindow(QtWidgets.QMainWindow):
    CURRENT_VERSION = "2.8"

    def __init__(self):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.resize(720, 600)
        self.setWindowIcon(QtGui.QIcon("icon.png"))
        
        self.setObjectName("MainWindow")
        
        self.container = QtWidgets.QFrame()
        self.container.setObjectName("rootContainer")
        self.container.setStyleSheet("""
            QFrame#rootContainer {
                border-radius: 16px;
                background-color: rgba(18, 18, 20, 200);
            }
        """ % COLORS)
        '''background-color: %(bg)s;'''

        self.shadow = QtWidgets.QGraphicsDropShadowEffect(self.container)
        self.shadow.setBlurRadius(30)
        self.shadow.setOffset(0, 10)
        self.shadow.setColor(QtGui.QColor(0, 0, 0, 160))
        self.container.setGraphicsEffect(self.shadow)

        root = QtWidgets.QVBoxLayout()
        root.setContentsMargins(14, 14, 14, 14)
        root.addWidget(self.container)
        wrapper = QtWidgets.QWidget()
        wrapper.setLayout(root)
        self.setCentralWidget(wrapper)

        v = QtWidgets.QVBoxLayout(self.container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        self.titlebar = TitleBar(self, "BOT [GTA5RP]")
        self.titlebar.setStyleSheet(f"""
            TitleBar {{
                background-color: rgba(255,255,255,0.03);
                border-bottom: 1px solid {COLORS["border"]};
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }}
            QLabel {{
                color: {COLORS["text"]};
            }}
            QPushButton[titleButton="true"] {{
                color: {COLORS["muted"]};
                background: transparent;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 6px;
                font-size: 13px;
            }}
            QPushButton[titleButton="true"]:hover {{
                background: rgba(255,255,255,0.06);
                color: {COLORS["text"]};
            }}
            QPushButton[closeButton="true"]:hover {{
                background: {COLORS["danger"]};
                color: white;
                border-color: {COLORS["danger"]};
            }}
        """)
        v.addWidget(self.titlebar)

        content = QtWidgets.QWidget()
        content_lay = QtWidgets.QVBoxLayout(content)
        content_lay.setContentsMargins(16, 16, 16, 16)
        content_lay.setSpacing(5)

        self.grid_widget = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 15)
        self.grid_layout.setHorizontalSpacing(14)
        self.grid_layout.setVerticalSpacing(14)

        self.max_columns = 3

        self.stack = QtWidgets.QStackedWidget()
        self.stack.setObjectName("stack")
        self.stack.setStyleSheet("""
            QStackedWidget#stack {
                background-color: rgba(26, 26, 30, 180);
                border: 1px solid %s;
                border-radius: 14px;
            }
        """ % COLORS["border"])

        self._buttons = []
        self._indicators = []
        self._pages = []

        modules = self._prepare_modules()

        row = col = 0
        self._module_states = {}

        for i, (title, emoji, page_cls, enabled) in enumerate(modules):
            if not enabled:
                continue

            ind = StatusPulseDot(QtGui.QColor(COLORS["accent"]))

            btn = ModuleButton(title, emoji, ind)
            btn.clicked.connect(lambda b=btn, pcls=page_cls: self.on_module_clicked(b, pcls))
            self.grid_layout.addWidget(btn, row, col)

            col += 1
            if col >= self.max_columns:
                col = 0
                row += 1

            self._buttons.append(btn)
            self._indicators.append(ind)

            if page_cls is IndexPage or title == "Главная":
                page = page_cls(version=self.CURRENT_VERSION)
            else:
                page = page_cls()

            page_index = len(self._pages)
            self._pages.append(page)
            self._module_states[page_index] = False

            if hasattr(page, 'statusChanged'):
                page.statusChanged.connect(lambda status, idx=page_index: self._handle_status_change(idx, status))

            self.stack.addWidget(page)

        content_lay.addWidget(self.grid_widget)
        content_lay.addWidget(self.stack, 1)
        v.addWidget(content, 1)

        if self._buttons:
            self.on_module_clicked(self._buttons[0], modules[0][2])
            
        self.check_for_updates()

    def _handle_status_change(self, page_index: int, status: bool):
        self._module_states[page_index] = status
        
        if 0 <= page_index < len(self._buttons):
            button = self._buttons[page_index]
            button.setModuleActive(status)

    def on_module_clicked(self, btn: ModuleButton, page_cls):
        for i, b in enumerate(self._buttons):
            b.setActive(False)
        
        btn.setActive(True)

        for i, page in enumerate(self._pages):
            if isinstance(page, page_cls):
                self.stack.setCurrentIndex(i)
                break

    def _prepare_modules(self):
        data = {
            "Главная": [
                ("Главная", "📇", IndexPage, True),
                ("Швейка", "👕", ShveikaPage, True),
                ("Токарь", "⚙️", TokarPage, True),
                ("Стройка\nШахта", "🚧", StroykaPage, True),
                ("Порт", "🚢", PortPage, True),
                ("Коровы", "🐄", CowPage, True),
                ("Качалка", "🏋️", GymPage, True),
                ("Кулинария", "🍜", GotovkaPage, True),
                ("Анти-АФК", "🎯", AntiAfkPage, True),
            ],
        }
        flat = []
        for _, items in data.items():
            for item in items:
                flat.append(item)
        return flat

    def on_module_clicked(self, btn: ModuleButton, page_cls):
        for b in self._buttons:
            b.setActive(b is btn)

        for i in range(self.stack.count()):
            if isinstance(self.stack.widget(i), page_cls):
                self.stack.setCurrentIndex(i)
                break
                
    def check_for_updates(self):
        try:
            version_url = "https://raw.githubusercontent.com/DornodeXXX/bot-gta/main/version.txt"
            with urllib.request.urlopen(version_url, timeout=5) as response:
                latest_version = response.read().decode('utf-8').strip()
                
                if latest_version > self.CURRENT_VERSION:
                    reply = QtWidgets.QMessageBox.question(
                        self,
                        "Обновление доступно",
                        f"Доступна новая версия {latest_version}!\nТекущая версия: {self.CURRENT_VERSION}\nХотите скачать?",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                    )
                    if reply == QtWidgets.QMessageBox.Yes:
                        github_url = "https://github.com/DornodeXXX/bot-gta/releases"
                        webbrowser.open(github_url)
        except urllib.error.URLError as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось проверить обновления: {str(e)}"
            )