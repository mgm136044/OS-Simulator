import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.process import Process
from schedulers.hrrn import HRRNScheduler


def make_processes():
    return [
        Process("P1", arrival_time=0, burst_time=3),
        Process("P2", arrival_time=1, burst_time=5),
        Process("P3", arrival_time=3, burst_time=2),
        Process("P4", arrival_time=5, burst_time=4),
    ]


def test_hrrn_metrics():
    procs = make_processes()
    scheduler = HRRNScheduler()
    scheduler.schedule(procs)

    assert procs[0].waiting_time == 0
    assert procs[1].waiting_time == 2
    assert procs[2].waiting_time == 5
    assert procs[3].waiting_time == 5

    assert procs[0].turnaround_time == 3
    assert procs[1].turnaround_time == 7
    assert procs[2].turnaround_time == 7
    assert procs[3].turnaround_time == 9


def test_hrrn_timeline():
    procs = make_processes()
    scheduler = HRRNScheduler()
    result = scheduler.schedule(procs)

    pids = [slot.pid for slot in result.timeline]
    assert pids == ["P1", "P2", "P3", "P4"]
    assert result.total_time == 14


def test_hrrn_name():
    assert HRRNScheduler().name == "HRRN"
