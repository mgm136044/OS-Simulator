from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QHBoxLayout,
)
from PyQt5.QtCore import Qt


class ResultTable(QWidget):
    """스케줄링 결과를 표 형태로 보여주는 위젯"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 프로세스별 결과 테이블
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["PID", "AT", "BT", "CT", "WT", "TT", "NTT"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        # 평균 지표
        avg_layout = QHBoxLayout()
        self.avg_wt_label = QLabel("Avg WT: -")
        self.avg_tt_label = QLabel("Avg TT: -")
        self.avg_ntt_label = QLabel("Avg NTT: -")
        for label in (self.avg_wt_label, self.avg_tt_label, self.avg_ntt_label):
            label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 4px 12px;")
            avg_layout.addWidget(label)
        avg_layout.addStretch()
        layout.addLayout(avg_layout)

    def update_results(self, report: dict):
        """Simulator.run() 결과를 테이블에 반영"""
        procs = report["processes"]
        self.table.setRowCount(len(procs))

        for row, p in enumerate(procs):
            for col, key in enumerate(["pid", "at", "bt", "ct", "wt", "tt", "ntt"]):
                val = p[key]
                text = f"{val:.2f}" if isinstance(val, float) else str(val)
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, col, item)

        metrics = report["metrics"]
        self.avg_wt_label.setText(f"Avg WT: {metrics['avg_wt']}")
        self.avg_tt_label.setText(f"Avg TT: {metrics['avg_tt']}")
        self.avg_ntt_label.setText(f"Avg NTT: {metrics['avg_ntt']}")
