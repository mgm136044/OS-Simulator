# 프로세스 스케줄링 시뮬레이터 — 발표 심층 대비 자료

> **목적:** 교수님과 학생들의 예리한 질문에 대비하기 위해 *프로젝트 전 영역*을 깊이 있게 정리. 단순 Q&A 모음이 아니라, **각 설계 결정의 이유와 그 결정이 만들어낸 결과**까지 추적한다.
>
> **사용 방법:** 발표 전날 한 번 정독하고, 발표 직전엔 §0(엘리베이터 피치) + §11(위험 답변 회피)만 다시 본다.

---

## 0. 발표 30초 요약 (엘리베이터 피치)

> "운영체제 6개 스케줄링 알고리즘을 P-core/E-core 멀티코어 환경에서 시뮬레이션하고, 간트차트·소비전력·가동률을 한 화면에서 비교하는 PyQt5 데스크톱 앱입니다.
>
> 이 중 'Thanos'는 제가 직접 설계한 알고리즘으로, **Round Robin을 기반으로 하되, 작업이 절반 이하 남으면 한 번에 한해 큐 맨 앞으로 부스트**해 일부 워크로드에서 완료 직전 작업을 더 빨리 회수하는 것을 목표로 합니다. 대상 시스템은 **이미지/영상 렌더링 서버**(예: 유튜브 트랜스코딩)이며, 작업량을 진행 중 측정 가능하고 soft real-time 특성을 가지는 환경에 적합합니다.
>
> 총 45개의 단위 테스트로 알고리즘 정확성과 P-core 도입 시 발견된 WT 음수 버그까지 회귀 방지하고 있습니다."

### 0.1 발표 대본 (5분 기준)

아래 문장은 그대로 읽어도 자연스럽게 이어지도록 만든 발표용 대본이다. 시간이 부족하면 각 문단 첫 문장만 말한다.

**도입 (30초)**

안녕하세요. 저는 운영체제의 대표적인 프로세스 스케줄링 알고리즘을 직접 시뮬레이션하고 시각화하는 데스크톱 앱을 만들었습니다. 이 프로젝트의 목적은 FCFS, RR, SPN, SRTN, HRRN 같은 교과서 알고리즘이 같은 입력에서 어떻게 다른 실행 순서와 성능 지표를 만드는지 눈으로 확인하는 것입니다. 여기에 P-core와 E-core가 섞인 멀티코어 환경, 전력 계산, 그리고 제가 설계한 커스텀 알고리즘인 Thanos를 추가했습니다.

**문제의식 (40초)**

기존 알고리즘은 각각 장단점이 뚜렷합니다. FCFS는 단순하지만 긴 작업이 앞에 오면 뒤의 짧은 작업이 오래 기다립니다. RR은 공정하지만 거의 끝난 작업도 새 작업과 똑같이 큐 뒤로 밀립니다. SPN이나 SRTN은 짧은 작업에 유리하지만 burst time을 정확히 알아야 하거나 선점이 잦아지는 문제가 있습니다. 그래서 저는 RR의 공정성을 유지하면서, 이미 절반 이상 진행된 작업은 한 번 더 빨리 마무리할 기회를 주는 Thanos 알고리즘을 설계했습니다.

**Thanos 설명 (60초)**

Thanos는 Round Robin 기반입니다. 기본적으로 time quantum만큼 실행하고, quantum이 끝났을 때 남은 작업량이 원래 burst time의 절반 이하이면 그 프로세스를 큐의 맨 앞으로 한 번만 보냅니다. 코드에서는 `boosted` set으로 이미 부스트를 받은 프로세스를 기록해서 무제한 부스트를 막습니다. 이 설계의 의도는 "거의 끝난 작업을 빨리 완료시켜 자원 회수를 앞당기되, 다른 작업의 기아는 막자"입니다. 따라서 Thanos가 모든 상황에서 가장 좋다는 주장은 하지 않습니다. 특정 워크로드, 특히 완료 직전 작업을 빨리 회수하는 것이 의미 있는 soft real-time 환경에서 효과를 기대하는 정책입니다.

**구현 구조 (60초)**

구현은 네 계층으로 나눴습니다. Process와 Processor는 데이터 모델이고, Scheduler 계층은 6개 알고리즘이 모두 같은 `schedule(processes, processors)` 인터페이스를 따릅니다. Engine의 Simulator는 스케줄러 결과를 GUI가 쓰기 쉬운 report dict로 바꿉니다. 마지막으로 PyQt5 GUI가 입력, 간트차트, Ready Queue, 결과 테이블, 알고리즘 비교 화면을 담당합니다. 이렇게 분리했기 때문에 GUI 없이도 테스트에서 스케줄러와 엔진을 독립적으로 검증할 수 있습니다.

**멀티코어와 전력 (50초)**

프로세서는 P-core와 E-core로 나눴습니다. P-core는 한 tick에 2 work를 처리하지만 3W를 소비하고, E-core는 한 tick에 1 work를 처리하지만 1W만 소비합니다. 그래서 burst time과 실제 CPU 점유 시간인 service_time을 분리했습니다. 예를 들어 P-core에서 BT 6인 작업은 실제로 3 tick만 점유합니다. 이 구분이 없으면 waiting time이 음수가 되거나 NTT가 1보다 작아지는 문제가 생깁니다. 전력은 timeline을 기준으로 코어별 busy tick과 시동전력을 합산해서 계산합니다.

**검증 (40초)**

테스트는 총 45개입니다. 알고리즘별 완료 시간과 평균 지표, P-core/E-core 스펙, 전력 계산, 멀티코어 병렬 실행, Thanos 부스트 동작을 확인합니다. 특히 P-core를 도입하면서 `WT = TT - BT` 공식을 그대로 쓰면 waiting time이 음수가 되는 버그가 있었고, 이를 `service_time` 기준으로 고치고 회귀 테스트를 추가했습니다.

**마무리 (30초)**

정리하면 이 프로젝트는 스케줄링 알고리즘을 단순히 표로 계산하는 것이 아니라, 멀티코어와 전력까지 포함해 시각적으로 비교할 수 있게 만든 시뮬레이터입니다. Thanos는 모든 알고리즘보다 우월하다는 주장이 아니라, RR 기반에서 완료 직전 작업을 한 번 앞당기는 정책을 실험해 본 커스텀 알고리즘입니다. 한계로는 컨텍스트 스위치 비용, 캐시, I/O, 메모리 사용량은 모델링하지 않았고, 이는 향후 확장 과제입니다.

### 0.2 Q&A 최우선 방어 답변 10개

발표 직전에는 이 표만 외워도 된다. 답변은 길게 설명하기보다 첫 문장을 먼저 말하고, 추가 질문이 오면 근거를 붙인다.

