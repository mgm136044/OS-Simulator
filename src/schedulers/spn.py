from models.process import Process
from schedulers.base import BaseScheduler, ScheduleResult, TimeSlot


class SPNScheduler(BaseScheduler):

    @property
    def name(self) -> str:
        return "SPN"

    def schedule(self, processes: list[Process], processors=None) -> ScheduleResult:
        for p in processes:
            p.reset()

        remaining = sorted(processes[:], key=lambda p: (p.arrival_time, p.pid))
        timeline: list[TimeSlot] = []
        current_time = 0
        completed: set[str] = set()

        while len(completed) < len(processes):
            # 현재 시간까지 도착한 프로세스 중 미완료 & BT가 가장 짧은 것
            available = [
                p for p in remaining
                if p.arrival_time <= current_time and p.pid not in completed
            ]

            if not available:
                # 다음 도착 프로세스까지 idle
                future = [p for p in remaining if p.pid not in completed]
                next_arrival = min(p.arrival_time for p in future)
                timeline.append(TimeSlot("idle", current_time, next_arrival))
                current_time = next_arrival
                continue

            # BT가 가장 짧은 프로세스 선택 (동일하면 AT가 빠른 것)
            proc = min(available, key=lambda p: (p.burst_time, p.arrival_time))

            start = current_time
            end = start + proc.burst_time
            timeline.append(TimeSlot(proc.pid, start, end))

            proc.completion_time = end
            proc.turnaround_time = end - proc.arrival_time
            proc.waiting_time = proc.turnaround_time - proc.burst_time
            proc.remaining_time = 0
            completed.add(proc.pid)
            current_time = end

        return ScheduleResult(timeline=timeline, total_time=current_time)
