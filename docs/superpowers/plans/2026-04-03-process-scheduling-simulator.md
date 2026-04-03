# 프로세스 스케줄링 시뮬레이터 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Python + PyQt5 기반 프로세스 스케줄링 시뮬레이터. 6개 알고리즘(FCFS, RR, SPN, SRTN, HRRN, Thanos)을 **멀티코어(P core + E core)** 환경에서 Gantt 차트 애니메이션으로 시각화하고, **소비전력 계산** 및 알고리즘 간 성능 비교 기능을 제공한다. 마감: 2026-05-08(금) 23:59

**Architecture:** 스케줄링 엔진(순수 로직)과 GUI(PyQt5)를 완전 분리. 각 스케줄러는 공통 인터페이스를 구현하며, Simulator 엔진이 스케줄러를 실행하고 실행 로그(코어별 타임라인)와 메트릭(AT, BT, WT, TT, NTT, 소비전력)을 산출한다. **멀티코어 지원**: 최대 4개 프로세서(P core: 2배 성능/3배 전력, E core: 기본), 시동전력 포함. 스케줄링은 1초 단위. GUI는 이 결과를 받아 코어별 Gantt 차트, Ready Queue 시각화, 결과 테이블, 비교 뷰로 렌더링한다.

**제약 조건:**
- 프로세스 최대 15개
- 프로세서 최대 4개 (P core / E core 지정 가능)
- E core: 1초에 1 work unit, 1W 소비, 시동전력 0.1W
- P core: 1초에 2 work unit(2배 성능), 3W 소비(3배), 시동전력 0.5W
- 스케줄링 1초 단위 (소수점 불가). P core에서 남은 일이 1이어도 1초 소모

**Tech Stack:** Python 3.11+, PyQt5, pytest

---

## File Structure

```
process-scheduling-simulator/
├── src/
│   ├── main.py                  # 앱 엔트리포인트
│   ├── models/
│   │   ├── process.py           # Process 데이터 모델
│   │   └── processor.py         # Processor(코어) 데이터 모델 (P core / E core)
│   ├── schedulers/
│   │   ├── base.py              # BaseScheduler ABC (멀티코어 지원)
│   │   ├── fcfs.py              # FCFS 스케줄러
│   │   ├── rr.py                # Round Robin 스케줄러
│   │   ├── spn.py               # SPN 스케줄러
│   │   ├── srtn.py              # SRTN 스케줄러
│   │   ├── hrrn.py              # HRRN 스케줄러
│   │   └── thanos.py            # Thanos 커스텀 스케줄러
│   ├── engine/
│   │   ├── simulator.py         # 시뮬레이션 엔진 (실행 + 메트릭 계산)
│   │   └── power.py             # 소비전력 계산 모듈
│   └── gui/
│       ├── main_window.py       # 메인 윈도우 레이아웃
│       ├── process_input.py     # 프로세스 입력 패널
│       ├── processor_config.py  # 프로세서 설정 패널 (코어 수, P/E 타입)
│       ├── gantt_chart.py       # Gantt 차트 위젯 (코어별)
│       ├── ready_queue_view.py  # Ready Queue 시각화 위젯
│       ├── result_table.py      # 결과 테이블 위젯 (전력 포함)
│       ├── comparison_view.py   # 알고리즘 비교 뷰
│       └── theme.py             # 다크 테마 스타일시트
├── tests/
│   ├── test_process.py
│   ├── test_processor.py
│   ├── test_fcfs.py
│   ├── test_rr.py
│   ├── test_spn.py
│   ├── test_srtn.py
│   ├── test_hrrn.py
│   ├── test_thanos.py
│   ├── test_power.py
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
        del_layout = QHBoxLayout()
        self.del_btn = QPushButton("선택 삭제")
        self.del_btn.clicked.connect(self._delete_selected)
        del_layout.addWidget(self.del_btn)

        self.clear_btn = QPushButton("전체 제거")
        self.clear_btn.clicked.connect(self._clear_all)
        del_layout.addWidget(self.clear_btn)
        layout.addLayout(del_layout)

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

    def _clear_all(self):
        self.table.setRowCount(0)
        self._process_count = 0

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

비교 실행 메서드 (코어 설정도 동일하게 적용):
```python
    def _on_compare(self, quantum: int, proc_tuples: list, core_tuples: list):
        reports = []
        for algo_name in ProcessInputPanel.ALGORITHMS:
            processes = [Process(pid, at, bt) for pid, at, bt in proc_tuples]
            processors = [
                Processor(cid, CoreType.P_CORE if ctype == "P" else CoreType.E_CORE)
                for cid, ctype in core_tuples
            ]
            scheduler = SCHEDULER_MAP[algo_name](quantum)
            report = self.simulator.run(scheduler, processes, processors)
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

---

## Task 16: Processor(코어) 모델 — P core / E core

**Files:**
- Create: `src/models/processor.py`
- Create: `tests/test_processor.py`

**시스템 속성:**
- E core: 1초에 1 work unit 처리, 1W 전력, 시동전력 0.1W
- P core: 1초에 2 work unit 처리, 3W 전력, 시동전력 0.5W
- 시동전력: 미사용 중이던 코어를 사용하는 경우 1회 발생

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_processor.py
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
    power = core.tick()  # idle → 사용: 시동전력은 assign 시점에 발생
    assert power == 0.0  # idle이면 전력 0

    core.assign("P1")
    power = core.tick()  # 첫 사용: startup + running
    assert power == 0.5 + 3.0  # 시동전력 + 동작전력

    power = core.tick()  # 계속 사용중: running만
    assert power == 3.0


