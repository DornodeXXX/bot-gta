from PyQt5 import QtWidgets, QtCore, QtGui

class SwitchButton(QtWidgets.QWidget):
    clicked = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 30)
        self._checked = False
        self._circle_position = 2
        self._animation = QtCore.QPropertyAnimation(self, b"circle_position", self)
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        bg_color = QtGui.QColor("#4cd964" if self._checked else "#888")
        p.setBrush(bg_color)
        p.setPen(QtCore.Qt.NoPen)
        p.drawRoundedRect(QtCore.QRectF(0, 0, self.width(), self.height()), 15, 15)

        radius = self.height() - 4
        p.setBrush(QtGui.QColor("white"))
        p.drawEllipse(QtCore.QRectF(self._circle_position, 2, radius, radius))

    def mousePressEvent(self, event):
        self._checked = not self._checked
        self.animate()
        self.clicked.emit(self._checked)

    def animate(self):
        start = 2 if not self._checked else self.width() - self.height() + 2
        end = self.width() - self.height() + 2 if not self._checked else 2
        if self._checked:
            start, end = 2, self.width() - self.height() + 2
        else:
            start, end = self.width() - self.height() + 2, 2

        self._animation.stop()
        self._animation.setStartValue(start)
        self._animation.setEndValue(end)
        self._animation.start()

    def isChecked(self):
        return self._checked

    def setChecked(self, state):
        if self._checked != state:
            self._checked = state
            self.animate()
            self.update()

    @QtCore.pyqtProperty(int)
    def circle_position(self):
        return self._circle_position

    @circle_position.setter
    def circle_position(self, pos):
        self._circle_position = pos
        self.update()
