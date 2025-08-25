from PyQt5 import QtWidgets, QtCore, QtGui, QtNetwork
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices


class IndexPage(QtWidgets.QWidget):
    def __init__(self, version):
        super().__init__()
        self.setStyleSheet("background-color: rgba(26, 26, 30, 180);")

        layout = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel("📇 Главная")
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;background: none;")
        layout.addWidget(title)
        layout.addSpacing(10)

        description = QtWidgets.QLabel(
            "🎮 Добро пожаловать в BOT [GTA5RP]!\n\n"
            "🔨 Этот инструмент предназначен для автоматизации задач в игре GTA5RP на платформе RAGE Multiplayer.\n\n"
            "📁 Выберите нужный модуль из меню слева.\n\n"
            "⚠️ Использование данного ПО может нарушать правила сервера.\nИспользуйте на свой страх и риск.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n"
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: lightgray; font-size: 14px;background: none;")
        layout.addWidget(description)

        telegram_container = QtWidgets.QHBoxLayout()
        telegram_container.setContentsMargins(1, 0, 0, 0)

        telegram_icon = QtWidgets.QLabel()
        telegram_icon.setPixmap(QtGui.QPixmap("assets/tg.png").scaled(16, 16, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        telegram_container.addWidget(telegram_icon)

        telegram_link = QtWidgets.QLabel('<a href="https://t.me/id3001" style="color: #0088cc; text-decoration: none;">Telegram - @id3001</a>')
        telegram_link.setOpenExternalLinks(False)
        telegram_link.linkActivated.connect(lambda: QDesktopServices.openUrl(QUrl("https://t.me/id3001")))
        telegram_link.setStyleSheet("color: #0088cc; font-size: 14px; background: none;")
        telegram_container.addWidget(telegram_link)
        telegram_container.addStretch()

        layout.addLayout(telegram_container)

        self.online_label = QtWidgets.QLabel("🌐 Запусков сегодня: ...")
        self.online_label.setStyleSheet("color: lightgray; font-size: 14px; background: none;")
        layout.addWidget(self.online_label)
        layout.addStretch()

        version_label = QtWidgets.QLabel(f"Версия: {version}")
        version_label.setStyleSheet("color: gray; font-size: 12px;background: none;")
        version_label.setAlignment(QtCore.Qt.AlignRight)
        layout.addWidget(version_label)
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