| 질문 | 첫 문장 답변 |
|------|-------------|
| Thanos가 RR보다 항상 좋은가? | 아닙니다. 특정 워크로드에서 완료 직전 작업을 앞당기는 정책이고, 항상 우월하다고 주장하지 않습니다. |
| SPN/SRTN이 더 좋은 것 아닌가? | SPN/SRTN은 burst time 또는 remaining time을 더 공격적으로 활용하지만, 예측 가능성이나 선점 비용 문제가 있습니다. |
| 왜 절반 이하에서 부스트하나? | 절반은 "이미 많이 진행된 작업"을 판단하는 직관적 기준이고, 최적 임계값은 워크로드별 실험 과제입니다. |
| 왜 부스트는 1회만 하나? | 무제한 부스트는 다른 작업의 기아를 만들 수 있어서, 공정성을 위해 한 번으로 제한했습니다. |
| 동일 BT면 RR과 같은가? | 꼭 같지 않습니다. 동일 BT라도 quantum 경계에서 절반 이하가 되면 Thanos는 appendleft 부스트를 수행합니다. |
| 실제 OS와 얼마나 비슷한가? | 실제 OS보다 훨씬 단순화했습니다. 이 프로젝트는 운영체제 개념을 실험하고 시각화하는 교육용 모델입니다. |
| P-core에서 왜 WT/NTT 계산이 달라졌나? | P-core는 한 tick에 더 많은 work를 처리하므로 BT가 아니라 실제 점유 tick인 service_time 기준으로 계산해야 합니다. |
| 전력 계산은 정확한가? | 실제 CPU 전력 모델은 아니고, 과제용 P/E-core 스펙을 기반으로 한 추상화된 계산입니다. |
| 알려진 버그나 한계는? | queue_snapshots는 같은 tick의 멀티코어 이벤트를 단일 key로 표현해 UI 애니메이션에 한계가 있습니다. |
| 메모리 절약을 측정했나? | 메모리 모델은 포함하지 않았습니다. 작업을 빨리 완료하면 자원 회수가 빨라질 수 있다는 설계 기대이고, 실측은 향후 과제입니다. |

### 0.3 질문 받을 때 말하는 순서

1. **결론 먼저**: "항상 좋지는 않습니다", "그 부분은 단순화했습니다"처럼 한 문장으로 답한다.
2. **근거 하나**: 코드 또는 OS 개념 하나만 붙인다. 예: `boosted` set, `service_time`, context switch cost.
3. **한계 인정**: 측정하지 않은 것은 측정하지 않았다고 말한다.
4. **확장 과제**: "다음 단계로는 X를 추가하면 검증할 수 있습니다"로 마무리한다.

---

## 1. 프로젝트 전체 구조

### 1.1 디렉토리 트리

```
process-scheduling-simulator/
├── src/
│   ├── main.py                  # PyQt5 엔트리포인트, QIcon 적용
│   ├── models/
│   │   ├── process.py           # Process 데이터클래스
│   │   └── processor.py         # Processor (P/E core), CoreType Enum
│   ├── schedulers/
│   │   ├── base.py              # BaseScheduler ABC, TimeSlot, ScheduleResult
│   │   ├── fcfs.py              # First Come First Served
│   │   ├── rr.py                # Round Robin
│   │   ├── spn.py               # Shortest Process Next
│   │   ├── srtn.py              # Shortest Remaining Time Next
│   │   ├── hrrn.py              # Highest Response Ratio Next
│   │   └── thanos.py            # 커스텀 (RR + 50% 부스트)
│   ├── engine/
│   │   ├── simulator.py         # Simulator: 스케줄러 + 리포트
│   │   └── power.py             # calc_power_summary
│   └── gui/
│       ├── main_window.py       # MainWindow, SCHEDULER_MAP
│       ├── process_input.py     # 좌측 입력 패널
│       ├── processor_config.py  # 프로세서 설정 패널
│       ├── gantt_chart.py       # 간트차트 + 애니메이션
│       ├── ready_queue_view.py  # Ready Queue 시각화
│       ├── result_table.py      # 결과 테이블
│       ├── comparison_view.py   # 6개 알고리즘 비교
│       └── theme.py             # Catppuccin 다크 테마
├── tests/                       # 45개 pytest
├── assets/icon.png              # 256×256 앱 아이콘
├── README.md
└── docs/
    ├── test-coverage.md         # 테스트 45개 전수 설명
    ├── presentation-qa.md       # Q&A 28선
    └── presentation-deep-dive.md # 본 문서
```

### 1.2 4계층 아키텍처 (의존성 방향)

```
┌─────────────────────────────────────────┐
│  Layer 4: GUI (PyQt5)                   │
│  main_window, gantt_chart, comparison   │
└─────────────────┬───────────────────────┘
                  │ 호출
                  ▼
┌─────────────────────────────────────────┐
│  Layer 3: Engine                        │
│  Simulator.run() → report dict          │
│  calc_power_summary()                   │
└─────────────────┬───────────────────────┘
                  │ 호출
                  ▼
┌─────────────────────────────────────────┐
│  Layer 2: Schedulers                    │
│  BaseScheduler.schedule(procs, cores)   │
│  → ScheduleResult(timeline, total_time, │
│     total_power, queue_snapshots)       │
└─────────────────┬───────────────────────┘
                  │ 사용
                  ▼
┌─────────────────────────────────────────┐
│  Layer 1: Models                        │
│  Process, Processor, TimeSlot           │
└─────────────────────────────────────────┘
```

**핵심 원칙:** 위 계층이 아래 계층에만 의존. 역방향 import 금지. **GUI를 떼어내도 스케줄러·엔진·모델은 단독 동작 가능** (pytest로 검증).

### 1.3 왜 이렇게 분리했는가

| 계층 분리 이유 | 구체적 이득 |
|---------------|------------|
| **Models 분리** | Process는 데이터만 보유, 행동 없음 → 어떤 스케줄러든 동일하게 사용 |
| **Schedulers ABC** | 6개 알고리즘이 동일 인터페이스(`schedule(procs, cores)`) → SCHEDULER_MAP에서 람다 1줄로 교체 가능 |
| **Engine 분리** | Simulator가 스케줄러 결과를 *report dict*로 변환 → GUI/CLI/테스트 모두 동일 형식 소비 |
| **GUI 분리** | PyQt5를 빼도 알고리즘은 동작. 대학원 진학 시 헤드리스 시뮬레이터로 재사용 가능 |

---

## 2. 데이터 모델 깊이 보기

### 2.1 Process 클래스 (src/models/process.py)

```python
@dataclass
class Process:
    pid: str
    arrival_time: int
    burst_time: int
    remaining_time: int = field(init=False)
    waiting_time: int = 0
    turnaround_time: int = 0
    completion_time: int = 0
    service_time: int = 0  # 실제 CPU 점유 tick (P-core에서 BT와 다름)

    @property
    def ntt(self) -> float:
        st = self.service_time if self.service_time > 0 else self.burst_time
        if st == 0:
            return 0.0
        return self.turnaround_time / st
```

#### 핵심 설계 결정 4가지

**① 왜 `service_time`을 별도로 두는가?**
- BT는 "총 작업량(work units)", service_time은 "실제 CPU 점유 시간(tick 수)"
- E-core: BT=6 → service_time=6 (1 work/tick)
- P-core: BT=6 → service_time=3 (2 work/tick)
- 이 구분이 없으면 P-core 작업의 NTT가 1 미만이 되어버려 "더 빨리 끝났다"가 음수 의미가 됨.

