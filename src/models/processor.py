from enum import Enum


class CoreType(Enum):
    P_CORE = "P"
    E_CORE = "E"


class Processor:
    """프로세서(코어) 모델. P core / E core 구분."""

    SPECS = {
        CoreType.P_CORE: {"work_per_tick": 2, "power_per_tick": 3.0, "startup_power": 0.5},
        CoreType.E_CORE: {"work_per_tick": 1, "power_per_tick": 1.0, "startup_power": 0.1},
    }

    def __init__(self, core_id: int, core_type: CoreType):
        self.core_id = core_id
        self.core_type = core_type
        spec = self.SPECS[core_type]
        self.work_per_tick: int = spec["work_per_tick"]
        self.power_per_tick: float = spec["power_per_tick"]
        self.startup_power: float = spec["startup_power"]

        self.current_process: str | None = None
        self.is_idle: bool = True
        self.total_power: float = 0.0
        self._needs_startup: bool = False
        self._had_idle_tick: bool = True

    def assign(self, pid: str):
        if self._had_idle_tick:
            self._needs_startup = True
        self.current_process = pid
        self.is_idle = False
        self._had_idle_tick = False

    def release(self):
        self.current_process = None
        self.is_idle = True

    def tick(self) -> float:
        if self.is_idle:
            self._had_idle_tick = True
            return 0.0

        power = self.power_per_tick
        if self._needs_startup:
            power += self.startup_power
            self._needs_startup = False

        self.total_power += power
        return power

    def reset(self):
        self.current_process = None
        self.is_idle = True
        self.total_power = 0.0
        self._needs_startup = False
        self._had_idle_tick = True
