import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.process import Process
from schedulers.spn import SPNScheduler


def make_processes():
    return [
        Process("P1", arrival_time=0, burst_time=3),
        Process("P2", arrival_time=1, burst_time=5),
        Process("P3", arrival_time=3, burst_time=2),
        Process("P4", arrival_time=5, burst_time=4),
    ]


def test_spn_metrics():
    procs = make_processes()
    scheduler = SPNScheduler()
    scheduler.schedule(procs)

    assert procs[0].waiting_time == 0
    assert procs[1].waiting_time == 8
    assert procs[2].waiting_time == 0
    assert procs[3].waiting_time == 0

    assert procs[0].turnaround_time == 3
    assert procs[1].turnaround_time == 13
    assert procs[2].turnaround_time == 2
    assert procs[3].turnaround_time == 4


def test_spn_timeline():
    procs = make_processes()
    scheduler = SPNScheduler()
    result = scheduler.schedule(procs)

    assert result.total_time == 14
    pids = [slot.pid for slot in result.timeline]
    assert pids == ["P1", "P3", "P4", "P2"]


def test_spn_name():
    assert SPNScheduler().name == "SPN"
