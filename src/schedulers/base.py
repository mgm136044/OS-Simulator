from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TimeSlot:
    """Gantt 차트 한 칸: 어떤 프로세스가 어느 코어에서 언제부터 언제까지 실행되었는지"""
    pid: str          # 프로세스 ID ("idle" for idle)
    start: int
    end: int
    core_id: int = 0  # 코어 ID (단일코어는 0)


@dataclass
class ScheduleResult:
    """스케줄링 결과"""
    timeline: list[TimeSlot] = field(default_factory=list)
    total_time: int = 0
    total_power: float = 0.0
    queue_snapshots: dict = field(default_factory=dict)  # {time: [pid, ...]}


class BaseScheduler(ABC):
    """모든 스케줄러의 공통 인터페이스"""

    @property
    @abstractmethod
    def name(self) -> str:
        """스케줄러 이름 (예: 'FCFS', 'RR')"""
        ...

    @abstractmethod
    def schedule(self, processes: list, processors: list | None = None) -> ScheduleResult:
        """
        프로세스 리스트를 받아 스케줄링 실행.
        processors가 None이면 E core 1개로 동작 (하위호환).
        """
        ...
