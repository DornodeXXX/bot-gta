from PyQt5 import QtWidgets, QtCore, QtGui, QtNetwork
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices


class IndexPage(QtWidgets.QWidget):
    def __init__(self, version):
        super().__init__()
        self.setStyleSheet("background-color: rgba(26, 26, 30, 180);")

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(20, 15, 20, 15)

        title = QtWidgets.QLabel("📇 Главная")
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold; background: none;")
        layout.addWidget(title)
        layout.addSpacing(5)

        description = QtWidgets.QLabel(
            "🎮 Добро пожаловать в BOT [GTA5RP]!\n\n"
            "🔨 Этот инструмент предназначен для автоматизации задач в игре GTA5RP на платформе RAGE Multiplayer.\n\n"
            "📁 Выберите нужный модуль из меню слева.\n\n"
            "⚠️ Использование данного ПО может нарушать правила сервера.\nИспользуйте на свой страх и риск."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: lightgray; font-size: 14px; background: none;")
        layout.addWidget(description)
        layout.addStretch(1)

        bottom_container = QtWidgets.QHBoxLayout()

        left_container = QtWidgets.QVBoxLayout()
        left_container.setContentsMargins(0, 0, 0, 0)

        telegram_row = QtWidgets.QHBoxLayout()
        telegram_row.setContentsMargins(0, 0, 0, 0)

        telegram_icon = QtWidgets.QLabel()
        telegram_icon.setPixmap(QtGui.QPixmap("assets/tg.png").scaled(16, 16, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        telegram_row.addWidget(telegram_icon)

        telegram_link = QtWidgets.QLabel(
            '<a href="https://t.me/id3001" style="color: #0088cc; text-decoration: none;">Telegram - @id3001</a>'
        )
        telegram_link.setOpenExternalLinks(False)
        telegram_link.linkActivated.connect(lambda: QDesktopServices.openUrl(QUrl("https://t.me/id3001")))
        telegram_link.setStyleSheet("color: #0088cc; font-size: 14px; background: none;padding-right:50px;")
        telegram_row.addWidget(telegram_link)

        left_container.addLayout(telegram_row)

        self.online_label = QtWidgets.QLabel("🌐 Запусков сегодня: ...")
        self.online_label.setStyleSheet("color: lightgray; font-size: 14px; background: none;")
        left_container.addWidget(self.online_label)

        bottom_container.addLayout(left_container)
        bottom_container.addStretch(1)

        version_label = QtWidgets.QLabel(f"Версия: {version}")
        version_label.setStyleSheet("color: gray; font-size: 12px; background: none;")
        bottom_container.addWidget(version_label, alignment=QtCore.Qt.AlignRight)

        layout.addLayout(bottom_container)
        self.setLayout(layout)

        self.load_online_count("https://dornode.ru/online.php")

    def load_online_count(self, url):
        self.manager = QtNetwork.QNetworkAccessManager(self)
        self.manager.finished.connect(self._on_response)
        request = QtNetwork.QNetworkRequest(QUrl(url))
        self.manager.get(request)

    def _on_response(self, reply):
        if reply.error() == QtNetwork.QNetworkReply.NoError:
            data = reply.readAll().data().decode("utf-8").strip()
            if data.isdigit():
                self.online_label.setText(f"🌐 Запусков сегодня: {data}")
            else:
                self.online_label.setText("🌐 Запусков сегодня: ошибка данных")
        else:
            self.online_label.setText("🌐 Запусков сегодня: ошибка сети")
        reply.deleteLater()
