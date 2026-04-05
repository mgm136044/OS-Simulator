from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QFont


class ReadyQueueView(QWidget):
    """Ready Queue 상태를 시각적으로 표시하는 위젯"""

    def __init__(self):
        super().__init__()
        self.queue_pids: list[str] = []
        self.color_map: dict[str, QColor] = {}
        self.setMinimumHeight(50)
        self.setMinimumWidth(200)

    def set_color_map(self, color_map: dict[str, QColor]):
        self.color_map = color_map

    def update_queue(self, pids: list[str]):
        self.queue_pids = pids
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        font = QFont("Segoe UI", 10, QFont.Bold)
        painter.setFont(font)

        x = 10
        block_h = 30
        y = (self.height() - block_h) // 2

        painter.setPen(QColor("#cdd6f4"))
        painter.drawText(QRectF(x, y, 100, block_h), Qt.AlignVCenter, "Ready Queue:")
        x += 105

        if not self.queue_pids:
            painter.setPen(QColor("#6c7086"))
            painter.drawText(QRectF(x, y, 100, block_h), Qt.AlignVCenter, "(비어있음)")
            painter.end()
            return

        block_w = 50
        for pid in self.queue_pids:
            color = self.color_map.get(pid, QColor("#89b4fa"))
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(x, y, block_w, block_h), 4, 4)

            painter.setPen(QColor("#1e1e2e"))
            painter.drawText(QRectF(x, y, block_w, block_h), Qt.AlignCenter, pid)
            x += block_w + 4

            if x + block_w > self.width():
                break

        painter.end()
