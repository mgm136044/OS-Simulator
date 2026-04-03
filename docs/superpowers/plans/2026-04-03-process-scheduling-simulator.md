# 프로세스 스케줄링 시뮬레이터 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Python + PyQt5 기반 프로세스 스케줄링 시뮬레이터. 6개 알고리즘(FCFS, RR, SPN, SRTN, HRRN, Thanos)을 Gantt 차트 애니메이션으로 시각화하고, 알고리즘 간 성능 비교 기능을 제공한다.

**Architecture:** 스케줄링 엔진(순수 로직)과 GUI(PyQt5)를 완전 분리. 각 스케줄러는 공통 인터페이스를 구현하며, Simulator 엔진이 스케줄러를 실행하고 실행 로그(타임라인)와 메트릭(AT, BT, WT, TT, NTT)을 산출한다. GUI는 이 결과를 받아 Gantt 차트, 결과 테이블, 비교 뷰로 렌더링한다.

**Tech Stack:** Python 3.11+, PyQt5, pytest

---

## File Structure

```
process-scheduling-simulator/
├── src/
│   ├── main.py                  # 앱 엔트리포인트
│   ├── models/
│   │   └── process.py           # Process 데이터 모델
│   ├── schedulers/
│   │   ├── base.py              # BaseScheduler ABC
│   │   ├── fcfs.py              # FCFS 스케줄러
│   │   ├── rr.py                # Round Robin 스케줄러
│   │   ├── spn.py               # SPN 스케줄러
│   │   ├── srtn.py              # SRTN 스케줄러
│   │   ├── hrrn.py              # HRRN 스케줄러
│   │   └── thanos.py            # Thanos 커스텀 스케줄러
│   ├── engine/
│   │   └── simulator.py         # 시뮬레이션 엔진 (실행 + 메트릭 계산)
│   └── gui/
│       ├── main_window.py       # 메인 윈도우 레이아웃
│       ├── process_input.py     # 프로세스 입력 패널
│       ├── gantt_chart.py       # Gantt 차트 위젯
│       ├── result_table.py      # 결과 테이블 위젯
│       ├── comparison_view.py   # 알고리즘 비교 뷰
│       └── theme.py             # 다크 테마 스타일시트
├── tests/
│   ├── test_process.py
│   ├── test_fcfs.py
│   ├── test_rr.py
│   ├── test_spn.py
│   ├── test_srtn.py
│   ├── test_hrrn.py
│   ├── test_thanos.py
│   └── test_simulator.py
└── requirements.txt
```

---

## 공통 테스트 데이터

모든 스케줄러 테스트에서 동일한 프로세스 세트를 사용한다:

| Process | AT (도착시간) | BT (실행시간) |
|---------|:---:|:---:|
| P1 | 0 | 3 |
| P2 | 1 | 5 |
| P3 | 3 | 2 |
| P4 | 5 | 4 |

---

## Task 1: 프로젝트 셋업 + Process 모델

**Files:**
- Create: `requirements.txt`
- Create: `src/models/process.py`
- Create: `tests/test_process.py`

- [ ] **Step 1: requirements.txt 생성**

```
PyQt5>=5.15
pytest>=7.0
```

- [ ] **Step 2: 의존성 설치**

Run: `pip install -r requirements.txt`

- [ ] **Step 3: Process 모델 테스트 작성**

```python
# tests/test_process.py
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
```

- [ ] **Step 4: 테스트 실패 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_process.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'models'`

- [ ] **Step 5: Process 모델 구현**

```python
# src/models/process.py
from dataclasses import dataclass, field


@dataclass
class Process:
    pid: str
    arrival_time: int
    burst_time: int
    remaining_time: int = field(init=False)
    waiting_time: int = 0
    turnaround_time: int = 0
    completion_time: int = 0

    def __post_init__(self):
        self.remaining_time = self.burst_time

    @property
    def ntt(self) -> float:
        """Normalized Turnaround Time = TT / BT"""
        if self.burst_time == 0:
            return 0.0
        return self.turnaround_time / self.burst_time

    def reset(self):
        self.remaining_time = self.burst_time
        self.waiting_time = 0
        self.turnaround_time = 0
        self.completion_time = 0
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_process.py -v`
Expected: 3 passed

- [ ] **Step 7: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git init
git add requirements.txt src/models/process.py tests/test_process.py
git commit -m "feat: add Process data model with metrics properties"
```

---

## Task 2: BaseScheduler 인터페이스 + ScheduleResult

**Files:**
- Create: `src/schedulers/base.py`

- [ ] **Step 1: BaseScheduler ABC 구현**

```python
# src/schedulers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TimeSlot:
    """Gantt 차트 한 칸: 어떤 프로세스가 언제부터 언제까지 실행되었는지"""
    pid: str          # 프로세스 ID ("idle" for idle)
    start: int
    end: int


@dataclass
class ScheduleResult:
    """스케줄링 결과"""
    timeline: list[TimeSlot] = field(default_factory=list)
    total_time: int = 0


class BaseScheduler(ABC):
    """모든 스케줄러의 공통 인터페이스"""

    @property
    @abstractmethod
    def name(self) -> str:
        """스케줄러 이름 (예: 'FCFS', 'RR')"""
        ...

    @abstractmethod
    def schedule(self, processes: list) -> ScheduleResult:
        """
        프로세스 리스트를 받아 스케줄링 실행.
        - 각 프로세스의 WT, TT, CT 필드를 업데이트
        - ScheduleResult (타임라인) 반환
        """
        ...
```

- [ ] **Step 2: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/schedulers/base.py
git commit -m "feat: add BaseScheduler ABC and ScheduleResult"
```

---

## Task 3: FCFS 스케줄러

**Files:**
- Create: `src/schedulers/fcfs.py`
- Create: `tests/test_fcfs.py`

**FCFS 검증 (AT순 실행):**
- P1(0-3), P2(3-8), P3(8-10), P4(10-14)
- WT: P1=0, P2=2, P3=5, P4=5 → avg=3.0
- TT: P1=3, P2=7, P3=7, P4=9 → avg=6.5

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_fcfs.py
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_fcfs.py -v`
Expected: FAIL

- [ ] **Step 3: FCFS 구현**

```python
# src/schedulers/fcfs.py
from models.process import Process
from schedulers.base import BaseScheduler, ScheduleResult, TimeSlot


class FCFSScheduler(BaseScheduler):

    @property
    def name(self) -> str:
        return "FCFS"

    def schedule(self, processes: list[Process]) -> ScheduleResult:
        for p in processes:
            p.reset()

        sorted_procs = sorted(processes, key=lambda p: (p.arrival_time, p.pid))
        timeline: list[TimeSlot] = []
        current_time = 0

        for proc in sorted_procs:
            if current_time < proc.arrival_time:
                timeline.append(TimeSlot("idle", current_time, proc.arrival_time))
                current_time = proc.arrival_time

            start = current_time
            end = start + proc.burst_time
            timeline.append(TimeSlot(proc.pid, start, end))

            proc.completion_time = end
            proc.turnaround_time = end - proc.arrival_time
            proc.waiting_time = proc.turnaround_time - proc.burst_time
            proc.remaining_time = 0
            current_time = end

        return ScheduleResult(timeline=timeline, total_time=current_time)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_fcfs.py -v`
Expected: 3 passed

