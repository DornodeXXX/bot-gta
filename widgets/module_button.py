from PyQt5 import QtCore, QtGui, QtWidgets
from .theme import COLORS
from .status_dot import StatusPulseDot

class ModuleButton(QtWidgets.QFrame):
    clicked = QtCore.pyqtSignal()

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        snow_height = 15
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(0, 0, self.width(), snow_height), 14, 14)

        gradient = QtGui.QLinearGradient(0, 0, 0, snow_height)
        gradient.setColorAt(0.0, QtGui.QColor(255, 255, 255, 230))
        gradient.setColorAt(0.6, QtGui.QColor(255, 255, 255, 60))
        gradient.setColorAt(1.0, QtCore.Qt.transparent)

        painter.fillPath(path, gradient)

    def __init__(self, title: str, emoji: str, right_indicator: StatusPulseDot):
        super().__init__()
        self._active = False
        self._indicator = right_indicator
        self._module_active = False

        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedHeight(73)
        self.setMinimumWidth(100)

        self.setObjectName("moduleCard")
        self.setStyleSheet("""
            QFrame#moduleCard {
                background-color: %(surface)s;
                border: 1px solid %(border)s;
                border-radius: 14px;
            }
        """ % COLORS)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        self.shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(18)
        self.shadow.setOffset(0, 4)
        self.shadow.setColor(COLORS["shadow"])
        self.setGraphicsEffect(self.shadow)

        self.anim_shadow = QtCore.QPropertyAnimation(self.shadow, b"blurRadius", self)
        self.anim_shadow.setDuration(180)
        self.anim_shadow.setStartValue(18)
        self.anim_shadow.setEndValue(28)
        self.anim_shadow.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        self.anim_shadow_off = QtCore.QPropertyAnimation(self.shadow, b"blurRadius", self)
        self.anim_shadow_off.setDuration(220)
        self.anim_shadow_off.setStartValue(28)
        self.anim_shadow_off.setEndValue(18)
        self.anim_shadow_off.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        h = QtWidgets.QHBoxLayout(self)
        h.setContentsMargins(14, 10, 14, 10)
        h.setSpacing(12)

        icon_wrap = QtWidgets.QLabel(emoji)
        icon_wrap.setFixedSize(36, 36)
        icon_wrap.setAlignment(QtCore.Qt.AlignCenter)
        icon_wrap.setStyleSheet("""
            QLabel {
                background-color: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 10px;
                font-size: 18px;
            }
        """)

        ttitle = QtWidgets.QLabel(f"{title}")
        ttitle.setStyleSheet("color: %s; font-size: 15px; font-weight: 600;" % COLORS["text"])

        subtitle = QtWidgets.QLabel("Модуль")
        subtitle.setStyleSheet("color: %s; font-size: 12px;" % COLORS["muted"])

        text_col = QtWidgets.QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.addWidget(ttitle)
        text_col.addWidget(subtitle)

        text_widget = QtWidgets.QWidget()
        text_widget.setLayout(text_col)

        self.ind_holder = QtWidgets.QWidget()
        ind_lay = QtWidgets.QHBoxLayout(self.ind_holder)
        ind_lay.setContentsMargins(0, 0, 0, 0)
        ind_lay.addStretch(1)
        ind_lay.addWidget(self._indicator)
        self._indicator.hide()

        h.addWidget(icon_wrap, 0)
        h.addWidget(text_widget, 1)
        h.addWidget(self.ind_holder, 0)

    def enterEvent(self, e: QtCore.QEvent):
        self.anim_shadow.stop()
        self.anim_shadow_off.stop()
        self.anim_shadow.start()
        self.setStyleSheet("""
            QFrame#moduleCard {
                background-color: %(surface_hover)s;
                border: 1px solid %(border)s;
                border-radius: 14px;
            }
        """ % COLORS)

    def leaveEvent(self, e: QtCore.QEvent):
        self.anim_shadow.stop()
        self.anim_shadow_off.stop()
        self.anim_shadow_off.start()
        self.setStyleSheet("""
            QFrame#moduleCard {
                background-color: %(surface)s;
                border: 1px solid %(border)s;
                border-radius: 14px;
            }
        """ % COLORS)

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton:
            self.setStyleSheet("""
                QFrame#moduleCard {
                    background-color: %(surface_press)s;
                    border: 1px solid %(border)s;
                    border-radius: 14px;
                }
            """ % COLORS)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
            if self.rect().contains(e.pos()):
                self.setStyleSheet("""
                    QFrame#moduleCard {
                        background-color: %(surface_hover)s;
                        border: 1px solid %(border)s;
                        border-radius: 14px;
                    }
                """ % COLORS)
            else:
                self.setStyleSheet("""
                    QFrame#moduleCard {
                        background-color: %(surface)s;
                        border: 1px solid %(border)s;
                        border-radius: 14px;
                    }
                """ % COLORS)
        super().mouseReleaseEvent(e)

    def setActive(self, active: bool):
        self._active = active
        self._update_indicator_visibility()

    def setModuleActive(self, active: bool):
        self._module_active = active
        self._update_indicator_visibility()

    def _update_indicator_visibility(self):
        if self._module_active:
            self._indicator.show()
            self._indicator.start()
        else:
            self._indicator.hide()
            self._indicator.stop()