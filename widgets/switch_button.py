from PyQt5 import QtWidgets, QtCore, QtGui
import math

def _gradient_145deg(rect, c1, c2):
    angle = math.radians(145)
    vx, vy = math.cos(angle), math.sin(angle)
    w, h = rect.width(), rect.height()
    cx, cy = rect.center().x(), rect.center().y()
    r = math.hypot(w, h)
    p1 = QtCore.QPointF(cx - vx * r, cy - vy * r)
    p2 = QtCore.QPointF(cx + vx * r, cy + vy * r)

    grad = QtGui.QLinearGradient(p1, p2)
    grad.setColorAt(0.0, c1)
    grad.setColorAt(1.0, c2)
    return grad

class SwitchButton(QtWidgets.QWidget):
    clicked = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None, padding=(5, 10, 5, 10)):
        super().__init__(parent)

        self._track_w, self._track_h = 76, 28
        self._padding = padding 

        full_width = self._track_w + self._padding[1] + self._padding[3]
        full_height = self._track_h + self._padding[0] + self._padding[2]

        self.setMinimumSize(full_width, full_height)
        self.setMaximumHeight(full_height)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        self._checked = False

        self._dot_w_ratio = 50 / 86.0
        self._dot_h_ratio = 32 / 38.0
        self._dot_margin = 4

        self._bg_mix = 0.0
        self._dot_x = float(self._dot_margin + self._padding[3])
        self._dot_scale = 1.0
        self._filter_opacity = 0.0
        self._specular_strength = 0.0

        self._off_c1 = QtGui.QColor("#e4e4e6")
        self._off_c2 = QtGui.QColor("#d7d7db")
        self._on_c1 = QtGui.QColor("#3ccb60")
        self._on_c2 = QtGui.QColor("#42ba64")

        self.animGroup = QtCore.QParallelAnimationGroup(self)

        self.anim_bg = QtCore.QPropertyAnimation(self, b"bg_mix", self)
        self.anim_bg.setDuration(500)
        self.anim_bg.setEasingCurve(QtCore.QEasingCurve.InOutCubic)

        self.anim_dot_x = QtCore.QPropertyAnimation(self, b"dot_x", self)
        self.anim_dot_x.setDuration(500)
        self.anim_dot_x.setEasingCurve(QtCore.QEasingCurve.Linear)

        self.anim_dot_scale = QtCore.QPropertyAnimation(self, b"dot_scale", self)
        self.anim_dot_scale.setDuration(500)
        self.anim_dot_scale.setEasingCurve(QtCore.QEasingCurve.Linear)

        self.anim_filter = QtCore.QPropertyAnimation(self, b"filter_opacity", self)
        self.anim_filter.setDuration(500)
        self.anim_filter.setEasingCurve(QtCore.QEasingCurve.Linear)

        self.anim_specular = QtCore.QPropertyAnimation(self, b"specular_strength", self)
        self.anim_specular.setDuration(500)
        self.anim_specular.setEasingCurve(QtCore.QEasingCurve.Linear)

        self.animGroup.addAnimation(self.anim_bg)
        self.animGroup.addAnimation(self.anim_dot_x)
        self.animGroup.addAnimation(self.anim_dot_scale)
        self.animGroup.addAnimation(self.anim_filter)
        self.animGroup.addAnimation(self.anim_specular)

        self.setCursor(QtCore.Qt.PointingHandCursor)

    @QtCore.pyqtProperty(float)
    def bg_mix(self):
        return self._bg_mix

    @bg_mix.setter
    def bg_mix(self, v):
        self._bg_mix = max(0.0, min(1.0, v))
        self.update()

    @QtCore.pyqtProperty(float)
    def dot_x(self):
        return self._dot_x

    @dot_x.setter
    def dot_x(self, v):
        self._dot_x = v
        self.update()

    @QtCore.pyqtProperty(float)
    def dot_scale(self):
        return self._dot_scale

    @dot_scale.setter
    def dot_scale(self, v):
        self._dot_scale = v
        self.update()

    @QtCore.pyqtProperty(float)
    def filter_opacity(self):
        return self._filter_opacity

    @filter_opacity.setter
    def filter_opacity(self, v):
        self._filter_opacity = max(0.0, min(1.0, v))
        self.update()

    @QtCore.pyqtProperty(float)
    def specular_strength(self):
        return self._specular_strength

    @specular_strength.setter
    def specular_strength(self, v):
        self._specular_strength = max(0.0, min(1.0, v))
        self.update()

    def isChecked(self):
        return self._checked

    def setChecked(self, state):
        state = bool(state)
        if self._checked == state:
            return
        self._checked = state
        self._start_animation(to_on=state)
        self.clicked.emit(self._checked)

    def setPadding(self, top: int, right: int, bottom: int, left: int):
        self._padding = (top, right, bottom, left)
        full_width = self._track_w + self._padding[1] + self._padding[3]
        full_height = self._track_h + self._padding[0] + self._padding[2]
        self.setMinimumSize(full_width, full_height)
        self.setMaximumHeight(full_height)
        self.updateGeometry()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.setChecked(not self._checked)

    def sizeHint(self):
        full_width = self._track_w + self._padding[1] + self._padding[3]
        full_height = self._track_h + self._padding[0] + self._padding[2]
        return QtCore.QSize(full_width, full_height)

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)

        track_w, track_h = self._track_w, self._track_h
        track_radius = track_h / 2.0
        track_rect = QtCore.QRectF(
            self._padding[3],
            self._padding[0],
            track_w, 
            track_h
        )

        p.save()
        path = QtGui.QPainterPath()
        path.addRoundedRect(track_rect, track_radius, track_radius)
        p.setClipPath(path)

        grad_off = _gradient_145deg(track_rect, self._off_c1, self._off_c2)
        grad_on = _gradient_145deg(track_rect, self._on_c1, self._on_c2)

        p.setBrush(grad_off)
        p.setPen(QtCore.Qt.NoPen)
        p.drawRect(track_rect)

        if self._bg_mix > 0:
            p.setOpacity(self._bg_mix)
            p.setBrush(grad_on)
            p.drawRect(track_rect)
        p.restore()

        dot_w_base = self._dot_w_ratio * track_w
        dot_h_base = self._dot_h_ratio * track_h
        dot_radius_base = dot_h_base / 2.0

        dot_y_base_offset = (track_h - dot_h_base) / 2.0 + self._padding[0]

        dx = self._dot_x

        cx_base = dx + dot_w_base / 2.0
        cy_base = dot_y_base_offset + dot_h_base / 2.0

        p.save()

        p.translate(cx_base, cy_base)
        p.scale(self._dot_scale, self._dot_scale)
        p.translate(-cx_base, -cy_base)

        dot_rect_draw = QtCore.QRectF(dx, dot_y_base_offset, dot_w_base, dot_h_base)

        base_alpha = 240
        if self._filter_opacity > 0.0:
            base_alpha = 200 + int(40 * (1.0 - abs(self._filter_opacity - 0.8) / 0.8))
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(255, 255, 255, base_alpha))
        p.drawRoundedRect(dot_rect_draw, dot_radius_base, dot_radius_base)

        if self._specular_strength > 0.0:
            grad_top = QtGui.QLinearGradient(dot_rect_draw.topLeft(), dot_rect_draw.bottomLeft())
            s = self._specular_strength
            grad_top.setColorAt(0.0, QtGui.QColor(255, 255, 255, int(140 * s)))
            grad_top.setColorAt(0.4, QtGui.QColor(255, 255, 255, int(40 * s)))
            grad_top.setColorAt(1.0, QtGui.QColor(255, 255, 255, 0))
            p.setBrush(grad_top)
            p.drawRoundedRect(dot_rect_draw.adjusted(1, 1, -1, -1), dot_radius_base - 1, dot_radius_base - 1)

            grad_bot = QtGui.QLinearGradient(dot_rect_draw.bottomLeft(), dot_rect_draw.topLeft())
            grad_bot.setColorAt(0.0, QtGui.QColor(0, 0, 0, int(35 * s)))
            grad_bot.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
            p.setBrush(grad_bot)
            p.drawRoundedRect(dot_rect_draw.adjusted(1, 1, -1, -1), dot_radius_base - 1, dot_radius_base - 1)

        if self._filter_opacity > 0.0:
            p.setOpacity(self._filter_opacity * 0.6)
            rg = QtGui.QRadialGradient(cx_base, cy_base, dot_w_base * 0.7, cx_base, cy_base)
            rg.setColorAt(0.0, QtGui.QColor(255, 255, 255, 180))
            rg.setColorAt(0.7, QtGui.QColor(255, 255, 255, 40))
            rg.setColorAt(1.0, QtGui.QColor(255, 255, 255, 0))
            p.setBrush(rg)
            p.setPen(QtCore.Qt.NoPen)
            p.drawRoundedRect(dot_rect_draw, dot_radius_base, dot_radius_base)

        p.restore()

    def _start_animation(self, to_on: bool):
        self.animGroup.stop()

        track_w = self._track_w
        dot_w_base = self._dot_w_ratio * track_w
        x_left = float(self._dot_margin + self._padding[3])
        x_right = float(track_w - self._dot_margin - dot_w_base + self._padding[3])

        self.anim_bg.setStartValue(self._bg_mix)
        self.anim_bg.setEndValue(1.0 if to_on else 0.0)

        self.anim_dot_x.setKeyValues({}) 
        self.anim_dot_x.setStartValue(self._dot_x)
        if to_on:
            self.anim_dot_x.setKeyValueAt(0.12, self._dot_x) 
            self.anim_dot_x.setKeyValueAt(0.50, x_right)
            self.anim_dot_x.setKeyValueAt(1.0, x_right)
        else:
            self.anim_dot_x.setKeyValueAt(0.12, self._dot_x)
            self.anim_dot_x.setKeyValueAt(0.50, x_left)
            self.anim_dot_x.setKeyValueAt(1.0, x_left)
        self.anim_dot_x.setEndValue(x_right if to_on else x_left)

        self.anim_dot_scale.setKeyValues({})
        self.anim_dot_scale.setStartValue(self._dot_scale)
        self.anim_dot_scale.setKeyValueAt(0.12, 1.6)
        self.anim_dot_scale.setKeyValueAt(0.50, 1.6)
        self.anim_dot_scale.setEndValue(1.0)

        self.anim_filter.setKeyValues({})
        self.anim_filter.setStartValue(self._filter_opacity)
        self.anim_filter.setKeyValueAt(0.12, 1.0)
        self.anim_filter.setKeyValueAt(0.80, 1.0)
        self.anim_filter.setEndValue(0.0)

        self.anim_specular.setKeyValues({})
        self.anim_specular.setStartValue(self._specular_strength)
        self.anim_specular.setKeyValueAt(0.12, 1.0)
        self.anim_specular.setKeyValueAt(0.80, 1.0)
        self.anim_specular.setEndValue(0.0)

        self.animGroup.start()
