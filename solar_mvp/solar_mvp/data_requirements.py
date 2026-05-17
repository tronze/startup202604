"""
SolarFit MVP v2 — 데이터 요구사항 체크.

실행: python -m solar_mvp.data_requirements
"""
from __future__ import annotations

import os
from pathlib import Path

from solar_mvp.config import DATA_DIR

REQUIREMENTS: list[dict] = [
    # ── API 키 ────────────────────────────────────────────────────────────────
    {
        "key": "VWORLD_API_KEY",
        "type": "env",
        "label": "VWorld API 키",
        "usage": "Stage 1 필지/경계 수집 (필수), Stage 3 변전소/전력선 WFS",
        "required": True,
        "how": "https://map.vworld.kr → 개발자 등록 → 오픈API 신청",
        "required_for": ["Stage 1 전체 (없으면 파이프라인 실행 불가)"],
    },
    {
        "key": "DATA_GO_KR_KEY",
        "type": "env",
        "label": "data.go.kr API 키",
        "usage": "Stage 3 기존 태양광발전소 밀도 (existing_solar_kw_5km), 변전소 현황",
        "required": False,
        "how": "https://data.go.kr → 로그인 → 마이페이지 → 일반 인증키 발급",
        "required_for": ["Stage 3 기존 태양광 밀도 — 없으면 0으로 처리"],
    },
    # ── 파일: 계통/인프라 ─────────────────────────────────────────────────────
    {
        "key": "data/substations.csv",
        "type": "file",
        "label": "변전소 현황 (수동 CSV — API보다 우선)",
        "usage": "Stage 3 dist_to_substation_km, substation_remaining_kw",
        "required": False,
        "how": "한전 배전계획처 협의 또는 KEPCO 공개 자료 정리",
        "columns": "name, lat, lon, remaining_kw (kW), voltage",
        "required_for": ["Stage 3 변전소 피처 — 없으면 API → 빈값 처리"],
    },
    {
        "key": "data/roads.geojson",
        "type": "file",
        "label": "도로망",
        "usage": "Stage 3 dist_to_road_m, has_road_access_3m, dist_to_powerline_m proxy",
        "required": True,
        "how": (
            "① VWorld WFS: lt_c_road (VWORLD_API_KEY 필요)\n"
            "     또는 ② OSM: https://overpass-turbo.eu → 해남군 roads query → GeoJSON 저장"
        ),
        "required_for": [
            "Stage 3 하드필터 현황도로<3m",
            "배전선 거리 proxy (전력선 데이터 없을 때)",
        ],
    },
    {
        "key": "data/buildings.geojson",
        "type": "file",
        "label": "건물 (주거 이격거리)",
        "usage": "Stage 3 nearest_building_dist_m — 300m 이격 하드필터",
        "required": True,
        "how": (
            "VWorld WFS: lt_c_lsigbldlm (건물통합정보) — VWORLD_API_KEY 필요\n"
            "     또는 국가공간정보포털 (nsdi.go.kr) → 건물 shapefile → GeoJSON 변환"
        ),
        "required_for": ["Stage 3 하드필터 이격거리 300m"],
    },
    # ── 파일: 토지 속성 ───────────────────────────────────────────────────────
    {
        "key": "data/land_price.csv",
        "type": "file",
        "label": "공시지가 (official_land_price)",
        "usage": "Stage 3 official_land_price (원/m²) — 스코어링 가중치 -0.10",
        "required": False,
        "how": (
            "국토교통부 공시지가 시스템 (realtyprice.kr) → 표준지/개별 공시지가 → 해남군\n"
            "     또는 국토정보 플랫폼 (map.ngii.go.kr) API\n"
            "     ※ 없으면 지목별 추정값 사용 (임야 5천, 전 25천, 답 30천 원/m²)"
        ),
        "columns": "pnu, official_land_price (또는 land_price_per_m2)",
        "required_for": ["Stage 3 스코어링 (없으면 지목 추정값 대체)"],
    },
    {
        "key": "data/solar_irradiance.csv",
        "type": "file",
        "label": "연간 일사량 (annual_ghi)",
        "usage": "Stage 3 annual_ghi (kWh/m²/year) — 스코어링 가중치 +0.15",
        "required": False,
        "how": (
            "기상청 기후데이터포털 (data.kma.go.kr) → 일사량 통계\n"
            "     또는 한국에너지기술연구원 태양자원지도 (kier.re.kr)\n"
            "     또는 NASA POWER (power.larc.nasa.gov) — GHI 그리드 데이터 → 필지 매핑\n"
            "     ※ 없으면 위도 기반 추정값 사용 (34.5°N ≈ 1400 kWh/m²/yr)"
        ),
        "columns": "pnu, annual_ghi",
        "required_for": ["Stage 3 스코어링 (없으면 위도 추정값 대체)"],
    },
    # ── 파일: 규제 구역 ───────────────────────────────────────────────────────
    {
        "key": "data/agri_promotion.shp",
        "type": "file",
        "label": "농업진흥지역 (in_agricultural_promotion_zone)",
        "usage": "Stage 3 하드필터 — 농업진흥구역 필지 전량 제외",
        "required": True,
        "how": (
            "농림축산식품부 농지정보 관리시스템 (fims.mafra.go.kr)\n"
            "     → 농업진흥지역 지정 현황 shp 다운로드 → 해남군 clip"
        ),
        "required_for": ["Stage 3 하드필터 농업진흥지역 — 없으면 False (낙관적 처리)"],
    },
    {
        "key": "data/protected/",
        "type": "dir",
        "label": "보전구역 (intersects_protected_area)",
        "usage": "Stage 3 하드필터 — 자연환경보전구역/자연공원 등 중첩 필지 제외",
        "required": True,
        "how": (
            "환경부 환경공간정보서비스 (egis.me.go.kr)\n"
            "     → 자연공원/생태·경관 보전지역/습지보호지역 각각 shp 다운로드\n"
            "     → data/protected/ 폴더에 저장 (복수 shp 자동 통합)"
        ),
        "required_for": ["Stage 3 하드필터 보전구역 — 없으면 False (낙관적 처리)"],
    },
    {
        "key": "data/forest_age.shp",
        "type": "file",
        "label": "임상도 영급 (forest_age_class)",
        "usage": "Stage 3 하드필터 — 4영급(IV) 이상 임야 제외",
        "required": False,
        "how": (
            "산림청 산림공간정보서비스 (forest.go.kr/gis)\n"
            "     → 임상도 (수종·영급) shp 다운로드 → 해남군 clip\n"
            "     ※ 없으면 forest_age_class = '' (영급 필터 미적용)"
        ),
        "required_for": ["Stage 3 하드필터 임상영급 (IV/V/VI 제외) — 없으면 미적용"],
    },
]


