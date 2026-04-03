from models.process import Process
from models.processor import Processor
from schedulers.base import BaseScheduler
from engine.power import calc_power_summary


class Simulator:

    def run(
        self,
        scheduler: BaseScheduler,
        processes: list[Process],
        processors: list[Processor] | None = None,
    ) -> dict:
        """스케줄러 실행 후 리포트 딕셔너리 반환"""
        result = scheduler.schedule(processes, processors)

        process_details = []
        for p in processes:
            process_details.append({
                "pid": p.pid,
                "at": p.arrival_time,
                "bt": p.burst_time,
                "ct": p.completion_time,
                "wt": p.waiting_time,
                "tt": p.turnaround_time,
                "ntt": round(p.ntt, 2),
            })

        n = len(processes)
        avg_wt = sum(p.waiting_time for p in processes) / n if n else 0
        avg_tt = sum(p.turnaround_time for p in processes) / n if n else 0
        avg_ntt = sum(p.ntt for p in processes) / n if n else 0

        power_summary = None
        if processors is not None:
            power_summary = calc_power_summary(processors, result.timeline, result.total_time)

        return {
            "algorithm": scheduler.name,
            "total_time": result.total_time,
            "timeline": result.timeline,
            "processes": process_details,
            "metrics": {
                "avg_wt": round(avg_wt, 2),
                "avg_tt": round(avg_tt, 2),
                "avg_ntt": round(avg_ntt, 2),
            },
            "power": power_summary,
        }
