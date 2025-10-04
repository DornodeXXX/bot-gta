from PyQt5 import QtCore, QtGui, QtWidgets
from functools import partial
import urllib.request
import urllib.error
import webbrowser
from packaging import version
from widgets import COLORS, ModuleButton, TitleBar, StatusPulseDot
from pages.index_page import IndexPage
from pages.port_page import PortPage
from pages.anti_afk_page import AntiAfkPage
from pages.stroyka_page import StroykaPage
from pages.gotovka_page import GotovkaPage
from pages.cow_page import CowPage
from pages.gym_page import GymPage
from pages.demorgan_page import DemorganPage

class UpdateChecker(QtCore.QObject):
    update_available = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version

    @QtCore.pyqtSlot()
    def check(self):
        try:
            version_url = "https://raw.githubusercontent.com/DornodeXXX/bot-gta/main/version.txt"
            with urllib.request.urlopen(version_url, timeout=5) as response:
                latest_version_str = response.read().decode('utf-8').strip()
                if version.parse(latest_version_str) > version.parse(self.current_version):
                    self.update_available.emit(latest_version_str)
        except (urllib.error.URLError, ValueError) as e:
            print(f"Could not check for updates: {e}")
        finally:
            self.finished.emit()

class ModernWindow(QtWidgets.QMainWindow):
    CURRENT_VERSION = "3.1"

    def __init__(self):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.resize(720, 600)
        self.setWindowIcon(QtGui.QIcon("icon.png"))
        self.setObjectName("MainWindow")
        
        self.container = QtWidgets.QFrame()
        self.container.setObjectName("rootContainer")
        self.container.setStyleSheet(f"""
            QFrame#rootContainer {{
                border-radius: 16px;
                background-color: rgba(18, 18, 20, 200);
            }}
        """)

        shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 10)
        shadow.setColor(QtGui.QColor(0, 0, 0, 160))
        self.container.setGraphicsEffect(shadow)

        root_layout = QtWidgets.QVBoxLayout()
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.addWidget(self.container)
        
        wrapper = QtWidgets.QWidget()
        wrapper.setLayout(root_layout)
        self.setCentralWidget(wrapper)

        main_layout = QtWidgets.QVBoxLayout(self.container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(TitleBar())

        content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(10)
        
        self.stack = QtWidgets.QStackedWidget()
        self.stack.setObjectName("stack")
        self.stack.setStyleSheet(f"""
            QStackedWidget#stack {{
                background-color: rgba(26, 26, 30, 180);
                border: 1px solid {COLORS["border"]};
                border-radius: 14px;
            }}
        """)

        self._buttons = []
        self._page_map = {}
        self._module_states = {}

        grid_widget = self._create_module_grid()
        
        content_layout.addWidget(grid_widget)
        content_layout.addWidget(self.stack, 1)
        main_layout.addWidget(content_widget, 1)

        if self._buttons:
            modules = self._get_modules()
            first_button = self._buttons[0]
            first_page_cls = modules[0][2]
            self.on_module_clicked(first_button, first_page_cls)

        self._start_update_check()

    def _create_module_grid(self):
        grid_widget = QtWidgets.QWidget()
        grid_layout = QtWidgets.QGridLayout(grid_widget)
        grid_layout.setContentsMargins(0, 0, 0, 15)
        grid_layout.setSpacing(14)

        modules = self._get_modules()
        max_columns = 3

        for i, (title, emoji, page_cls, enabled) in enumerate(modules):
            if not enabled:
                continue

            indicator = StatusPulseDot(QtGui.QColor(COLORS["accent"]))
            button = ModuleButton(title, emoji, indicator)
            button.clicked.connect(partial(self.on_module_clicked, button, page_cls))
            
            row, col = divmod(i, max_columns)
            grid_layout.addWidget(button, row, col)

            page = page_cls(version=self.CURRENT_VERSION) if page_cls is IndexPage else page_cls()
            page_index = self.stack.addWidget(page)
            
            if hasattr(page, 'statusChanged'):
                page.statusChanged.connect(lambda status, idx=page_index: self._handle_status_change(idx, status))
            
            self._buttons.append(button)
            self._page_map[page_cls] = page
            self._module_states[page_index] = False
        
        return grid_widget

    def _get_modules(self):
        return [
            ("Главная", "📇", IndexPage, True),
            ("Деморган", "⛓️", DemorganPage, True),
            ("Стройка\nШахта", "🚧", StroykaPage, True),
            ("Порт", "🚢", PortPage, True),
            ("Коровы", "🐄", CowPage, True),
            ("Качалка", "🏋️", GymPage, True),
            ("Кулинария", "🍜", GotovkaPage, True),
            ("Анти-АФК", "🎯", AntiAfkPage, True),
        ]

    def _handle_status_change(self, page_index: int, status: bool):
        self._module_states[page_index] = status
        if 0 <= page_index < len(self._buttons):
            self._buttons[page_index].setModuleActive(status)

    def on_module_clicked(self, clicked_btn: ModuleButton, page_cls):
        for btn in self._buttons:
            btn.setActive(btn is clicked_btn)
        
        if page_cls in self._page_map:
            self.stack.setCurrentWidget(self._page_map[page_cls])

    def _start_update_check(self):
        self.thread = QtCore.QThread(self)
        self.checker = UpdateChecker(self.CURRENT_VERSION)
        self.checker.moveToThread(self.thread)

        self.thread.started.connect(self.checker.check)
        self.checker.update_available.connect(self._handle_update)
        self.checker.finished.connect(self.thread.quit)

        self.thread.finished.connect(self.checker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    @QtCore.pyqtSlot(str)
    def _handle_update(self, latest_version_str):
        reply = QtWidgets.QMessageBox.question(
            self,
            "Обновление доступно",
            f"Доступна новая версия {latest_version_str}!\n"
            f"Текущая версия: {self.CURRENT_VERSION}\nХотите скачать?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            github_url = "https://github.com/DornodeXXX/bot-gta/releases"
            webbrowser.open(github_url)
            
        self.thread.quit()
        self.thread.wait()