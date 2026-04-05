from dataclasses import dataclass, field


@dataclass
class Process:
    pid: str
    arrival_time: int
    burst_time: int
    remaining_time: int = field(init=False)
    waiting_time: int = 0
    turnaround_time: int = 0
    completion_time: int = 0
    service_time: int = 0  # 실제 CPU 점유 시간 (ticks). P-core에서 BT와 다를 수 있음

    def __post_init__(self):
        self.remaining_time = self.burst_time

    @property
    def ntt(self) -> float:
        """Normalized Turnaround Time = TT / service_time (우선), service_time 없으면 TT / burst_time"""
        st = self.service_time if self.service_time > 0 else self.burst_time
        if st == 0:
            return 0.0
        return self.turnaround_time / st

    def reset(self):
        self.remaining_time = self.burst_time
        self.waiting_time = 0
        self.turnaround_time = 0
        self.completion_time = 0
        self.service_time = 0
