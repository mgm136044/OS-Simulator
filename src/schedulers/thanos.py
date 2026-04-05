import math
from collections import deque
from models.process import Process
from models.processor import Processor, CoreType
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

        if processors is None:
            processors = [Processor(core_id=0, core_type=CoreType.E_CORE)]
        for core in processors:
            core.reset()

        sorted_procs = sorted(processes, key=lambda p: (p.arrival_time, p.pid))
        timeline: list[TimeSlot] = []
        ready_queue: deque[Process] = deque()
        current_time = 0
        idx = 0
        n = len(sorted_procs)
        num_cores = len(processors)
        completed = 0
        total_power = 0.0
        boosted: set[str] = set()

        core_state: list[dict | None] = [None] * num_cores
        queue_snapshots: dict = {}

        while idx < n and sorted_procs[idx].arrival_time <= current_time:
            ready_queue.append(sorted_procs[idx])
            idx += 1

        while completed < n:
            # 빈 코어에 할당
            for ci in range(num_cores):
                if core_state[ci] is None and ready_queue:
                    proc = ready_queue.popleft()
                    core_state[ci] = {"process": proc, "started_at": current_time, "quantum_used": 0}
                    processors[ci].assign(proc.pid)

            # 모든 코어 idle → 다음 도착까지 점프
            if all(s is None for s in core_state) and not ready_queue:
                if idx < n:
                    current_time = sorted_procs[idx].arrival_time
                    while idx < n and sorted_procs[idx].arrival_time <= current_time:
                        ready_queue.append(sorted_procs[idx])
                        idx += 1
                    continue
                else:
                    break

            # 1 tick 실행
            for ci in range(num_cores):
                state = core_state[ci]
                if state is None:
                    processors[ci].tick()
                    continue
                proc = state["process"]
                core = processors[ci]
                work = min(core.work_per_tick, proc.remaining_time)
                proc.remaining_time -= work
                proc.service_time += 1
                state["quantum_used"] += 1
                total_power += core.tick()

            current_time += 1

            # 도착 프로세스 추가 (RR과 동일: arrivals before requeue)
            while idx < n and sorted_procs[idx].arrival_time <= current_time:
                ready_queue.append(sorted_procs[idx])
                idx += 1

            # 완료/선점 처리
            for ci in range(num_cores):
                state = core_state[ci]
                if state is None:
                    continue
                proc = state["process"]

                if proc.remaining_time <= 0:
                    proc.remaining_time = 0
                    proc.completion_time = current_time
                    proc.turnaround_time = current_time - proc.arrival_time
                    proc.waiting_time = proc.turnaround_time - proc.service_time
                    timeline.append(TimeSlot(proc.pid, state["started_at"], current_time, processors[ci].core_id))
                    processors[ci].release()
                    core_state[ci] = None
                    completed += 1
                elif state["quantum_used"] >= self.time_quantum:
                    timeline.append(TimeSlot(proc.pid, state["started_at"], current_time, processors[ci].core_id))
                    # 부스트 체크: 잔여시간이 원래 BT의 절반 이하이면 큐 앞으로
                    half_threshold = proc.burst_time / 2
                    if proc.remaining_time <= half_threshold and proc.pid not in boosted:
                        ready_queue.appendleft(proc)
                        boosted.add(proc.pid)
                    else:
                        ready_queue.append(proc)
                    processors[ci].release()
                    core_state[ci] = None

            queue_snapshots[current_time] = [p.pid for p in ready_queue]

        total_time = current_time
        timeline.sort(key=lambda s: (s.core_id, s.start))
        return ScheduleResult(timeline=timeline, total_time=total_time,
                              total_power=round(total_power, 2), queue_snapshots=queue_snapshots)
