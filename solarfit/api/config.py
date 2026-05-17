import os
from dotenv import load_dotenv

load_dotenv()

VWORLD_API_KEY: str = os.getenv("VWORLD_API_KEY", "")

VWORLD_DATA_URL = "https://api.vworld.kr/req/data"
VWORLD_SEARCH_URL = "https://api.vworld.kr/req/search"
VWORLD_GEOCODER_URL = "https://api.vworld.kr/req/address"

NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"
OPENTOPODATA_URL = "https://api.opentopodata.org/v1/srtm90m"

HAENAM_CENTER = (34.57, 126.60)
SUBSTATIONS_CSV = "data/substations.csv"
