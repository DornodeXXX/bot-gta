from PyQt5 import QtCore, QtGui, QtWidgets
from .theme import COLORS

class TitleBar(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self._dragPos = None
        self.setFixedHeight(44)
        self.setAutoFillBackground(False)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        
        self.icon_label = QtWidgets.QLabel()
        self.icon_label.setPixmap(QtGui.QPixmap("icon.png").scaled(25, 25, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        self.icon_label.setAlignment(QtCore.Qt.AlignCenter)
        self.icon_label.setFixedSize(25, 25)

        self.title_label = QtWidgets.QLabel("BOT [GTA5RP] 🎄")
        
        self.btn_min = QtWidgets.QPushButton("–")
        self.btn_close = QtWidgets.QPushButton("✕")

        for b in (self.btn_min, self.btn_close):
            b.setCursor(QtCore.Qt.PointingHandCursor)
            b.setFixedSize(36, 28)
            b.setFocusPolicy(QtCore.Qt.NoFocus)
            b.setProperty("titleButton", True)

        self.btn_close.setProperty("closeButton", True)

        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 8, 6)
        lay.setSpacing(8)
        lay.addWidget(self.icon_label)
        lay.addWidget(self.title_label)
        lay.addStretch(1)
        lay.addWidget(self.btn_min)
        lay.addWidget(self.btn_close)

        self.btn_min.clicked.connect(self.on_minimize)
        self.btn_close.clicked.connect(self.on_close)
        
        self.setStyleSheet(f"""
            TitleBar {{
                background-color: rgba(255, 255, 255, 0.03);
                border-bottom: 1px solid {COLORS["border"]};
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }}
            QLabel {{ 
                color: {COLORS["text"]}; 
                font-size: 14px; 
                font-weight: 600; 
            }}
            QPushButton[titleButton="true"] {{
                color: {COLORS["muted"]};
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 6px;
                font-size: 13px;
            }}
            QPushButton[titleButton="true"]:hover {{
                background: rgba(255, 255, 255, 0.06);
                color: {COLORS["text"]};
            }}
            QPushButton[closeButton="true"]:hover {{
                background: {COLORS["danger"]};
                color: white;
                border-color: {COLORS["danger"]};
            }}
        """)

    def on_minimize(self):
        self.window().showMinimized()

    def on_close(self):
        self.window().close()

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton:
            self._dragPos = e.globalPos() - self.window().frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if self._dragPos and e.buttons() == QtCore.Qt.LeftButton and not self.window().isMaximized():
            self.window().move(e.globalPos() - self._dragPos)
            e.accept()