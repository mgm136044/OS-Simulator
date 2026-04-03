import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.process import Process


def test_process_creation():
    p = Process(pid="P1", arrival_time=0, burst_time=5)
    assert p.pid == "P1"
    assert p.arrival_time == 0
    assert p.burst_time == 5
    assert p.remaining_time == 5
    assert p.waiting_time == 0
    assert p.turnaround_time == 0
    assert p.completion_time == 0


def test_process_ntt():
    p = Process(pid="P1", arrival_time=0, burst_time=4)
    p.completion_time = 8
    p.turnaround_time = 8  # CT - AT = 8 - 0
    p.waiting_time = 4     # TT - BT = 8 - 4
    assert p.ntt == 2.0     # TT / BT = 8 / 4


def test_process_reset():
    p = Process(pid="P1", arrival_time=0, burst_time=5)
    p.remaining_time = 2
    p.waiting_time = 3
    p.reset()
    assert p.remaining_time == 5
    assert p.waiting_time == 0
    assert p.completion_time == 0
