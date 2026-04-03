from models.process import Process
from schedulers.base import BaseScheduler, ScheduleResult, TimeSlot


class SRTNScheduler(BaseScheduler):

    @property
    def name(self) -> str:
        return "SRTN"

    def schedule(self, processes: list[Process]) -> ScheduleResult:
        for p in processes:
            p.reset()

        timeline: list[TimeSlot] = []
        current_time = 0
        completed = 0
        n = len(processes)
        current_proc = None
        current_start = 0

        while completed < n:
            # 도착한 프로세스 중 remaining이 가장 작은 것
            available = [
                p for p in processes
                if p.arrival_time <= current_time and p.remaining_time > 0
            ]

            if not available:
                # idle: 다음 도착까지 점프
                future = [p for p in processes if p.remaining_time > 0]
                next_arrival = min(p.arrival_time for p in future)
                if current_proc is not None:
                    timeline.append(TimeSlot(current_proc.pid, current_start, current_time))
                    current_proc = None
                timeline.append(TimeSlot("idle", current_time, next_arrival))
                current_time = next_arrival
                continue

            best = min(available, key=lambda p: (p.remaining_time, p.arrival_time))

            if current_proc != best:
                # 프로세스 전환 (선점 또는 새 시작)
                if current_proc is not None and current_start < current_time:
                    timeline.append(TimeSlot(current_proc.pid, current_start, current_time))
                current_proc = best
                current_start = current_time

            # 다음 이벤트 시점 계산 (새 프로세스 도착 또는 현재 프로세스 완료)
            next_event = current_time + best.remaining_time
            for p in processes:
                if p.arrival_time > current_time and p.remaining_time > 0:
                    if p.arrival_time < next_event:
                        next_event = p.arrival_time

            elapsed = next_event - current_time
            best.remaining_time -= elapsed
            current_time = next_event

            if best.remaining_time == 0:
                best.completion_time = current_time
                best.turnaround_time = current_time - best.arrival_time
                best.waiting_time = best.turnaround_time - best.burst_time
                completed += 1
                timeline.append(TimeSlot(best.pid, current_start, current_time))
                current_proc = None

        return ScheduleResult(timeline=timeline, total_time=current_time)
