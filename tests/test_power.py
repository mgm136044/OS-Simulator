import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from engine.power import calc_power_summary
from models.processor import Processor, CoreType
from schedulers.base import TimeSlot


def test_power_single_e_core():
    cores = [Processor(0, CoreType.E_CORE)]
    timeline = [TimeSlot("P1", 0, 3, 0)]
    total_time = 3

    summary = calc_power_summary(cores, timeline, total_time)
    assert summary["total_power"] == 3.1
    assert summary["cores"][0]["power"] == 3.1
    assert summary["cores"][0]["utilization"] == 100.0


def test_power_mixed_cores():
    cores = [Processor(0, CoreType.E_CORE), Processor(1, CoreType.P_CORE)]
    timeline = [
        TimeSlot("P1", 0, 3, 0),
        TimeSlot("P2", 0, 2, 1),
    ]
    total_time = 3

    summary = calc_power_summary(cores, timeline, total_time)
    assert summary["total_power"] == 9.6
    assert summary["cores"][0]["utilization"] == 100.0
    assert summary["cores"][1]["utilization"] == round(2/3*100, 1)


def test_power_idle_core():
    cores = [Processor(0, CoreType.E_CORE), Processor(1, CoreType.P_CORE)]
    timeline = [TimeSlot("P1", 0, 2, 0)]
    total_time = 2

    summary = calc_power_summary(cores, timeline, total_time)
    assert summary["total_power"] == 2.1
    assert summary["cores"][1]["power"] == 0.0
    assert summary["cores"][1]["utilization"] == 0.0