- [ ] **Step 5: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/schedulers/fcfs.py tests/test_fcfs.py
git commit -m "feat: add FCFS scheduler with tests"
```

---

## Task 4: RR (Round Robin) 스케줄러

**Files:**
- Create: `src/schedulers/rr.py`
- Create: `tests/test_rr.py`

**RR 검증 (quantum=2):**
- t=0: P1 실행(0-2) rem=1
- t=2: P2 실행(2-4) rem=3, P3 도착(t=3)
- t=4: Queue=[P1(1),P3(2),P2(3)]. P1 실행(4-5) done
- t=5: P4 도착. Queue=[P3(2),P2(3),P4(4)]. P3 실행(5-7) done
- t=7: Queue=[P2(3),P4(4)]. P2 실행(7-9) rem=1
- t=9: P4 실행(9-11) rem=2
- t=11: P2 실행(11-12) done
- t=12: P4 실행(12-14) done
- WT: P1=2, P2=6, P3=2, P4=5
- TT: P1=5, P2=11, P3=4, P4=9

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_rr.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.process import Process
from schedulers.rr import RRScheduler


def make_processes():
    return [
        Process("P1", arrival_time=0, burst_time=3),
        Process("P2", arrival_time=1, burst_time=5),
        Process("P3", arrival_time=3, burst_time=2),
        Process("P4", arrival_time=5, burst_time=4),
    ]


def test_rr_metrics():
    procs = make_processes()
    scheduler = RRScheduler(time_quantum=2)
    scheduler.schedule(procs)

    # WT: P1=2, P2=6, P3=2, P4=5
    assert procs[0].waiting_time == 2
    assert procs[1].waiting_time == 6
    assert procs[2].waiting_time == 2
    assert procs[3].waiting_time == 5

    # TT: P1=5, P2=11, P3=4, P4=9
    assert procs[0].turnaround_time == 5
    assert procs[1].turnaround_time == 11
    assert procs[2].turnaround_time == 4
    assert procs[3].turnaround_time == 9


def test_rr_total_time():
    procs = make_processes()
    scheduler = RRScheduler(time_quantum=2)
    result = scheduler.schedule(procs)
    assert result.total_time == 14


def test_rr_name():
    assert RRScheduler(time_quantum=2).name == "RR"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_rr.py -v`
Expected: FAIL

- [ ] **Step 3: RR 구현**

```python
# src/schedulers/rr.py
from collections import deque
from models.process import Process
from schedulers.base import BaseScheduler, ScheduleResult, TimeSlot


class RRScheduler(BaseScheduler):

    def __init__(self, time_quantum: int = 2):
        self.time_quantum = time_quantum

    @property
    def name(self) -> str:
        return "RR"

    def schedule(self, processes: list[Process]) -> ScheduleResult:
        for p in processes:
            p.reset()

        sorted_procs = sorted(processes, key=lambda p: (p.arrival_time, p.pid))
        timeline: list[TimeSlot] = []
        ready_queue: deque[Process] = deque()
        current_time = 0
        idx = 0  # 다음으로 도착할 프로세스 인덱스
        n = len(sorted_procs)

        # 시간 0에 도착하는 프로세스 추가
        while idx < n and sorted_procs[idx].arrival_time <= current_time:
            ready_queue.append(sorted_procs[idx])
            idx += 1

        while ready_queue or idx < n:
            if not ready_queue:
                # idle 시간
                next_arrival = sorted_procs[idx].arrival_time
                timeline.append(TimeSlot("idle", current_time, next_arrival))
                current_time = next_arrival
                while idx < n and sorted_procs[idx].arrival_time <= current_time:
                    ready_queue.append(sorted_procs[idx])
                    idx += 1
                continue

            proc = ready_queue.popleft()
            exec_time = min(self.time_quantum, proc.remaining_time)
            start = current_time
            end = start + exec_time
            timeline.append(TimeSlot(proc.pid, start, end))
            proc.remaining_time -= exec_time
            current_time = end

            # 이 시간 동안 도착한 프로세스를 큐에 추가 (현재 프로세스보다 먼저)
            while idx < n and sorted_procs[idx].arrival_time <= current_time:
                ready_queue.append(sorted_procs[idx])
                idx += 1

            # 현재 프로세스가 아직 남아있으면 큐 뒤에 추가
            if proc.remaining_time > 0:
                ready_queue.append(proc)
            else:
                proc.completion_time = end
                proc.turnaround_time = end - proc.arrival_time
                proc.waiting_time = proc.turnaround_time - proc.burst_time

        return ScheduleResult(timeline=timeline, total_time=current_time)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_rr.py -v`
Expected: 3 passed

- [ ] **Step 5: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/schedulers/rr.py tests/test_rr.py
git commit -m "feat: add Round Robin scheduler with tests"
```

---

## Task 5: SPN (Shortest Process Next) 스케줄러

**Files:**
- Create: `src/schedulers/spn.py`
- Create: `tests/test_spn.py`

**SPN 검증 (비선점, 도착한 프로세스 중 BT가 가장 짧은 것 선택):**
- t=0: P1만 도착 → P1(0-3)
- t=3: P2(BT=5), P3(BT=2) 도착 → P3(3-5)
- t=5: P2(BT=5), P4(BT=4) 도착 → P4(5-9)
- t=9: P2(BT=5) → P2(9-14)
- WT: P1=0, P2=8, P3=0, P4=0 → avg=2.0
- TT: P1=3, P2=13, P3=2, P4=4 → avg=5.5

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_spn.py
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_spn.py -v`
Expected: FAIL

- [ ] **Step 3: SPN 구현**

```python
# src/schedulers/spn.py
from models.process import Process
from schedulers.base import BaseScheduler, ScheduleResult, TimeSlot


class SPNScheduler(BaseScheduler):

    @property
    def name(self) -> str:
        return "SPN"

    def schedule(self, processes: list[Process]) -> ScheduleResult:
        for p in processes:
            p.reset()

        remaining = sorted(processes[:], key=lambda p: (p.arrival_time, p.pid))
        timeline: list[TimeSlot] = []
        current_time = 0
        completed: set[str] = set()

        while len(completed) < len(processes):
            # 현재 시간까지 도착한 프로세스 중 미완료 & BT가 가장 짧은 것
            available = [
                p for p in remaining
                if p.arrival_time <= current_time and p.pid not in completed
            ]

            if not available:
                # 다음 도착 프로세스까지 idle
                future = [p for p in remaining if p.pid not in completed]
                next_arrival = min(p.arrival_time for p in future)
                timeline.append(TimeSlot("idle", current_time, next_arrival))
                current_time = next_arrival
                continue

            # BT가 가장 짧은 프로세스 선택 (동일하면 AT가 빠른 것)
            proc = min(available, key=lambda p: (p.burst_time, p.arrival_time))

            start = current_time
            end = start + proc.burst_time
            timeline.append(TimeSlot(proc.pid, start, end))

            proc.completion_time = end
            proc.turnaround_time = end - proc.arrival_time
            proc.waiting_time = proc.turnaround_time - proc.burst_time
            proc.remaining_time = 0
            completed.add(proc.pid)
            current_time = end

        return ScheduleResult(timeline=timeline, total_time=current_time)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_spn.py -v`
Expected: 3 passed

