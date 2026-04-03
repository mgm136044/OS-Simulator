from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QGroupBox, QScrollArea,
)
from PyQt5.QtCore import Qt
from gui.process_input import ProcessInputPanel
from gui.result_table import ResultTable
from gui.gantt_chart import GanttChart
from gui.comparison_view import ComparisonView
from models.process import Process
from engine.simulator import Simulator
from schedulers.fcfs import FCFSScheduler
from schedulers.rr import RRScheduler
from schedulers.spn import SPNScheduler
from schedulers.srtn import SRTNScheduler
from schedulers.hrrn import HRRNScheduler
from schedulers.thanos import ThanosScheduler


SCHEDULER_MAP = {
    "FCFS": lambda q: FCFSScheduler(),
    "RR": lambda q: RRScheduler(time_quantum=q),
    "SPN": lambda q: SPNScheduler(),
    "SRTN": lambda q: SRTNScheduler(),
    "HRRN": lambda q: HRRNScheduler(),
    "Thanos": lambda q: ThanosScheduler(time_quantum=q),
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("프로세스 스케줄링 시뮬레이터")
        self.setMinimumSize(1200, 700)
        self.simulator = Simulator()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # 좌측: 프로세스 입력 패널
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_panel = QGroupBox("프로세스 관리")
        left_layout = QVBoxLayout(left_panel)
        self.input_panel = ProcessInputPanel()
        self.input_panel.run_requested.connect(self._on_run)
        self.input_panel.compare_requested.connect(self._on_compare)
        left_layout.addWidget(self.input_panel)
        left_scroll.setWidget(left_panel)
        splitter.addWidget(left_scroll)

        # 우측: Gantt + 결과 + 비교
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Gantt 차트
        gantt_group = QGroupBox("Gantt 차트")
        gantt_layout = QVBoxLayout(gantt_group)
        self.gantt_chart = GanttChart()
        gantt_layout.addWidget(self.gantt_chart)
        right_layout.addWidget(gantt_group, stretch=2)

        # 결과 테이블
        result_group = QGroupBox("스케줄링 결과")
        result_layout = QVBoxLayout(result_group)
        self.result_table = ResultTable()
        result_layout.addWidget(self.result_table)
        right_layout.addWidget(result_group, stretch=1)

        # 비교 뷰
        self.comparison_view = ComparisonView()
        self.comparison_view.setVisible(False)
        right_layout.addWidget(self.comparison_view, stretch=2)

        right_scroll.setWidget(right_widget)
        splitter.addWidget(right_scroll)
        splitter.setSizes([300, 900])

    def _on_run(self, algo_name: str, quantum: int, proc_tuples: list):
        processes = [Process(pid, at, bt) for pid, at, bt in proc_tuples]
        scheduler = SCHEDULER_MAP[algo_name](quantum)
        report = self.simulator.run(scheduler, processes)

        process_ids = [p["pid"] for p in report["processes"]]
        self.gantt_chart.set_data(report["timeline"], report["total_time"], process_ids)
        self.result_table.update_results(report)
        self.comparison_view.setVisible(False)

    def _on_compare(self, quantum: int, proc_tuples: list):
        reports = []
        for algo_name in ProcessInputPanel.ALGORITHMS:
            processes = [Process(pid, at, bt) for pid, at, bt in proc_tuples]
            scheduler = SCHEDULER_MAP[algo_name](quantum)
            report = self.simulator.run(scheduler, processes)
            reports.append(report)

        self.comparison_view.set_results(reports)
        self.comparison_view.setVisible(True)
