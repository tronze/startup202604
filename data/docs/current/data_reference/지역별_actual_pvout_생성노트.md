# 지역별 actual PVOUT 생성 노트

## 목적

- KPX 지역별 태양광 발전량과 지역별 태양광 설비용량을 같은 단위로 맞춰 `실제 단위용량당 발전량`을 만든다.
- 결과 단위는 `kWh/kWp/day`이며 Solargis `PVOUT`와 같은 해석이 가능하다.

## 사용 데이터

- 발전량: `kpx_generation_download`
- 설비용량: `kpx_capacity_download` 내부 월별 CSV

## 계산식

```text
actual_pvout_kwh_per_kwp_day = 지역 월간 발전량(MWh) / 지역 월간 설비용량(MW) / 그달 일수
```

- `MWh / MW / day`는 수치상 `kWh / kW / day`와 동일하므로 PVOUT과 비교 가능한 단위다.

## 주의사항

- 발전량과 설비용량 모두 KPX 전력시장 참여 설비 기준이다.
- 한전 직접거래(PPA), 자가용, 비시장 설비 전체를 대표하는 값으로 보면 안 된다.
- 2025 발전량 파일과 월별 설비용량 파일을 같은 지역명 체계로 정규화해서 조인했다.

## 산출물

- 월별: `data/processed/actual_pvout_region_monthly.csv`
- 연간: `data/processed/actual_pvout_region_annual.csv`

## 2025 연간 평균 상위 5개 지역

- 부산시: 3.813 kWh/kWp/day
- 울산시: 3.755 kWh/kWp/day
- 대구시: 3.660 kWh/kWp/day
- 서울시: 3.585 kWh/kWp/day
- 전라북도: 3.581 kWh/kWp/day

