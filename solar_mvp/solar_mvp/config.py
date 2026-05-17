from pathlib import Path

# === Paths ===
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / "cache"
OUTPUT_DIR = BASE_DIR / "output"

# === Target region ===
SIGUNGU_CODE = "46810"  # 전라남도 해남군
SIGUNGU_NAME = "해남군"

# === Coordinate systems ===
CRS_ANALYSIS = "EPSG:5179"   # UTM-K for area/distance calcs
CRS_WGS84 = "EPSG:4326"      # for visualization and external APIs

# === Hard filter thresholds ===
ALLOWED_JIMOK = {"임야", "전", "답", "잡종지", "목장용지"}
BLOCKED_USE_ZONES = {
    "자연환경보전지역", "농업진흥구역", "보전산지",
    "공익용산지", "자연공원", "상수원보호구역",
    "문화재보호구역", "군사시설보호구역"
}
BLOCKED_OWNER_TYPES = {"국유", "공유", "종중", "분할미정", "외국인"}

MIN_AREA_M2 = 1000
MAX_SLOPE_DEG = 15.0
MAX_ELEVATION_M = 600
BLOCKED_FOREST_AGES = {"IV", "V", "VI"}  # 4영급 이상
REQUIRED_KW = 100  # 100kW급 사업 기준
MIN_ROAD_WIDTH_M = 3.0

# === 해남군 도시계획조례 이격거리 (Day 0 수동 조사 필요 — 현재 기본값) ===
HAENAM_RESIDENTIAL_BUFFER_M = 300  # TODO(Day 0): Verify with 해남군청 도시계획과; 300m is Jeonnam model ordinance default

# === 고압 송전선로 이격거리 (전기사업법 시행규칙 별표 12) ===
HVLINE_SETBACK_M: dict[str, int] = {
    "765kV": 80,
    "345kV": 60,
    "154kV": 33,
}
HV_LINE_SETBACK_DEFAULT_M = 33  # 154kV 기준 (최소 고압)

# === 계통 포화 판단 기준 ===
GRID_SATURATION_RADIUS_KM = 5.0        # 반경 5km 내 기존 태양광 밀집도 측정
GRID_SATURATION_HARD_LIMIT_KW = 50_000  # 반경 5km 내 기존 설치량 ≥ 50MW → 계통포화 위험

# === Feature list for scoring/ML ===
FEATURES_V2 = [
    'slope_mean',
    'slope_std',
    'aspect_south',          # 0 or 1
    'annual_ghi',
    'area_m2',
    'dist_to_substation_km',
    'substation_remaining_kw',
    'dist_to_road_m',
    'nearest_building_dist_m',
    'official_land_price',
    'elevation_m',
    'dist_to_powerline_m',       # 배전선로까지 거리 — 인입공사비 직결
    'existing_solar_kw_5km',     # 반경 5km 기존 태양광 용량 합 — 계통 포화 추정
]

# Features that must NEVER appear in ML training (data leakage guard)
FORBIDDEN_FEATURES = {
    'install_capacity_kw',
    'completion_date',
    'permit_date',
    'operation_status',
    'is_installed',           # label itself
    'num_nearby_plants',      # spatial leakage
    'land_use_after_install', # post-installation change
}

# === Rule-based weights (domain knowledge) ===
# abs(weights) sum = 1.25; scorer must normalize by sum(abs(v) for v in weights.values())
WEIGHTS_RULE = {
    'slope_mean':               -0.15,
    'slope_std':                -0.05,
    'aspect_south':              0.10,
    'annual_ghi':                0.15,
    'area_m2':                   0.10,
    'dist_to_substation_km':    -0.13,
    'substation_remaining_kw':   0.13,
    'dist_to_road_m':           -0.05,
    'nearest_building_dist_m':   0.05,
    'official_land_price':      -0.10,
    'elevation_m':              -0.05,
    'dist_to_powerline_m':      -0.09,  # 배전선로 인접 = 인입공사비↓ = 사업성↑
    'existing_solar_kw_5km':    -0.10,  # 주변 태양광 밀집 = 계통 포화 위험↑
}

# === Evaluation thresholds ===
RECALL_K_VALUES = [50, 100, 500, 1000]
TARGET_RECALL_AT_100 = 0.30   # MVP 기준
TARGET_RECALL_AT_500 = 0.60

# === VWorld API ===
VWORLD_BASE_URL = "https://api.vworld.kr/req"
VWORLD_WFS_URL = "https://api.vworld.kr/ogc/wfs"

# === data.go.kr ===
DATA_GO_KR_BASE_URL = "https://apis.data.go.kr"
SOLAR_PLANT_SERVICE_ID = "15107742"   # 전국태양광발전소 표준데이터

# === ML config ===
SPATIAL_FOLD_COLUMN = "eup_myeon"     # 읍면 단위 K-fold
N_SPATIAL_FOLDS = 5
TRAIN_YEAR_MAX = 2020                  # 2020 이전 = train
TEST_YEAR_MIN = 2021                   # 2021-2024 = test
LABEL_BUFFER_M = 100                   # PNU 매핑 buffer radius

# === Ensemble weights ===
ENSEMBLE_RULE_WEIGHT = 0.5
ENSEMBLE_ML_WEIGHT = 0.5