def test_core_startup_power_after_idle():
    core = Processor(core_id=0, core_type=CoreType.E_CORE)
    core.assign("P1")
    core.tick()  # startup + running = 0.1 + 1.0
    core.release()
    core.tick()  # idle tick

    core.assign("P2")  # 다시 사용 → 시동전력 재발생
    power = core.tick()
    assert power == 0.1 + 1.0


def test_core_no_startup_on_immediate_reassign():
    """선점 후 즉시 재배정 시 시동전력 미발생 (idle tick 없음)"""
    core = Processor(core_id=0, core_type=CoreType.E_CORE)
    core.assign("P1")
    power1 = core.tick()  # startup 0.1 + running 1.0 = 1.1
    assert power1 == 1.1

    core.release()           # release 직후
    core.assign("P2")       # idle tick 없이 바로 재배정
    power2 = core.tick()    # 시동전력 없음, running만 = 1.0
    assert power2 == 1.0    # startup 미발생!


def test_core_reset():
    core = Processor(core_id=0, core_type=CoreType.E_CORE)
    core.assign("P1")
    core.tick()
    core.reset()
    assert core.is_idle is True
    assert core.total_power == 0.0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_processor.py -v`
Expected: FAIL

- [ ] **Step 3: Processor 모델 구현**

```python
# src/models/processor.py
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
        self._had_idle_tick: bool = True  # 초기 상태는 idle이므로 첫 사용 시 시동전력

    def assign(self, pid: str):
        """프로세스를 이 코어에 할당. 실제 idle tick이 있었을 때만 시동전력 발생."""
        if self._had_idle_tick:
            self._needs_startup = True
        self.current_process = pid
        self.is_idle = False
        self._had_idle_tick = False

    def release(self):
        """현재 프로세스 해제 (다음 tick에서 assign 안 되면 idle로 확정)"""
        self.current_process = None
        self.is_idle = True
        # _had_idle_tick은 아직 False: 다음 tick()에서 idle 상태가 확인되면 True로 전환

    def tick(self) -> float:
        """1초 진행. 소비전력 반환."""
        if self.is_idle:
            self._had_idle_tick = True  # 실제로 idle tick이 지남 → 다음 assign 시 시동전력
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_processor.py -v`
Expected: 8 passed

- [ ] **Step 5: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/models/processor.py tests/test_processor.py
git commit -m "feat: add Processor model with P-core/E-core specs and power tracking"
```

---

## Task 17: 멀티코어 스케줄러 확장 — BaseScheduler 리팩토링

**Files:**
- Modify: `src/schedulers/base.py`

현재 BaseScheduler는 단일 코어 전제. 멀티코어를 지원하도록 `ScheduleResult`와 인터페이스를 확장한다.

- [ ] **Step 1: base.py 확장**

```python
# src/schedulers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TimeSlot:
    """Gantt 차트 한 칸: 어떤 프로세스가 어느 코어에서 언제부터 언제까지 실행되었는지"""
    pid: str          # 프로세스 ID ("idle" for idle)
    start: int
    end: int
    core_id: int = 0  # 코어 ID (단일코어는 0)


@dataclass
class ScheduleResult:
    """스케줄링 결과"""
    timeline: list[TimeSlot] = field(default_factory=list)
    total_time: int = 0
    total_power: float = 0.0  # 총 소비전력

    def get_core_timeline(self, core_id: int) -> list[TimeSlot]:
        """특정 코어의 타임라인만 반환"""
        return [slot for slot in self.timeline if slot.core_id == core_id]


class BaseScheduler(ABC):
    """모든 스케줄러의 공통 인터페이스"""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def schedule(self, processes: list, processors: list | None = None) -> ScheduleResult:
        """
        프로세스 리스트를 받아 스케줄링 실행.
        processors가 None이면 E core 1개로 동작 (하위호환).
        - 각 프로세스의 WT, TT, CT 필드를 업데이트
        - ScheduleResult (코어별 타임라인 + 전력) 반환
        """
        ...
```

- [ ] **Step 2: 기존 테스트 통과 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/ -v`
Expected: 기존 테스트 전부 통과 (TimeSlot에 core_id=0 기본값이라 하위호환 유지)

- [ ] **Step 3: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/schedulers/base.py
git commit -m "feat: extend BaseScheduler and ScheduleResult for multi-core support"
```

---

## Task 18: 멀티코어 FCFS 구현 (대표 멀티코어 스케줄러)

**Files:**
- Modify: `src/schedulers/fcfs.py`
- Create: `tests/test_fcfs_multicore.py`

멀티코어 스케줄링 전략: 도착한 프로세스를 가장 먼저 비는 코어에 할당. 동시에 비면 core_id가 낮은 코어 우선.

**멀티코어 FCFS 검증 (E core 1개 + P core 1개):**
- 프로세스: P1(AT=0, BT=4), P2(AT=0, BT=6), P3(AT=3, BT=2)
- E core (core 0): work_per_tick=1, P core (core 1): work_per_tick=2
- t=0: P1→core0 (E, 4/1=4초), P2→core1 (P, 6/2=3초, 남은일 6, 매 tick -2)
  - P core에서 BT=6 처리 시 ceil(6/2)=3초 소요
- t=3: core1 비었음. P3→core1 (P, 2/2=1초)
- t=4: core0 완료(P1), core1 완료(P3)
- P1: CT=4, TT=4, WT=0
- P2: CT=3, TT=3, WT=0 (P core에서 3초만에 완료)
  - 주의: BT는 work unit 기준, CT는 실제 경과 시간
  - WT = CT - AT - ceil(BT / work_per_tick) 이 아니라
  - WT = 실제 대기한 시간 (ready queue에서 보낸 시간)
- P3: CT=4, TT=4-3=1, WT=0

- [ ] **Step 1: 멀티코어 테스트 작성**

