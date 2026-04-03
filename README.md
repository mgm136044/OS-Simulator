# 프로세스 스케줄링 시뮬레이터

Python + PyQt5 기반 프로세스 스케줄링 시뮬레이터. 6개 알고리즘을 멀티코어(P core + E core) 환경에서 Gantt 차트 애니메이션으로 시각화하고, 소비전력 계산 및 알고리즘 간 성능 비교 기능을 제공한다.

## 지원 알고리즘

| 알고리즘 | 유형 | 설명 |
|---------|------|------|
| FCFS | 비선점 | First Come First Served |
| RR | 선점 | Round Robin (Time Quantum 설정 가능) |
| SPN | 비선점 | Shortest Process Next |
| SRTN | 선점 | Shortest Remaining Time Next |
| HRRN | 비선점 | Highest Response Ratio Next |
| Thanos | 선점 | 커스텀 알고리즘 — RR 기반 + 50% 완료 시 1회 부스트 |

## 시스템 요구사항

- Python 3.9 이상
- Windows / macOS / Linux

## 실행 방법

### 방법 1: Python 직접 실행

```bash
# 프로젝트 폴더로 이동
cd process-scheduling-simulator

# 의존성 설치
pip install -r requirements.txt

# 실행
cd src
python main.py
```

### 방법 2: Windows 실행 파일 (.exe) 빌드

```bash
# 의존성 설치
pip install -r requirements.txt

# exe 빌드
pyinstaller --onefile --windowed --name "ProcessSchedulingSimulator" src/main.py

# 실행 (Python 없이도 가능)
dist\ProcessSchedulingSimulator.exe
```

## 테스트 실행

```bash
cd process-scheduling-simulator
python -m pytest tests/ -v
```

## 프로젝트 구조

```
src/
├── main.py                    # 앱 엔트리포인트
├── models/
│   ├── process.py             # Process 데이터 모델
│   └── processor.py           # Processor(코어) 모델 (P core / E core)
├── schedulers/
│   ├── base.py                # BaseScheduler ABC
│   ├── fcfs.py                # FCFS 스케줄러
│   ├── rr.py                  # Round Robin 스케줄러
│   ├── spn.py                 # SPN 스케줄러
│   ├── srtn.py                # SRTN 스케줄러
│   ├── hrrn.py                # HRRN 스케줄러
│   └── thanos.py              # Thanos 커스텀 스케줄러
├── engine/
│   ├── simulator.py           # 시뮬레이션 엔진
│   └── power.py               # 소비전력 계산 모듈
└── gui/
    ├── main_window.py         # 메인 윈도우
    ├── process_input.py       # 프로세스 입력 패널
    ├── processor_config.py    # 프로세서 설정 패널
    ├── gantt_chart.py         # Gantt 차트 + 애니메이션
    ├── ready_queue_view.py    # Ready Queue 시각화
    ├── result_table.py        # 결과 테이블
    ├── comparison_view.py     # 알고리즘 비교 뷰
    └── theme.py               # 다크 테마
tests/                         # pytest 테스트 (42개)
```

## 주요 기능

- **멀티코어 지원**: 최대 4개 프로세서 (P core: 2배 성능/3W, E core: 1배 성능/1W)
- **소비전력 계산**: 코어별 동작전력 + 시동전력 (P: 0.5W, E: 0.1W)
- **Gantt 차트 애니메이션**: 재생/일시정지/리셋 컨트롤
- **Ready Queue 시각화**: 실시간 큐 상태 표시
- **알고리즘 비교**: 6개 알고리즘 동시 비교 (요약 테이블 + 미니 Gantt 차트)
- **다크 테마**: Catppuccin 기반 UI

## 제약 조건

- 프로세스 최대 15개
- 프로세서 최대 4개
- 스케줄링 1초 단위 (소수점 불가)
