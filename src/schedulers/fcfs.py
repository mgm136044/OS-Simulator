import math
from collections import deque
from models.process import Process
from models.processor import Processor, CoreType
from schedulers.base import BaseScheduler, ScheduleResult, TimeSlot


class FCFSScheduler(BaseScheduler):

    @property
    def name(self) -> str:
        return "FCFS"

    def schedule(self, processes: list[Process], processors=None) -> ScheduleResult:
        for p in processes:
            p.reset()

        if processors is None:
            processors = [Processor(core_id=0, core_type=CoreType.E_CORE)]
        for core in processors:
            core.reset()

        sorted_procs = deque(sorted(processes, key=lambda p: (p.arrival_time, p.pid)))
        timeline: list[TimeSlot] = []
        num_cores = len(processors)

        # 각 코어가 비는 시각
        core_free_at = [0] * num_cores
        total_power = 0.0

        for proc in sorted_procs:
            # 가장 먼저 비는 코어 (동률이면 core_id 낮은 것)
            best_idx = min(range(num_cores),
                          key=lambda i: (max(core_free_at[i], proc.arrival_time), i))
            core = processors[best_idx]
            start = max(core_free_at[best_idx], proc.arrival_time)
            exec_ticks = math.ceil(proc.burst_time / core.work_per_tick)
            end = start + exec_ticks

            timeline.append(TimeSlot(proc.pid, start, end, core.core_id))

            # 전력: idle gap이 있으면 시동전력 발생
            has_idle_gap = core_free_at[best_idx] < start or core_free_at[best_idx] == 0
            if has_idle_gap:
                total_power += core.startup_power
            total_power += exec_ticks * core.power_per_tick

            core_free_at[best_idx] = end
            proc.completion_time = end
            proc.turnaround_time = end - proc.arrival_time
            proc.waiting_time = start - proc.arrival_time
            proc.remaining_time = 0

        total_time = max(core_free_at) if core_free_at else 0
        timeline.sort(key=lambda s: (s.core_id, s.start))

        # queue_snapshots: 슬롯 시작 + 프로세스 도착 시점마다 대기 중인 프로세스 기록
        proc_start = {slot.pid: slot.start for slot in timeline}
        event_times = sorted({slot.start for slot in timeline} | {p.arrival_time for p in processes})
        queue_snapshots = {}
        for t in event_times:
            queue_snapshots[t] = [
                p.pid for p in sorted(processes, key=lambda p: (p.arrival_time, p.pid))
                if p.arrival_time <= t and proc_start.get(p.pid, t + 1) > t
            ]

        return ScheduleResult(timeline=timeline, total_time=total_time, total_power=round(total_power, 2),
                              queue_snapshots=queue_snapshots)
