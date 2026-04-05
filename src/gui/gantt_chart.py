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
    """Gantt 차트를 그리는 캔버스 — 코어별 행 표시 지원"""

    def __init__(self):
        super().__init__()
        self.timeline: list[TimeSlot] = []
        self.total_time = 0
        self.process_ids: list[str] = []
        self.core_ids: list[int] = []
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
        # 코어 ID 추출
        self.core_ids = sorted(set(slot.core_id for slot in timeline if slot.pid != "idle"))
        if not self.core_ids:
            self.core_ids = [0]
        self.animated_time = 0
        # 캔버스 최소 높이: 코어 행 + 프로세스 행 + 시간축
        total_rows = len(self.core_ids) + len(self.process_ids) + (1 if self.has_idle else 0)
        self.setMinimumHeight(max(200, total_rows * 35 + 80))
        self.update()

    def set_animated_time(self, t: int):
        self.animated_time = t
        self.update()

    def paintEvent(self, event):
        if not self.timeline or self.total_time == 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        right_margin = 20
        left_margin = 90
        w = self.width() - left_margin - right_margin
        top_margin = 10
        num_core_rows = len(self.core_ids)
        num_proc_rows = len(self.process_ids) + (1 if self.has_idle else 0)
        total_visual_rows = num_core_rows + 1 + num_proc_rows  # +1 for separator
        row_height = max(24, min(40, (self.height() - top_margin - 40) // max(total_visual_rows, 1)))
        unit_width = w / self.total_time

        font = QFont("Segoe UI", 10)
        small_font = QFont("Segoe UI", 7)
        painter.setFont(font)

        # === 코어별 Gantt (상단) ===
        for ci, core_id in enumerate(self.core_ids):
            y_row = top_margin + ci * row_height
            label = f"Core {core_id}"
            painter.setPen(QColor("#89b4fa"))
            painter.drawText(QRectF(0, y_row, left_margin - 10, row_height),
                             Qt.AlignVCenter | Qt.AlignRight, label)

            # 이 코어의 슬롯만 그리기
            for slot in self.timeline:
                if slot.core_id != core_id or slot.start >= self.animated_time:
                    continue
                visible_end = min(slot.end, self.animated_time)
                x = left_margin + slot.start * unit_width
                bar_w = (visible_end - slot.start) * unit_width

                if slot.pid == "idle":
                    painter.setBrush(QColor("#45475a"))
                    painter.setPen(QPen(QColor("#6c7086"), 1, Qt.DashLine))
                    painter.drawRoundedRect(QRectF(x, y_row + 3, bar_w, row_height - 6), 3, 3)
                    painter.setFont(font)
                else:
                    color = self.color_map.get(slot.pid, QColor("#89b4fa"))
                    painter.setBrush(color)
                    painter.setPen(QPen(color.darker(120), 1))
                    painter.drawRoundedRect(QRectF(x, y_row + 3, bar_w, row_height - 6), 3, 3)
                    if bar_w > 15:
                        painter.setPen(QColor("#1e1e2e"))
                        painter.setFont(small_font)
                        painter.drawText(QRectF(x + 1, y_row + 3, bar_w - 2, row_height - 6),
                                         Qt.AlignCenter, slot.pid)
                        painter.setFont(font)

        # === 구분선 ===
        sep_y = top_margin + num_core_rows * row_height + row_height // 2
        painter.setPen(QPen(QColor("#45475a"), 1, Qt.DashLine))
        painter.drawLine(int(left_margin), int(sep_y), int(self.width() - right_margin), int(sep_y))

        # === 프로세스별 Gantt (하단) ===
        proc_offset = top_margin + (num_core_rows + 1) * row_height

        for i, pid in enumerate(self.process_ids):
            y_row = proc_offset + i * row_height
            painter.setPen(QColor("#cdd6f4"))
            painter.drawText(QRectF(0, y_row, left_margin - 10, row_height),
                             Qt.AlignVCenter | Qt.AlignRight, pid)

        idle_row = len(self.process_ids) if self.has_idle else -1
        if self.has_idle:
            y_row = proc_offset + idle_row * row_height
            painter.setPen(QColor("#6c7086"))
            painter.drawText(QRectF(0, y_row, left_margin - 10, row_height),
                             Qt.AlignVCenter | Qt.AlignRight, "idle")

        for slot in self.timeline:
            if slot.start >= self.animated_time:
                continue

            if slot.pid == "idle":
                if not self.has_idle:
                    continue
                row = idle_row
                y = proc_offset + row * row_height + 3
                visible_end = min(slot.end, self.animated_time)
                x = left_margin + slot.start * unit_width
                bar_w = (visible_end - slot.start) * unit_width
                painter.setBrush(QColor("#45475a"))
                painter.setPen(QPen(QColor("#6c7086"), 1, Qt.DashLine))
                painter.drawRoundedRect(QRectF(x, y, bar_w, row_height - 6), 3, 3)
                continue

            if slot.pid not in self.color_map:
                continue

            row = self.process_ids.index(slot.pid)
            y = proc_offset + row * row_height + 3
            visible_end = min(slot.end, self.animated_time)
            x = left_margin + slot.start * unit_width
            bar_w = (visible_end - slot.start) * unit_width

            color = self.color_map[slot.pid]
            painter.setBrush(color)
            painter.setPen(QPen(color.darker(120), 1))
            painter.drawRoundedRect(QRectF(x, y, bar_w, row_height - 6), 3, 3)

            if bar_w > 15:
                painter.setPen(QColor("#1e1e2e"))
                painter.setFont(small_font)
                painter.drawText(QRectF(x + 1, y, bar_w - 2, row_height - 6),
                                 Qt.AlignCenter, f"{slot.start}-{visible_end}")
                painter.setFont(font)

        # === 시간 축 ===
        axis_y = proc_offset + num_proc_rows * row_height + 8
        painter.setPen(QColor("#6c7086"))
        painter.setFont(small_font)
        min_label_gap = 40
        pixels_per_unit = unit_width
        step = max(1, int(min_label_gap / max(pixels_per_unit, 1)) + 1)
        step = max(1, min(step, self.total_time // 2)) if self.total_time > 0 else 1
        for t in range(0, self.total_time + 1, step):
            x = left_margin + t * unit_width
            if x + 15 <= self.width():
                painter.drawText(QRectF(x - 15, axis_y, 30, 20), Qt.AlignCenter, str(t))
        # 마지막 시각 항상 표시
        last_x = left_margin + self.total_time * unit_width
        if last_x - 15 >= 0:
            painter.drawText(QRectF(min(last_x - 15, self.width() - 30), axis_y, 30, 20),
                             Qt.AlignCenter, str(self.total_time))

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
