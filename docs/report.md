# REPORT

## 운영체제 프로젝트 보고서

| 항목 | 내용 |
|------|------|
| 교과목명 | 운영체제 (Operating System) / CSE132 |
| 담당교수 | 김덕수 |
| 팀명 | _(팀명 기입)_ |
| 팀원 | _(이름/학번 기입)_ |
| 제출일 | 2026년 5월 8일 |

---

## [ 보고서 대목차 ]

Ⅰ. 프로젝트 개요

Ⅱ. 소스 코드 설명

Ⅲ. 커스텀 알고리즘 — Thanos

Ⅳ. 실행 결과

Ⅴ. 결론

---

## Ⅰ. 프로젝트 개요

### 1. 목표

6개 프로세스 스케줄링 알고리즘(FCFS, RR, SPN, SRTN, HRRN, Thanos)을 멀티코어(P core + E core) 환경에서 시뮬레이션하고, Gantt 차트 애니메이션으로 시각화하며, 소비전력 계산 및 알고리즘 간 성능 비교 기능을 제공하는 시뮬레이터를 개발한다.

### 2. 기술 스택

| 항목 | 기술 |
|------|------|
| 언어 | Python 3.9+ |
| GUI | PyQt5 |
| 테스트 | pytest |
| 패키징 | PyInstaller (Windows .exe) |

### 3. 아키텍처

엔진(스케줄링 로직)과 GUI(시각화)를 완전 분리하여, 스케줄러 교체나 테스트가 GUI 없이도 가능하도록 설계하였다.

```
src/
├── models/           ← 데이터 모델 (Process, Processor)
├── schedulers/       ← 스케줄링 알고리즘 6개 + 공통 인터페이스
├── engine/           ← 시뮬레이션 엔진 + 소비전력 계산
└── gui/              ← PyQt5 GUI 컴포넌트 (다크 테마)
tests/                ← 42개 자동화 테스트
```

**데이터 흐름:**

```
사용자 입력 (GUI)
    ↓
ProcessInputPanel → (프로세스, 코어 설정)
    ↓
Simulator.run(scheduler, processes, processors)
    ↓
ScheduleResult (timeline, metrics, power)
    ↓
GanttChart + ResultTable + ReadyQueueView (GUI 출력)
```

---

## Ⅱ. 소스 코드 설명

### 1. 데이터 모델

#### 1.1 Process (`src/models/process.py`)

프로세스의 속성과 스케줄링 결과를 저장하는 데이터 클래스이다.

```python
@dataclass
class Process:
    pid: str                          # 프로세스 ID
    arrival_time: int                 # 도착 시간
    burst_time: int                   # 실행 시간
    remaining_time: int = field(init=False)  # 잔여 시간 (__post_init__에서 burst_time으로 초기화)
    waiting_time: int = 0             # 대기 시간
    turnaround_time: int = 0          # 반환 시간 (CT - AT)
    completion_time: int = 0          # 완료 시간

    def __post_init__(self):
        self.remaining_time = self.burst_time

    @property
    def ntt(self) -> float:
        """Normalized Turnaround Time = TT / BT"""
        if self.burst_time == 0:
            return 0.0
        return self.turnaround_time / self.burst_time

    def reset(self):
        """스케줄러 재실행 시 메트릭 초기화"""
```

`remaining_time`은 `field(init=False)`로 선언되어 생성자 파라미터가 아니며, `__post_init__`에서 `burst_time`으로 자동 초기화된다. `ntt`는 `burst_time == 0`인 경우를 방어한다.

`reset()` 메서드를 통해 동일한 프로세스 객체를 여러 알고리즘에서 재사용할 수 있다. 이는 전체 비교 기능에서 핵심적으로 활용된다.

#### 1.2 Processor (`src/models/processor.py`)

P core / E core를 구분하는 프로세서 모델이다.

```python
class CoreType(Enum):
    P_CORE = "P"    # 2배 성능, 3W, 시동 0.5W
    E_CORE = "E"    # 1배 성능, 1W, 시동 0.1W
```

