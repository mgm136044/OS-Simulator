from models.process import Process
from schedulers.base import BaseScheduler, ScheduleResult, TimeSlot


class FCFSScheduler(BaseScheduler):

    @property
    def name(self) -> str:
        return "FCFS"

    def schedule(self, processes: list[Process], processors=None) -> ScheduleResult:
        for p in processes:
            p.reset()

        sorted_procs = sorted(processes, key=lambda p: (p.arrival_time, p.pid))
        timeline: list[TimeSlot] = []
        current_time = 0

        for proc in sorted_procs:
            if current_time < proc.arrival_time:
                timeline.append(TimeSlot("idle", current_time, proc.arrival_time))
                current_time = proc.arrival_time

            start = current_time
            end = start + proc.burst_time
            timeline.append(TimeSlot(proc.pid, start, end))

            proc.completion_time = end
            proc.turnaround_time = end - proc.arrival_time
            proc.waiting_time = proc.turnaround_time - proc.burst_time
            proc.remaining_time = 0
            current_time = end

        return ScheduleResult(timeline=timeline, total_time=current_time)
