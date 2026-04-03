import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.process import Process
from engine.simulator import Simulator
from schedulers.fcfs import FCFSScheduler


def make_processes():
    return [
        Process("P1", arrival_time=0, burst_time=3),
        Process("P2", arrival_time=1, burst_time=5),
        Process("P3", arrival_time=3, burst_time=2),
        Process("P4", arrival_time=5, burst_time=4),
    ]


def test_simulator_run():
    sim = Simulator()
    procs = make_processes()
    report = sim.run(FCFSScheduler(), procs)

    assert report["algorithm"] == "FCFS"
    assert report["total_time"] == 14
    assert len(report["timeline"]) == 4
    assert len(report["processes"]) == 4


def test_simulator_metrics():
    sim = Simulator()
    procs = make_processes()
    report = sim.run(FCFSScheduler(), procs)

    metrics = report["metrics"]
    assert metrics["avg_wt"] == 3.0
    assert metrics["avg_tt"] == 6.5


def test_simulator_process_details():
    sim = Simulator()
    procs = make_processes()
    report = sim.run(FCFSScheduler(), procs)

    p1 = report["processes"][0]
    assert p1["pid"] == "P1"
    assert p1["at"] == 0
    assert p1["bt"] == 3
    assert p1["wt"] == 0
    assert p1["tt"] == 3
    assert p1["ntt"] == 1.0