| 속성 | P core | E core |
|------|:------:|:------:|
| work_per_tick | 2 | 1 |
| power_per_tick | 3.0W | 1.0W |
| startup_power | 0.5W | 0.1W |

시동전력은 idle 상태에서 처음 프로세스가 할당될 때 1회 발생하며, 연속 재배정 시에는 발생하지 않는다. 이를 `_had_idle_tick` 플래그로 추적한다.

```python
def assign(self, pid: str):
    if self._had_idle_tick:        # idle tick이 있었을 때만
        self._needs_startup = True  # 시동전력 발생
    self.current_process = pid
    self.is_idle = False
    self._had_idle_tick = False    # 연속 재배정 시 시동전력 방지

def tick(self) -> float:
    if self.is_idle:
        self._had_idle_tick = True  # idle 확정
        return 0.0
    power = self.power_per_tick
    if self._needs_startup:
        power += self.startup_power  # 시동전력 추가
        self._needs_startup = False
    return power
```

### 2. 스케줄러 공통 구조

#### 2.1 BaseScheduler (`src/schedulers/base.py`)

모든 스케줄러가 구현해야 하는 추상 인터페이스이다.

```python
@dataclass
class TimeSlot:
    pid: str       # 프로세스 ID ("idle" for idle)
    start: int     # 시작 시각
    end: int       # 종료 시각
    core_id: int   # 코어 ID (멀티코어 지원)

@dataclass
class ScheduleResult:
    timeline: list[TimeSlot]    # Gantt 차트 데이터
    total_time: int             # 전체 실행 시간
    total_power: float          # 총 소비전력
    queue_snapshots: dict       # Ready Queue 상태 ({time: [pid, ...]})

class BaseScheduler(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """스케줄러 이름 (예: 'FCFS', 'RR')"""
        ...

    @abstractmethod
    def schedule(self, processes, processors=None) -> ScheduleResult:
        ...
```

`processors`가 `None`이면 E core 1개로 단일코어 동작하여 하위호환을 유지한다.

### 3. 알고리즘별 핵심 로직

#### 3.1 FCFS (First-Come First-Served)

비선점 방식으로, 도착 순서대로 프로세스를 실행한다.

```python
sorted_procs = deque(sorted(processes, key=lambda p: (p.arrival_time, p.pid)))
for proc in sorted_procs:
    best_idx = min(range(num_cores),
                   key=lambda i: (max(core_free_at[i], proc.arrival_time), i))
    exec_ticks = math.ceil(proc.burst_time / core.work_per_tick)
```

- 가장 먼저 비는 코어에 할당 (`core_free_at[]` 배열)
- P core에서 실행 시 `ceil(BT/2)` 초 소요

#### 3.2 RR (Round Robin)

선점 방식으로, 각 프로세스에 고정 Time Quantum을 부여한다.

```python
# 1 tick 실행
work = min(core.work_per_tick, proc.remaining_time)
proc.remaining_time -= work
state["quantum_used"] += 1

# quantum 만료 시 선점
if state["quantum_used"] >= self.time_quantum:
    ready_queue.append(proc)  # 큐 뒤로
```

- Tick 기반 시뮬레이션: 매 1초마다 각 코어의 상태를 갱신
- `quantum_used`로 코어별 퀀텀 소진을 독립 추적
- 도착 → 재큐잉 순서 (arrivals-before-requeue)

#### 3.3 SPN (Shortest Process Next)

비선점 방식으로, 대기 중인 프로세스 중 BT가 가장 짧은 것을 선택한다.

```python
proc = min(available, key=lambda p: (p.burst_time, p.arrival_time))
```

- 평균 TT를 최소화하지만, 장기 프로세스에 기아(starvation) 발생 가능

#### 3.4 SRTN (Shortest Remaining Time Next)

SPN의 선점 버전으로, 매 tick마다 잔여 시간이 가장 짧은 프로세스를 선택한다.

