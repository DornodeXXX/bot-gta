import sys
import os
from functools import partial
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

ENABLED_BUTTON_STYLE = """
QPushButton {
    background-color: #2e2e2e;
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 14px;
    text-align: left;
    padding-left:15px;
    width:150px;
}
QPushButton:hover {
    background-color: #444;
}
QPushButton:checked {
    background-color: #2e2e2e;
    border-left: 4px solid #00aaff;
    border-radius: 10px;
    padding-left: 11px;
}"""

DISABLED_BUTTON_STYLE = """
QPushButton {
    background-color: #222;
    color: gray;
    border: none;
    border-radius: 10px;
    font-size: 14px;
    text-align: left;
    padding-left: 15px;
}"""

class BotMasterApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_window_properties()
        self.setup_menu()
        self.setup_pages()
        
    def setup_ui(self):
        self.setWindowTitle("BOT [GTA5RP]")
        self.setMinimumSize(800, 680)
        self.resize(800, 600)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        self.container = QtWidgets.QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: rgba(18, 18, 20, 200);
                border-radius: 20px;
            }
        """)
        
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
        self.stack.setStyleSheet("""
            background-color: rgba(26, 26, 30, 180); 
            border-radius: 10px; 
            color: white;
        """)
        
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
        self.title_bar.setFixedHeight(40)
        self.title_bar.setStyleSheet("""
            background-color: rgba(18, 18, 20, 220); 
            border-top-left-radius: 20px; 
            border-top-right-radius: 20px;
        """)
        
        title_bar_layout = QtWidgets.QHBoxLayout(self.title_bar)
        title_bar_layout.setContentsMargins(17, 0, 17, 0)
        
        icon_label = QtWidgets.QLabel()
        if os.path.exists("icon.png"):
            pixmap = QtGui.QPixmap("icon.png")
            icon_label.setPixmap(pixmap.scaled(20, 20, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        icon_label.setFixedSize(20, 20)
        
        self.title_label = QtWidgets.QLabel("BOT [GTA5RP]")
        self.title_label.setStyleSheet("""
            color: white; 
            font-size: 16px; 
            margin-left: 5px;
        """)
        
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
        btn.setFixedSize(24, 24)
        btn.setStyleSheet("""
            QPushButton {
                color: white;
                background-color: transparent;
                border: none;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: red;
                border-radius: 12px;
            }
        """)
        btn.clicked.connect(action)
        return btn
    
    def setup_menu(self):
        self.menu_buttons = {}
        features = [
            ("Главная", "📇", IndexPage, True),
            ("Швейка", "👕", ShveikaPage, True),
            ("Качалка", "🏋️", GymPage, True),
            ("Стройка|Шахта", "🚧", StroykaPage, True),
            ("Порт", "🚢", PortPage, True),
            ("Коровы", "🐄", CowPage, False),
            ("Анти-АФК", "🎯", AntiAfkPage, True),
            ("Кулинария", "🍜", GotovkaPage, True),
        ]
        
        for name, emoji, _, enabled in features:
            btn = self.create_menu_button(f"{emoji} {name}", enabled)
            self.menu_buttons[name] = btn
            self.menu_layout.addWidget(btn)
        
        self.menu_layout.addStretch()
    
    def create_menu_button(self, text, enabled=True):
        btn = QtWidgets.QPushButton(text)
        btn.setFixedHeight(40)
        btn.setCheckable(True)
        btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        
        if enabled:
            btn.setStyleSheet(ENABLED_BUTTON_STYLE)
        else:
            btn.setEnabled(False)
            btn.setStyleSheet(DISABLED_BUTTON_STYLE)
        
        return btn
    
    def setup_pages(self):
        self.pages = {
            "Главная": IndexPage(),
            "Швейка": ShveikaPage(),
            "Качалка": GymPage(),
            "Стройка|Шахта": StroykaPage(),
            "Порт": PortPage(),
            "Коровы": CowPage(),
            "Анти-АФК": AntiAfkPage(),
            "Кулинария": GotovkaPage(),
        }
        
        for name, page in self.pages.items():
            self.stack.addWidget(page)
            if name in self.menu_buttons and self.menu_buttons[name].isEnabled():
                self.menu_buttons[name].clicked.connect(
                    partial(self.switch_tab, name, self.menu_buttons[name])
                )
        
        self.stack.setCurrentWidget(self.pages["Главная"])
        self.menu_buttons["Главная"].setChecked(True)
        self.current_button = self.menu_buttons["Главная"]
    
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

if __name__ == "__main__":
    if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = BotMasterApp()
    window.show()
    
    sys.exit(app.exec_())