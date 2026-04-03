from models.processor import Processor
from schedulers.base import TimeSlot


def calc_power_summary(
    processors: list[Processor],
    timeline: list[TimeSlot],
    total_time: int,
) -> dict:
    """코어별/전체 소비전력과 가동률 계산"""
    core_info = {}
    for core in processors:
        core_info[core.core_id] = {
            "core_type": core.core_type.value,
            "power": 0.0,
            "busy_ticks": 0,
        }

    for slot in timeline:
        if slot.pid == "idle":
            continue
        cid = slot.core_id
        if cid not in core_info:
            continue
        core = next(c for c in processors if c.core_id == cid)
        ticks = slot.end - slot.start
        core_info[cid]["busy_ticks"] += ticks
        core_info[cid]["power"] += ticks * core.power_per_tick

    for core in processors:
        cid = core.core_id
        slots = sorted(
            [s for s in timeline if s.core_id == cid and s.pid != "idle"],
            key=lambda s: s.start,
        )
        if not slots:
            continue
        core_info[cid]["power"] += core.startup_power
        for i in range(1, len(slots)):
            if slots[i].start > slots[i - 1].end:
                core_info[cid]["power"] += core.startup_power

    total_power = sum(info["power"] for info in core_info.values())

    cores_summary = []
    for core in processors:
        cid = core.core_id
        info = core_info[cid]
        util = round(info["busy_ticks"] / total_time * 100, 1) if total_time > 0 else 0.0
        cores_summary.append({
            "core_id": cid,
            "core_type": info["core_type"],
            "power": round(info["power"], 2),
            "utilization": util,
        })

    return {
        "total_power": round(total_power, 2),
        "cores": cores_summary,
    }
