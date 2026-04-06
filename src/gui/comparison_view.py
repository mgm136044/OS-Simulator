from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QScrollArea,
)
from PyQt5.QtCore import Qt
from gui.gantt_chart import GanttCanvas


class ComparisonView(QWidget):
    """여러 알고리즘 결과를 나란히 비교하는 뷰 (자체 스크롤 포함)"""

    def __init__(self):
        super().__init__()
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        outer_layout.addWidget(self.scroll)

        self._content = QWidget()
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(8)
        self.scroll.setWidget(self._content)

        self._widgets: list[QWidget] = []

    def clear(self):
        for w in self._widgets:
            self._layout.removeWidget(w)
            w.deleteLater()
        self._widgets.clear()

    def set_results(self, reports: list[dict], configured_core_ids: list[int] | None = None):
        """여러 알고리즘 결과를 한 번에 표시"""
        self.clear()

        # 요약 비교 테이블
        summary_group = QGroupBox("알고리즘 비교 요약")
        summary_layout = QVBoxLayout(summary_group)
        summary_table = QTableWidget(len(reports), 4)
        summary_table.setHorizontalHeaderLabels(["Algorithm", "Avg WT", "Avg TT", "Avg NTT"])
        summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        summary_table.verticalHeader().setVisible(False)

        for row, report in enumerate(reports):
            m = report["metrics"]
            for col, val in enumerate([
                report["algorithm"],
                str(m["avg_wt"]),
                str(m["avg_tt"]),
                str(m["avg_ntt"]),
            ]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                summary_table.setItem(row, col, item)

        summary_table.setMinimumHeight(40 + len(reports) * 30)
        summary_table.setMaximumHeight(60 + len(reports) * 32)
        summary_layout.addWidget(summary_table)
        self._layout.addWidget(summary_group)
        self._widgets.append(summary_group)

        shared_total_time = max(r["total_time"] for r in reports)

        for report in reports:
            group = QGroupBox(f"{report['algorithm']}  (makespan: {report['total_time']})")
            group_layout = QVBoxLayout(group)
            canvas = GanttCanvas()
            process_ids = [p["pid"] for p in report["processes"]]
            canvas.set_data(report["timeline"], shared_total_time, process_ids, configured_core_ids)
            canvas.set_animated_time(shared_total_time)
            # set_data 이후 실제 행 수 기반 높이
            actual_min = canvas.minimumHeight()
            canvas.setFixedHeight(max(160, actual_min))
            group_layout.addWidget(canvas)
            self._layout.addWidget(group)
            self._widgets.append(group)

        # 하단 여백
        self._layout.addStretch()