**② 왜 `remaining_time = field(init=False)`인가?**
- 사용자가 Process 생성 시 `remaining_time`을 지정할 수 없도록 강제
- `__post_init__`에서 BT로 자동 초기화 → 잘못된 초기 상태 진입 방지

**③ NTT의 폴백 로직 (`service_time > 0` else BT)**
- 비선점형(FCFS/SPN/HRRN)은 `service_time = exec_ticks` 일괄 설정 → 항상 service_time 사용
- 선점형(RR/SRTN/Thanos)은 매 tick `service_time += 1` 누적
- 만약 service_time 누적 전에 ntt를 호출하면 BT로 폴백 → 안전장치

**④ `reset()`의 존재 이유**
- 같은 Process 인스턴스를 여러 알고리즘에서 재사용할 때 상태 초기화
- 비교 모드(comparison_view)에서 6개 알고리즘 연속 실행 시 필요

### 2.2 Processor 클래스 — `_had_idle_tick`의 비밀

```python
class Processor:
    SPECS = {
        CoreType.P_CORE: {"work_per_tick": 2, "power_per_tick": 3.0, "startup_power": 0.5},
        CoreType.E_CORE: {"work_per_tick": 1, "power_per_tick": 1.0, "startup_power": 0.1},
    }

    def assign(self, pid: str):
        if self._had_idle_tick:
            self._needs_startup = True
        self.current_process = pid
        self.is_idle = False
        self._had_idle_tick = False

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
```

#### 핵심 메커니즘: 시동전력은 *진짜 idle 후*에만 부과

**시나리오 A** (시동전력 발생):
```
t=0~3: P1 실행 (busy)
t=3~5: idle (아무도 안 옴) → _had_idle_tick=True
t=5~8: P2 실행 → assign() 호출 시 _needs_startup=True → 첫 tick에 시동전력 부과
```

**시나리오 B** (시동전력 미발생, 즉시 컨텍스트 스위치):
```
t=0~2: P1 실행, quantum 끝
t=2: P1 release, P2 assign — idle tick 0회 → _had_idle_tick=False
t=2~4: P2 실행 → 시동전력 없음 (이미 켜져있던 코어)
```

**왜 이렇게 했는가?** 실제 CPU는 sleep state(C-state)에서 깰 때만 시동 비용이 든다. RR로 매 quantum마다 시동전력을 부과하면 전력 계산이 비현실적으로 부풀려진다.

### 2.3 TimeSlot / ScheduleResult (src/schedulers/base.py)

```python
@dataclass
class TimeSlot:
    pid: str          # "idle" 또는 프로세스 ID
    start: int
    end: int
    core_id: int = 0  # 어느 코어에서 실행됐는가

@dataclass
class ScheduleResult:
    timeline: list[TimeSlot]
    total_time: int
    total_power: float
    queue_snapshots: dict  # {time: [pid, ...]} — UI 애니메이션용
```

**왜 timeline이 핵심 자료구조인가?** 간트차트와 전력/가동률 계산은 timeline에서 파생된다. WT, TT, NTT는 각 스케줄러가 Process 필드에 직접 기록하고, Simulator가 이를 report dict로 묶는다.

**queue_snapshots의 한계 (정직 인정 포인트):** 단일 정수 키 → 멀티코어에서 같은 tick에 여러 배정이 일어나면 마지막 것만 남음. 영향 범위는 *UI 애니메이션 한정*, 스케줄링 결과 자체는 정확.

---

## 3. 6개 알고리즘 상세 분석

### 3.1 FCFS (비선점, src/schedulers/fcfs.py)

**알고리즘 본질:** 도착 순서대로 실행. 한 프로세스가 끝나야 다음.

**멀티코어 변형 (이 구현의 특이점):**
```python
# 가장 빨리 비는 코어에 도착순으로 배정
best_idx = min(range(num_cores),
               key=lambda i: (max(core_free_at[i], proc.arrival_time), i))
```
- 코어 free 시각 기준 *최소값* → 빠른 코어 선호
- tie-break은 코어 ID 낮은 순

**예리한 질문 포인트:**
- 진짜 FCFS는 단일 큐에서 한 명씩 빼는 건데, 이건 멀티코어 work-stealing처럼 보임 → 답: "교과서적 단일코어 FCFS의 멀티코어 자연스러운 확장. 도착 순서 보존 + 빈 코어 즉시 사용"

### 3.2 RR (선점, src/schedulers/rr.py)

**핵심 루프 구조 (tick-by-tick 시뮬레이션):**
```
while completed < n:
    1. 빈 코어에 ready_queue에서 popleft 배정
    2. 모든 코어 idle + 큐 빔 → 다음 도착까지 점프
    3. 1 tick 실행: work=min(work_per_tick, remaining), service_time+=1
    4. current_time += 1
    5. 도착 처리 (← 완료/선점 처리 *전*에)
    6. 완료/선점 처리 (quantum_used >= 2면 ready_queue.append)
```

**핵심 디테일:** **5번이 6번보다 먼저** 실행됨. 즉 *quantum 끝난 프로세스가 큐로 돌아갈 때, 같은 tick에 도착한 새 프로세스는 이미 큐에 들어와 있다.* 이는 교과서 RR의 표준 동작(새 도착이 우선).

**왜 quantum=2가 기본값인가?**
- quantum=1: P-core(work=2) 한 번에 2 work 처리 후 바로 컨텍스트 스위치 → 부담
- quantum=2: P-core 한 번에 4 work 처리, E-core 2 work 처리 → 균형
- quantum=5+: RR의 fairness 효과 사라짐

### 3.3 SPN (비선점, src/schedulers/spn.py)

**핵심 로직:**
```python
# earliest_free 시점에 도착한 미완료 프로세스 중 BT 가장 짧은 것 선택
proc = min(available, key=lambda p: (p.burst_time, p.arrival_time))
```

**예리한 질문 포인트:**
- "BT를 어떻게 미리 아는가?" → 교과서 가정: 사용자가 신고하거나 historical data로 추정. 본 시뮬레이터는 입력으로 받음. 실제 OS는 추정 어려움 → SPN의 실용적 한계.

### 3.4 SRTN (선점, src/schedulers/srtn.py)

**핵심 로직:**
```python
# 매 tick마다 선점 체크
shortest = min(ready_queue, key=lambda p: (p.remaining_time, p.arrival_time))
if shortest.remaining_time < proc.remaining_time:
    # 선점!
```

**예리한 질문 포인트:**
- "매 tick 선점 체크면 컨텍스트 스위치 폭증 아닌가?" → 답: 시뮬레이터는 비용 0으로 단순화. 실제로는 SRTN이 응답성 좋지만 오버헤드 큼.

### 3.5 HRRN (비선점, src/schedulers/hrrn.py)

**HRR(Highest Response Ratio) 공식:**
```python
def response_ratio(p):
    wt = earliest_free - p.arrival_time
    return (wt + p.burst_time) / p.burst_time
```
- **분자**: 대기 시간 + BT (= 응답 시간)
- **분모**: BT (정규화)
- WT가 클수록 ratio 증가 → **기아 방지** (오래 기다리면 우선순위 ↑)
- BT가 작을수록 ratio 증가 → **짧은 작업 선호** (SPN의 장점 유지)

