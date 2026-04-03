from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QRadioButton, QButtonGroup,
)


class CoreConfigRow(QWidget):
    """개별 코어 설정 행: OFF / P-Core / E-Core 라디오"""

    def __init__(self, core_id: int):
        super().__init__()
        self.core_id = core_id
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(f"Core {core_id}")
        label.setFixedWidth(60)
        layout.addWidget(label)

        self.btn_group = QButtonGroup(self)
        self.off_btn = QRadioButton("OFF")
        self.p_btn = QRadioButton("P-Core")
        self.e_btn = QRadioButton("E-Core")

        self.btn_group.addButton(self.off_btn, 0)
        self.btn_group.addButton(self.p_btn, 1)
        self.btn_group.addButton(self.e_btn, 2)

        if core_id == 0:
            self.e_btn.setChecked(True)
        else:
            self.off_btn.setChecked(True)

        layout.addWidget(self.off_btn)
        layout.addWidget(self.p_btn)
        layout.addWidget(self.e_btn)

    def get_type(self) -> str | None:
        checked = self.btn_group.checkedId()
        if checked == 1:
            return "P"
        elif checked == 2:
            return "E"
        return None


class ProcessorConfigPanel(QWidget):
    """프로세서 설정 패널: 최대 4코어, P/E/OFF 선택"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        header.addWidget(QLabel("프로세서 설정 (최대 4코어)"))
        layout.addLayout(header)

        self.core_rows: list[CoreConfigRow] = []
        for i in range(4):
            row = CoreConfigRow(i)
            self.core_rows.append(row)
            layout.addWidget(row)

        spec_label = QLabel(
            "P-Core: 2배 성능, 3W, 시동 0.5W  |  E-Core: 1배 성능, 1W, 시동 0.1W"
        )
        spec_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        layout.addWidget(spec_label)

    def get_active_cores(self) -> list[tuple[int, str]]:
        cores = []
        for row in self.core_rows:
            core_type = row.get_type()
            if core_type is not None:
                cores.append((row.core_id, core_type))
        return cores