```python
# tests/test_fcfs_multicore.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import math
from models.process import Process
from models.processor import Processor, CoreType
from schedulers.fcfs import FCFSScheduler


def test_fcfs_multicore_two_cores():
    procs = [
        Process("P1", arrival_time=0, burst_time=4),
        Process("P2", arrival_time=0, burst_time=6),
        Process("P3", arrival_time=3, burst_time=2),
    ]
    cores = [
        Processor(core_id=0, core_type=CoreType.E_CORE),
        Processor(core_id=1, core_type=CoreType.P_CORE),
    ]
    scheduler = FCFSScheduler()
    result = scheduler.schedule(procs, processors=cores)

    # P1 → E core(0): ceil(4/1)=4초, CT=4
    # P2 → P core(1): ceil(6/2)=3초, CT=3
    # P3 → t=3에 도착, core1 비었음 → P core(1): ceil(2/2)=1초, CT=4
    assert procs[0].completion_time == 4
    assert procs[1].completion_time == 3
    assert procs[2].completion_time == 4

    assert procs[0].waiting_time == 0
    assert procs[1].waiting_time == 0
    assert procs[2].waiting_time == 0


def test_fcfs_multicore_power():
    procs = [
        Process("P1", arrival_time=0, burst_time=2),
    ]
    cores = [
        Processor(core_id=0, core_type=CoreType.E_CORE),
        Processor(core_id=1, core_type=CoreType.P_CORE),
    ]
    scheduler = FCFSScheduler()
    result = scheduler.schedule(procs, processors=cores)

    # P1 → core0 (E core): 2초 동작
    # 전력: 시동 0.1W + 2초 × 1W = 2.1W
    # core1은 사용 안 함 → 0W
    assert result.total_power == 2.1


def test_fcfs_multicore_p_core_ceiling():
    """P core에서 BT=1 → 남은 work=1, work_per_tick=2이지만 1초 소모"""
    procs = [
        Process("P1", arrival_time=0, burst_time=1),
    ]
    cores = [
        Processor(core_id=0, core_type=CoreType.P_CORE),
    ]
    scheduler = FCFSScheduler()
    result = scheduler.schedule(procs, processors=cores)

    # P core에서 BT=1: ceil(1/2)=1초
    assert procs[0].completion_time == 1
    assert result.total_time == 1
    # 전력: 시동 0.5 + 1초 × 3W = 3.5W
    assert result.total_power == 3.5


def test_fcfs_multicore_no_startup_on_consecutive():
    """같은 코어에서 연속 실행 시 시동전력은 최초 1회만"""
    procs = [
        Process("P1", arrival_time=0, burst_time=2),
        Process("P2", arrival_time=0, burst_time=3),
    ]
    cores = [
        Processor(core_id=0, core_type=CoreType.E_CORE),
    ]
    scheduler = FCFSScheduler()
    result = scheduler.schedule(procs, processors=cores)

    # P1(0-2), P2(2-5): 연속, idle gap 없음
    # 전력: 시동 0.1 (1회만) + 5초 × 1W = 5.1W
    assert result.total_power == 5.1
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_fcfs_multicore.py -v`
Expected: FAIL

- [ ] **Step 3: FCFS 멀티코어 구현**

```python
# src/schedulers/fcfs.py
import math
from collections import deque
from models.process import Process
from models.processor import Processor, CoreType
from schedulers.base import BaseScheduler, ScheduleResult, TimeSlot


class FCFSScheduler(BaseScheduler):

    @property
    def name(self) -> str:
        return "FCFS"

    def schedule(self, processes: list[Process], processors: list[Processor] | None = None) -> ScheduleResult:
        for p in processes:
            p.reset()

        # 프로세서 미지정 시 E core 1개로 단일코어 동작
        if processors is None:
            processors = [Processor(core_id=0, core_type=CoreType.E_CORE)]
        for core in processors:
            core.reset()

        sorted_procs = deque(sorted(processes, key=lambda p: (p.arrival_time, p.pid)))
        timeline: list[TimeSlot] = []
        n = len(processes)
        completed = 0
        current_time = 0

        # 각 코어의 종료 시각과 현재 작업 추적
        core_free_at: list[int] = [0] * len(processors)  # 각 코어가 비는 시각
        core_slots: list[list[TimeSlot]] = [[] for _ in processors]

        # FCFS: 도착순으로 가장 먼저 비는 코어에 할당
        total_power = 0.0
        assigned: list[tuple] = []  # (start_time, end_time, core_id, process)

        for proc in sorted_procs:
            # 가장 먼저 비는 코어 찾기 (동률이면 core_id 낮은 것)
            earliest_free = min(
                range(len(processors)),
                key=lambda i: (max(core_free_at[i], proc.arrival_time), i)
            )
            core = processors[earliest_free]
            start = max(core_free_at[earliest_free], proc.arrival_time)
            exec_ticks = math.ceil(proc.burst_time / core.work_per_tick)
            end = start + exec_ticks

            timeline.append(TimeSlot(proc.pid, start, end, core.core_id))

            # idle 슬롯 삽입
            if start > core_free_at[earliest_free]:
                timeline.append(TimeSlot("idle", core_free_at[earliest_free], start, core.core_id))

            # 전력 계산: 시동전력은 실제 idle gap이 있을 때만 (첫 사용 또는 빈 시간대)
            has_idle_gap = core_free_at[earliest_free] < start or core_free_at[earliest_free] == 0
            if has_idle_gap:
                total_power += core.startup_power  # 시동전력
            total_power += exec_ticks * core.power_per_tick  # 동작전력

            core_free_at[earliest_free] = end
            proc.completion_time = end
            proc.turnaround_time = end - proc.arrival_time
            proc.waiting_time = start - proc.arrival_time
            proc.remaining_time = 0

        total_time = max(core_free_at) if core_free_at else 0

        # 타임라인을 시간순 정렬
        timeline.sort(key=lambda s: (s.core_id, s.start))

        return ScheduleResult(timeline=timeline, total_time=total_time, total_power=round(total_power, 2))
```