```python
# 선점 체크: ready_queue에 더 짧은 프로세스가 있으면 교체
shortest = min(ready_queue, key=lambda p: (p.remaining_time, p.arrival_time))
if shortest.remaining_time < proc.remaining_time:
    # 현재 프로세스를 ready_queue로 반환, shortest를 코어에 할당
```

- 새 프로세스 도착 시 현재 실행 중인 프로세스와 비교하여 선점 결정

#### 3.5 HRRN (Highest Response Ratio Next)

비선점 방식으로, 응답 비율이 가장 높은 프로세스를 선택한다.

```python
def response_ratio(p):
    wt = earliest_free - p.arrival_time  # 가장 먼저 비는 코어 시각 기준
    return (wt + p.burst_time) / p.burst_time

proc = max(available, key=lambda p: (response_ratio(p), -p.arrival_time))
```

- Response Ratio = (WT + BT) / BT
- 대기 시간이 길어질수록 비율이 올라가므로 기아를 자연스럽게 방지

#### 3.6 Thanos (커스텀 알고리즘)

*Ⅲ장에서 상세 설명*

### 4. 멀티코어 처리 방식

6개 알고리즘 모두 멀티코어를 지원하며, 유형에 따라 두 가지 패턴을 사용한다.

| 유형 | 알고리즘 | 방식 |
|------|---------|------|
| 비선점 | FCFS, SPN, HRRN | `core_free_at[]` 배열로 가장 먼저 비는 코어에 할당 |
| 선점 | RR, SRTN, Thanos | `core_state[]` 딕셔너리 + tick 기반 시뮬레이션 |

**비선점 스케줄러의 멀티코어 할당:**
```python
core_free_at = [0] * num_cores  # 각 코어가 비는 시각
for proc in sorted_procs:
    best_idx = min(range(num_cores),
                   key=lambda i: (max(core_free_at[i], proc.arrival_time), i))
    exec_ticks = math.ceil(proc.burst_time / core.work_per_tick)
```

**선점 스케줄러의 멀티코어 tick 루프:**
```python
core_state = [None] * num_cores  # 코어별 실행 상태
while completed < n:
    # 빈 코어에 프로세스 할당
    # 모든 코어 1 tick 실행 (work_per_tick만큼 remaining 감소)
    # 도착 프로세스 큐 추가
    # 완료/선점 처리
    current_time += 1
```

P core에서 실행 시 `work_per_tick=2`이므로 1초에 2단위의 작업을 처리한다. 남은 작업이 1이어도 1초를 소모한다 (`math.ceil` 적용).

### 5. 소비전력 계산 (`src/engine/power.py`)

타임라인을 분석하여 코어별 소비전력과 가동률을 산출한다.

```python
def calc_power_summary(processors, timeline, total_time) -> dict:
```

**전력 계산 공식:**

```
코어별 전력 = 시동전력 × (idle→busy 전환 횟수) + 동작전력 × 실행 tick 수
총 전력 = Σ(각 코어 전력)
가동률 = (실행 tick 수 / 전체 시간) × 100%
```

- idle 구간 후 프로세스가 할당되면 시동전력 발생 (E: 0.1W, P: 0.5W)
- 연속 실행 시에는 시동전력 미발생
- 타임라인의 gap(빈 구간)을 감지하여 시동전력 횟수를 정확히 계산

### 6. GUI 컴포넌트

| 파일 | 역할 |
|------|------|
| `main_window.py` | 메인 윈도우 — 모든 패널 조율, 스케줄러 실행 및 결과 전달 |
| `process_input.py` | 프로세스 입력 패널 — AT/BT 입력, 알고리즘 선택, 실행/비교 버튼 |
| `processor_config.py` | 프로세서 설정 — Core 0~3 각각 OFF/P-Core/E-Core 선택 |
| `gantt_chart.py` | Gantt 차트 — 프로세스별 색상 바, 시간축, 재생/일시정지/리셋 애니메이션 |
| `ready_queue_view.py` | Ready Queue 시각화 — 현재 시각의 큐 상태를 색상 블록으로 표시 |
| `result_table.py` | 결과 테이블 — PID, AT, BT, CT, WT, TT, NTT + 평균 + 전력 정보 |
| `comparison_view.py` | 알고리즘 비교 — 6개 알고리즘 요약 테이블 + 공유 시간축 미니 Gantt |
| `theme.py` | 다크 테마 — Catppuccin 기반 스타일시트 |

