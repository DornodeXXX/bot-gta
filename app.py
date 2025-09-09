import sys
from PyQt5 import QtWidgets, QtCore, QtGui
from widgets.modern_window import ModernWindow
from widgets.styles import COLORS

def main():
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("BOT [GTA5RP]")
    app.setStyle("Fusion")

    font = app.font()
    font.setFamily("Helvetica")
    font.setPointSize(10)
    app.setFont(font)

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
