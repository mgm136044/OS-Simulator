# 테스트 커버리지 문서

> 총 45개 테스트 / 전체 통과  
> 실행: `cd ~/development/process-scheduling-simulator && python -m pytest tests/ -v`

---

## 1. Process 모델 (`tests/test_process.py`) — 4개

| # | 테스트명 | 검증 내용 |
|---|---|---|
| 1 | `test_process_creation` | Process(pid, arrival_time, burst_time) 생성 시 remaining_time=BT, WT=0, TT=0, CT=0 초기값 확인 |
| 2 | `test_process_ntt` | NTT(Normalized Turnaround Time) = TT / BT 계산 정확성. CT=8, BT=4 → NTT=2.0 |
| 3 | `test_process_reset` | reset() 호출 시 remaining_time, WT, CT, service_time이 모두 초기값으로 복원되는지 확인 |
| 4 | `test_process_ntt_with_service_time` | P코어처럼 work_per_tick=2인 경우, NTT = TT / service_time (BT 아님). BT=6, service_time=3(ceil(6/2)) → NTT=1.0 (TT/BT=0.5가 되면 안 됨) |

**핵심 설계 이유:** P코어는 1 tick에 2의 일을 처리하므로 service_time(실제 tick 수)이 BT(총 작업량)와 다르다. NTT를 BT로 나누면 P코어 작업의 NTT가 1.0 미만이 되는 오류 발생. service_time 기준으로 계산해야 올바름.

---

## 2. Processor 모델 (`tests/test_processor.py`) — 8개

| # | 테스트명 | 검증 내용 |
|---|---|---|
| 5 | `test_e_core_properties` | E코어 스펙: work_per_tick=1, power_per_tick=1.0W, startup_power=0.1W |
| 6 | `test_p_core_properties` | P코어 스펙: work_per_tick=2, power_per_tick=3.0W, startup_power=0.5W |
| 7 | `test_core_initial_state` | 코어 초기 상태: is_idle=True, current_process=None, total_power=0.0 |
| 8 | `test_core_assign_process` | assign("P1") 호출 후 is_idle=False, current_process="P1"로 변경됨 |
| 9 | `test_core_startup_power_on_first_use` | 최초 사용 시 첫 tick에서 시동전력 포함 (P코어: 3.0+0.5=3.5W). 이후 tick은 3.0W만 소비 |
| 10 | `test_core_startup_power_after_idle` | 작업 완료 후 idle tick이 1회 이상 발생한 뒤 재할당 시 시동전력 발생 (E코어: 1.0+0.1=1.1W) |
| 11 | `test_core_no_startup_on_immediate_reassign` | idle tick 없이 즉시 다음 프로세스 할당 시 시동전력 미발생 (E코어: 1.0W만 소비). 컨텍스트 스위치 시 불필요한 시동전력 방지 |
| 12 | `test_core_reset` | reset() 후 is_idle=True, total_power=0.0으로 초기화 |

**핵심 설계 이유:** `_had_idle_tick` 플래그로 "실제 쉰 적이 있는가"를 추적. release() 직후 바로 assign()하면 idle tick이 없으므로 시동전력 미발생. 이 구분이 없으면 모든 컨텍스트 스위치마다 시동전력이 중복 계산됨.

---

## 3. FCFS 스케줄러 (`tests/test_fcfs.py`) — 3개

테스트 입력: P1(AT=0, BT=3), P2(AT=1, BT=5), P3(AT=3, BT=2), P4(AT=5, BT=4)

| # | 테스트명 | 검증 내용 |
|---|---|---|
| 13 | `test_fcfs_timeline` | 도착 순서대로 P1→P2→P3→P4 실행. 각 start/end: P1(0-3), P2(3-8), P3(8-10), P4(10-14). total_time=14 |
| 14 | `test_fcfs_metrics` | WT: P1=0, P2=2, P3=5, P4=5 / TT: P1=3, P2=7, P3=7, P4=9 |
| 15 | `test_fcfs_name` | scheduler.name == "FCFS" |

---

## 4. RR 스케줄러 (`tests/test_rr.py`) — 3개

테스트 입력: 동일 4개 프로세스 / quantum=2

| # | 테스트명 | 검증 내용 |
|---|---|---|
| 16 | `test_rr_metrics` | 라운드로빈 순환 실행 결과. WT: P1=2, P2=6, P3=2, P4=5 / TT: P1=5, P2=11, P3=4, P4=9 |
| 17 | `test_rr_total_time` | 모든 프로세스 완료까지 total_time == 14 |
| 18 | `test_rr_name` | scheduler.name == "RR" |

---

## 5. SPN 스케줄러 (`tests/test_spn.py`) — 3개

테스트 입력: 동일 4개 프로세스 (비선점)

| # | 테스트명 | 검증 내용 |
|---|---|---|
| 19 | `test_spn_metrics` | BT 짧은 순 선택. P3(BT=2), P4(BT=4)가 P2(BT=5)보다 먼저 실행. WT: P1=0, P2=8, P3=0, P4=0 |
| 20 | `test_spn_timeline` | 실행 순서가 P1→P3→P4→P2 (도착 이후 BT 기준 정렬). total_time=14 |
| 21 | `test_spn_name` | scheduler.name == "SPN" |

---

## 6. SRTN 스케줄러 (`tests/test_srtn.py`) — 3개

