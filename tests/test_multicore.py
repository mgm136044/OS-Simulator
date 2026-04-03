import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.process import Process
from models.processor import Processor, CoreType
from schedulers.fcfs import FCFSScheduler
from schedulers.rr import RRScheduler
from schedulers.spn import SPNScheduler
from schedulers.thanos import ThanosScheduler


def test_fcfs_two_cores_parallel():
    """두 프로세스가 두 코어에서 병렬 실행"""
    procs = [
        Process("P1", arrival_time=0, burst_time=4),
        Process("P2", arrival_time=0, burst_time=6),
    ]
    cores = [
        Processor(0, CoreType.E_CORE),
        Processor(1, CoreType.E_CORE),
    ]
    result = FCFSScheduler().schedule(procs, cores)

    # P1 → core0: 0-4, P2 → core1: 0-6
    assert procs[0].completion_time == 4
    assert procs[1].completion_time == 6
    assert result.total_time == 6  # max(4, 6)


def test_fcfs_p_core_speed():
    """P core는 2배 속도: BT=6 → ceil(6/2)=3초"""
    procs = [Process("P1", arrival_time=0, burst_time=6)]
    cores = [Processor(0, CoreType.P_CORE)]
    result = FCFSScheduler().schedule(procs, cores)

    assert procs[0].completion_time == 3
    assert result.total_time == 3


def test_fcfs_power_calculation():
    """E core 2초: 시동 0.1 + 2*1W = 2.1W"""
    procs = [Process("P1", arrival_time=0, burst_time=2)]
    cores = [Processor(0, CoreType.E_CORE)]
    result = FCFSScheduler().schedule(procs, cores)

    assert result.total_power == 2.1


def test_rr_two_cores():
    """RR 멀티코어: 두 코어에서 동시 실행"""
    procs = [
        Process("P1", arrival_time=0, burst_time=3),
        Process("P2", arrival_time=0, burst_time=3),
    ]
    cores = [
        Processor(0, CoreType.E_CORE),
        Processor(1, CoreType.E_CORE),
    ]
    result = RRScheduler(time_quantum=2).schedule(procs, cores)

    # P1 → core0, P2 → core1: 둘 다 3초에 완료
    assert procs[0].completion_time == 3
    assert procs[1].completion_time == 3
    assert result.total_time == 3


def test_spn_two_cores():
    """SPN 멀티코어"""
    procs = [
        Process("P1", arrival_time=0, burst_time=4),
        Process("P2", arrival_time=0, burst_time=2),
        Process("P3", arrival_time=0, burst_time=3),
    ]
    cores = [
        Processor(0, CoreType.E_CORE),
        Processor(1, CoreType.E_CORE),
    ]
    result = SPNScheduler().schedule(procs, cores)

    # SPN picks shortest first: P2(2) → core0, P3(3) → core1, P1(4) → core0 at t=2
    assert procs[1].completion_time == 2  # P2
    assert result.total_time <= 6


def test_thanos_two_cores():
    """Thanos 멀티코어: 두 코어에서 동시 실행"""
    procs = [
        Process("P1", arrival_time=0, burst_time=4),
        Process("P2", arrival_time=0, burst_time=4),
    ]
    cores = [
        Processor(0, CoreType.E_CORE),
        Processor(1, CoreType.E_CORE),
    ]
    result = ThanosScheduler(time_quantum=2).schedule(procs, cores)

    # 각 코어에서 병렬: 4초면 완료
    assert procs[0].completion_time == 4
    assert procs[1].completion_time == 4
    assert result.total_time == 4
