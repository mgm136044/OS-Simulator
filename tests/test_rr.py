import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.process import Process
from schedulers.rr import RRScheduler


def make_processes():
    return [
        Process("P1", arrival_time=0, burst_time=3),
        Process("P2", arrival_time=1, burst_time=5),
        Process("P3", arrival_time=3, burst_time=2),
        Process("P4", arrival_time=5, burst_time=4),
    ]


def test_rr_metrics():
    procs = make_processes()
    scheduler = RRScheduler(time_quantum=2)
    scheduler.schedule(procs)

    # WT: P1=2, P2=6, P3=2, P4=5
    assert procs[0].waiting_time == 2
    assert procs[1].waiting_time == 6
    assert procs[2].waiting_time == 2
    assert procs[3].waiting_time == 5

    # TT: P1=5, P2=11, P3=4, P4=9
    assert procs[0].turnaround_time == 5
    assert procs[1].turnaround_time == 11
    assert procs[2].turnaround_time == 4
    assert procs[3].turnaround_time == 9


def test_rr_total_time():
    procs = make_processes()
    scheduler = RRScheduler(time_quantum=2)
    result = scheduler.schedule(procs)
    assert result.total_time == 14


def test_rr_name():
    assert RRScheduler(time_quantum=2).name == "RR"