- [ ] **Step 4: 기존 + 새 테스트 통과 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_fcfs.py tests/test_fcfs_multicore.py -v`
Expected: 전부 passed (기존 단일코어 테스트도 하위호환으로 통과)

- [ ] **Step 5: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/schedulers/fcfs.py tests/test_fcfs_multicore.py
git commit -m "feat: add multi-core support to FCFS scheduler with power calculation"
```

---

## Task 19: 나머지 스케줄러 멀티코어 확장

**Files:**
- Modify: `src/schedulers/rr.py`
- Modify: `src/schedulers/spn.py`
- Modify: `src/schedulers/srtn.py`
- Modify: `src/schedulers/hrrn.py`
- Modify: `src/schedulers/thanos.py`

멀티코어 확장 패턴은 FCFS와 동일: `processors` 파라미터 추가, 기본값 None → E core 1개.
핵심 차이점:
- **비선점(FCFS, SPN, HRRN):** 프로세스 선택 후 빈 코어에 할당. 끝날 때까지 점유.
- **선점(RR, SRTN, Thanos):** 매 tick마다 코어별로 실행 중인 프로세스를 평가. Time quantum 만료/더 짧은 프로세스 도착 시 ready queue로 반환 후 재할당.

모든 스케줄러에서 tick 기반 시뮬레이션으로 통일:
- 매 tick(1초)마다: 도착 프로세스 ready queue 추가 → 빈 코어에 할당 → 각 코어 1 tick 실행 (work_per_tick만큼 remaining 감소) → 완료된 프로세스 처리
- P core에서 remaining이 work_per_tick보다 작아도 1초 소모 (남은 일이 1이어도 1초)

- [ ] **Step 1: 각 스케줄러에 processors 파라미터 추가 + tick 기반 멀티코어 로직 구현**

각 스케줄러의 `schedule` 메서드 시그니처를 변경:
```python
def schedule(self, processes: list[Process], processors: list[Processor] | None = None) -> ScheduleResult:
```

`processors is None`이면 `[Processor(0, CoreType.E_CORE)]`로 초기화.

선점형 스케줄러(RR, SRTN, Thanos) 멀티코어 tick 루프 공통 패턴:

```python
import math
from collections import deque
from models.processor import Processor, CoreType

# 초기화
if processors is None:
    processors = [Processor(core_id=0, core_type=CoreType.E_CORE)]
for core in processors:
    core.reset()

sorted_procs = sorted(processes, key=lambda p: (p.arrival_time, p.pid))
ready_queue = deque()
core_state = {}  # core_id → {"process": Process, "started_at": int}
for core in processors:
    core_state[core.core_id] = None

current_time = 0
idx = 0
completed = 0
timeline = []
total_power = 0.0
n = len(processes)
exec_ticks = {}  # pid → 실제 실행에 사용된 tick 수 누적

while completed < n:
    # 1. 도착 프로세스 추가
    while idx < n and sorted_procs[idx].arrival_time <= current_time:
        ready_queue.append(sorted_procs[idx])
        idx += 1

    # 2. 빈 코어에 프로세스 할당 (스케줄러별 선택 로직)
    for core in processors:
        if core_state[core.core_id] is None and ready_queue:
            proc = _select_next(ready_queue)  # 스케줄러별 구현
            core_state[core.core_id] = {
                "process": proc, "started_at": current_time
            }
            if proc.pid not in exec_ticks:
                exec_ticks[proc.pid] = 0
            core.assign(proc.pid)

    # 3. 1 tick 실행
    for core in processors:
        state = core_state[core.core_id]
        if state is not None:
            proc = state["process"]
            work_done = min(core.work_per_tick, proc.remaining_time)
            proc.remaining_time -= work_done
            exec_ticks[proc.pid] = exec_ticks.get(proc.pid, 0) + 1
            power = core.tick()
            total_power += power

            # 완료 체크
            if proc.remaining_time <= 0:
                proc.remaining_time = 0
                proc.completion_time = current_time + 1
                proc.turnaround_time = proc.completion_time - proc.arrival_time
                # WT = TT - 실제 실행에 사용된 총 tick 수 (코어 이동과 무관하게 정확)
                proc.waiting_time = proc.turnaround_time - exec_ticks[proc.pid]
                timeline.append(TimeSlot(proc.pid, state["started_at"], current_time + 1, core.core_id))
                core.release()
                core_state[core.core_id] = None
                completed += 1

            # 선점 체크 (RR: quantum 만료, SRTN: 더 짧은 도착 등)
            elif _should_preempt(state, core, ready_queue):  # 스케줄러별
                timeline.append(TimeSlot(proc.pid, state["started_at"], current_time + 1, core.core_id))
                ready_queue.append(proc)  # 또는 appendleft (Thanos boost)
                core.release()
                core_state[core.core_id] = None

    current_time += 1

    # 4. idle 코어 처리 (아무 일 안 함, 전력 0)
```

비선점 스케줄러(SPN, HRRN)는 FCFS와 유사한 "빈 코어에 할당" 패턴 사용.

- [ ] **Step 2: 각 스케줄러의 기존 단일코어 테스트 통과 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/ -v`
Expected: 기존 테스트 전부 통과

- [ ] **Step 3: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/schedulers/
git commit -m "feat: extend all schedulers with multi-core processor support"
```

---

## Task 20: 소비전력 계산 모듈