- [ ] **Step 5: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/schedulers/spn.py tests/test_spn.py
git commit -m "feat: add SPN scheduler with tests"
```

---

## Task 6: SRTN (Shortest Remaining Time Next) 스케줄러

**Files:**
- Create: `src/schedulers/srtn.py`
- Create: `tests/test_srtn.py`

**SRTN 검증 (선점형 SPN):**
- t=0: P1 실행 (rem=3)
- t=1: P2 도착(rem=5), P1(rem=2) 더 짧음 → P1 계속
- t=3: P1 완료. P2(rem=5), P3(rem=2) → P3 실행
- t=5: P3 완료. P2(rem=5), P4(rem=4) → P4 실행
- t=9: P4 완료. P2 실행(rem=5)
- t=14: P2 완료
- WT: P1=0, P2=8, P3=0, P4=0
- TT: P1=3, P2=13, P3=2, P4=4

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_srtn.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.process import Process
from schedulers.srtn import SRTNScheduler


def make_processes():
    return [
        Process("P1", arrival_time=0, burst_time=3),
        Process("P2", arrival_time=1, burst_time=5),
        Process("P3", arrival_time=3, burst_time=2),
        Process("P4", arrival_time=5, burst_time=4),
    ]


def test_srtn_metrics():
    procs = make_processes()
    scheduler = SRTNScheduler()
    scheduler.schedule(procs)

    assert procs[0].waiting_time == 0
    assert procs[1].waiting_time == 8
    assert procs[2].waiting_time == 0
    assert procs[3].waiting_time == 0

    assert procs[0].turnaround_time == 3
    assert procs[1].turnaround_time == 13
    assert procs[2].turnaround_time == 2
    assert procs[3].turnaround_time == 4


def test_srtn_preemption():
    """선점이 발생하는 케이스 테스트"""
    procs = [
        Process("P1", arrival_time=0, burst_time=7),
        Process("P2", arrival_time=2, burst_time=3),
    ]
    scheduler = SRTNScheduler()
    result = scheduler.schedule(procs)

    # t=0: P1(rem=7)
    # t=2: P2 도착(rem=3), P1(rem=5) → P2 선점
    # t=5: P2 완료, P1 재개(rem=5)
    # t=10: P1 완료
    assert procs[0].turnaround_time == 10  # 10 - 0
    assert procs[1].turnaround_time == 3   # 5 - 2
    assert procs[0].waiting_time == 3      # 10 - 7
    assert procs[1].waiting_time == 0      # 3 - 3


def test_srtn_name():
    assert SRTNScheduler().name == "SRTN"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_srtn.py -v`
Expected: FAIL

- [ ] **Step 3: SRTN 구현**

```python
# src/schedulers/srtn.py
from models.process import Process
from schedulers.base import BaseScheduler, ScheduleResult, TimeSlot


class SRTNScheduler(BaseScheduler):

    @property
    def name(self) -> str:
        return "SRTN"

    def schedule(self, processes: list[Process]) -> ScheduleResult:
        for p in processes:
            p.reset()

        timeline: list[TimeSlot] = []
        current_time = 0
        completed = 0
        n = len(processes)
        current_proc = None
        current_start = 0

        while completed < n:
            # 도착한 프로세스 중 remaining이 가장 작은 것
            available = [
                p for p in processes
                if p.arrival_time <= current_time and p.remaining_time > 0
            ]

            if not available:
                # idle: 다음 도착까지 점프
                future = [p for p in processes if p.remaining_time > 0]
                next_arrival = min(p.arrival_time for p in future)
                if current_proc is not None:
                    timeline.append(TimeSlot(current_proc.pid, current_start, current_time))
                    current_proc = None
                timeline.append(TimeSlot("idle", current_time, next_arrival))
                current_time = next_arrival
                continue

            best = min(available, key=lambda p: (p.remaining_time, p.arrival_time))

            if current_proc != best:
                # 프로세스 전환 (선점 또는 새 시작)
                if current_proc is not None and current_start < current_time:
                    timeline.append(TimeSlot(current_proc.pid, current_start, current_time))
                current_proc = best
                current_start = current_time

            # 다음 이벤트 시점 계산 (새 프로세스 도착 또는 현재 프로세스 완료)
            next_event = current_time + best.remaining_time
            for p in processes:
                if p.arrival_time > current_time and p.remaining_time > 0:
                    if p.arrival_time < next_event:
                        next_event = p.arrival_time

            elapsed = next_event - current_time
            best.remaining_time -= elapsed
            current_time = next_event

            if best.remaining_time == 0:
                best.completion_time = current_time
                best.turnaround_time = current_time - best.arrival_time
                best.waiting_time = best.turnaround_time - best.burst_time
                completed += 1
                timeline.append(TimeSlot(best.pid, current_start, current_time))
                current_proc = None

        return ScheduleResult(timeline=timeline, total_time=current_time)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_srtn.py -v`
Expected: 3 passed

- [ ] **Step 5: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/schedulers/srtn.py tests/test_srtn.py
git commit -m "feat: add SRTN preemptive scheduler with tests"
```

---

## Task 7: HRRN (Highest Response Ratio Next) 스케줄러

**Files:**
- Create: `src/schedulers/hrrn.py`
- Create: `tests/test_hrrn.py`

**HRRN 검증 (비선점, Response Ratio = (WT + BT) / BT):**
- t=0: P1만 도착 → P1(0-3)
- t=3: P2(RR=(2+5)/5=1.4), P3(RR=(0+2)/2=1.0) → P2 실행(3-8)
- t=8: P3(RR=(5+2)/2=3.5), P4(RR=(3+4)/4=1.75) → P3 실행(8-10)
- t=10: P4(10-14)
- WT: P1=0, P2=2, P3=5, P4=5
- TT: P1=3, P2=7, P3=7, P4=9

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_hrrn.py
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_hrrn.py -v`
Expected: FAIL

- [ ] **Step 3: HRRN 구현**

```python
# src/schedulers/hrrn.py
from models.process import Process
from schedulers.base import BaseScheduler, ScheduleResult, TimeSlot


class HRRNScheduler(BaseScheduler):

    @property
    def name(self) -> str:
        return "HRRN"

    def schedule(self, processes: list[Process]) -> ScheduleResult:
        for p in processes:
            p.reset()

        remaining = processes[:]
        timeline: list[TimeSlot] = []
        current_time = 0
        completed: set[str] = set()

        while len(completed) < len(processes):
            available = [
                p for p in remaining
                if p.arrival_time <= current_time and p.pid not in completed
            ]

            if not available:
                future = [p for p in remaining if p.pid not in completed]
                next_arrival = min(p.arrival_time for p in future)
                timeline.append(TimeSlot("idle", current_time, next_arrival))
                current_time = next_arrival
                continue

            def response_ratio(p: Process) -> float:
                wt = current_time - p.arrival_time
                return (wt + p.burst_time) / p.burst_time

            # RR이 가장 높은 프로세스 선택 (동일하면 AT가 빠른 것)
            proc = max(available, key=lambda p: (response_ratio(p), -p.arrival_time))

            start = current_time
            end = start + proc.burst_time
            timeline.append(TimeSlot(proc.pid, start, end))

            proc.completion_time = end
            proc.turnaround_time = end - proc.arrival_time
            proc.waiting_time = proc.turnaround_time - proc.burst_time
            proc.remaining_time = 0
            completed.add(proc.pid)
            current_time = end

        return ScheduleResult(timeline=timeline, total_time=current_time)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_hrrn.py -v`
Expected: 3 passed