def check_requirements() -> list[dict]:
    """각 요구사항의 현재 충족 여부를 반환."""
    statuses = []
    for req in REQUIREMENTS:
        s = req.copy()
        key = req["key"]
        rtype = req["type"]

        if rtype == "env":
            val = os.environ.get(key, "").strip()
            s["available"] = bool(val)
            s["current"] = f"설정됨 ({val[:6]}...)" if val else "❌ 미설정"
        elif rtype == "file":
            path = DATA_DIR / key.replace("data/", "", 1)
            s["available"] = path.exists()
            if path.exists():
                size_kb = path.stat().st_size // 1024
                s["current"] = f"있음 ({size_kb} KB)"
            else:
                s["current"] = f"❌ 없음 — {path}"
        elif rtype == "dir":
            dir_path = DATA_DIR / key.replace("data/", "", 1).rstrip("/")
            shps = list(dir_path.glob("*.shp")) if dir_path.exists() else []
            s["available"] = bool(shps)
            s["current"] = f"있음 ({len(shps)}개 .shp)" if shps else f"❌ 없음 — {dir_path}/"

        statuses.append(s)
    return statuses


def print_requirements(verbose: bool = True) -> None:
    """데이터 요구사항 현황을 터미널에 출력."""
    statuses = check_requirements()
    available = sum(1 for s in statuses if s["available"])
    total = len(statuses)
    required_missing = [s for s in statuses if not s["available"] and s.get("required")]
    optional_missing = [s for s in statuses if not s["available"] and not s.get("required")]

    W = 72
    print()
    print("=" * W)
    print("  SolarFit MVP v2 — 데이터 요구사항 현황")
    print(f"  준비됨: {available}/{total}  |  필수 미준비: {len(required_missing)}  |  선택 미준비: {len(optional_missing)}")
    print("=" * W)

    sections = [
        ("🔑 API 키", [s for s in statuses if s["type"] == "env"]),
        ("🗄️  데이터 파일", [s for s in statuses if s["type"] in ("file", "dir")]),
    ]

    for section_title, items in sections:
        print(f"\n  {section_title}")
        print("  " + "-" * (W - 2))
        for s in items:
            icon = "✅" if s["available"] else ("🔴" if s.get("required") else "🟡")
            req_tag = "[필수]" if s.get("required") else "[선택]"
            print(f"  {icon} {req_tag} {s['label']}")
            print(f"       현재: {s['current']}")
            if verbose and not s["available"]:
                print(f"       용도: {s['usage']}")
                how_lines = s["how"].split("\n")
                print(f"       방법: {how_lines[0].strip()}")
                for line in how_lines[1:]:
                    print(f"             {line.strip()}")
                if "columns" in s:
                    print(f"       컬럼: {s['columns']}")
            print()

    print("=" * W)
    if required_missing:
        print(f"  🔴 필수 데이터 {len(required_missing)}개 미준비 — 파이프라인 실행 불가")
        for s in required_missing:
            print(f"     • {s['label']}")
    if optional_missing:
        print(f"  🟡 선택 데이터 {len(optional_missing)}개 미준비 — 해당 기능 제한 또는 추정값 사용")

    print()
    print("  환경변수 설정 방법:")
    print("    export VWORLD_API_KEY=your_key_here")
    print("    export DATA_GO_KR_KEY=your_key_here")
    print("    # 또는 프로젝트 루트에 .env 파일 생성")
    print("=" * W)
    print()


if __name__ == "__main__":
    print_requirements()