**Files:**
- Create: `src/engine/power.py`
- Create: `tests/test_power.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_power.py
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
    # E core: startup 0.1 + 3초 × 1W = 3.1W
    assert summary["total_power"] == 3.1
    assert summary["cores"][0]["power"] == 3.1
    assert summary["cores"][0]["utilization"] == 100.0


def test_power_mixed_cores():
    cores = [Processor(0, CoreType.E_CORE), Processor(1, CoreType.P_CORE)]
    timeline = [
        TimeSlot("P1", 0, 3, 0),  # E core 3초
        TimeSlot("P2", 0, 2, 1),  # P core 2초
    ]
    total_time = 3

    summary = calc_power_summary(cores, timeline, total_time)
    # E: 0.1 + 3*1 = 3.1W, P: 0.5 + 2*3 = 6.5W → total 9.6W
    assert summary["total_power"] == 9.6
    assert summary["cores"][0]["utilization"] == 100.0  # 3/3
    assert summary["cores"][1]["utilization"] == round(2/3*100, 1)  # 66.7%


def test_power_idle_core():
    cores = [Processor(0, CoreType.E_CORE), Processor(1, CoreType.P_CORE)]
    timeline = [TimeSlot("P1", 0, 2, 0)]
    total_time = 2

    summary = calc_power_summary(cores, timeline, total_time)
    # E: 0.1 + 2*1 = 2.1W, P: 미사용 0W → total 2.1W
    assert summary["total_power"] == 2.1
    assert summary["cores"][1]["power"] == 0.0
    assert summary["cores"][1]["utilization"] == 0.0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_power.py -v`
Expected: FAIL

- [ ] **Step 3: 소비전력 모듈 구현**

```python
# src/engine/power.py
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

    # 시동전력: 코어가 사용된 적 있으면 1회 (간단 모델)
    # 실제로는 idle→busy 전환마다 발생하지만, 타임라인에서 gap 감지
    for core in processors:
        cid = core.core_id
        slots = sorted(
            [s for s in timeline if s.core_id == cid and s.pid != "idle"],
            key=lambda s: s.start,
        )
        if not slots:
            continue
        # 첫 사용 시 시동전력
        core_info[cid]["power"] += core.startup_power
        # 이후 gap이 있으면 시동전력 추가
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_power.py -v`
Expected: 3 passed

- [ ] **Step 5: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/engine/power.py tests/test_power.py
git commit -m "feat: add power consumption calculation module"
```

---

## Task 21: Simulator 엔진 멀티코어 + 전력 통합

**Files:**
- Modify: `src/engine/simulator.py`
- Modify: `tests/test_simulator.py`

- [ ] **Step 1: Simulator에 processors 파라미터 추가**

```python
# src/engine/simulator.py
from models.process import Process
from models.processor import Processor, CoreType
from schedulers.base import BaseScheduler
from engine.power import calc_power_summary


class Simulator:

    def run(
        self,
        scheduler: BaseScheduler,
        processes: list[Process],
        processors: list[Processor] | None = None,
    ) -> dict:
        """스케줄러 실행 후 리포트 딕셔너리 반환"""
        result = scheduler.schedule(processes, processors)

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

        # 전력 요약
        power_summary = None
        if processors is not None:
            power_summary = calc_power_summary(processors, result.timeline, result.total_time)

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
            "power": power_summary,
        }
```

- [ ] **Step 2: 기존 테스트 통과 확인 (하위호환)**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/test_simulator.py -v`
Expected: 기존 3개 테스트 통과 (power는 None)

- [ ] **Step 3: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/engine/simulator.py
git commit -m "feat: integrate multi-core and power calculation into Simulator"
```

---

## Task 22: GUI — 프로세서 설정 패널

**Files:**
- Create: `src/gui/processor_config.py`
- Modify: `src/gui/process_input.py`

- [ ] **Step 1: 프로세서 설정 위젯 작성**

```python
# src/gui/processor_config.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QComboBox, QGroupBox, QRadioButton,
    QButtonGroup,
)
from PyQt5.QtCore import Qt


class CoreConfigRow(QWidget):
    """개별 코어 설정 행: OFF / P-Core / E-Core 라디오"""

    def __init__(self, core_id: int):
        super().__init__()
        self.core_id = core_id
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(f"Core {core_id}")
        label.setFixedWidth(60)
        layout.addWidget(label)

        self.btn_group = QButtonGroup(self)
        self.off_btn = QRadioButton("OFF")
        self.p_btn = QRadioButton("P-Core")
        self.e_btn = QRadioButton("E-Core")

        self.btn_group.addButton(self.off_btn, 0)
        self.btn_group.addButton(self.p_btn, 1)
        self.btn_group.addButton(self.e_btn, 2)

        # 기본값: Core 0은 E-Core, 나머지 OFF
        if core_id == 0:
            self.e_btn.setChecked(True)
        else:
            self.off_btn.setChecked(True)

        layout.addWidget(self.off_btn)
        layout.addWidget(self.p_btn)
        layout.addWidget(self.e_btn)

    def get_type(self) -> str | None:
        """'P', 'E', 또는 None (OFF)"""
        checked = self.btn_group.checkedId()
        if checked == 1:
            return "P"
        elif checked == 2:
            return "E"
        return None