- [ ] **Step 5: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/schedulers/hrrn.py tests/test_hrrn.py
git commit -m "feat: add HRRN scheduler with tests"
```

---

## Task 8: Thanos 커스텀 스케줄러

**Files:**
- Create: `src/schedulers/thanos.py`
- Create: `tests/test_thanos.py`

**Thanos 알고리즘:**
- 기본은 RR (Time Quantum = σ)
- 프로세스의 잔여 실행시간이 원래 BT의 절반 이하가 되면 Ready Queue 최상단으로 이동 (부스트)
- 부스트는 프로세스당 1회만 적용

**Thanos 검증 (quantum=2):**
- t=0: P1(BT=3) 실행(0-2), rem=1. half=1.5 → rem(1)≤1 → 부스트!
- t=2: Queue=[P1(boosted,1), P2(5)]. P1 실행(2-3), done
- t=3: P3 도착. Queue=[P2(5), P3(2)]. P2 실행(3-5), rem=3
- t=5: P4 도착. Queue=[P3(2), P2(3), P4(4)]. P3 실행(5-7), done
- t=7: Queue=[P2(3), P4(4)]. P2 실행(7-9), rem=1. half=2.5 → rem(1)≤2 → 부스트!
- t=9: Queue=[P2(boosted,1), P4(4)]. P2 실행(9-10), done
- t=10: P4 실행(10-12), rem=2. half=2 → rem(2)≤2 → 부스트!
- t=12: Queue=[P4(boosted,2)]. P4 실행(12-14), done
- WT: P1=0, P2=4, P3=2, P4=5 → TT: P1=3, P2=9, P3=4, P4=9

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_thanos.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.process import Process
from schedulers.thanos import ThanosScheduler


def make_processes():
    return [
        Process("P1", arrival_time=0, burst_time=3),
        Process("P2", arrival_time=1, burst_time=5),
        Process("P3", arrival_time=3, burst_time=2),
        Process("P4", arrival_time=5, burst_time=4),
    ]


def test_thanos_metrics():
    procs = make_processes()
    scheduler = ThanosScheduler(time_quantum=2)
    scheduler.schedule(procs)

    # WT: P1=0, P2=4, P3=2, P4=5
    assert procs[0].waiting_time == 0
    assert procs[1].waiting_time == 4
    assert procs[2].waiting_time == 2
    assert procs[3].waiting_time == 5

    # TT: P1=3, P2=9, P3=4, P4=9
    assert procs[0].turnaround_time == 3
    assert procs[1].turnaround_time == 9
    assert procs[2].turnaround_time == 4
    assert procs[3].turnaround_time == 9


def test_thanos_boost():
    """부스트가 작동하는지 확인: P1이 RR보다 일찍 완료"""
    procs = [
        Process("P1", arrival_time=0, burst_time=3),
        Process("P2", arrival_time=0, burst_time=6),
    ]
    scheduler = ThanosScheduler(time_quantum=2)
    result = scheduler.schedule(procs)

    # t=0: P1(0-2) rem=1, half=1.5 → boost
    # t=2: Queue=[P1(boosted), P2(6)]. P1(2-3) done
    # t=3: P2(3-5) rem=4
    # t=5: P2(5-7) rem=2, half=3 → boost
    # t=7: P2(7-9) done
    assert procs[0].completion_time == 3
    assert procs[1].completion_time == 9


def test_thanos_total_time():
    procs = make_processes()
    scheduler = ThanosScheduler(time_quantum=2)
    result = scheduler.schedule(procs)
    assert result.total_time == 14


def test_thanos_name():
    assert ThanosScheduler(time_quantum=2).name == "Thanos"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_thanos.py -v`
Expected: FAIL

- [ ] **Step 3: Thanos 구현**

```python
# src/schedulers/thanos.py
from collections import deque
from models.process import Process
from schedulers.base import BaseScheduler, ScheduleResult, TimeSlot


class ThanosScheduler(BaseScheduler):

    def __init__(self, time_quantum: int = 2):
        self.time_quantum = time_quantum

    @property
    def name(self) -> str:
        return "Thanos"

    def schedule(self, processes: list[Process]) -> ScheduleResult:
        for p in processes:
            p.reset()

        sorted_procs = sorted(processes, key=lambda p: (p.arrival_time, p.pid))
        timeline: list[TimeSlot] = []
        ready_queue: deque[Process] = deque()
        current_time = 0
        idx = 0
        n = len(sorted_procs)
        boosted: set[str] = set()  # 부스트 1회 제한 추적

        # 시간 0에 도착하는 프로세스 추가
        while idx < n and sorted_procs[idx].arrival_time <= current_time:
            ready_queue.append(sorted_procs[idx])
            idx += 1

        while ready_queue or idx < n:
            if not ready_queue:
                next_arrival = sorted_procs[idx].arrival_time
                timeline.append(TimeSlot("idle", current_time, next_arrival))
                current_time = next_arrival
                while idx < n and sorted_procs[idx].arrival_time <= current_time:
                    ready_queue.append(sorted_procs[idx])
                    idx += 1
                continue

            proc = ready_queue.popleft()
            exec_time = min(self.time_quantum, proc.remaining_time)
            start = current_time
            end = start + exec_time
            timeline.append(TimeSlot(proc.pid, start, end))
            proc.remaining_time -= exec_time
            current_time = end

            # 이 시간 동안 도착한 프로세스를 큐에 추가
            while idx < n and sorted_procs[idx].arrival_time <= current_time:
                ready_queue.append(sorted_procs[idx])
                idx += 1

            if proc.remaining_time > 0:
                half_threshold = proc.burst_time / 2
                if proc.remaining_time <= half_threshold and proc.pid not in boosted:
                    # 부스트: Ready Queue 최상단에 삽입
                    ready_queue.appendleft(proc)
                    boosted.add(proc.pid)
                else:
                    ready_queue.append(proc)
            else:
                proc.completion_time = end
                proc.turnaround_time = end - proc.arrival_time
                proc.waiting_time = proc.turnaround_time - proc.burst_time

        return ScheduleResult(timeline=timeline, total_time=current_time)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_thanos.py -v`
Expected: 4 passed

- [ ] **Step 5: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/schedulers/thanos.py tests/test_thanos.py
git commit -m "feat: add Thanos custom scheduler (RR + half-remaining boost)"
```

---

## Task 9: Simulator 엔진

**Files:**
- Create: `src/engine/simulator.py`
- Create: `tests/test_simulator.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_simulator.py
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_simulator.py -v`
Expected: FAIL

- [ ] **Step 3: Simulator 구현**

```python
# src/engine/simulator.py
from models.process import Process
from schedulers.base import BaseScheduler


class Simulator:

    def run(self, scheduler: BaseScheduler, processes: list[Process]) -> dict:
        """스케줄러 실행 후 리포트 딕셔너리 반환"""
        result = scheduler.schedule(processes)

        process_details = []
        for p in processes:
            process_details.append({
                "pid": p.pid,
                "at": p.arrival_time,
                "bt": p.burst_time,
                "ct": p.completion_time,
                "wt": p.waiting_time,
                "tt": p.turnaround_time,
                "ntt": round(p.ntt, 2),
            })

        n = len(processes)
        avg_wt = sum(p.waiting_time for p in processes) / n if n else 0
        avg_tt = sum(p.turnaround_time for p in processes) / n if n else 0
        avg_ntt = sum(p.ntt for p in processes) / n if n else 0

        return {
            "algorithm": scheduler.name,
            "total_time": result.total_time,
            "timeline": result.timeline,
            "processes": process_details,
            "metrics": {
                "avg_wt": round(avg_wt, 2),
                "avg_tt": round(avg_tt, 2),
                "avg_ntt": round(avg_ntt, 2),
            },
        }
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_simulator.py -v`
Expected: 3 passed

- [ ] **Step 5: 전체 테스트 통과 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/ -v`
Expected: ALL passed

