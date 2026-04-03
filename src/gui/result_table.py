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

        # 프로세서 개요
        overview_layout = QHBoxLayout()
        self.total_tasks_label = QLabel("처리 작업: -")
        self.total_time_label = QLabel("전체 수행시간: -")
        for label in (self.total_tasks_label, self.total_time_label):
            label.setStyleSheet("font-size: 12px; padding: 2px 8px;")
            overview_layout.addWidget(label)
        overview_layout.addStretch()
        layout.addLayout(overview_layout)

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
        self.power_label = QLabel("총 소비전력: -")
        self.power_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 4px 12px; color: #f9e2af;")
        for label in (self.avg_wt_label, self.avg_tt_label, self.avg_ntt_label):
            label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 4px 12px;")
            avg_layout.addWidget(label)
        avg_layout.addWidget(self.power_label)
        avg_layout.addStretch()
        layout.addLayout(avg_layout)

        # 코어별 상세
        self.core_detail_label = QLabel("")
        self.core_detail_label.setStyleSheet("font-size: 11px; padding: 4px 12px; color: #6c7086;")
        layout.addWidget(self.core_detail_label)

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

        self.total_tasks_label.setText(f"처리 작업: {len(procs)}개")
        self.total_time_label.setText(f"전체 수행시간: {report['total_time']}초")

        power = report.get("power")
        if power:
            self.power_label.setText(f"총 소비전력: {power['total_power']}W")
            core_texts = []
            for c in power["cores"]:
                core_texts.append(
                    f"Core {c['core_id']}({c['core_type']}): {c['power']}W, 가동률 {c['utilization']}%"
                )
            self.core_detail_label.setText("  |  ".join(core_texts))
        else:
            self.power_label.setText("총 소비전력: -")
            self.core_detail_label.setText("")
