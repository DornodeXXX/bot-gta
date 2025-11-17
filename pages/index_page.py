from PyQt5 import QtWidgets, QtCore, QtGui, QtNetwork
from PyQt5.QtCore import QUrl

class IndexPage(QtWidgets.QWidget):
    def __init__(self, version):
        super().__init__()
        self.setStyleSheet("background-color: rgba(26, 26, 30, 180);")

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)

        title = QtWidgets.QLabel("🏠 Главная")
        title.setStyleSheet("""
            color: white;
            font-size: 26px;
            font-weight: bold;
            letter-spacing: 1px;
            background: none;
        """)
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
        description.setStyleSheet("""
            color: lightgray;
            font-size: 14px;
            background: none;
            line-height: 1.5em;
            font-family: 'Inter', sans-serif;
        """)
        layout.addWidget(description)
        layout.addStretch(1)

        bottom_container = QtWidgets.QHBoxLayout()

        left_container = QtWidgets.QVBoxLayout()
        left_container.setContentsMargins(0, 0, 0, 0)
        left_container.setSpacing(8)

        telegram_row = QtWidgets.QHBoxLayout()
        vpn_row = QtWidgets.QHBoxLayout()
        telegram_icon = QtWidgets.QLabel()
        pixmap = QtGui.QPixmap("assets/tg.png")
        pixmap = pixmap.scaled(18, 18, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        telegram_icon.setPixmap(pixmap)
        telegram_icon.setStyleSheet("background: transparent;")
        telegram_row.addWidget(telegram_icon)

        telegram_link = QtWidgets.QLabel(
            '<a href="https://t.me/id3001" '
            'style="color:#0088cc; text-decoration:none; font-size:14px;">'
            'Telegram — <b>@id3001</b></a>'
        )
        telegram_link.setTextFormat(QtCore.Qt.RichText)
        telegram_link.setOpenExternalLinks(True)
        telegram_link.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        telegram_link.setStyleSheet("""
            QLabel {
                background: transparent;
                color: #0088cc;
            }
            a {
                color: #0088cc;
                text-decoration: none;
            }
        """)
        telegram_row.addWidget(telegram_link)
        left_container.addLayout(telegram_row)

        vpn_link = QtWidgets.QLabel(
            '🛡️   <a href="https://t.me/vpnGLOBALKINTEK_bot" '
            'style="color:#0088cc; text-decoration:none; font-size:14px;">'
            '<b> Мой VPN</b></a>'
        )
        vpn_link.setTextFormat(QtCore.Qt.RichText)
        vpn_link.setOpenExternalLinks(True)
        vpn_link.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        vpn_link.setStyleSheet("""
            QLabel {
                background: transparent;
                color: #0088cc;
            }
            a {
                color: #0088cc;
                text-decoration: none;
            }
        """)
        vpn_row.addWidget(vpn_link)
        left_container.addLayout(vpn_row)

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