**예리한 질문 포인트:**
- "HRRN은 비선점인데 멀티코어에서 어떻게 동작하는가?" → 답: earliest_free 시점에 결정. 코어마다 결정 시각이 다를 수 있어 이론적으로 완만한 근사 (코드 리뷰 문서에서 인정한 한계).

### 3.6 Thanos (선점, src/schedulers/thanos.py)

**RR과 다른 단 한 부분 (8줄):**
```python
elif state["quantum_used"] >= self.time_quantum:
    timeline.append(TimeSlot(...))
    half_threshold = proc.burst_time / 2
    if proc.remaining_time <= half_threshold and proc.pid not in boosted:
        ready_queue.appendleft(proc)
        boosted.add(proc.pid)
    else:
        ready_queue.append(proc)
```

#### 부스트 메커니즘 4가지 결정

**① `proc.burst_time / 2`를 매 quantum 마다 *재계산*하는 이유**
- 원래 BT는 변하지 않음 → 사실상 상수. 변수 처리해도 동작 같음.
- 직관: "원래 작업량의 절반 이하만 남았다"가 부스트 트리거

**② `boosted` set의 의미**
- "이 프로세스는 이미 부스트 한 번 받았다"
- 무제한 부스트 시 같은 프로세스가 quantum마다 계속 앞으로 가서 다른 프로세스 기아 발생
- 1회 제한 = "기회는 평등하게, 한 번씩"

**③ `appendleft` vs 우선순위 큐**
- `deque.appendleft`: O(1)
- heapq: O(log n)
- 부스트는 "한 번만 빠르게 앞으로 가면 끝" → 정렬 자료구조 불필요

**④ 부스트 못 받는 경우 그냥 append (큐 뒤)**
- 일반 RR과 동일 동작 → 부스트 조건 미충족 시 fallback

#### 부스트 효과 시뮬레이션 예 (test_thanos_boost.py)

```
입력: P1(BT=3), P2(BT=6), quantum=2

t=0: ready=[P1, P2], P1 실행
t=2: P1 quantum 끝. remaining=1 ≤ 3/2=1.5 → 부스트!
     ready=[P1, P2] (P1 appendleft, boosted={P1})
     P1 실행
t=3: P1 완료 (1 work 더 처리)
     ready=[P2], P2 실행
...
```

**부스트 없었으면:** t=2에 P1을 큐 뒤로(append) → ready=[P2, P1]. P2 실행 후 P1 → P1 완료 시각 더 늦음.

---

## 4. 멀티코어 동작 메커니즘

### 4.1 비선점형 멀티코어 (FCFS/SPN/HRRN)

**공통 패턴:**
```python
core_free_at = [0] * num_cores  # 각 코어가 비는 시각
while not all_done:
    earliest_free = min(core_free_at)
    available = [도착한 미완료 프로세스]
    if not available: jump to next_arrival
    proc = 선택(available)  # FCFS:도착순, SPN:BT, HRRN:HRR
    best_idx = min(코어, key=비는 시각)
    start = max(core_free_at[best_idx], proc.arrival_time)
    end = start + ceil(BT / work_per_tick)
    core_free_at[best_idx] = end
```

**왜 tick 단위가 아닌 *결정 단위* 시뮬레이션?**
- 비선점은 한 번 시작하면 끝까지 → tick 진행 의미 없음
- 결정 시점만 보면 충분 → O(n) 또는 O(n²)로 빠름

### 4.2 선점형 멀티코어 (RR/SRTN/Thanos)

**tick 단위 시뮬레이션 필요 이유:**
- quantum 만료, remaining_time 비교, 도착 처리 → 매 tick 발생
- core_state[ci]에 현재 프로세스, 시작 시각, quantum_used 저장

**병렬 실행:**
```python
for ci in range(num_cores):
    state = core_state[ci]
    if state is None:
        processors[ci].tick()  # idle tick (전력=0)
        continue
    # 1 tick 실행
    work = min(core.work_per_tick, proc.remaining_time)
    proc.remaining_time -= work
    proc.service_time += 1
```

**P-core와 E-core 혼합:** P-core가 한 tick에 2 work 처리 → 같은 BT라도 P-core 쪽이 빨리 끝남.

### 4.3 코어 선택 정책 (예리한 질문 대비)

**현재 구현:** 가장 일찍 비는 코어 → tie-break은 ID 낮은 순.
- 코어 ID 0이 P-core면 P-core 우선 사용 → 전력 비효율 가능
- 실제 OS(Linux EAS, Apple Scheduler)는 작업 크기·전력 정책 종합

**솔직한 한계:** 본 시뮬레이터는 작업 크기 기반 코어 배정 정책 미구현. 향후 확장 과제.

---

## 5. 전력 모델

### 5.1 시동전력의 의미

| 코어 | power_per_tick | startup_power | 의미 |
|------|---------------|---------------|------|
| P | 3.0 W | 0.5 W | 한 번 켜지면 전력 폭증, 매 tick 3W |
| E | 1.0 W | 0.1 W | 켜질 때 비용 적음, 매 tick 1W |

### 5.2 `_had_idle_tick` 플래그의 역할 (중요!)

**문제:** RR로 매 quantum 컨텍스트 스위치마다 시동전력 부과하면 전력 비현실적으로 부풀려짐.

**해결:** "실제 idle tick이 있었는가"를 추적.

```
예시: RR로 P1, P2 번갈아 실행 (둘 다 ready)
t=0~2: P1 실행, idle 없음
t=2: P1 release (큐 뒤), P2 assign (큐 앞에서)
     → assign() 시 _had_idle_tick=False (직전 tick에 P1 실행 중이었음)
     → _needs_startup=False → 시동전력 미부과
t=2~4: P2 실행, 시동전력 없이 1.0W/tick
```

**반대 예시:**
```
t=0~3: P1 실행, t=3에 완료
t=3~5: 큐 비어있음, 코어 idle 2 tick
       → tick() 호출 시 _had_idle_tick=True
t=5: P2 도착, assign()
     → _needs_startup=True
     → 첫 tick에 시동전력 0.1W 부과
```

### 5.3 전력 계산의 *이중 정의* 문제 (코드 리뷰에서 발견)

- **스케줄러 내부:** `total_power` 누적 (timeline + 시동 합산)
- **engine/power.py:** `calc_power_summary` (timeline 기준 사후 재계산)

**simulator.py는 후자만 노출**:
```python
power_summary = calc_power_summary(processors, result.timeline, result.total_time)
```

**왜 이중 정의가 남아있는가?** 스케줄러 내부 합은 디버깅용·테스트용. UI/리포트는 calc_power_summary 단일 소스. 향후 통합 검토 필요 (정직한 한계).

---

## 6. GUI 데이터 흐름

### 6.1 사용자 입력 → 결과 표시 (단일 실행)

```
1. ProcessInputPanel (좌측)에서 [▶ 실행] 클릭
   └─ run_requested 시그널 발생
2. MainWindow._on_run() 호출
   ├─ Process 인스턴스 생성
   ├─ Processor 인스턴스 생성
   ├─ SCHEDULER_MAP[algo](quantum)으로 스케줄러 생성
   └─ Simulator.run(scheduler, processes, processors) 호출
3. report dict 반환
   ├─ algorithm, total_time, timeline
   ├─ processes (pid/at/bt/wt/tt/ntt)
   ├─ metrics (avg_wt, avg_tt, avg_ntt)
   ├─ power (total, per-core)
   └─ queue_snapshots
4. 결과 분배:
   ├─ GanttChart.set_data()
   ├─ ResultTable.update_results()
   └─ ReadyQueueView (시간 변경 시그널 연결)
```