---

## Ⅲ. 커스텀 알고리즘 — Thanos

### 1. 대상 시스템

**온라인 게임 매칭 서버** — 다수의 매치메이킹 요청이 동시에 들어오는 환경에서, 매칭 난이도에 따라 처리 시간이 다르고(다양한 BT), 모든 유저의 요청이 일정 시간 내 처리되어야 하며(공정성), 이미 절반 이상 매칭 조건을 충족한 요청은 빨리 완료해야 유저 이탈을 방지할 수 있다(완료 우선).

### 2. 설계 철학 — "절반의 균형 (Half Balance)"

타노스가 우주의 절반을 정리하여 균형을 맞추듯, 작업의 절반이 완료된 시점에서 우선순위를 부여하여 **공정성과 효율성의 균형**을 달성한다.

| 비교 | RR | SPN | Thanos |
|------|:--:|:---:|:------:|
| 공정성 | 높음 | 낮음 (기아) | 높음 (RR 기반) |
| 평균 TT | 높음 | 낮음 | 중간 (부스트 개선) |
| 기아 방지 | ✓ | ✗ | ✓ |

### 3. 핵심 메커니즘

```python
# quantum 만료 시 부스트 체크
if state["quantum_used"] >= self.time_quantum:
    half_threshold = proc.burst_time / 2
    if proc.remaining_time <= half_threshold and proc.pid not in boosted:
        ready_queue.appendleft(proc)   # 큐 최상단으로 이동 (부스트)
        boosted.add(proc.pid)          # 1회 제한
    else:
        ready_queue.append(proc)       # 일반 RR과 동일 (큐 뒤로)
```

**동작 요약:**
1. 기본은 RR과 동일 — Time Quantum마다 선점, 도착→재큐잉 순서
2. quantum 만료 시점에 `remaining_time ≤ burst_time / 2`이면 큐 앞으로 이동 (부스트)
3. 각 프로세스는 최대 1회만 부스트 가능 (`boosted` 집합으로 추적)
4. 부스트되지 않은 경로는 RR과 완전히 동일

### 4. RR과의 차이

```
[RR]     quantum 만료 → 항상 큐 뒤에 append
[Thanos] quantum 만료 → 50% 이상 완료 시 큐 앞에 appendleft (1회)
                        그 외에는 RR과 동일하게 큐 뒤에 append
```

기반 큐 규칙(도착 처리 순서)이 RR과 동일하므로, 성능 비교가 공정하게(apples-to-apples) 이루어진다.

### 5. 장점

- **기아 방지**: RR 기반이므로 모든 프로세스가 반드시 CPU 시간을 할당받음
- **진행률 기반 최적화**: 절반 이상 완료된 프로세스를 우선 마무리하여 평균 TT 개선
- **매몰 비용 감소**: 거의 완료된 작업이 타임아웃되는 상황을 방지
- **스케줄링 순서에 BT 불필요**: SPN/SRTN은 BT로 실행 순서를 결정하지만, Thanos는 RR 기반으로 실행 순서를 정하고 부스트 판정에만 BT를 참조. 스케줄링 진입 시점에 BT 예측이 필요 없다.

---

## Ⅳ. 실행 결과

### 1. GUI 실행 화면

_(스크린샷 삽입 위치 — 한컴 편집 시 추가)_

- 좌측: 프로세서 설정 (Core 0~3 OFF/P/E) + 프로세스 입력 + 알고리즘 선택
- 우측 상단: Gantt 차트 (재생/일시정지/리셋 애니메이션)
- 우측 중앙: Ready Queue 시각화
- 우측 하단: 결과 테이블 (WT, TT, NTT, 전력)

### 2. 알고리즘별 성능 비교

**테스트 데이터:** 단일 E core, Time Quantum = 2