- [ ] **Step 6: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/engine/simulator.py tests/test_simulator.py
git commit -m "feat: add Simulator engine with metrics aggregation"
```

---

## Task 10: 다크 테마 + 메인 윈도우 레이아웃

**Files:**
- Create: `src/gui/theme.py`
- Create: `src/gui/main_window.py`
- Create: `src/main.py`

- [ ] **Step 1: 다크 테마 스타일시트 작성**

```python
# src/gui/theme.py

DARK_STYLESHEET = """
QMainWindow {
    background-color: #1e1e2e;
}
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "맑은 고딕", sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QTableWidget {
    background-color: #181825;
    gridline-color: #45475a;
    border: 1px solid #45475a;
    border-radius: 4px;
    selection-background-color: #45475a;
}
QTableWidget::item {
    padding: 4px 8px;
}
QHeaderView::section {
    background-color: #313244;
    color: #cdd6f4;
    padding: 6px;
    border: 1px solid #45475a;
    font-weight: bold;
}
QPushButton {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #74c7ec;
}
QPushButton:pressed {
    background-color: #89dceb;
}
QPushButton:disabled {
    background-color: #45475a;
    color: #6c7086;
}
QComboBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 6px 12px;
}
QComboBox::drop-down {
    border: none;
}
QSpinBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
}
QLabel {
    background-color: transparent;
}
QScrollBar:vertical {
    background-color: #181825;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 5px;
    min-height: 20px;
}
QSplitter::handle {
    background-color: #45475a;
}
"""
```

- [ ] **Step 2: 메인 윈도우 뼈대 작성**

```python
# src/gui/main_window.py
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QGroupBox, QLabel,
)
from PyQt5.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("프로세스 스케줄링 시뮬레이터")
        self.setMinimumSize(1200, 700)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # 좌측: 프로세스 입력 패널 (placeholder)
        left_panel = QGroupBox("프로세스 관리")
        left_layout = QVBoxLayout(left_panel)
        self.input_placeholder = QLabel("프로세스 입력 패널")
        left_layout.addWidget(self.input_placeholder)
        splitter.addWidget(left_panel)

        # 우측: Gantt 차트 + 결과
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Gantt 차트 영역 (placeholder)
        gantt_group = QGroupBox("Gantt 차트")
        gantt_layout = QVBoxLayout(gantt_group)
        self.gantt_placeholder = QLabel("Gantt 차트 영역")
        gantt_layout.addWidget(self.gantt_placeholder)
        right_layout.addWidget(gantt_group, stretch=2)

        # 결과 테이블 영역 (placeholder)
        result_group = QGroupBox("스케줄링 결과")
        result_layout = QVBoxLayout(result_group)
        self.result_placeholder = QLabel("결과 테이블 영역")
        result_layout.addWidget(self.result_placeholder)
        right_layout.addWidget(result_group, stretch=1)

        splitter.addWidget(right_widget)
        splitter.setSizes([300, 900])
```

- [ ] **Step 3: 엔트리포인트 작성**

```python
# src/main.py
import sys
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow
from gui.theme import DARK_STYLESHEET


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 수동 실행 확인**

Run: `cd ~/development/process-scheduling-simulator/src && python main.py`
Expected: 다크 테마 윈도우가 나타남. 좌측 프로세스 관리 패널, 우측 Gantt/결과 placeholder.

- [ ] **Step 5: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/gui/theme.py src/gui/main_window.py src/main.py
git commit -m "feat: add dark theme main window layout"
```

---

## Task 11: 프로세스 입력 패널

**Files:**
- Create: `src/gui/process_input.py`
- Modify: `src/gui/main_window.py`

- [ ] **Step 1: 프로세스 입력 위젯 작성**

```python
# src/gui/process_input.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QComboBox, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox,
)
from PyQt5.QtCore import pyqtSignal, Qt


class ProcessInputPanel(QWidget):
    """프로세스 추가/삭제 + 알고리즘 선택 + 실행 버튼"""

    run_requested = pyqtSignal(str, int, list)  # (algorithm, quantum, [(pid, at, bt)])

    ALGORITHMS = ["FCFS", "RR", "SPN", "SRTN", "HRRN", "Thanos"]

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 알고리즘 선택
        algo_layout = QHBoxLayout()
        algo_layout.addWidget(QLabel("알고리즘:"))
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(self.ALGORITHMS)
        algo_layout.addWidget(self.algo_combo)
        layout.addLayout(algo_layout)

        # Time Quantum (RR, Thanos용)
        quantum_layout = QHBoxLayout()
        quantum_layout.addWidget(QLabel("Time Quantum (σ):"))
        self.quantum_spin = QSpinBox()
        self.quantum_spin.setRange(1, 100)
        self.quantum_spin.setValue(2)
        quantum_layout.addWidget(self.quantum_spin)
        layout.addLayout(quantum_layout)

        self.algo_combo.currentTextChanged.connect(self._on_algo_changed)
        self._on_algo_changed(self.algo_combo.currentText())

        # 프로세스 입력 필드
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("AT:"))
        self.at_spin = QSpinBox()
        self.at_spin.setRange(0, 999)
        input_layout.addWidget(self.at_spin)

        input_layout.addWidget(QLabel("BT:"))
        self.bt_spin = QSpinBox()
        self.bt_spin.setRange(1, 999)
        self.bt_spin.setValue(1)
        input_layout.addWidget(self.bt_spin)

        self.add_btn = QPushButton("추가")
        self.add_btn.clicked.connect(self._add_process)
        input_layout.addWidget(self.add_btn)
        layout.addLayout(input_layout)

        # 프로세스 테이블
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["PID", "AT", "BT"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # 삭제 버튼
        self.del_btn = QPushButton("선택 삭제")
        self.del_btn.clicked.connect(self._delete_selected)
        layout.addWidget(self.del_btn)

        # 실행 버튼
        self.run_btn = QPushButton("▶  실행")
        self.run_btn.setStyleSheet(
            "QPushButton { font-size: 15px; padding: 12px; }"
        )
        self.run_btn.clicked.connect(self._on_run)
        layout.addWidget(self.run_btn)

        self._process_count = 0

    def _on_algo_changed(self, algo: str):
        needs_quantum = algo in ("RR", "Thanos")
        self.quantum_spin.setEnabled(needs_quantum)

    def _add_process(self):
        self._process_count += 1
        pid = f"P{self._process_count}"
        at = self.at_spin.value()
        bt = self.bt_spin.value()

        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, val in enumerate([pid, str(at), str(bt)]):
            item = QTableWidgetItem(val)
            item.setTextAlignment(Qt.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, col, item)

    def _delete_selected(self):
        rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()), reverse=True)
        for row in rows:
            self.table.removeRow(row)

    def _on_run(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "경고", "프로세스를 1개 이상 추가하세요.")
            return

        algo = self.algo_combo.currentText()
        quantum = self.quantum_spin.value()
        procs = []
        for row in range(self.table.rowCount()):
            pid = self.table.item(row, 0).text()
            at = int(self.table.item(row, 1).text())
            bt = int(self.table.item(row, 2).text())
            procs.append((pid, at, bt))

        self.run_requested.emit(algo, quantum, procs)
