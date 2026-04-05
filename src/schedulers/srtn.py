from models.process import Process
from models.processor import Processor, CoreType
from schedulers.base import BaseScheduler, ScheduleResult, TimeSlot


class SRTNScheduler(BaseScheduler):

    @property
    def name(self) -> str:
        return "SRTN"

    def schedule(self, processes: list[Process], processors=None) -> ScheduleResult:
        for p in processes:
            p.reset()

        if processors is None:
            processors = [Processor(core_id=0, core_type=CoreType.E_CORE)]
        for core in processors:
            core.reset()

        sorted_procs = sorted(processes, key=lambda p: (p.arrival_time, p.pid))
        timeline: list[TimeSlot] = []
        ready_queue: list[Process] = []
        current_time = 0
        idx = 0
        n = len(sorted_procs)
        num_cores = len(processors)
        completed = 0
        total_power = 0.0

        core_state: list[dict | None] = [None] * num_cores
        queue_snapshots: dict = {}

        while idx < n and sorted_procs[idx].arrival_time <= current_time:
            ready_queue.append(sorted_procs[idx])
            idx += 1

        queue_snapshots[0] = [p.pid for p in ready_queue]

        while completed < n:
            # 도착 처리
            while idx < n and sorted_procs[idx].arrival_time <= current_time:
                ready_queue.append(sorted_procs[idx])
                idx += 1

            # 선점 체크: ready_queue에 현재 코어의 프로세스보다 짧은 것이 있으면 교체
            for ci in range(num_cores):
                state = core_state[ci]
                if state is not None and ready_queue:
                    proc = state["process"]
                    shortest = min(ready_queue, key=lambda p: (p.remaining_time, p.arrival_time))
                    if shortest.remaining_time < proc.remaining_time:
                        # 선점
                        timeline.append(TimeSlot(proc.pid, state["started_at"], current_time, processors[ci].core_id))
                        ready_queue.append(proc)
                        processors[ci].release()
                        core_state[ci] = None

            # 빈 코어에 할당 (remaining 가장 짧은 것)
            for ci in range(num_cores):
                if core_state[ci] is None and ready_queue:
                    ready_queue.sort(key=lambda p: (p.remaining_time, p.arrival_time))
                    proc = ready_queue.pop(0)
                    core_state[ci] = {"process": proc, "started_at": current_time}
                    processors[ci].assign(proc.pid)

            # 모든 코어 idle → 다음 도착까지 점프
            if all(s is None for s in core_state):
                if idx < n:
                    current_time = sorted_procs[idx].arrival_time
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
                total_power += core.tick()

            current_time += 1

            # 완료 처리
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

            queue_snapshots[current_time] = [p.pid for p in ready_queue]

        total_time = current_time
        timeline.sort(key=lambda s: (s.core_id, s.start))
        return ScheduleResult(timeline=timeline, total_time=total_time,
                              total_power=round(total_power, 2), queue_snapshots=queue_snapshots)