class ProcessorConfigPanel(QWidget):
    """프로세서 설정 패널: 최대 4코어, P/E/OFF 선택"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        header.addWidget(QLabel("프로세서 설정 (최대 4코어)"))
        layout.addLayout(header)

        self.core_rows: list[CoreConfigRow] = []
        for i in range(4):
            row = CoreConfigRow(i)
            self.core_rows.append(row)
            layout.addWidget(row)

        # 스펙 안내
        spec_label = QLabel(
            "P-Core: 2배 성능, 3W, 시동 0.5W  |  E-Core: 1배 성능, 1W, 시동 0.1W"
        )
        spec_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        layout.addWidget(spec_label)

    def get_active_cores(self) -> list[tuple[int, str]]:
        """활성화된 코어 목록 반환: [(core_id, 'P' or 'E'), ...]"""
        cores = []
        for row in self.core_rows:
            core_type = row.get_type()
            if core_type is not None:
                cores.append((row.core_id, core_type))
        return cores
```

- [ ] **Step 2: process_input.py에 프로세서 설정 통합 + 프로세스 15개 제한 + 무작위 추가 버튼**

`src/gui/process_input.py`의 `__init__`에서 프로세서 설정 패널 추가, 프로세스 추가 시 15개 제한:

import에 추가:
```python
import random
from gui.processor_config import ProcessorConfigPanel
```

시그널 변경 (코어 정보 포함):
```python
    run_requested = pyqtSignal(str, int, list, list)  # (algorithm, quantum, [(pid,at,bt)], [(core_id,type)])
    compare_requested = pyqtSignal(int, list, list)    # (quantum, [(pid,at,bt)], [(core_id,type)])
```

`__init__`에서 프로세서 설정 패널을 알고리즘 선택 앞에 추가:
```python
        # 프로세서 설정
        self.processor_config = ProcessorConfigPanel()
        layout.addWidget(self.processor_config)
```

프로세스 추가에 15개 제한:
```python
    def _add_process(self):
        if self.table.rowCount() >= 15:
            QMessageBox.warning(self, "경고", "프로세스는 최대 15개까지 추가할 수 있습니다.")
            return
        # ... 기존 로직
```

무작위 추가 버튼 (추가 버튼 옆에):
```python
        self.random_btn = QPushButton("무작위 추가")
        self.random_btn.clicked.connect(self._add_random_process)
        input_layout.addWidget(self.random_btn)
```

```python
    def _add_random_process(self):
        if self.table.rowCount() >= 15:
            QMessageBox.warning(self, "경고", "프로세스는 최대 15개까지 추가할 수 있습니다.")
            return
        self.at_spin.setValue(random.randint(0, 20))
        self.bt_spin.setValue(random.randint(1, 15))
        self._add_process()
```

`_on_run`과 `_on_compare`에서 코어 정보 emit:
```python
    def _on_run(self):
        # ... 기존 유효성 검사 ...
        cores = self.processor_config.get_active_cores()
        if not cores:
            QMessageBox.warning(self, "경고", "활성화된 코어가 없습니다.")
            return
        self.run_requested.emit(algo, quantum, procs, cores)

    def _on_compare(self):
        # ... 기존 유효성 검사 ...
        cores = self.processor_config.get_active_cores()
        if not cores:
            QMessageBox.warning(self, "경고", "활성화된 코어가 없습니다.")
            return
        self.compare_requested.emit(quantum, procs, cores)
```

- [ ] **Step 3: MainWindow에서 코어 정보 반영**

`src/gui/main_window.py`의 `_on_run` 시그니처 변경:
```python
    def _on_run(self, algo_name: str, quantum: int, proc_tuples: list, core_tuples: list):
        processes = [Process(pid, at, bt) for pid, at, bt in proc_tuples]
        processors = [
            Processor(cid, CoreType.P_CORE if ctype == "P" else CoreType.E_CORE)
            for cid, ctype in core_tuples
        ]
        scheduler = SCHEDULER_MAP[algo_name](quantum)
        report = self.simulator.run(scheduler, processes, processors)

        process_ids = [p["pid"] for p in report["processes"]]
        self.gantt_chart.set_data(report["timeline"], report["total_time"], process_ids)
        self.result_table.update_results(report)
```

- [ ] **Step 4: 수동 실행 확인**

Run: `cd ~/development/process-scheduling-simulator/src && python main.py`
Expected: 코어 설정 라디오 버튼(OFF/P-Core/E-Core) 4개, 무작위 추가 버튼, 15개 제한 동작.

- [ ] **Step 5: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/gui/processor_config.py src/gui/process_input.py src/gui/main_window.py
git commit -m "feat: add processor config panel with P/E core selection and process limits"
```

---

## Task 23: GUI — Ready Queue 시각화

**Files:**
- Create: `src/gui/ready_queue_view.py`
- Modify: `src/gui/main_window.py`

- [ ] **Step 1: Ready Queue 위젯 작성**

```python
# src/gui/ready_queue_view.py
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QFont


QUEUE_COLORS = [
    "#f38ba8", "#fab387", "#f9e2af", "#a6e3a1",
    "#89dceb", "#89b4fa", "#cba6f7", "#f5c2e7",
    "#94e2d5", "#eba0ac", "#74c7ec", "#b4befe",
    "#f38ba8", "#fab387", "#f9e2af",
]


class ReadyQueueView(QWidget):
    """Ready Queue 상태를 시각적으로 표시하는 위젯"""

    def __init__(self):
        super().__init__()
        self.queue_pids: list[str] = []
        self.color_map: dict[str, QColor] = {}
        self.setFixedHeight(50)
        self.setMinimumWidth(200)

    def set_color_map(self, color_map: dict[str, QColor]):
        self.color_map = color_map

    def update_queue(self, pids: list[str]):
        """현재 Ready Queue 상태 업데이트"""
        self.queue_pids = pids
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        font = QFont("Segoe UI", 10, QFont.Bold)
        painter.setFont(font)

        x = 10
        block_h = 30
        y = (self.height() - block_h) // 2

        # "Ready Queue:" 라벨
        painter.setPen(QColor("#cdd6f4"))
        painter.drawText(QRectF(x, y, 100, block_h), Qt.AlignVCenter, "Ready Queue:")
        x += 105

        if not self.queue_pids:
            painter.setPen(QColor("#6c7086"))
            painter.drawText(QRectF(x, y, 100, block_h), Qt.AlignVCenter, "(비어있음)")
            painter.end()
            return

        block_w = 50
        for pid in self.queue_pids:
            color = self.color_map.get(pid, QColor("#89b4fa"))
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(x, y, block_w, block_h), 4, 4)

            painter.setPen(QColor("#1e1e2e"))
            painter.drawText(QRectF(x, y, block_w, block_h), Qt.AlignCenter, pid)
            x += block_w + 4

            if x + block_w > self.width():
                break

        painter.end()
```

- [ ] **Step 2: MainWindow에 Ready Queue 위젯 추가**

`src/gui/main_window.py`에서 Gantt 차트와 결과 테이블 사이에 Ready Queue 뷰 삽입:

import 추가:
```python
from gui.ready_queue_view import ReadyQueueView
```

`__init__`에서 gantt_group 아래에:
```python
        # Ready Queue
        self.ready_queue_view = ReadyQueueView()
        right_layout.addWidget(self.ready_queue_view)
```

Gantt 애니메이션 tick과 연동하여 해당 시점의 ready queue 상태를 표시하려면, ScheduleResult에 ready queue 스냅샷을 포함하거나 GUI에서 재계산. 기본 구현은 정적으로 비워두고, 애니메이션 연동은 후속 개선.

- [ ] **Step 3: 수동 실행 확인**

Run: `cd ~/development/process-scheduling-simulator/src && python main.py`
Expected: Gantt 차트 아래에 Ready Queue 시각화 영역 표시.

- [ ] **Step 4: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/gui/ready_queue_view.py src/gui/main_window.py
git commit -m "feat: add Ready Queue visualization widget"
```

---

## Task 24: GUI — Gantt 차트 멀티코어 표시 + 결과 테이블 전력 표시

**Files:**
- Modify: `src/gui/gantt_chart.py`
- Modify: `src/gui/result_table.py`

- [ ] **Step 1: Gantt 차트를 프로세스별 + 코어별 동시 표시로 변경**

참조 이미지처럼 상단에 "프로세스 관리"(프로세스별 Gantt), 하단에 "스케줄링 결과"(코어별 Gantt)를 동시 표시.

`src/gui/gantt_chart.py`의 `GanttChart` 위젯을 두 개의 `GanttCanvas`를 포함하도록 변경:

```python
class GanttChart(QWidget):
    """Gantt 차트 위젯: 프로세스별 + 코어별 동시 표시"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 상단: 프로세스별 Gantt (프로세스 관리)
        proc_group = QGroupBox("프로세스 관리")
        proc_layout = QVBoxLayout(proc_group)
        scroll1 = QScrollArea()
        scroll1.setWidgetResizable(True)
        self.process_canvas = GanttCanvas()
        scroll1.setWidget(self.process_canvas)
        proc_layout.addWidget(scroll1)
        layout.addWidget(proc_group, stretch=1)

        # 하단: 코어별 Gantt (스케줄링 결과)
        core_group = QGroupBox("스케줄링 결과")
        core_layout = QVBoxLayout(core_group)
        scroll2 = QScrollArea()
        scroll2.setWidgetResizable(True)
        self.core_canvas = GanttCanvas()
        scroll2.setWidget(self.core_canvas)
        core_layout.addWidget(scroll2)
        layout.addWidget(core_group, stretch=1)

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
        self.timer.setInterval(400)
        self.timer.timeout.connect(self._tick)
        self._playing = False