### 6.2 비교 모드

```
ProcessInputPanel [📊 비교] 버튼
  └─ MainWindow._on_compare()
     └─ 6개 알고리즘 순회, 각각 새 Process 인스턴스로 실행
     └─ ComparisonView.set_results(reports)
        └─ 요약 테이블 + 미니 간트차트 6개 표시
```

**중요 디테일:** 비교 모드에서 *새 Process 인스턴스*를 매번 생성. 같은 인스턴스 재사용 시 reset() 필수.

### 6.3 간트차트 애니메이션 (시간 진행)

```python
# gantt_chart.py
self.timer = QTimer()
self.timer.setInterval(400)  # 400ms마다 1 tick 진행
self.timer.timeout.connect(self._tick)

def _tick(self):
    self.canvas.animated_time += 1
    self.canvas.update()
    self.time_changed.emit(self.canvas.animated_time)
```

**ReadyQueueView 연결:** time_changed 시그널 → MainWindow._update_ready_queue → queue_snapshots에서 현재 시각 이하의 가장 가까운 스냅샷 찾아 표시.

---

## 7. 테스트 전략

### 7.1 45개 테스트 분포

| 영역 | 테스트 수 | 핵심 검증 |
|------|----------|----------|
| Process 모델 | 4 | NTT 계산, service_time, reset |
| Processor 모델 | 8 | P/E 스펙, 시동전력 idle/no-idle |
| 6개 스케줄러 | 19 (각 3~4) | timeline, 메트릭, 이름, 부스트 |
| 전력 계산 | 3 | 단일 E, 혼합, idle |
| Simulator 엔진 | 3 | run, metrics, process 디테일 |
| 멀티코어 | 8 | 병렬, P-core, RR, SPN, Thanos, WT 음수 방지 |

### 7.2 발견된 버그와 회귀 방지 테스트

| 버그 | 발견 시점 | 방지 테스트 | 해결책 |
|------|----------|------------|--------|
| **WT 음수** | P-core 도입 후 | #4, #44, #45 | NTT·WT를 service_time 기준으로 계산 |
| **시동전력 중복** | 컨텍스트 스위치 검증 시 | #11 | `_had_idle_tick` 플래그 |
| **멀티코어 NTT 0.5** | P-core BT=6 단일 작업 | #44 | NTT = TT / service_time |

**WT 음수 버그 상세:**
- 원래 공식: `WT = TT - BT`
- P-core BT=6: TT=3 (실행 3 tick), BT=6 → WT = 3 - 6 = **-3** (불가능!)
- 수정: `WT = TT - service_time` = 3 - 3 = 0 ✓

### 7.3 테스트 커버리지 갭 (정직 인정)

미테스트 영역:
- 같은 시각 멀티코어 동시 배정 시 queue_snapshots 덮어쓰기
- 비교 모드 UX 엣지케이스
- BT=0 프로세스 (GUI에서 막지만 라이브러리 방어 없음)
- 4개 코어 + 15개 프로세스 같은 최대 부하

---

## 8. 알려진 한계 (정직 인정 포인트)

### 8.1 시뮬레이터 추상화의 한계

| 항목 | 본 구현 | 실제 OS |
|------|---------|---------|
| 컨텍스트 스위치 비용 | 0 | 수십~수백 μs |
| 캐시 무효화 | 미모델링 | 코어 이동 시 큰 비용 |
| I/O 대기 | 미모델링 | CPU bound vs I/O bound 구분 |
| 메모리 사용량 | 미모델링 | 페이지 폴트, 스왑 등 |
| 시간 단위 | 1초 정수 | ns~μs 단위 |
| 우선순위 | 알고리즘 단일 | nice/realtime 우선순위 |

### 8.2 코드 품질 잔여 이슈

- `queue_snapshots` 단일 정수 키 → 멀티코어 덮어쓰기 (UI 한정)
- `ScheduleResult.queue_snapshots: dict` → `dict[int, list[str]]`로 좁히면 좋음

### 8.3 알고리즘 자체의 한계

| 알고리즘 | 한계 |
|---------|------|
| FCFS | Convoy effect (긴 작업 뒤 짧은 작업 대기) |
| RR | quantum 선택에 민감, fairness vs 응답성 trade-off |
| SPN | BT 사전 예측 필요 (현실적 어려움), 긴 작업 기아 |
| SRTN | 컨텍스트 스위치 폭증 |
| HRRN | BT 필요, 멀티코어에서 결정 시각 문제 |
| Thanos | 동일 BT 작업에서도 부스트 때문에 RR과 실행 순서가 달라질 수 있음, 부스트 1회 한정 |

---

## 9. 예리한 질문 50선

> §1~§8 내용을 바탕으로 *교수님과 학생들이 던질 가장 날카로운 질문*을 추출. 각 질문에 **약점 분석 한 줄 + 답변 가이드**.

### 9.1 알고리즘 이론 (12문)

**Q1. Thanos 부스트 조건이 `remaining ≤ BT/2`인 이유? 이게 최적인가?**
- 약점: 임계값 1/2은 직관일 뿐 수학적 최적성 증명 없음
- 답변: "직관적 균형점. 1/4은 부스트 발생이 적고, 3/4은 너무 많은 작업이 일찍 부스트되어 일반 RR의 공정성을 크게 바꿀 수 있습니다. 워크로드별 최적값은 향후 실험 과제입니다."

**Q2. 부스트 1회 제한이 오히려 알고리즘을 약화시키는 것 아닌가?**
- 약점: 두 번째 절반 진행 후 또 부스트 받을 자격 있는데 못 받음
- 답변: "기아 방지가 1차 목표. 두 번째 부스트가 필요할 정도로 긴 작업은 SPN/SRTN이 더 적합. 단순함 + 공정성 trade-off"

**Q3. Thanos가 SPN보다 평균 TT가 *항상* 짧다고 증명할 수 있나?**
- 약점: 증명 없음. 워크로드 의존
- 답변: "증명 불가. SPN은 BT 정확히 알면 평균 TT 최소 보장. Thanos는 *현실적 적용 가능성*에 우위"

**Q4. RR의 quantum과 Thanos의 quantum 같은 값(2)으로 비교하는 게 공정한가?**
- 약점: quantum=2가 RR에 최적이 아닐 수 있음
- 답변: "동일 조건 비교로 부스트 효과 *분리*. quantum 별도 튜닝은 다른 실험"

**Q5. SPN 비선점인데 멀티코어에서 어떻게 동작하는가? 이론 정의에 어긋나지 않나?**
- 약점: 클래식 SPN은 단일 큐 가정
- 답변: "다중 코어로 자연 확장. earliest_free 시점에 결정. 이론 변경이 아니라 멀티코어 적응"

