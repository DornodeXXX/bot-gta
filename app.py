import sys
import os
from functools import partial
import urllib.request
import urllib.error
import webbrowser
from PyQt5 import QtWidgets, QtCore, QtGui
from widgets.switch_button import SwitchButton
from pages.index_page import IndexPage
from pages.port_page import PortPage
from pages.anti_afk_page import AntiAfkPage
from pages.stroyka_page import StroykaPage
from pages.shveika_page import ShveikaPage
from pages.gotovka_page import GotovkaPage
from pages.cow_page import CowPage
from pages.gym_page import GymPage

class BotMasterApp(QtWidgets.QWidget):
    CURRENT_VERSION = "2.6"

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_window_properties()
        self.setup_menu_and_pages()
        self.check_for_updates()
        
    def setup_ui(self):
        self.setWindowTitle("BOT [GTA5RP]")
        self.setMinimumSize(800, 680)
        self.resize(800, 600)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        self.container = QtWidgets.QFrame()
        self.container.setObjectName("container")
        
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QtGui.QColor(0, 0, 0, 80))
        self.container.setGraphicsEffect(shadow)
        
        container_layout = QtWidgets.QVBoxLayout(self.container)
        container_layout.setSpacing(0)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.setup_title_bar()
        container_layout.addWidget(self.title_bar)
        
        content_layout = QtWidgets.QHBoxLayout()
        content_layout.setContentsMargins(20, 10, 20, 20)
        content_layout.setSpacing(20)
        
        self.menu_layout = QtWidgets.QVBoxLayout()
        self.menu_layout.setSpacing(10)
        
        self.stack = QtWidgets.QStackedWidget()
        self.stack.setObjectName("stack")
        
        content_layout.addLayout(self.menu_layout, 1)
        content_layout.addWidget(self.stack, 3)
        container_layout.addLayout(content_layout)
        main_layout.addWidget(self.container)
        
    def setup_window_properties(self):
        icon_path = "icon.png"
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))
        
        self.drag_pos = None
        self.current_button = None
    
    def setup_title_bar(self):
        self.title_bar = QtWidgets.QFrame()
        self.title_bar.setObjectName("titleBar")
        self.title_bar.setFixedHeight(40)
        
        title_bar_layout = QtWidgets.QHBoxLayout(self.title_bar)
        title_bar_layout.setContentsMargins(17, 0, 17, 0)
        
        icon_label = QtWidgets.QLabel()
        if os.path.exists("icon.png"):
            pixmap = QtGui.QPixmap("icon.png")
            icon_label.setPixmap(pixmap.scaled(20, 20, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        icon_label.setFixedSize(20, 20)
        
        self.title_label = QtWidgets.QLabel("BOT [GTA5RP]")
        self.title_label.setObjectName("titleLabel")
        
        title_with_icon = QtWidgets.QHBoxLayout()
        title_with_icon.addWidget(icon_label)
        title_with_icon.addWidget(self.title_label)
        
        title_container = QtWidgets.QWidget()
        title_container.setLayout(title_with_icon)
        
        title_bar_layout.addWidget(title_container)
        title_bar_layout.addStretch()
        
        minimize_btn = self.create_window_button("-", self.showMinimized)
        close_btn = self.create_window_button("×", self.close)
        
        title_bar_layout.addWidget(minimize_btn)
        title_bar_layout.addWidget(close_btn)
        
        self.title_bar.mousePressEvent = self.title_mouse_press
        self.title_bar.mouseMoveEvent = self.title_mouse_move
    
    def create_window_button(self, text, action):
        btn = QtWidgets.QPushButton(text)
        btn.setObjectName("windowButton")
        btn.setFixedSize(24, 24)
        btn.clicked.connect(action)
        return btn
    
    def setup_menu_and_pages(self):
        self.menu_buttons = {}
        self.pages = {}
        
        features = [
            ("Главная", "📇", IndexPage, True),
            ("Швейка", "👕", ShveikaPage, True),
            ("Качалка", "🏋️", GymPage, True),
            ("Стройка|Шахта", "🚧", StroykaPage, True),
            ("Порт", "🚢", PortPage, True),
            ("Коровы", "🐄", CowPage, True),
            ("Анти-АФК", "🎯", AntiAfkPage, True),
            ("Кулинария", "🍜", GotovkaPage, True),
        ]
        
        menu_buttons_layout = QtWidgets.QVBoxLayout()
        menu_buttons_layout.setSpacing(10)
        
        for name, emoji, page_class, enabled in features:
            btn = self.create_menu_button(f"{emoji} {name}", enabled)
            self.menu_buttons[name] = btn
            menu_buttons_layout.addWidget(btn)
            
            if enabled:
                if name == "Главная":
                    self.pages[name] = page_class(version=self.CURRENT_VERSION)
                else:
                    self.pages[name] = page_class()
                self.stack.addWidget(self.pages[name])
                btn.clicked.connect(partial(self.switch_tab, name, btn))
        
        self.update_btn = self.create_menu_button("🔄 Доступна новая версия", True)
        self.update_btn.setObjectName("updateButton")
        self.update_btn.clicked.connect(self.open_updates)
        self.update_btn.hide()
        
        update_layout = QtWidgets.QVBoxLayout()
        update_layout.setSpacing(10)
        update_layout.addWidget(self.update_btn)
        
        self.menu_layout.addLayout(menu_buttons_layout)
        self.menu_layout.addStretch()
        self.menu_layout.addLayout(update_layout)
        
        if "Главная" in self.pages:
            self.stack.setCurrentWidget(self.pages["Главная"])
            self.menu_buttons["Главная"].setChecked(True)
            self.current_button = self.menu_buttons["Главная"]
    
    def create_menu_button(self, text, enabled=True):
        btn = QtWidgets.QPushButton(text)
        btn.setFixedHeight(40)
        btn.setCheckable(True)
        btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        btn.setObjectName("menuButton" if enabled else "disabledMenuButton")
        btn.setEnabled(enabled)
        return btn
    
    def title_mouse_press(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
    
    def title_mouse_move(self, event):
        if self.drag_pos and event.buttons() == QtCore.Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
    
    def switch_tab(self, name, button):
        self.stack.setCurrentWidget(self.pages[name])
        if self.current_button and self.current_button != button:
            self.current_button.setChecked(False)
        button.setChecked(True)
        self.current_button = button
    
    
    def open_updates(self):
        webbrowser.open("https://github.com/DornodeXXX/bot-gta/releases")
    
    def check_for_updates(self):
        try:
            version_url = "https://raw.githubusercontent.com/DornodeXXX/bot-gta/main/version.txt"
            with urllib.request.urlopen(version_url, timeout=5) as response:
                latest_version = response.read().decode('utf-8').strip()
                
                if latest_version > self.CURRENT_VERSION:
                    self.update_btn.show()
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

if __name__ == "__main__":
    if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    
    with open("styles.qss", "r") as file:
        app.setStyleSheet(file.read())
    
    window = BotMasterApp()
    window.show()
    
    sys.exit(app.exec_())