```

`set_data`에서 두 캔버스를 동시에 설정:

```python
    def set_data(self, timeline: list[TimeSlot], total_time: int, process_ids: list[str],
                 core_ids: list[int] | None = None, core_types: list[str] | None = None):
        self.timer.stop()
        self._playing = False
        self.play_btn.setText("▶ 재생")

        # 프로세스별 캔버스: 기존 방식 (프로세스 행)
        self.process_canvas.row_mode = "process"
        self.process_canvas.set_data(timeline, total_time, process_ids)

        # 코어별 캔버스: 코어 행으로 표시
        if core_ids and len(core_ids) >= 1:
            self.core_canvas.row_mode = "core"
            self.core_canvas.core_ids = core_ids
            self.core_canvas.core_types = core_types or ["E"] * len(core_ids)
            self.core_canvas.set_data(timeline, total_time, process_ids)
        else:
            self.core_canvas.row_mode = "core"
            self.core_canvas.core_ids = [0]
            self.core_canvas.core_types = ["E"]
            self.core_canvas.set_data(timeline, total_time, process_ids)

        self._skip_to_end()
```

`_tick`, `_reset`, `_skip_to_end`에서 두 캔버스 동시 업데이트:

```python
    def _tick(self):
        t = self.process_canvas.animated_time + 1
        total = self.process_canvas.total_time
        if t > total:
            t = total
            self.timer.stop()
            self._playing = False
            self.play_btn.setText("▶ 재생")
        self.process_canvas.set_animated_time(t)
        self.core_canvas.set_animated_time(t)

    def _reset(self):
        self.timer.stop()
        self._playing = False
        self.play_btn.setText("▶ 재생")
        self.process_canvas.set_animated_time(0)
        self.core_canvas.set_animated_time(0)

    def _skip_to_end(self):
        self.timer.stop()
        self._playing = False
        self.play_btn.setText("▶ 재생")
        self.process_canvas.set_animated_time(self.process_canvas.total_time)
        self.core_canvas.set_animated_time(self.core_canvas.total_time)
