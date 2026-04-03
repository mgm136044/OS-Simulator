import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.process import Process
from schedulers.fcfs import FCFSScheduler


def make_processes():
    return [
        Process("P1", arrival_time=0, burst_time=3),
        Process("P2", arrival_time=1, burst_time=5),
        Process("P3", arrival_time=3, burst_time=2),
        Process("P4", arrival_time=5, burst_time=4),
    ]


def test_fcfs_timeline():
    procs = make_processes()
    scheduler = FCFSScheduler()
    result = scheduler.schedule(procs)

    assert result.total_time == 14
    assert len(result.timeline) == 4
    assert result.timeline[0].pid == "P1"
    assert result.timeline[0].start == 0
    assert result.timeline[0].end == 3
    assert result.timeline[1].pid == "P2"
    assert result.timeline[1].start == 3
    assert result.timeline[1].end == 8
    assert result.timeline[2].pid == "P3"
    assert result.timeline[2].start == 8
    assert result.timeline[2].end == 10
    assert result.timeline[3].pid == "P4"
    assert result.timeline[3].start == 10
    assert result.timeline[3].end == 14


def test_fcfs_metrics():
    procs = make_processes()
    scheduler = FCFSScheduler()
    scheduler.schedule(procs)

    # WT: P1=0, P2=2, P3=5, P4=5
    assert procs[0].waiting_time == 0
    assert procs[1].waiting_time == 2
    assert procs[2].waiting_time == 5
    assert procs[3].waiting_time == 5

    # TT: P1=3, P2=7, P3=7, P4=9
    assert procs[0].turnaround_time == 3
    assert procs[1].turnaround_time == 7
    assert procs[2].turnaround_time == 7
    assert procs[3].turnaround_time == 9


def test_fcfs_name():
    assert FCFSScheduler().name == "FCFS"
