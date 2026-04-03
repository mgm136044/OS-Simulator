import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.processor import Processor, CoreType


def test_e_core_properties():
    core = Processor(core_id=0, core_type=CoreType.E_CORE)
    assert core.work_per_tick == 1
    assert core.power_per_tick == 1.0
    assert core.startup_power == 0.1


def test_p_core_properties():
    core = Processor(core_id=0, core_type=CoreType.P_CORE)
    assert core.work_per_tick == 2
    assert core.power_per_tick == 3.0
    assert core.startup_power == 0.5


def test_core_initial_state():
    core = Processor(core_id=0, core_type=CoreType.E_CORE)
    assert core.is_idle is True
    assert core.current_process is None
    assert core.total_power == 0.0


def test_core_assign_process():
    core = Processor(core_id=0, core_type=CoreType.E_CORE)
    core.assign("P1")
    assert core.is_idle is False
    assert core.current_process == "P1"


def test_core_startup_power_on_first_use():
    core = Processor(core_id=0, core_type=CoreType.P_CORE)
    power = core.tick()
    assert power == 0.0

    core.assign("P1")
    power = core.tick()
    assert power == 0.5 + 3.0

    power = core.tick()
    assert power == 3.0


def test_core_startup_power_after_idle():
    core = Processor(core_id=0, core_type=CoreType.E_CORE)
    core.assign("P1")
    core.tick()
    core.release()
    core.tick()

    core.assign("P2")
    power = core.tick()
    assert power == 0.1 + 1.0


def test_core_no_startup_on_immediate_reassign():
    core = Processor(core_id=0, core_type=CoreType.E_CORE)
    core.assign("P1")
    power1 = core.tick()
    assert power1 == 1.1

    core.release()
    core.assign("P2")
    power2 = core.tick()
    assert power2 == 1.0


def test_core_reset():
    core = Processor(core_id=0, core_type=CoreType.E_CORE)
    core.assign("P1")
    core.tick()
    core.reset()
    assert core.is_idle is True
    assert core.total_power == 0.0