**Q6. HRRN의 응답비 분모가 BT인 이유? 왜 service_time이 아닌가?**
- 약점: P-core에서는 실제 점유 tick(service_time)이 BT보다 작을 수 있어 디자인 일관성 의문
- 답변: "HRRN의 선택 기준은 교과서 정의인 BT를 그대로 사용합니다. 다만 완료 후 WT/NTT 계산은 P-core 속도를 반영하기 위해 service_time 기준으로 처리합니다."

**Q7. SRTN과 Thanos의 본질 차이는?**
- 약점: 둘 다 remaining_time 본다는 점 같음
- 답변: "SRTN은 매 tick 비교(컨텍스트 스위치 폭증), Thanos는 quantum boundary에서만 1회 체크 + 부스트 1회 한정"

**Q8. FCFS의 멀티코어 변형이 진짜 FCFS인가? Work-stealing 아닌가?**
- 약점: 도착 순서대로 빈 코어에 배정 = 일종의 분배
- 답변: "단일 코어 FCFS의 자연 확장. 도착 순서 보존이 핵심. 코어 분배는 OS의 역할"

**Q9. 모든 프로세스 BT가 동일하면 Thanos는 RR과 동일한가?**
- 약점: 직관적으로는 동일해 보이지만, 구현상 절반 이하 조건에 도달하면 appendleft 부스트가 걸림
- 답변: "아닙니다. 동일 BT라도 quantum 경계에서 remaining ≤ BT/2가 되면 부스트가 발생해 RR과 실행 순서가 달라질 수 있습니다. Thanos의 핵심은 동질/이질 여부보다 '절반 이하 남은 작업을 한 번 앞당기는 정책'입니다."

**Q10. 부스트 받은 프로세스가 부스트 직후 또 quantum 만료되면?**
- 약점: 그럼 그냥 큐 뒤로 (else 분기) → 부스트 효과 1 quantum만 지속
- 답변: "의도된 동작. 부스트 = '한 번의 빠른 출발 기회'. 그 후엔 일반 RR"

**Q11. 부스트 조건 비교가 `<=`인데 정확히 BT/2면? (예: BT=4, remaining=2)**
- 약점: 경계값 처리 불명확
- 답변: "코드: `proc.remaining_time <= half_threshold`. 정확히 절반이면 부스트 OK. 경계 포함 의도"

**Q12. Thanos가 부스트로 처리량(throughput)이 증가하나?**
- 약점: 처리량 = 단위 시간 당 완료 작업 수. 스케줄링만으로 증가 어려움
- 답변: "처리량 증가는 *조건부*. 작업 완료 시 자원(메모리) 회전이 빨라지면 후속 작업 처리 능력 ↑. 단순 스케줄링 자체는 throughput 불변"

### 9.2 데이터 모델 / 구현 (10문)

**Q13. NTT 폴백이 service_time→BT인 이유?**
- 약점: 서로 다른 분모로 NTT 비교 시 불일치
- 답변: "선점형 누적 전 호출 시 안전장치. 모든 알고리즘 종료 후엔 service_time 확정 → 일관"

**Q14. service_time을 누적하지 않는 비선점형(FCFS/SPN/HRRN)은 어떻게 채우나?**
- 약점: 코드 분기됨
- 답변: "비선점은 결정 시 `proc.service_time = exec_ticks` 일괄 설정. 선점은 매 tick `+= 1`. 의도된 분리"

**Q15. Process가 dataclass인 이유?**
- 약점: 일반 클래스 대비 이점 설명 필요
- 답변: "필드 자동 생성 + 가독성. 스케줄링 로직은 데이터 + 메서드 분리 명확. ntt만 @property로 동적 계산"

**Q16. Processor의 SPECS를 클래스 변수로 둔 이유?**
- 약점: 인스턴스마다 같은 값 → 클래스 변수 적절 vs 상수 모듈 변수
- 답변: "P/E 매핑이 Processor 책임. 외부 노출 없음. 향후 코어 타입 추가 시 SPECS만 확장"

**Q17. `@dataclass`의 `field(init=False)` 사용 이유? 그냥 `__init__`에서 초기화하면 안 되나?**
- 약점: dataclass 패턴 일관성
- 답변: "사용자가 remaining_time 지정 못 하게 강제. __post_init__에서 BT로 자동. 잘못된 초기 상태 방지"

**Q18. `total_power` 계산이 스케줄러 내부와 calc_power_summary 두 곳? 어느 게 진짜?**
- 약점: 이중 정의 (코드 리뷰 지적)
- 답변: "UI는 calc_power_summary 단일 소스. 스케줄러 내부는 디버그용. 향후 통합 과제"

**Q19. timeline의 `core_id` 기본값이 0인 이유? 멀티코어 도입 후 의도는?**
- 약점: 단일 코어와 멀티 코어가 같은 자료구조 사용
- 답변: "단일 코어는 core_id=0 묵시 사용. 멀티 코어는 명시 지정. 하위호환"

**Q20. queue_snapshots가 단일 정수 키인 이유? 같은 시각 여러 이벤트는?**
- 약점: 멀티코어 동시 배정 시 덮어씀 (코드 리뷰에서 지적)
- 답변: "교육용 UI 단순화. 실제 스케줄링 결과는 timeline에 정확. snapshots는 보조"

**Q21. PyQt5 시그널/슬롯 구조 — MVC 패턴과의 관계는?**
- 약점: PyQt5 패턴 명확화
- 답변: "Model(report dict) - View(GanttChart 등) - Controller(MainWindow). 시그널은 Observer 패턴"

**Q22. `_make_processors`가 람다·튜플로 된 이유?**
- 약점: 함수 시그니처 단순화
- 답변: "GUI에서 (id, type) 튜플로 전달 → Processor 인스턴스 변환. 순수 변환 함수"

### 9.3 멀티코어 (8문)

**Q23. 코어 ID 0이 P-core면 항상 P 우선 사용 → 전력 비효율?**
- 약점: 작업 배정 정책 미구현
- 답변: "맞음. 본 구현은 ID 낮은 순. 실제 OS는 작업 크기·전력 정책 종합. 향후 확장 과제"

**Q24. RR에서 같은 tick에 여러 코어 quantum 끝나면 ready_queue 입출 순서는?**
- 약점: 결정성(determinism) 의문
- 답변: "코어 ID 낮은 순으로 처리 (for ci in range(num_cores)). 결정적이지만 OS 실제 동작과는 다를 수 있음"

**Q25. P-core와 E-core가 *동일 BT 작업*을 받으면 P가 먼저 끝남. 이게 공정한가?**
- 약점: 코어 간 fairness vs throughput
- 답변: "성능 차이 자체가 P/E 의도. fairness는 작업 *배정* 시 고려할 일이지 코어 *속도*가 아님"

**Q26. P-core 1개 + E-core 1개 환경에서 SRTN 돌리면 어떻게 되나?**
- 약점: 작업 크기 vs 코어 능력 매칭
- 답변: "SRTN은 remaining 짧은 것 P/E 무관 짧은 곳으로. 본 구현은 코어 ID 우선. 최적 매칭은 별도 정책 필요"

**Q27. queue_snapshots 멀티코어 덮어쓰기 — 영향 범위?**
- 약점: 알려진 버그
- 답변: "UI 애니메이션 한정. 스케줄링 결과(timeline, 메트릭)는 정확. 향후 (time, core_id) 복합 키로 개선"

