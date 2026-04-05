import math
from models.process import Process
from models.processor import Processor, CoreType
from schedulers.base import BaseScheduler, ScheduleResult, TimeSlot


class HRRNScheduler(BaseScheduler):

    @property
    def name(self) -> str:
        return "HRRN"

    def schedule(self, processes: list[Process], processors=None) -> ScheduleResult:
        for p in processes:
            p.reset()

        if processors is None:
            processors = [Processor(core_id=0, core_type=CoreType.E_CORE)]
        for core in processors:
            core.reset()

        remaining = processes[:]
        timeline: list[TimeSlot] = []
        num_cores = len(processors)
        core_free_at = [0] * num_cores
        completed: set[str] = set()
        total_power = 0.0
        queue_snapshots: dict = {}

        while len(completed) < len(processes):
            earliest_free = min(core_free_at)
            available = [
                p for p in remaining
                if p.arrival_time <= earliest_free and p.pid not in completed
            ]

            if not available:
                future = [p for p in remaining if p.pid not in completed]
                if not future:
                    break
                next_arrival = min(p.arrival_time for p in future)
                for i in range(num_cores):
                    if core_free_at[i] < next_arrival:
                        core_free_at[i] = next_arrival
                continue

            def response_ratio(p: Process) -> float:
                wt = earliest_free - p.arrival_time
                return (wt + p.burst_time) / p.burst_time

            proc = max(available, key=lambda p: (response_ratio(p), -p.arrival_time))

            best_idx = min(range(num_cores),
                          key=lambda i: (max(core_free_at[i], proc.arrival_time), i))
            core = processors[best_idx]
            start = max(core_free_at[best_idx], proc.arrival_time)
            exec_ticks = math.ceil(proc.burst_time / core.work_per_tick)
            end = start + exec_ticks

            timeline.append(TimeSlot(proc.pid, start, end, core.core_id))

            waiting = [p.pid for p in available if p.pid != proc.pid]
            queue_snapshots[start] = waiting
            for rp in remaining:
                if rp.pid not in completed and start < rp.arrival_time <= end:
                    at = rp.arrival_time
                    waiting_at = [p.pid for p in remaining
                                  if p.pid not in completed and p.pid != proc.pid and p.arrival_time <= at]
                    queue_snapshots[at] = waiting_at

            has_idle_gap = core_free_at[best_idx] < start or core_free_at[best_idx] == 0
            if has_idle_gap:
                total_power += core.startup_power
            total_power += exec_ticks * core.power_per_tick

            core_free_at[best_idx] = end
            proc.completion_time = end
            proc.turnaround_time = end - proc.arrival_time
            proc.service_time = exec_ticks
            proc.waiting_time = proc.turnaround_time - proc.service_time
            proc.remaining_time = 0
            completed.add(proc.pid)

        total_time = max(core_free_at) if core_free_at else 0
        timeline.sort(key=lambda s: (s.core_id, s.start))

        return ScheduleResult(timeline=timeline, total_time=total_time,
                              total_power=round(total_power, 2), queue_snapshots=queue_snapshots)
