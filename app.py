import sys
from PyQt5 import QtWidgets, QtCore, QtGui
from widgets import COLORS, ModernWindow

def main():
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("BOT [GTA5RP]")
    app.setStyle("Fusion")

    font = app.font()
    font.setFamily("Helvetica")
    font.setPointSize(10)
    app.setFont(font)

    class FocusRemover(QtCore.QObject):
        def eventFilter(self, obj, event):
            if event.type() in (QtCore.QEvent.MouseButtonPress, QtCore.QEvent.MouseButtonRelease):
                try:
                    pos = event.globalPos()
                except Exception:
                    pos = None
                clicked = QtWidgets.QApplication.widgetAt(pos) if pos is not None else None
                focused = QtWidgets.QApplication.focusWidget()
                if isinstance(focused, QtWidgets.QLineEdit):
                    if clicked is None:
                        focused.clearFocus()
                    else:
                        w = clicked
                        inside = False
                        while w is not None:
                            if w is focused:
                                inside = True
                                break
                            w = w.parent()
                        if not inside:
                            focused.clearFocus()
            return super().eventFilter(obj, event)
            
    _focus_remover = FocusRemover()
    app.installEventFilter(_focus_remover)
    app._focus_remover = _focus_remover

    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(COLORS["bg"]))
    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(COLORS["text"]))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(COLORS["surface"]))
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(COLORS["surface_hover"]))
    palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(COLORS["surface"]))
    palette.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor(COLORS["text"]))
    palette.setColor(QtGui.QPalette.Text, QtGui.QColor(COLORS["text"]))
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor(COLORS["surface"]))
    palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(COLORS["text"]))
    palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
    app.setPalette(palette)

    w = ModernWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