**Q28. 4개 코어 모두 사용 시 메모리 사용량은?**
- 약점: 메모리 모델 미구현
- 답변: "본 시뮬레이터는 메모리 미모델링. 코어 수와 메모리 사용은 무관"

**Q29. 멀티코어에서 평균 TT가 단일코어 대비 *반*이 되는가?**
- 약점: 단순 산수 문제로 보이지만 도착 시간·동기화 영향 있음
- 답변: "이상적 병렬화 시 ~1/n. 실제는 도착 시간·작업 크기 의존. 약한 작업이 약한 코어에 가면 효과 감소"

**Q30. 모든 코어가 idle이면 시간 점프 처리 — 무한 루프 안 되나?**
- 약점: 종료 조건 명확화
- 답변: "while completed < n + 빈 큐 + 미도착 처리 시 break. idx == n이면 루프 종료. 무한 루프 불가능"

### 9.4 전력 / 성능 (6문)

**Q31. 시동전력이 0.1W vs 0.5W로 작은 이유?**
- 약점: 임의 값으로 보일 수 있음
- 답변: "과제 명세에서 제공된 값. 실제 CPU sleep state 진입 비용을 단순화한 모델"

**Q32. P-core가 항상 더 많은 전력 소비 — E-core 사용해야 절약?**
- 약점: 성능 vs 전력 trade-off
- 답변: "맞음. 같은 BT라도 P:3W×3tick=9W vs E:1W×6tick=6W. 짧은 작업은 P가 빨라 총 시간 단축, 긴 작업은 E가 전력 효율"

**Q33. 가동률(utilization) 100% 초과 가능?**
- 약점: 정의 명확화
- 답변: "busy_ticks / total_time. 항상 ≤ 100%. timeline 슬롯 길이 합 ≤ total_time"

**Q34. 전력 그래프가 시간에 따라 변하는 모습은?**
- 약점: 시간별 전력 시각화 없음
- 답변: "본 시뮬레이터는 *총 전력*만 표시. 시간별 그래프는 향후 확장. timeline에서 도출 가능"

**Q35. 부동소수점 합산 오차 — 0.1W를 100번 더하면 정확히 10W?**
- 약점: IEEE 754 누적 오차
- 답변: "round(power, 2)로 표시 시 보정. 테스트는 정확한 기댓값(2.1, 3.1)으로 검증"

**Q36. `calc_power_summary`가 스케줄러 끝난 후 호출 — 시뮬레이션 중 전력 모니터링은?**
- 약점: 사후 계산만 가능
- 답변: "현재는 사후. tick별 callback 추가로 실시간 모니터링 확장 가능"

### 9.5 비교 / 공정성 (6문)

**Q37. SPN은 BT를 미리 알고, 다른 알고리즘은 모름 — 공정한 비교인가?**
- 약점: SPN의 *치트* 가정
- 답변: "SPN은 *오라클* 비교 기준. 실제 적용 어려움 인정. Thanos는 동일 정보 없이 진행 중 측정만 사용"

**Q38. 동일 입력 4개 프로세스로 비교 — 단일 시나리오의 일반화 위험?**
- 약점: 한 가지 케이스로 결론 내림
- 답변: "발표용 데모. 본 시뮬레이터는 사용자가 임의 입력 가능 → 다양한 시나리오 비교"

**Q39. 평균 TT만 비교하면 불공평. 분산은?**
- 약점: 분산·최악값 미고려
- 답변: "맞음. 평균뿐 아니라 max(TT)도 봐야 fairness 평가. 본 시뮬레이터 GUI는 평균만 표시. 표 데이터로 max 도출 가능"

**Q40. Gantt 차트로 *시각적* 비교만 가능. 정량 분석 도구는?**
- 약점: 분석 깊이 한계
- 답변: "report dict로 모든 메트릭 추출 가능. CSV 익스포트는 향후 확장"

**Q41. 6개 알고리즘 비교 시 *우열 결론*을 내릴 수 있는가?**
- 약점: 알고리즘별 적용 시나리오 다름
- 답변: "단일 우열 불가. 워크로드별 적합성 다름. 본 시뮬레이터는 *비교 도구*이지 *우열 판정*이 아님"

**Q42. Thanos가 다른 5개보다 우월하다는 주장의 근거?**
- 약점: 우월성 증명 부족
- 답변: "우월하지 않음. *특정 시나리오(soft real-time + 완료 직전 작업을 빨리 회수하고 싶은 상황)*에서 평균 TT 단축과 자원 회전을 기대할 수 있습니다. 그 외에는 RR 수준이거나 더 나쁠 수 있습니다."

### 9.6 실제 OS와의 차이 (5문)

**Q43. Linux CFS(Completely Fair Scheduler)와 Thanos의 차이?**
- 약점: 실제 OS 비교 깊이
- 답변: "CFS는 vruntime 기반 가중 fairness. red-black tree로 O(log n) 선택. Thanos는 단순 deque + 1회 부스트. 교육용 vs 프로덕션"

**Q44. MLFQ(Multi-Level Feedback Queue)와 Thanos의 차이?**
- 약점: 다단계 큐 vs 단일 큐
- 답변: "MLFQ는 *우선순위 자동 조정* (CPU bound는 강등). Thanos는 *진행률 기반 부스트* 1회. 다른 철학"

**Q45. 실제 유튜브 트랜스코딩 서버는 어떤 스케줄러를 쓸까?**
- 약점: 추측 답변 위험
- 답변: "공개 자료 부족. 일반적으로 Kubernetes job queue + priority class. 본 시뮬레이터는 *원리적 비유*"

**Q46. ARM big.LITTLE 아키텍처의 실제 스케줄링과 본 P/E 모델 차이?**
- 약점: 실제 EAS(Energy Aware Scheduler) 복잡성
- 답변: "EAS는 작업 크기·온도·전력 정책 종합. 본 모델은 단순 work_per_tick 차이만. 교육 목적 단순화"

**Q47. 실시간 OS(RTOS)에서 Thanos 적용 가능한가?**
- 약점: hard real-time vs soft real-time
- 답변: "hard RTOS는 deadline 보장 필요 → Thanos 부적합. soft real-time(렌더링 등)에는 가능. RTOS는 EDF/RM 등 별도 알고리즘"

### 9.7 발표/시연 관련 (3문)

**Q48. 시연 중 알고리즘 한 번 실행에 몇 초 걸리나?**
- 답변: "본 시뮬레이터 자체는 즉시 (ms 단위). 간트차트 애니메이션은 400ms/tick → total_time × 0.4초"

**Q49. PyQt5가 아닌 웹(Flask/Streamlit)으로 만들었다면?**
- 답변: "PyQt5는 데스크톱 네이티브 → 빠른 반응. 웹은 배포 쉬움. 본 과제는 단일 머신 시연이라 PyQt5 선택"

**Q50. 코드량은? 개발 기간은?**
- 답변: "현재 기준 src/ 약 1,900줄, tests/ 약 660줄입니다. 핵심 알고리즘은 1주, GUI + 비교 + 멀티코어 + 전력은 추가 2주 정도 걸렸습니다."

