import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from gui.main_window import MainWindow
from gui.theme import DARK_STYLESHEET

ICON_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.png")


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)
    icon = QIcon(ICON_PATH)
    app.setWindowIcon(icon)

    window = MainWindow()
    window.setWindowIcon(icon)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
