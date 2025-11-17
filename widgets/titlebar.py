from PyQt5 import QtCore, QtGui, QtWidgets
from .theme import COLORS
import math, colorsys

class TitleBar(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self._dragPos = None
        self.setFixedHeight(44)
        self.setAutoFillBackground(False)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        self._phase = 0.0
        self._animation_timer = QtCore.QTimer(self)
        self._animation_timer.timeout.connect(self._update_lights)
        self._animation_timer.start(80)

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

    def _update_lights(self):
        self._phase += 0.08
        if self._phase > 1000:
            self._phase = 0
        self.update()

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

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        w = self.width()
        base_y = 4
        step = 26
        amp = 4
        light_radius = 3

        path = QtGui.QPainterPath()
        path.moveTo(8, base_y)
        for x in range(8, w - 8, step):
            y = base_y + math.sin(x / 35) * amp
            path.lineTo(x, y)
        pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 35))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawPath(path)

        for i, x in enumerate(range(8, w - 8, step)):
            hue = (i * 0.08 + (self._phase / 10.0)) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            color = QtGui.QColor(int(r * 255), int(g * 255), int(b * 255))

            pulse = (math.sin(self._phase * 1.5 + i) + 1) / 2  # 0..1
            glow_radius = 6 + pulse * 4
            alpha = int(120 + pulse * 120)

            y = base_y + math.sin(x / 35) * amp + 6

            glow = QtGui.QRadialGradient(QtCore.QPointF(x, y), glow_radius)
            glow.setColorAt(0, QtGui.QColor(color.red(), color.green(), color.blue(), alpha))
            glow.setColorAt(1, QtGui.QColor(color.red(), color.green(), color.blue(), 0))
            painter.setBrush(QtGui.QBrush(glow))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(QtCore.QPointF(x, y), glow_radius, glow_radius)

            painter.setBrush(QtGui.QColor(color.red(), color.green(), color.blue(), 230))
            painter.drawEllipse(QtCore.QPointF(x, y), light_radius, light_radius)

        painter.end()
