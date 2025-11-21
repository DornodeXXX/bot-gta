from PyQt5 import QtWidgets, QtCore, QtGui, QtNetwork
from PyQt5.QtCore import QUrl

GLOBAL_NETWORK_MANAGER = QtNetwork.QNetworkAccessManager()

class IndexPage(QtWidgets.QWidget):
    def __init__(self, version):
        super().__init__()
        self.version = version
        self.telegram_icon_pixmap = QtGui.QPixmap("assets/tg.png").scaled(18, 18,QtCore.Qt.KeepAspectRatio,QtCore.Qt.SmoothTransformation)

        self.init_styles()
        self.build_ui()
        self.load_online_count()

    def init_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(26, 26, 30, 180);
                font-family: 'Inter', sans-serif;
            }

            QLabel {
                background: transparent;
                color: lightgray;
                font-size: 14px;
            }

            QLabel#title {
                color: white;
                font-size: 26px;
                font-weight: bold;
                letter-spacing: 1px;
            }
                           
            QLabel.small {
                color: gray;
                font-size: 12px;
            }
        """)

    def build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)

        title = QtWidgets.QLabel("🏠 Главная")
        title.setObjectName("title")
        layout.addWidget(title)

        description = QtWidgets.QLabel(
            "🎮 <b>Добро пожаловать в BOT [GTA5RP]!</b><br><br>"
            "Этот мощный инструмент поможет вам <span style='color:#00ffcc;'>автоматизировать рутину</span> "
            "в <b>GTA5RP</b> на платформе <b>RAGE Multiplayer</b>.<br><br>"
            "⚙️ <u>Ключевые фичи:</u><br>"
            "• Автоматизация повторяющихся задач<br>"
            "• Интуитивный и стильный интерфейс<br>"
            "• Полная кастомизация под ваш стиль игры<br>"
            "• Регулярные обновления и поддержка<br><br>"
            "📁 Перейдите в меню сверху и выберите модуль — и вперёд к доминации!<br><br>"
            "⚠️ <i>Внимание: использование может нарушать правила сервера. Играйте умно!</i><br><br>"
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        layout.addStretch(1)

        bottom_container = QtWidgets.QHBoxLayout()

        left_container = QtWidgets.QVBoxLayout()
        left_container.setSpacing(8)

        telegram_row = QtWidgets.QHBoxLayout()

        telegram_icon = QtWidgets.QLabel()
        telegram_icon.setPixmap(self.telegram_icon_pixmap)
        telegram_row.addWidget(telegram_icon)

        telegram_link = QtWidgets.QLabel(
            '<a href="https://t.me/id3001" '
            'style="color:#0088cc; text-decoration:none; font-size:14px;">'
            'Telegram — <b>@id3001</b></a>'
        )
        telegram_link.setTextFormat(QtCore.Qt.RichText)
        telegram_link.setOpenExternalLinks(True)
        telegram_link.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        telegram_row.addWidget(telegram_link, alignment=QtCore.Qt.AlignLeft)
        telegram_row.addWidget(telegram_link)

        left_container.addLayout(telegram_row)

        self.online_label = QtWidgets.QLabel("🌐 Запусков сегодня: ...")
        left_container.addWidget(self.online_label)

        bottom_container.addLayout(left_container)
        bottom_container.addStretch(1)

        version_label = QtWidgets.QLabel(f"Версия: {self.version}")
        version_label.setProperty("class", "small")
        bottom_container.addWidget(version_label, alignment=QtCore.Qt.AlignRight)

        layout.addLayout(bottom_container)

    def load_online_count(self):
        request = QtNetwork.QNetworkRequest(QUrl("https://dornode.ru/online.php"))
        GLOBAL_NETWORK_MANAGER.finished.connect(self._on_response)
        GLOBAL_NETWORK_MANAGER.get(request)

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
