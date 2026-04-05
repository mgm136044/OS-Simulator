from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QGroupBox, QScrollArea,
)
from PyQt5.QtCore import Qt
from gui.process_input import ProcessInputPanel
from gui.result_table import ResultTable
from gui.gantt_chart import GanttChart
from gui.comparison_view import ComparisonView
from gui.ready_queue_view import ReadyQueueView
from models.process import Process
from models.processor import Processor, CoreType
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


def _make_processors(core_tuples):
    return [
        Processor(cid, CoreType.P_CORE if ctype == "P" else CoreType.E_CORE)
        for cid, ctype in core_tuples
    ]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("프로세스 스케줄링 시뮬레이터")
        self.setMinimumSize(1200, 700)
        self.resize(1600, 860)
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

        # 우측
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

        # Ready Queue
        self.ready_queue_view = ReadyQueueView()
        right_layout.addWidget(self.ready_queue_view)

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
        splitter.setSizes([350, 850])

        # ReadyQueue 초기화 + 시간 변경 시그널 연결 (1회만, __init__에서)
        self._queue_snapshots = {}
        self.gantt_chart.time_changed.connect(self._update_ready_queue)

    def _on_run(self, algo_name: str, quantum: int, proc_tuples: list, core_tuples: list):
        processes = [Process(pid, at, bt) for pid, at, bt in proc_tuples]
        processors = _make_processors(core_tuples)
        scheduler = SCHEDULER_MAP[algo_name](quantum)
        report = self.simulator.run(scheduler, processes, processors)

        process_ids = [p["pid"] for p in report["processes"]]
        configured_core_ids = [cid for cid, _ in core_tuples]
        self.gantt_chart.set_data(report["timeline"], report["total_time"], process_ids, configured_core_ids)
        self.result_table.update_results(report)

        # ReadyQueueView 연결: queue_snapshots + 색상맵
        self._queue_snapshots = report.get("queue_snapshots", {})
        self.ready_queue_view.set_color_map(self.gantt_chart.canvas.color_map)
        self._update_ready_queue()
        self.comparison_view.setVisible(False)

    def _on_compare(self, quantum: int, proc_tuples: list, core_tuples: list):
        reports = []
        for algo_name in ProcessInputPanel.ALGORITHMS:
            processes = [Process(pid, at, bt) for pid, at, bt in proc_tuples]
            processors = _make_processors(core_tuples)
            scheduler = SCHEDULER_MAP[algo_name](quantum)
            report = self.simulator.run(scheduler, processes, processors)
            reports.append(report)

        configured_core_ids = [cid for cid, _ in core_tuples]
        self.comparison_view.set_results(reports, configured_core_ids)
        self.comparison_view.setVisible(True)

    def _update_ready_queue(self, t: int | None = None):
        """GanttChart의 현재 애니메이션 시각에 맞춰 ReadyQueueView 갱신"""
        if t is None:
            t = self.gantt_chart.canvas.animated_time
        snapshots = getattr(self, '_queue_snapshots', {})
        # 현재 시각 이하의 가장 가까운 snapshot
        pids = []
        for st in sorted(snapshots.keys()):
            if st <= t:
                pids = snapshots[st]
            else:
                break
        self.ready_queue_view.update_queue(pids)