---

## 10. 발표 시연 시나리오 (3분 데모)

### 10.0 시연 전 준비

시연은 실수할 수 있으므로 입력값을 미리 정해 둔다. 아래 값은 테스트에서 검증된 값과 맞아 발표 중 설명하기 쉽다.

| 용도 | 입력 |
|------|------|
| 기본 FCFS 설명 | P1(AT=0,BT=3), P2(AT=1,BT=5), P3(AT=3,BT=2), P4(AT=5,BT=4) |
| Thanos 부스트 설명 | P1(AT=0,BT=3), P2(AT=0,BT=6) |
| 멀티코어 설명 | P-core 1개 + E-core 1개, 기본 FCFS 입력 재사용 |

시연 중 말할 핵심 문장:

> "지금 보시는 간트차트는 단순 결과표가 아니라, 각 프로세스가 어느 코어에서 몇 초부터 몇 초까지 실행됐는지를 timeline으로 시각화한 것입니다."

> "Thanos는 RR처럼 돌다가, 절반 이하 남은 작업을 한 번만 큐 앞으로 보내는 차이가 있습니다."

> "P-core는 빠르지만 전력을 더 쓰고, E-core는 느리지만 전력 효율이 좋습니다. 그래서 완료 시간과 소비전력을 같이 봐야 합니다."

### 10.1 시연 1: 단일 알고리즘 (FCFS)
1. P1(0,3), P2(1,5), P3(3,2), P4(5,4) 직접 입력
2. 코어는 기본 E-core 1개 유지
3. FCFS 선택 → 실행
4. 결과 테이블 보여주기: avg_wt=3.0, avg_tt=6.5
5. 말할 내용:

> "FCFS는 도착 순서대로 실행되기 때문에 구현과 해석이 가장 단순합니다. 대신 앞쪽에 긴 작업이 있으면 뒤 작업이 기다리는 convoy effect가 생길 수 있습니다. 이 결과를 기준선으로 삼고 다른 알고리즘과 비교하겠습니다."

### 10.2 시연 2: Thanos 부스트 (핵심)
1. 전체 제거 후 P1(AT=0,BT=3), P2(AT=0,BT=6) 입력
2. RR 선택 → 실행 → P1 완료 시각 확인
3. Thanos 선택 → 실행 → P1이 t=3에 완료되는 것 확인
4. 말할 내용:

> "RR에서는 quantum이 끝난 작업이 일반적으로 큐 뒤로 갑니다. Thanos는 여기서 남은 시간이 원래 작업량의 절반 이하이면 한 번만 큐 앞으로 보냅니다. 이 예시에서는 P1이 거의 끝난 상태라 바로 한 번 더 실행되고, 그래서 먼저 완료됩니다."

질문이 들어오면 덧붙일 내용:

> "이것이 항상 좋은 것은 아닙니다. 대신 완료 직전 작업을 빨리 회수하고 싶은 워크로드에서 의미가 있는 정책입니다."

### 10.3 시연 3: 멀티코어 + 전력
1. 기본 4개 프로세스 입력으로 복귀
2. Core 0은 P-core, Core 1은 E-core로 설정
3. Thanos 또는 FCFS 실행
4. P/E 코어가 다른 행에 표시되는 것 보여주기
5. 결과 테이블의 *코어별 전력·가동률* 강조
6. 말할 내용:

> "P-core는 한 tick에 2 work를 처리해서 같은 BT라도 더 빨리 끝낼 수 있습니다. 하지만 tick당 전력은 더 큽니다. 그래서 이 시뮬레이터는 단순히 수행 시간만 보는 것이 아니라, 코어별 전력과 가동률도 같이 보여줍니다."

### 10.4 시연 4: 비교 모드 (마무리)
1. 동일 입력 → [📊 비교] 버튼
2. 6개 알고리즘 미니 간트차트 한 화면
3. 평균 WT/TT/NTT 비교표
4. 말할 내용:

> "마지막으로 비교 모드는 같은 입력을 6개 알고리즘에 각각 독립적으로 실행합니다. 그래서 평균 WT, 평균 TT, 평균 NTT를 한 화면에서 비교할 수 있습니다. 여기서 중요한 건 특정 알고리즘이 항상 최고라는 결론이 아니라, 입력과 목적에 따라 결과가 달라진다는 점입니다."

---

## 11. 위험 답변 회피 표현집

### 11.1 절대 하지 말아야 할 답변

| ❌ 위험 답변 | ✅ 안전 답변 |
|------------|-------------|
| "그냥 그렇게 했어요" | "직관적 균형점이며, 실험적 최적값은 향후 과제입니다" |
| "측정해봤는데 더 빨라요" (실제 측정 안 했을 때) | "이론적 기대치이며 실측은 향후 과제입니다" |
| "RR보다 *항상* 좋아요" | "*특정 워크로드*에서 평균 TT 단축을 기대할 수 있지만, 항상 우월하지는 않습니다" |
| "실제 유튜브가 이런 식이에요" | "원리적 비유이며, 실제 시스템은 더 복잡합니다" |
| "버그 없습니다" | "알려진 한계로 X가 있고, Y는 향후 개선 과제입니다" |

### 11.2 모르는 질문 받을 때 대처

**Step 1: 솔직 인정** — "그 부분은 제가 깊이 있게 다루지 못했습니다"
**Step 2: 추측 대신 추론** — "다만 X 원리상 Y일 것으로 보입니다"
**Step 3: 향후 검토 약속** — "흥미로운 지적이라 추가 조사하겠습니다"

### 11.3 공격적 질문 받을 때

| 질문 톤 | 답변 전략 |
|---------|----------|
| "이건 잘못된 거 아니에요?" | "지적 감사합니다. 제가 X 측면에서 단순화했고, 그로 인해 Y 한계가 있습니다" |
| "왜 이걸 안 했어요?" | "범위 한정 때문에 제외했습니다. Z 시점에 추가하면 좋을 것 같습니다" |
| "다른 사람이 이미 한 거 아니에요?" | "비슷한 선행 연구가 있을 것입니다. 제 기여는 X 부분의 구체화입니다" |

### 11.4 시간 부족할 때 답변 압축

**3-2-1 구조:**
- **3초 결론**: "한 마디로 X입니다"
- **2문장 근거**: "왜냐하면 Y이고 Z이기 때문입니다"
- **1제안 마무리**: "추가 검증으로 W 가능합니다"

---

## 마무리: 발표 직전 체크리스트

- [ ] §0 엘리베이터 피치 1번 소리내어 연습
- [ ] §3.6 Thanos 부스트 메커니즘 8줄 코드 외우기
- [ ] §9 가장 위험한 5개 질문 답변 손에 익히기 (Q1, Q3, Q9, Q23, Q42)
- [ ] §11 위험 답변 표현집 한 번 더 보기
- [ ] 시뮬레이터 한 번 실행해 GUI 정상 동작 확인
- [ ] 노트북 풀충전, 어댑터 챙기기

**핵심 마인드셋:** *"내가 만든 것의 한계를 누구보다 잘 안다"*가 최강의 방어. 우물쭈물 옹호보다 *솔직한 인정 + 향후 과제 제시*가 점수가 높다.
