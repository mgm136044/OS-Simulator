from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QScrollArea
from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QPainter, QColor, QFont, QPen
from schedulers.base import TimeSlot

PROCESS_COLORS = [
    "#f38ba8", "#fab387", "#f9e2af", "#a6e3a1",
    "#89dceb", "#89b4fa", "#cba6f7", "#f5c2e7",
    "#94e2d5", "#eba0ac", "#74c7ec", "#b4befe",
]


class GanttCanvas(QWidget):
    """Gantt 차트를 그리는 캔버스"""

    def __init__(self):
        super().__init__()
        self.timeline: list[TimeSlot] = []
        self.total_time = 0
        self.process_ids: list[str] = []
        self.color_map: dict[str, QColor] = {}
        self.animated_time = 0
        self.setMinimumHeight(200)

    def set_data(self, timeline: list[TimeSlot], total_time: int, process_ids: list[str]):
        self.timeline = timeline
        self.total_time = total_time
        self.process_ids = [pid for pid in process_ids if pid != "idle"]
        self.color_map = {}
        for i, pid in enumerate(self.process_ids):
            self.color_map[pid] = QColor(PROCESS_COLORS[i % len(PROCESS_COLORS)])
        self.has_idle = any(slot.pid == "idle" for slot in timeline)
        self.animated_time = 0

        num_rows = len(self.process_ids) + (1 if self.has_idle else 0)
        needed_h = 10 + num_rows * 35 + 30 + 10  # top_margin + rows + axis + buffer
        self.setMinimumHeight(max(200, needed_h))

        self.update()

    def set_animated_time(self, t: int):
        self.animated_time = t
        self.update()

    def paintEvent(self, event):
        if not self.timeline or self.total_time == 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width() - 80
        left_margin = 70
        top_margin = 10
        row_height = max(30, min(50, (self.height() - top_margin - 30) // max(len(self.process_ids), 1)))
        unit_width = w / self.total_time

        font = QFont("Segoe UI", 10)
        painter.setFont(font)

        # 프로세스 행 라벨
        for i, pid in enumerate(self.process_ids):
            y = top_margin + i * row_height
            painter.setPen(QColor("#cdd6f4"))
            painter.drawText(QRectF(0, y, left_margin - 10, row_height),
                             Qt.AlignVCenter | Qt.AlignRight, pid)

        # idle 행
        idle_row = len(self.process_ids) if self.has_idle else -1
        if self.has_idle:
            y = top_margin + idle_row * row_height
            painter.setPen(QColor("#6c7086"))
            painter.drawText(QRectF(0, y, left_margin - 10, row_height),
                             Qt.AlignVCenter | Qt.AlignRight, "idle")

        # 타임라인 바
        for slot in self.timeline:
            if slot.start >= self.animated_time:
                continue

            if slot.pid == "idle":
                if not self.has_idle:
                    continue
                row = idle_row
                y = top_margin + row * row_height + 4
                visible_end = min(slot.end, self.animated_time)
                x = left_margin + slot.start * unit_width
                bar_w = (visible_end - slot.start) * unit_width
                painter.setBrush(QColor("#45475a"))
                painter.setPen(QPen(QColor("#6c7086"), 1, Qt.DashLine))
                painter.drawRoundedRect(QRectF(x, y, bar_w, row_height - 8), 4, 4)
                continue

            if slot.pid not in self.color_map:
                continue

            row = self.process_ids.index(slot.pid)
            y = top_margin + row * row_height + 4
            visible_end = min(slot.end, self.animated_time)
            x = left_margin + slot.start * unit_width
            bar_w = (visible_end - slot.start) * unit_width

            color = self.color_map[slot.pid]
            painter.setBrush(color)
            painter.setPen(QPen(color.darker(120), 1))
            painter.drawRoundedRect(QRectF(x, y, bar_w, row_height - 8), 4, 4)

            if bar_w > 20:
                painter.setPen(QColor("#1e1e2e"))
                small_font = QFont("Segoe UI", 8)
                painter.setFont(small_font)
                painter.drawText(QRectF(x, y, bar_w, row_height - 8),
                                 Qt.AlignCenter, f"{slot.start}-{visible_end}")
                painter.setFont(font)

        # 시간 축
        total_rows = len(self.process_ids) + (1 if self.has_idle else 0)
        axis_y = top_margin + total_rows * row_height + 4
        painter.setPen(QColor("#6c7086"))
        small_font = QFont("Segoe UI", 8)
        painter.setFont(small_font)
        step = max(1, self.total_time // 20)
        for t in range(0, self.total_time + 1, step):
            x = left_margin + t * unit_width
            painter.drawText(QRectF(x - 10, axis_y, 20, 16), Qt.AlignCenter, str(t))

        painter.end()


class GanttChart(QWidget):
    """Gantt 차트 위젯 (캔버스 + 애니메이션 컨트롤)"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.canvas = GanttCanvas()
        scroll.setWidget(self.canvas)
        layout.addWidget(scroll, stretch=1)

        ctrl_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶ 재생")
        self.play_btn.clicked.connect(self._toggle_play)
        ctrl_layout.addWidget(self.play_btn)

        self.reset_btn = QPushButton("↺ 리셋")
        self.reset_btn.clicked.connect(self._reset)
        ctrl_layout.addWidget(self.reset_btn)

        self.skip_btn = QPushButton("⏩ 전체 보기")
        self.skip_btn.clicked.connect(self._skip_to_end)
        ctrl_layout.addWidget(self.skip_btn)

        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        self.timer = QTimer()
        self.timer.setInterval(400)
        self.timer.timeout.connect(self._tick)
        self._playing = False

    def set_data(self, timeline: list[TimeSlot], total_time: int, process_ids: list[str]):
        self.timer.stop()
        self._playing = False
        self.play_btn.setText("▶ 재생")
        self.canvas.set_data(timeline, total_time, process_ids)
        self._skip_to_end()

    def _toggle_play(self):
        if self._playing:
            self.timer.stop()
            self._playing = False
            self.play_btn.setText("▶ 재생")
        else:
            if self.canvas.animated_time >= self.canvas.total_time:
                self.canvas.animated_time = 0
            self._playing = True
            self.play_btn.setText("⏸ 일시정지")
            self.timer.start()

    def _tick(self):
        self.canvas.animated_time += 1
        if self.canvas.animated_time > self.canvas.total_time:
            self.canvas.animated_time = self.canvas.total_time
            self.timer.stop()
            self._playing = False
            self.play_btn.setText("▶ 재생")
        self.canvas.update()

    def _reset(self):
        self.timer.stop()
        self._playing = False
        self.play_btn.setText("▶ 재생")
        self.canvas.set_animated_time(0)

    def _skip_to_end(self):
        self.timer.stop()
        self._playing = False
        self.play_btn.setText("▶ 재생")
        self.canvas.set_animated_time(self.canvas.total_time)