| # | 테스트명 | 검증 내용 |
|---|---|---|
| 22 | `test_srtn_metrics` | 선점형 최단잔여시간 기준. WT: P1=0, P2=8, P3=0, P4=0 |
| 23 | `test_srtn_preemption` | P1(BT=7) 실행 중 t=2에 P2(BT=3) 도착 → P1 선점. P2 완료(t=5) 후 P1 재개. P1 WT=3(선점 대기), P2 WT=0 |
| 24 | `test_srtn_name` | scheduler.name == "SRTN" |

---

## 7. HRRN 스케줄러 (`tests/test_hrrn.py`) — 3개

테스트 입력: 동일 4개 프로세스 (비선점, HRR = (WT+BT)/BT 기준)

| # | 테스트명 | 검증 내용 |
|---|---|---|
| 25 | `test_hrrn_metrics` | HRR 비율 계산으로 기아 방지. WT: P1=0, P2=2, P3=5, P4=5 |
| 26 | `test_hrrn_timeline` | 실행 순서 P1→P2→P3→P4. total_time=14 |
| 27 | `test_hrrn_name` | scheduler.name == "HRRN" |

---

## 8. Thanos 스케줄러 (`tests/test_thanos.py`) — 4개

| # | 테스트명 | 검증 내용 |
|---|---|---|
| 28 | `test_thanos_metrics` | quantum=2, E코어 기준 tick 단위 trace 검증. WT: P1=0, P2=8, P3=2, P4=2 / TT: P1=3, P2=13, P3=4, P4=6 |
| 29 | `test_thanos_boost` | P1(BT=3), P2(BT=6). t=2에 P1 remaining=1 ≤ BT/2=1.5 → appendleft 부스트 → P1이 t=3에 완료. 부스트 없었다면 P1은 더 늦게 완료됨 |
| 30 | `test_thanos_total_time` | 동일 4개 프로세스 기준 total_time == 14 |
| 31 | `test_thanos_name` | scheduler.name == "Thanos" |

**부스트 메커니즘:** `remaining_time ≤ burst_time / 2` 조건 충족 시 레디큐 맨 앞(appendleft) 삽입. `boosted` set으로 프로세스당 1회만 부스트. 이미 부스트받은 프로세스는 이후 quantum 소진 시 일반 큐 뒤(append)로 복귀.

---

## 9. 전력 계산 엔진 (`tests/test_power.py`) — 3개

| # | 테스트명 | 검증 내용 |
|---|---|---|
| 32 | `test_power_single_e_core` | E코어 1개, 3초 실행: 시동전력 0.1W + 3×1.0W = 3.1W. 가동률 100% |
| 33 | `test_power_mixed_cores` | E코어+P코어 혼합. E코어 3초 풀가동(3.1W), P코어 2초만 가동(6.5W). 총 9.6W. P코어 가동률 66.7% |
| 34 | `test_power_idle_core` | P코어가 한 번도 사용되지 않으면 전력=0W, 가동률=0% |

---

## 10. Simulator 엔진 (`tests/test_simulator.py`) — 3개

| # | 테스트명 | 검증 내용 |
|---|---|---|
| 35 | `test_simulator_run` | sim.run() 반환 report에 algorithm, total_time, timeline(4개), processes(4개) 포함 |
| 36 | `test_simulator_metrics` | report["metrics"]의 avg_wt=3.0, avg_tt=6.5 평균 계산 정확성 |
| 37 | `test_simulator_process_details` | report["processes"][0]의 pid, at, bt, wt, tt, ntt 필드 전체 정확성 |

---

## 11. 멀티코어 (`tests/test_multicore.py`) — 8개

| # | 테스트명 | 검증 내용 |
|---|---|---|
| 38 | `test_fcfs_two_cores_parallel` | E코어 2개: P1(BT=4)→core0, P2(BT=6)→core1 병렬 실행. total_time=max(4,6)=6 |
| 39 | `test_fcfs_p_core_speed` | P코어 1개: BT=6 → ceil(6/2)=3 tick에 완료. total_time=3 |
| 40 | `test_fcfs_power_calculation` | E코어, BT=2: 시동전력0.1 + 2×1.0W = 2.1W. total_power 정확성 |
| 41 | `test_rr_two_cores` | RR E코어 2개: P1(BT=3), P2(BT=3) 각 코어에서 독립 실행. 둘 다 t=3 완료 |
| 42 | `test_spn_two_cores` | SPN E코어 2개: 3개 프로세스 중 BT 짧은 순서로 코어 배정. P2(BT=2)가 t=2 완료 |
| 43 | `test_thanos_two_cores` | Thanos E코어 2개: P1·P2(BT=4) 병렬. total_time=4 |
| 44 | `test_fcfs_p_core_wt_ntt` | P코어 WT 음수 버그 방지 검증. BT=6, service_time=3 → WT=TT-service_time=0 (이전 공식 TT-BT=-3이었음). NTT=1.0 |
| 45 | `test_rr_p_core_wt` | RR+P코어 혼합에서 모든 프로세스 WT≥0, NTT≥1.0 보장. total_time=5 확인 |

**멀티코어 핵심:** test 44·45는 P코어 도입 후 발견된 WT 음수 버그를 막기 위해 추가됨. `exec_ticks` 누적 방식(WT = TT - service_time)으로 해결.

---

## 버그 방지 테스트 요약

| 버그 | 관련 테스트 | 해결책 |
|---|---|---|
| P코어 WT 음수 | #4, #44, #45 | NTT·WT를 service_time 기준으로 계산 |
| 컨텍스트 스위치마다 시동전력 중복 | #11 | `_had_idle_tick` 플래그로 실제 idle 후에만 발동 |
| 멀티코어 마이그레이션 시 WT 오계산 | #44, #45 | exec_ticks 누적 방식 (WT = TT - service_time) |
