from models.process import Process
from schedulers.base import BaseScheduler, ScheduleResult, TimeSlot


class HRRNScheduler(BaseScheduler):

    @property
    def name(self) -> str:
        return "HRRN"

    def schedule(self, processes: list[Process]) -> ScheduleResult:
        for p in processes:
            p.reset()

        remaining = processes[:]
        timeline: list[TimeSlot] = []
        current_time = 0
        completed: set[str] = set()

        while len(completed) < len(processes):
            available = [
                p for p in remaining
                if p.arrival_time <= current_time and p.pid not in completed
            ]

            if not available:
                future = [p for p in remaining if p.pid not in completed]
                next_arrival = min(p.arrival_time for p in future)
                timeline.append(TimeSlot("idle", current_time, next_arrival))
                current_time = next_arrival
                continue

            def response_ratio(p: Process) -> float:
                wt = current_time - p.arrival_time
                return (wt + p.burst_time) / p.burst_time

            # RR이 가장 높은 프로세스 선택 (동일하면 AT가 빠른 것)
            proc = max(available, key=lambda p: (response_ratio(p), -p.arrival_time))

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
