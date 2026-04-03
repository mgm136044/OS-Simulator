from collections import deque
from models.process import Process
from schedulers.base import BaseScheduler, ScheduleResult, TimeSlot


class ThanosScheduler(BaseScheduler):

    def __init__(self, time_quantum: int = 2):
        self.time_quantum = time_quantum

    @property
    def name(self) -> str:
        return "Thanos"

    def schedule(self, processes: list[Process], processors=None) -> ScheduleResult:
        for p in processes:
            p.reset()

        sorted_procs = sorted(processes, key=lambda p: (p.arrival_time, p.pid))
        timeline: list[TimeSlot] = []
        ready_queue: deque[Process] = deque()
        current_time = 0
        idx = 0
        n = len(sorted_procs)
        boosted: set[str] = set()  # 부스트 1회 제한 추적

        # 시간 0에 도착하는 프로세스 추가
        while idx < n and sorted_procs[idx].arrival_time <= current_time:
            ready_queue.append(sorted_procs[idx])
            idx += 1

        while ready_queue or idx < n:
            if not ready_queue:
                next_arrival = sorted_procs[idx].arrival_time
                timeline.append(TimeSlot("idle", current_time, next_arrival))
                current_time = next_arrival
                while idx < n and sorted_procs[idx].arrival_time <= current_time:
                    ready_queue.append(sorted_procs[idx])
                    idx += 1
                continue

            proc = ready_queue.popleft()
            exec_time = min(self.time_quantum, proc.remaining_time)
            start = current_time
            end = start + exec_time
            timeline.append(TimeSlot(proc.pid, start, end))
            proc.remaining_time -= exec_time
            current_time = end

            # 현재 프로세스 재큐잉 (도착 처리보다 먼저 — trace/테스트 기대값과 일치)
            if proc.remaining_time > 0:
                half_threshold = proc.burst_time / 2
                if proc.remaining_time <= half_threshold and proc.pid not in boosted:
                    # 부스트: Ready Queue 최상단에 삽입
                    ready_queue.appendleft(proc)
                    boosted.add(proc.pid)
                else:
                    ready_queue.append(proc)
            else:
                proc.completion_time = end
                proc.turnaround_time = end - proc.arrival_time
                proc.waiting_time = proc.turnaround_time - proc.burst_time

            # 이 시간 동안 도착한 프로세스를 큐에 추가
            while idx < n and sorted_procs[idx].arrival_time <= current_time:
                ready_queue.append(sorted_procs[idx])
                idx += 1

        return ScheduleResult(timeline=timeline, total_time=current_time)