```

`GanttCanvas.paintEvent`에서 `self.row_mode == "core"`일 때:
- 행 라벨: "Core 0 (E)", "Core 1 (P)" 등 (core_types 사용)
- 각 TimeSlot을 해당 core_id 행에 배치
- 프로세스는 색상으로 구분

`self.row_mode == "process"`일 때:
- 기존 동작: 프로세스별 행에 해당 프로세스의 실행 구간 표시

- [ ] **Step 2: 결과 테이블에 전력 정보 표시**

`src/gui/result_table.py`의 `update_results`에 전력 요약 추가:

```python
    def update_results(self, report: dict):
        # ... 기존 테이블 로직 ...

        # 프로세서 개요 + 전력 정보
        power = report.get("power")
        if power:
            p_cores = [c for c in power["cores"] if c["core_type"] == "P"]
            e_cores = [c for c in power["cores"] if c["core_type"] == "E"]
            p_power = sum(c["power"] for c in p_cores)
            e_power = sum(c["power"] for c in e_cores)

            self.p_core_label.setText(f"성능(P): {len(p_cores)}개  ⚡{p_power}W")
            self.e_core_label.setText(f"효율(E): {len(e_cores)}개  ⚡{e_power}W")
            self.total_tasks_label.setText(f"처리 작업: {len(procs)}개")
            self.total_time_label.setText(f"전체 수행시간: {report['total_time']}초")

            # 평균 가동률
            utils = [c["utilization"] for c in power["cores"]]
            avg_util = round(sum(utils) / len(utils), 1) if utils else 0.0
            self.avg_util_label.setText(f"평균 가동률: {avg_util}%")

            self.power_label.setText(f"총 소비전력: {power['total_power']}W")
            core_texts = []
            for c in power["cores"]:
                core_texts.append(
                    f"Core {c['core_id']}({c['core_type']}): {c['power']}W, 가동률 {c['utilization']}%"
                )
            self.core_detail_label.setText("  |  ".join(core_texts))
        else:
            self.p_core_label.setText("성능(P): -")
            self.e_core_label.setText("효율(E): -")
            self.total_tasks_label.setText(f"처리 작업: {len(procs)}개")
            self.total_time_label.setText(f"전체 수행시간: {report['total_time']}초")
            self.avg_util_label.setText("평균 가동률: -")
            self.power_label.setText("총 소비전력: -")
            self.core_detail_label.setText("")
```

`__init__`에 프로세서 개요 + 전력 라벨 추가:
```python
        # 프로세서 개요 섹션
        overview_layout = QHBoxLayout()
        self.p_core_label = QLabel("성능(P): -")
        self.e_core_label = QLabel("효율(E): -")
        self.total_tasks_label = QLabel("처리 작업: -")
        self.total_time_label = QLabel("전체 수행시간: -")
        self.avg_util_label = QLabel("평균 가동률: -")
        for label in (self.p_core_label, self.e_core_label, self.total_tasks_label,
                       self.total_time_label, self.avg_util_label):
            label.setStyleSheet("font-size: 12px; padding: 2px 8px;")
            overview_layout.addWidget(label)
        overview_layout.addStretch()
        layout.addLayout(overview_layout)

        self.power_label = QLabel("총 소비전력: -")
        self.power_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 4px 12px; color: #f9e2af;")
        avg_layout.addWidget(self.power_label)

        self.core_detail_label = QLabel("")
        self.core_detail_label.setStyleSheet("font-size: 11px; padding: 4px 12px; color: #6c7086;")
        layout.addWidget(self.core_detail_label)
```

- [ ] **Step 3: MainWindow에서 코어 ID 전달**

`_on_run`에서 Gantt 차트에 코어 ID + 타입 전달:
```python
        core_ids = [cid for cid, _ in core_tuples]
        core_types = [ctype for _, ctype in core_tuples]
        self.gantt_chart.set_data(
            report["timeline"], report["total_time"], process_ids,
            core_ids, core_types
        )
```

- [ ] **Step 4: 수동 실행 확인**

Run: `cd ~/development/process-scheduling-simulator/src && python main.py`
Expected:
- 상단 "프로세스 관리" Gantt: 프로세스별 행으로 실행 구간 표시
- 하단 "스케줄링 결과" Gantt: 코어별 행(Core 0 (E), Core 1 (P)...)으로 표시
- 프로세서 개요: 성능/효율 코어 수, 전력, 처리 작업 수, 전체 수행시간, 평균 가동률
- 결과 테이블 하단에 총 소비전력 + 코어별 전력/가동률 표시

- [ ] **Step 5: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add src/gui/gantt_chart.py src/gui/result_table.py src/gui/main_window.py
git commit -m "feat: add multi-core Gantt chart rows and power display in result table"
```

---

## Task 25: 최종 통합 테스트 + 실행 파일 패키징

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: requirements.txt에 pyinstaller 추가**

```
PyQt5>=5.15
pytest>=7.0
pyinstaller>=6.0
```

- [ ] **Step 2: 전체 테스트 실행**

Run: `cd ~/development/process-scheduling-simulator && python -m pytest tests/ -v`
Expected: ALL passed

- [ ] **Step 3: GUI 전체 검증**

Run: `cd ~/development/process-scheduling-simulator/src && python main.py`
확인 사항:
1. 프로세스 추가/삭제/무작위 추가 (15개 제한)
2. 프로세서 설정 (P core/E core/OFF, 최대 4코어)
3. 각 알고리즘별 실행 → 코어별 Gantt 차트 + 결과 테이블 + 전력 표시
4. 애니메이션 재생/일시정지/리셋
5. Ready Queue 시각화
6. "전체 비교" → 6개 알고리즘 비교 뷰 (공유 시간축)
7. 다크 테마 적용

- [ ] **Step 4: 실행 파일 빌드 (Windows 제출용)**

Run: `cd ~/development/process-scheduling-simulator && pyinstaller --onefile --windowed --name "ProcessSchedulingSimulator" src/main.py`
Expected: `dist/ProcessSchedulingSimulator.exe` 생성

- [ ] **Step 5: 커밋**

```bash
cd ~/development/process-scheduling-simulator
git add requirements.txt
git commit -m "feat: add pyinstaller for executable packaging"
```
