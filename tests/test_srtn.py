import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.process import Process
from schedulers.srtn import SRTNScheduler


def make_processes():
    return [
        Process("P1", arrival_time=0, burst_time=3),
        Process("P2", arrival_time=1, burst_time=5),
        Process("P3", arrival_time=3, burst_time=2),
        Process("P4", arrival_time=5, burst_time=4),
    ]


def test_srtn_metrics():
    procs = make_processes()
    scheduler = SRTNScheduler()
    scheduler.schedule(procs)

    assert procs[0].waiting_time == 0
    assert procs[1].waiting_time == 8
    assert procs[2].waiting_time == 0
    assert procs[3].waiting_time == 0

    assert procs[0].turnaround_time == 3
    assert procs[1].turnaround_time == 13
    assert procs[2].turnaround_time == 2
    assert procs[3].turnaround_time == 4


def test_srtn_preemption():
    """선점이 발생하는 케이스 테스트"""
    procs = [
        Process("P1", arrival_time=0, burst_time=7),
        Process("P2", arrival_time=2, burst_time=3),
    ]
    scheduler = SRTNScheduler()
    result = scheduler.schedule(procs)

    # t=0: P1(rem=7)
    # t=2: P2 도착(rem=3), P1(rem=5) → P2 선점
    # t=5: P2 완료, P1 재개(rem=5)
    # t=10: P1 완료
    assert procs[0].turnaround_time == 10  # 10 - 0
    assert procs[1].turnaround_time == 3   # 5 - 2
    assert procs[0].waiting_time == 3      # 10 - 7
    assert procs[1].waiting_time == 0      # 3 - 3


def test_srtn_name():
    assert SRTNScheduler().name == "SRTN"