```

- [ ] **Step 2: MainWindow에 입력 패널 연결**

`src/gui/main_window.py`를 수정하여 placeholder를 `ProcessInputPanel`로 교체:

```python
# src/gui/main_window.py
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QGroupBox, QLabel,
)
from PyQt5.QtCore import Qt
from gui.process_input import ProcessInputPanel
from models.process import Process
from engine.simulator import Simulator
from schedulers.fcfs import FCFSScheduler
from schedulers.rr import RRScheduler
from schedulers.spn import SPNScheduler
from schedulers.srtn import SRTNScheduler
from schedulers.hrrn import HRRNScheduler
from schedulers.thanos import ThanosScheduler


SCHEDULER_MAP = {
    "FCFS": lambda q: FCFSScheduler(),
    "RR": lambda q: RRScheduler(time_quantum=q),
    "SPN": lambda q: SPNScheduler(),
    "SRTN": lambda q: SRTNScheduler(),
    "HRRN": lambda q: HRRNScheduler(),
    "Thanos": lambda q: ThanosScheduler(time_quantum=q),
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("프로세스 스케줄링 시뮬레이터")
        self.setMinimumSize(1200, 700)
        self.simulator = Simulator()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # 좌측: 프로세스 입력 패널
        left_panel = QGroupBox("프로세스 관리")
        left_layout = QVBoxLayout(left_panel)
        self.input_panel = ProcessInputPanel()
        self.input_panel.run_requested.connect(self._on_run)
        left_layout.addWidget(self.input_panel)
        splitter.addWidget(left_panel)

        # 우측: Gantt 차트 + 결과
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        gantt_group = QGroupBox("Gantt 차트")
        gantt_layout = QVBoxLayout(gantt_group)
        self.gantt_placeholder = QLabel("Gantt 차트 영역")
        gantt_layout.addWidget(self.gantt_placeholder)
        right_layout.addWidget(gantt_group, stretch=2)

        result_group = QGroupBox("스케줄링 결과")
        result_layout = QVBoxLayout(result_group)
        self.result_placeholder = QLabel("결과 테이블 영역")
        result_layout.addWidget(self.result_placeholder)
        right_layout.addWidget(result_group, stretch=1)

        splitter.addWidget(right_widget)
        splitter.setSizes([300, 900])

    def _on_run(self, algo_name: str, quantum: int, proc_tuples: list):
        processes = [Process(pid, at, bt) for pid, at, bt in proc_tuples]
        scheduler = SCHEDULER_MAP[algo_name](quantum)
        report = self.simulator.run(scheduler, processes)
        # TODO: Gantt 차트 + 결과 테이블에 report 전달
        print(report)  # 임시 확인용
```

- [ ] **Step 3: 수동 실행 확인**

Run: `cd ~/development/process-scheduling-simulator/src && python main.py`
Expected: 좌측에 알고리즘 선택, AT/BT 입력, 프로세스 테이블, 실행 버튼 표시. 프로세스 추가/삭제 동작 확인.

- [ ] **Step 4: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/gui/process_input.py src/gui/main_window.py
git commit -m "feat: add process input panel with algorithm selection"
```

---

## Task 12: 결과 테이블 위젯

**Files:**
- Create: `src/gui/result_table.py`
- Modify: `src/gui/main_window.py`

- [ ] **Step 1: 결과 테이블 위젯 작성**

```python
# src/gui/result_table.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QHBoxLayout,
)
from PyQt5.QtCore import Qt


class ResultTable(QWidget):
    """스케줄링 결과를 표 형태로 보여주는 위젯"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 프로세스별 결과 테이블
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["PID", "AT", "BT", "CT", "WT", "TT", "NTT"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        # 평균 지표
        avg_layout = QHBoxLayout()
        self.avg_wt_label = QLabel("Avg WT: -")
        self.avg_tt_label = QLabel("Avg TT: -")
        self.avg_ntt_label = QLabel("Avg NTT: -")
        for label in (self.avg_wt_label, self.avg_tt_label, self.avg_ntt_label):
            label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 4px 12px;")
            avg_layout.addWidget(label)
        avg_layout.addStretch()
        layout.addLayout(avg_layout)

    def update_results(self, report: dict):
        """Simulator.run() 결과를 테이블에 반영"""
        procs = report["processes"]
        self.table.setRowCount(len(procs))

        for row, p in enumerate(procs):
            for col, key in enumerate(["pid", "at", "bt", "ct", "wt", "tt", "ntt"]):
                val = p[key]
                text = f"{val:.2f}" if isinstance(val, float) else str(val)
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, col, item)

        metrics = report["metrics"]
        self.avg_wt_label.setText(f"Avg WT: {metrics['avg_wt']}")
        self.avg_tt_label.setText(f"Avg TT: {metrics['avg_tt']}")
        self.avg_ntt_label.setText(f"Avg NTT: {metrics['avg_ntt']}")
```

- [ ] **Step 2: MainWindow에 결과 테이블 연결**

`src/gui/main_window.py`에서 `result_placeholder`를 `ResultTable`로 교체. `_on_run`에서 `self.result_table.update_results(report)` 호출:

`main_window.py`의 import에 추가:
```python
from gui.result_table import ResultTable
```

`__init__`에서 결과 그룹 부분을:
```python
        result_group = QGroupBox("스케줄링 결과")
        result_layout = QVBoxLayout(result_group)
        self.result_table = ResultTable()
        result_layout.addWidget(self.result_table)
        right_layout.addWidget(result_group, stretch=1)
```

`_on_run`의 마지막을:
```python
        report = self.simulator.run(scheduler, processes)
        self.result_table.update_results(report)
```

- [ ] **Step 3: 수동 실행 확인**

Run: `cd ~/development/process-scheduling-simulator/src && python main.py`
Expected: 프로세스 추가 후 실행 → 하단에 결과 테이블(PID, AT, BT, CT, WT, TT, NTT)과 평균 지표 표시.

- [ ] **Step 4: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/gui/result_table.py src/gui/main_window.py
git commit -m "feat: add result table widget showing per-process metrics"
```

---

## Task 13: Gantt 차트 위젯 + 애니메이션

**Files:**
- Create: `src/gui/gantt_chart.py`
- Modify: `src/gui/main_window.py`

- [ ] **Step 1: Gantt 차트 위젯 작성**

```python
# src/gui/gantt_chart.py
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QScrollArea
from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QPainter, QColor, QFont, QPen
from schedulers.base import TimeSlot

# 프로세스별 색상
PROCESS_COLORS = [
    "#f38ba8", "#fab387", "#f9e2af", "#a6e3a1",
    "#89dceb", "#89b4fa", "#cba6f7", "#f5c2e7",
    "#94e2d5", "#eba0ac", "#74c7ec", "#b4befe",
]


class GanttCanvas(QWidget):
    """Gantt 차트를 그리는 캔버스"""

    def __init__(self):
        super().__init__()
        self.timeline: list[TimeSlot] = []
        self.total_time = 0
        self.process_ids: list[str] = []
        self.color_map: dict[str, QColor] = {}
        self.animated_time = 0  # 애니메이션 진행 시각
        self.setMinimumHeight(200)

    def set_data(self, timeline: list[TimeSlot], total_time: int, process_ids: list[str]):
        self.timeline = timeline
        self.total_time = total_time
        self.process_ids = [pid for pid in process_ids if pid != "idle"]
        self.color_map = {}
        for i, pid in enumerate(self.process_ids):
            self.color_map[pid] = QColor(PROCESS_COLORS[i % len(PROCESS_COLORS)])
        # idle 여부 확인
        self.has_idle = any(slot.pid == "idle" for slot in timeline)
        self.animated_time = 0
        self.update()

    def set_animated_time(self, t: int):
        self.animated_time = t
        self.update()

    def paintEvent(self, event):
        if not self.timeline or self.total_time == 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width() - 80  # 좌측 PID 라벨 공간
        h = self.height()
        left_margin = 70
        top_margin = 10
        row_height = max(30, min(50, (h - top_margin - 30) // max(len(self.process_ids), 1)))
        unit_width = w / self.total_time

        font = QFont("Segoe UI", 10)
        painter.setFont(font)

        # 프로세스 행 라벨
        for i, pid in enumerate(self.process_ids):
            y = top_margin + i * row_height
            painter.setPen(QColor("#cdd6f4"))
            painter.drawText(QRectF(0, y, left_margin - 10, row_height),
                             Qt.AlignVCenter | Qt.AlignRight, pid)

        # idle 행 (있으면 최하단에 표시)
        idle_row = len(self.process_ids) if self.has_idle else -1
        if self.has_idle:
            y = top_margin + idle_row * row_height
            painter.setPen(QColor("#6c7086"))
            painter.drawText(QRectF(0, y, left_margin - 10, row_height),
                             Qt.AlignVCenter | Qt.AlignRight, "idle")

        # 타임라인 바 그리기
        for slot in self.timeline:
            if slot.start >= self.animated_time:
                continue

            if slot.pid == "idle":
                if not self.has_idle:
                    continue
                row = idle_row
                y = top_margin + row * row_height + 4
                visible_end = min(slot.end, self.animated_time)
                x = left_margin + slot.start * unit_width
                bar_w = (visible_end - slot.start) * unit_width
                # idle은 빗금 패턴의 회색 블록으로 표시
                idle_color = QColor("#45475a")
                painter.setBrush(idle_color)
                painter.setPen(QPen(QColor("#6c7086"), 1, Qt.DashLine))
                painter.drawRoundedRect(QRectF(x, y, bar_w, row_height - 8), 4, 4)
                if bar_w > 20:
                    painter.setPen(QColor("#cdd6f4"))
                    small_font = QFont("Segoe UI", 8)
                    painter.setFont(small_font)
                    painter.drawText(QRectF(x, y, bar_w, row_height - 8),
                                     Qt.AlignCenter, f"idle")
                    painter.setFont(font)
                continue

            if slot.pid not in self.color_map:
                continue

            row = self.process_ids.index(slot.pid)
            y = top_margin + row * row_height + 4
            visible_end = min(slot.end, self.animated_time)
            x = left_margin + slot.start * unit_width
            bar_w = (visible_end - slot.start) * unit_width

            color = self.color_map[slot.pid]
            painter.setBrush(color)
            painter.setPen(QPen(color.darker(120), 1))
            painter.drawRoundedRect(QRectF(x, y, bar_w, row_height - 8), 4, 4)

            # 시간 라벨
            if bar_w > 20:
                painter.setPen(QColor("#1e1e2e"))
                small_font = QFont("Segoe UI", 8)
                painter.setFont(small_font)
                painter.drawText(QRectF(x, y, bar_w, row_height - 8),
                                 Qt.AlignCenter, f"{slot.start}-{visible_end}")
                painter.setFont(font)

        # 시간 축
        total_rows = len(self.process_ids) + (1 if self.has_idle else 0)
        axis_y = top_margin + total_rows * row_height + 4
        painter.setPen(QColor("#6c7086"))
        small_font = QFont("Segoe UI", 8)
        painter.setFont(small_font)
        step = max(1, self.total_time // 20)
        for t in range(0, self.total_time + 1, step):
            x = left_margin + t * unit_width
            painter.drawText(QRectF(x - 10, axis_y, 20, 16), Qt.AlignCenter, str(t))

        painter.end()


class GanttChart(QWidget):
    """Gantt 차트 위젯 (캔버스 + 애니메이션 컨트롤)"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 캔버스
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.canvas = GanttCanvas()
        scroll.setWidget(self.canvas)
        layout.addWidget(scroll, stretch=1)

        # 컨트롤 버튼
        ctrl_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶ 재생")
        self.play_btn.clicked.connect(self._toggle_play)
        ctrl_layout.addWidget(self.play_btn)

        self.reset_btn = QPushButton("↺ 리셋")
        self.reset_btn.clicked.connect(self._reset)
        ctrl_layout.addWidget(self.reset_btn)

        self.skip_btn = QPushButton("⏩ 전체 보기")
        self.skip_btn.clicked.connect(self._skip_to_end)
        ctrl_layout.addWidget(self.skip_btn)

        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        # 타이머
        self.timer = QTimer()
        self.timer.setInterval(400)  # 0.4초 간격
        self.timer.timeout.connect(self._tick)
        self._playing = False

    def set_data(self, timeline: list[TimeSlot], total_time: int, process_ids: list[str]):
        self.timer.stop()
        self._playing = False
        self.play_btn.setText("▶ 재생")
        self.canvas.set_data(timeline, total_time, process_ids)
        self._skip_to_end()  # 기본값: 전체 표시

    def _toggle_play(self):
        if self._playing:
            self.timer.stop()
            self._playing = False
            self.play_btn.setText("▶ 재생")
        else:
            if self.canvas.animated_time >= self.canvas.total_time:
                self.canvas.animated_time = 0
            self._playing = True
            self.play_btn.setText("⏸ 일시정지")
            self.timer.start()

    def _tick(self):
        self.canvas.animated_time += 1
        if self.canvas.animated_time > self.canvas.total_time:
            self.canvas.animated_time = self.canvas.total_time
            self.timer.stop()
            self._playing = False
            self.play_btn.setText("▶ 재생")
        self.canvas.update()

    def _reset(self):
        self.timer.stop()
        self._playing = False
        self.play_btn.setText("▶ 재생")
        self.canvas.set_animated_time(0)

    def _skip_to_end(self):
        self.timer.stop()
        self._playing = False
        self.play_btn.setText("▶ 재생")
        self.canvas.set_animated_time(self.canvas.total_time)
```

- [ ] **Step 2: MainWindow에 Gantt 차트 연결**

`src/gui/main_window.py`의 import에 추가:
```python
from gui.gantt_chart import GanttChart
```

`__init__`에서 gantt 그룹 부분을:
```python
        gantt_group = QGroupBox("Gantt 차트")
        gantt_layout = QVBoxLayout(gantt_group)
        self.gantt_chart = GanttChart()
        gantt_layout.addWidget(self.gantt_chart)
        right_layout.addWidget(gantt_group, stretch=2)
```

`_on_run`을:
```python
    def _on_run(self, algo_name: str, quantum: int, proc_tuples: list):
        processes = [Process(pid, at, bt) for pid, at, bt in proc_tuples]
        scheduler = SCHEDULER_MAP[algo_name](quantum)
        report = self.simulator.run(scheduler, processes)

        # Gantt 차트 업데이트
        process_ids = [p["pid"] for p in report["processes"]]
        self.gantt_chart.set_data(report["timeline"], report["total_time"], process_ids)

        # 결과 테이블 업데이트
        self.result_table.update_results(report)
```

- [ ] **Step 3: 수동 실행 확인**

Run: `cd ~/development/process-scheduling-simulator/src && python main.py`
Expected: 프로세스 추가 → 실행 → 우측에 Gantt 차트(색상 바, 시간축) 표시. 재생/일시정지/리셋 버튼 동작 확인.

- [ ] **Step 4: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/gui/gantt_chart.py src/gui/main_window.py
git commit -m "feat: add Gantt chart widget with animation playback"
```

---

## Task 14: 알고리즘 비교 뷰

**Files:**
- Create: `src/gui/comparison_view.py`
- Modify: `src/gui/main_window.py`
- Modify: `src/gui/process_input.py`

- [ ] **Step 1: 비교 뷰 위젯 작성**

```python
# src/gui/comparison_view.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
)
from PyQt5.QtCore import Qt
from gui.gantt_chart import GanttCanvas


class ComparisonView(QWidget):
    """여러 알고리즘 결과를 나란히 비교하는 뷰"""

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self._widgets: list[QWidget] = []

    def clear(self):
        for w in self._widgets:
            self.layout.removeWidget(w)
            w.deleteLater()
        self._widgets.clear()

    def set_results(self, reports: list[dict]):
        """여러 알고리즘 결과를 한 번에 표시"""
        self.clear()

        # 요약 비교 테이블
        summary_group = QGroupBox("알고리즘 비교 요약")
        summary_layout = QVBoxLayout(summary_group)
        summary_table = QTableWidget(len(reports), 4)
        summary_table.setHorizontalHeaderLabels(["Algorithm", "Avg WT", "Avg TT", "Avg NTT"])
        summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for row, report in enumerate(reports):
            m = report["metrics"]
            for col, val in enumerate([
                report["algorithm"],
                str(m["avg_wt"]),
                str(m["avg_tt"]),
                str(m["avg_ntt"]),
            ]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                summary_table.setItem(row, col, item)

        summary_table.setMaximumHeight(40 + len(reports) * 30)
        summary_layout.addWidget(summary_table)
        self.layout.addWidget(summary_group)
        self._widgets.append(summary_group)

        # 공유 시간 축: 모든 알고리즘 중 가장 긴 makespan을 기준으로 통일
        shared_total_time = max(r["total_time"] for r in reports)

        # 각 알고리즘별 미니 Gantt 차트
        for report in reports:
            group = QGroupBox(f"{report['algorithm']}  (makespan: {report['total_time']})")
            group_layout = QVBoxLayout(group)
            canvas = GanttCanvas()
            canvas.setMinimumHeight(120)
            canvas.setMaximumHeight(160)
            process_ids = [p["pid"] for p in report["processes"]]
            # 공유 시간 축 사용: 모든 차트가 동일한 스케일로 렌더링
            canvas.set_data(report["timeline"], shared_total_time, process_ids)
            canvas.set_animated_time(shared_total_time)
            group_layout.addWidget(canvas)
            self.layout.addWidget(group)
            self._widgets.append(group)
```

- [ ] **Step 2: 입력 패널에 비교 모드 버튼 추가**

`src/gui/process_input.py`에 비교 실행 시그널 추가:

class 상단에 시그널 추가:
```python
    compare_requested = pyqtSignal(int, list)  # (quantum, [(pid, at, bt)])
```

`__init__`의 실행 버튼 아래에 비교 버튼 추가:
```python
        # 비교 실행 버튼
        self.compare_btn = QPushButton("⚖  전체 비교")
        self.compare_btn.setStyleSheet(
            "QPushButton { font-size: 15px; padding: 12px; background-color: #cba6f7; }"
        )
        self.compare_btn.clicked.connect(self._on_compare)
        layout.addWidget(self.compare_btn)
```

비교 메서드 추가:
```python
    def _on_compare(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "경고", "프로세스를 1개 이상 추가하세요.")
            return
        quantum = self.quantum_spin.value()
        procs = []
        for row in range(self.table.rowCount()):
            pid = self.table.item(row, 0).text()
            at = int(self.table.item(row, 1).text())
            bt = int(self.table.item(row, 2).text())
            procs.append((pid, at, bt))
        self.compare_requested.emit(quantum, procs)
```

- [ ] **Step 3: MainWindow에 비교 모드 연결**

`src/gui/main_window.py`에 import 추가:
```python
from gui.comparison_view import ComparisonView
```

`__init__`에서 우측 레이아웃에 비교 뷰 추가 (결과 그룹 아래에):
```python
        # 비교 뷰 (기본 숨김)
        self.comparison_view = ComparisonView()
        self.comparison_view.setVisible(False)
        right_layout.addWidget(self.comparison_view, stretch=2)
```

입력 패널 시그널 연결:
```python
        self.input_panel.compare_requested.connect(self._on_compare)
```

비교 실행 메서드:
```python
    def _on_compare(self, quantum: int, proc_tuples: list):
        reports = []
        for algo_name in ProcessInputPanel.ALGORITHMS:
            processes = [Process(pid, at, bt) for pid, at, bt in proc_tuples]
            scheduler = SCHEDULER_MAP[algo_name](quantum)
            report = self.simulator.run(scheduler, processes)
            reports.append(report)

        self.comparison_view.set_results(reports)
        self.comparison_view.setVisible(True)
```

import 추가:
```python
from gui.process_input import ProcessInputPanel
```

- [ ] **Step 4: 수동 실행 확인**

Run: `cd ~/development/process-scheduling-simulator/src && python main.py`
Expected: "전체 비교" 클릭 시 모든 알고리즘의 Avg WT/TT/NTT 요약 테이블 + 미니 Gantt 차트가 표시.

- [ ] **Step 5: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/gui/comparison_view.py src/gui/process_input.py src/gui/main_window.py
git commit -m "feat: add algorithm comparison view with summary table and mini Gantt charts"
```

---

## Task 15: __init__.py 파일 + 최종 통합 테스트

**Files:**
- Create: `src/models/__init__.py`
- Create: `src/schedulers/__init__.py`
- Create: `src/engine/__init__.py`
- Create: `src/gui/__init__.py`

- [ ] **Step 1: __init__.py 생성**

모든 패키지에 빈 `__init__.py` 생성:

```python
# src/models/__init__.py
# src/schedulers/__init__.py
# src/engine/__init__.py
# src/gui/__init__.py
```

(각각 빈 파일)

- [ ] **Step 2: 전체 테스트 실행**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/ -v`
Expected: ALL passed (test_process 3개, test_fcfs 3개, test_rr 3개, test_spn 3개, test_srtn 3개, test_hrrn 3개, test_thanos 4개, test_simulator 3개 = 총 25개)

- [ ] **Step 3: GUI 수동 확인**

Run: `cd ~/development/process-scheduling-simulator/src && python main.py`
확인 사항:
1. 프로세스 추가/삭제 동작
2. 각 알고리즘별 실행 → Gantt 차트 + 결과 테이블 정상 표시
3. 애니메이션 재생/일시정지/리셋 동작
4. "전체 비교" → 6개 알고리즘 비교 뷰 정상 표시
5. 다크 테마 적용 확인

- [ ] **Step 4: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/models/__init__.py src/schedulers/__init__.py src/engine/__init__.py src/gui/__init__.py
git commit -m "feat: add package init files and verify full integration"
```
