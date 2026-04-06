import random
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QComboBox, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox,
)
from PyQt5.QtCore import pyqtSignal, Qt
from gui.processor_config import ProcessorConfigPanel


class ProcessInputPanel(QWidget):
    """프로세스 추가/삭제 + 알고리즘 선택 + 프로세서 설정 + 실행 버튼"""

    run_requested = pyqtSignal(str, int, list, list)  # (algorithm, quantum, [(pid,at,bt)], [(core_id,type)])
    compare_requested = pyqtSignal(int, list, list)   # (quantum, [(pid,at,bt)], [(core_id,type)])

    ALGORITHMS = ["FCFS", "RR", "SPN", "SRTN", "HRRN", "Thanos"]

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 프로세서 설정
        self.processor_config = ProcessorConfigPanel()
        layout.addWidget(self.processor_config)

        # 알고리즘 선택
        algo_layout = QHBoxLayout()
        algo_layout.addWidget(QLabel("알고리즘:"))
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(self.ALGORITHMS)
        algo_layout.addWidget(self.algo_combo)
        layout.addLayout(algo_layout)

        # Time Quantum
        quantum_layout = QHBoxLayout()
        quantum_layout.addWidget(QLabel("Time Quantum:"))
        self.quantum_spin = QSpinBox()
        self.quantum_spin.setRange(1, 100)
        self.quantum_spin.setValue(2)
        quantum_layout.addWidget(self.quantum_spin)
        layout.addLayout(quantum_layout)

        self.algo_combo.currentTextChanged.connect(self._on_algo_changed)
        self._on_algo_changed(self.algo_combo.currentText())

        # 프로세스 입력 필드
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("AT:"))
        self.at_spin = QSpinBox()
        self.at_spin.setRange(0, 999)
        input_layout.addWidget(self.at_spin)

        input_layout.addWidget(QLabel("BT:"))
        self.bt_spin = QSpinBox()
        self.bt_spin.setRange(1, 999)
        self.bt_spin.setValue(1)
        input_layout.addWidget(self.bt_spin)

        self.add_btn = QPushButton("추가")
        self.add_btn.clicked.connect(self._add_process)
        input_layout.addWidget(self.add_btn)

        self.random_btn = QPushButton("무작위")
        self.random_btn.clicked.connect(self._add_random_process)
        input_layout.addWidget(self.random_btn)
        layout.addLayout(input_layout)

        # 프로세스 테이블
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["PID", "AT", "BT"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # 삭제 버튼
        del_layout = QHBoxLayout()
        self.del_btn = QPushButton("선택 삭제")
        self.del_btn.clicked.connect(self._delete_selected)
        del_layout.addWidget(self.del_btn)

        self.clear_btn = QPushButton("전체 제거")
        self.clear_btn.clicked.connect(self._clear_all)
        del_layout.addWidget(self.clear_btn)
        layout.addLayout(del_layout)

        # 실행 버튼
        self.run_btn = QPushButton("▶  실행")
        self.run_btn.setStyleSheet(
            "QPushButton { font-size: 15px; padding: 12px; }"
        )
        self.run_btn.clicked.connect(self._on_run)
        layout.addWidget(self.run_btn)

        # 비교 실행 버튼
        self.compare_btn = QPushButton("⚖  전체 비교")
        self.compare_btn.setStyleSheet(
            "QPushButton { font-size: 15px; padding: 12px; background-color: #cba6f7; }"
        )
        self.compare_btn.clicked.connect(self._on_compare)
        layout.addWidget(self.compare_btn)

        self._process_count = 0

    def _on_algo_changed(self, algo: str):
        self.quantum_spin.setEnabled(True)

    def _add_process(self):
        if self.table.rowCount() >= 15:
            QMessageBox.warning(self, "경고", "프로세스는 최대 15개까지 추가할 수 있습니다.")
            return
        self._process_count += 1
        pid = f"P{self._process_count}"
        at = self.at_spin.value()
        bt = self.bt_spin.value()

        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, val in enumerate([pid, str(at), str(bt)]):
            item = QTableWidgetItem(val)
            item.setTextAlignment(Qt.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, col, item)

    def _add_random_process(self):
        if self.table.rowCount() >= 15:
            QMessageBox.warning(self, "경고", "프로세스는 최대 15개까지 추가할 수 있습니다.")
            return
        self.at_spin.setValue(random.randint(0, 20))
        self.bt_spin.setValue(random.randint(1, 15))
        self._add_process()

    def _delete_selected(self):
        rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()), reverse=True)
        for row in rows:
            self.table.removeRow(row)

    def _clear_all(self):
        self.table.setRowCount(0)
        self._process_count = 0

    def _get_proc_tuples(self):
        procs = []
        for row in range(self.table.rowCount()):
            pid = self.table.item(row, 0).text()
            at = int(self.table.item(row, 1).text())
            bt = int(self.table.item(row, 2).text())
            procs.append((pid, at, bt))
        return procs

    def _validate(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "경고", "프로세스를 1개 이상 추가하세요.")
            return False
        cores = self.processor_config.get_active_cores()
        if not cores:
            QMessageBox.warning(self, "경고", "활성화된 코어가 없습니다.")
            return False
        return True

    def _on_run(self):
        if not self._validate():
            return
        algo = self.algo_combo.currentText()
        quantum = self.quantum_spin.value()
        cores = self.processor_config.get_active_cores()
        self.run_requested.emit(algo, quantum, self._get_proc_tuples(), cores)

    def _on_compare(self):
        if not self._validate():
            return
        quantum = self.quantum_spin.value()
        cores = self.processor_config.get_active_cores()
        self.compare_requested.emit(quantum, self._get_proc_tuples(), cores)
