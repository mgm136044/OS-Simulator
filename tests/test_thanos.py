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
    procs = make_processes()
    scheduler = ThanosScheduler(time_quantum=2)
    scheduler.schedule(procs)

    # WT: P1=0, P2=4, P3=2, P4=5
    assert procs[0].waiting_time == 0
    assert procs[1].waiting_time == 4
    assert procs[2].waiting_time == 2
    assert procs[3].waiting_time == 5

    # TT: P1=3, P2=9, P3=4, P4=9
    assert procs[0].turnaround_time == 3
    assert procs[1].turnaround_time == 9
    assert procs[2].turnaround_time == 4
    assert procs[3].turnaround_time == 9


def test_thanos_boost():
    """부스트가 작동하는지 확인: P1이 RR보다 일찍 완료"""
    procs = [
        Process("P1", arrival_time=0, burst_time=3),
        Process("P2", arrival_time=0, burst_time=6),
    ]
    scheduler = ThanosScheduler(time_quantum=2)
    result = scheduler.schedule(procs)

    # t=0: P1(0-2) rem=1, half=1.5 → boost
    # t=2: Queue=[P1(boosted), P2(6)]. P1(2-3) done
    # t=3: P2(3-5) rem=4
    # t=5: P2(5-7) rem=2, half=3 → boost
    # t=7: P2(7-9) done
    assert procs[0].completion_time == 3
    assert procs[1].completion_time == 9


def test_thanos_total_time():
    procs = make_processes()
    scheduler = ThanosScheduler(time_quantum=2)
    result = scheduler.schedule(procs)
    assert result.total_time == 14


def test_thanos_name():
    assert ThanosScheduler(time_quantum=2).name == "Thanos"
