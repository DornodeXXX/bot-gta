from PyQt5 import QtCore, QtGui, QtWidgets
from widgets.styles import COLORS

class StatusPulseDot(QtWidgets.QWidget):
    def __init__(self, color=QtGui.QColor(COLORS["accent"])):
        super().__init__()
        self._halo_radius = 18.0
        self._halo_opacity = 0.35
        self._active = False
        self._color = color
        self.setFixedSize(35, 35)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self.anim_radius = QtCore.QPropertyAnimation(self, b"haloRadius", self)
        self.anim_radius.setDuration(1200)
        self.anim_radius.setStartValue(12.0)
        self.anim_radius.setEndValue(22.0)
        self.anim_radius.setEasingCurve(QtCore.QEasingCurve.InOutSine)
        self.anim_radius.setLoopCount(-1)

        self.anim_opacity = QtCore.QPropertyAnimation(self, b"haloOpacity", self)
        self.anim_opacity.setDuration(1200)
        self.anim_opacity.setStartValue(0.50)
        self.anim_opacity.setEndValue(0.05)
        self.anim_opacity.setEasingCurve(QtCore.QEasingCurve.InOutSine)
        self.anim_opacity.setLoopCount(-1)

    def sizeHint(self):
        return QtCore.QSize(22, 22)

    def getHaloRadius(self):
        return self._halo_radius

    def setHaloRadius(self, value):
        self._halo_radius = float(value)
        self.update()

    haloRadius = QtCore.pyqtProperty(float, fget=getHaloRadius, fset=setHaloRadius)

    def getHaloOpacity(self):
        return self._halo_opacity

    def setHaloOpacity(self, value):
        self._halo_opacity = float(value)
        self.update()

    haloOpacity = QtCore.pyqtProperty(float, fget=getHaloOpacity, fset=setHaloOpacity)

    def start(self):
        if not self._active:
            self._active = True
            self.anim_radius.start()
            self.anim_opacity.start()
            self.show()
            self.update()

    def stop(self):
        if self._active:
            self._active = False
            self.anim_radius.stop()
            self.anim_opacity.stop()
            self.hide()
            self.update()

    def paintEvent(self, e: QtGui.QPaintEvent):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)

        rect = self.rect()
        center = rect.center()

        if self._active:
            gradient = QtGui.QRadialGradient(center, self._halo_radius)
            c = QtGui.QColor(self._color)
            c.setAlphaF(self._halo_opacity)
            transparent = QtGui.QColor(self._color)
            transparent.setAlpha(0)
            gradient.setColorAt(0.0, c)
            gradient.setColorAt(1.0, transparent)
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QBrush(gradient))
            p.drawEllipse(center, self._halo_radius, self._halo_radius)

        p.setBrush(QtGui.QColor(self._color))
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(center, 5, 5)
        p.end()