| Process | AT | BT |
|---------|:--:|:--:|
| P1 | 0 | 3 |
| P2 | 1 | 5 |
| P3 | 3 | 2 |
| P4 | 5 | 4 |

**결과:**

| 알고리즘 | Avg WT | Avg TT | Avg NTT | Makespan |
|---------|:------:|:------:|:-------:|:--------:|
| FCFS | 3.00 | 6.50 | 2.04 | 14 |
| RR | 3.75 | 7.25 | 2.03 | 14 |
| SPN | 2.00 | 5.50 | 1.40 | 14 |
| SRTN | 2.00 | 5.50 | 1.40 | 14 |
| HRRN | 3.00 | 6.50 | 2.04 | 14 |
| Thanos | 3.00 | 6.50 | 1.78 | 14 |

### 3. 멀티코어 실행 결과

**테스트:** 2개 E core, FCFS

| Process | AT | BT | 완료 시각 | 할당 코어 |
|---------|:--:|:--:|:--------:|:--------:|
| P1 | 0 | 4 | 4 | Core 0 |
| P2 | 0 | 6 | 6 | Core 1 |

- Makespan: 6 (단일코어 시 10 → 40% 단축)
- 두 프로세스가 병렬로 실행됨

### 4. 소비전력 비교 예시

**설정:** P core 1개 + E core 1개

| 코어 | 실행 시간 | 동작전력 | 시동전력 | 합계 |
|------|:--------:|:-------:|:-------:|:----:|
| P core (Core 0) | 3초 | 9.0W | 0.5W | 9.5W |
| E core (Core 1) | 5초 | 5.0W | 0.1W | 5.1W |
| **합계** | | | | **14.6W** |

### 5. 테스트 커버리지

```
42 tests passed (0.02s)

test_fcfs.py        3 tests  — FCFS 타임라인, 메트릭, 이름
test_rr.py          3 tests  — RR 메트릭, 전체 시간, 이름
test_spn.py         3 tests  — SPN 메트릭, 타임라인, 이름
test_srtn.py        3 tests  — SRTN 메트릭, 선점, 이름
test_hrrn.py        3 tests  — HRRN 메트릭, 타임라인, 이름
test_thanos.py      4 tests  — Thanos 메트릭, 부스트, 전체 시간, 이름
test_process.py     3 tests  — Process 생성, NTT, reset
test_processor.py   8 tests  — P/E core 속성, 시동전력, 재배정
test_simulator.py   3 tests  — Simulator 실행, 메트릭, 상세
test_power.py       3 tests  — 단일/혼합 코어 전력, idle 처리
test_multicore.py   6 tests  — 병렬 실행, P core 속도, 전력
```

---

## Ⅴ. 결론

### 1. 구현 성과

- 6개 스케줄링 알고리즘 구현 및 멀티코어(최대 4코어, P/E core) 지원
- P core 2배 성능/3배 전력, E core 기본 성능/전력, 시동전력 모델 구현
- Gantt 차트 애니메이션 + Ready Queue 시각화 + 결과 테이블 + 전체 비교 뷰
- 다크 테마 GUI, 42개 자동화 테스트로 알고리즘 정확성 검증
- 엔진/GUI 완전 분리 아키텍처로 테스트 용이성 확보

### 2. Thanos 알고리즘의 의의

Thanos는 RR의 공정성을 유지하면서, 진행률이 높은 프로세스를 우선 완료하여 효율성을 개선하는 커스텀 알고리즘이다. 게임 매칭 서버처럼 "완료되어야만 가치가 발생하는" 시스템에서, 절반 이상 진행된 작업의 매몰 비용을 줄이는 데 효과적이다.

### 3. 한계점 및 개선 방향

- **멀티코어 Thanos**: 현재 코어 간 프로세스 마이그레이션은 미지원. 부스트된 프로세스를 고성능 코어로 이동시키는 전략이 가능
- **적응형 임계값**: 고정 50% 대신 빌드 유형별 최적 임계값 탐색
- **실제 데이터 검증**: 시뮬레이터의 이론적 결과를 실제 시스템 로그와 대조 검증
