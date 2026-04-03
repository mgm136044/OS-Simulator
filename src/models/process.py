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

    def __post_init__(self):
        self.remaining_time = self.burst_time

    @property
    def ntt(self) -> float:
        """Normalized Turnaround Time = TT / BT"""
        if self.burst_time == 0:
            return 0.0
        return self.turnaround_time / self.burst_time

    def reset(self):
        self.remaining_time = self.burst_time
        self.waiting_time = 0
        self.turnaround_time = 0
        self.completion_time = 0
