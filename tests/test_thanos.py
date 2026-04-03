import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.process import Process
from schedulers.thanos import ThanosScheduler


def make_processes():
    return [
        Process("P1", arrival_time=0, burst_time=3),
        Process("P2", arrival_time=1, burst_time=5),
        Process("P3", arrival_time=3, burst_time=2),
        Process("P4", arrival_time=5, burst_time=4),
    ]


def test_thanos_metrics():
    """Tick-based single E-core with arrivals-before-requeue + boost"""
    procs = make_processes()
    scheduler = ThanosScheduler(time_quantum=2)
    scheduler.schedule(procs)

    # Tick-based trace (E core, work_per_tick=1):
    # t=0-2: P1 runs, rem=1. quantum done. Arrivals: P2(AT=1). Boost: 1<=1.5 → appendleft
    #   Queue after: [P1(boosted), P2(5)]
    # t=2-3: P1 runs, rem=0. Done. CT=3, TT=3, WT=0. Arrivals: P3(AT=3).
    #   Queue: [P2(5), P3(2)]
    # t=3-5: P2 runs 2 ticks, rem=3. quantum done. Arrivals: J4(AT=5). No boost.
    #   Queue: [P3(2), P4(4), P2(3)]
    # t=5-7: P3 runs 2 ticks, rem=0. Done. CT=7, TT=4, WT=2.
    #   Queue: [P4(4), P2(3)]
    # t=7-9: P4 runs 2 ticks, rem=2. quantum done. No arrivals. Boost: 2<=2 → appendleft
    #   Queue: [P4(boosted,2), P2(3)]
    # t=9-11: P4 runs 2 ticks, rem=0. Done. CT=11, TT=6, WT=2.
    #   Queue: [P2(3)]
    # t=11-13: P2 runs 2 ticks, rem=1. quantum done. Boost: 1<=2.5 → appendleft
    #   Queue: [P2(boosted,1)]
    # t=13-14: P2 runs 1 tick, rem=0. Done. CT=14, TT=13, WT=8.

    assert procs[0].waiting_time == 0    # P1
    assert procs[1].waiting_time == 8    # P2
    assert procs[2].waiting_time == 2    # P3
    assert procs[3].waiting_time == 2    # P4

    assert procs[0].turnaround_time == 3   # P1
    assert procs[1].turnaround_time == 13  # P2
    assert procs[2].turnaround_time == 4   # P3
    assert procs[3].turnaround_time == 6   # P4


def test_thanos_boost():
    """부스트가 작동하는지 확인: P1이 RR보다 일찍 완료"""
    procs = [
        Process("P1", arrival_time=0, burst_time=3),
        Process("P2", arrival_time=0, burst_time=6),
    ]
    scheduler = ThanosScheduler(time_quantum=2)
    result = scheduler.schedule(procs)

    # t=0-2: P1 runs, rem=1. Arrivals: none (both AT=0, already in queue).
    #   Boost: 1<=1.5 → appendleft. Queue: [P1(1), P2(6)]
    # t=2-3: P1 runs, rem=0. Done. CT=3.
    # t=3-5: P2 runs, rem=4. No boost. Queue: [P2(4)]
    # t=5-7: P2 runs, rem=2. Boost: 2<=3 → appendleft. Queue: [P2(2)]
    # t=7-9: P2 runs, rem=0. Done. CT=9.
    assert procs[0].completion_time == 3
    assert procs[1].completion_time == 9


def test_thanos_total_time():
    procs = make_processes()
    scheduler = ThanosScheduler(time_quantum=2)
    result = scheduler.schedule(procs)
    assert result.total_time == 14


def test_thanos_name():
    assert ThanosScheduler(time_quantum=2).name == "Thanos"
