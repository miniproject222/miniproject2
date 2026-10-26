# 홈 중앙 비주얼: 독일 중심 지구본 (회색 유럽 지도 + 연보라 독일 + 나라 이름) + 주요 도시 기온 핀
# 국경: Natural Earth 1:50m Admin 0 Countries v5.1.2 (퍼블릭 도메인)에서 유럽 중부만 잘라 둔
#   data/home_europe_countries_ne50m.geojson
# (2026-10-26) 위성 사진 지구본 → 사용자가 준 사진처럼 회색 지도 + 연보라 독일로 바꿈, 사진보다 독일을 조금 더 확대
import base64
import io
import json
import math
from datetime import date
from functools import lru_cache
from pathlib import Path

import numpy as np
import requests
import streamlit as st
from PIL import Image, ImageDraw

HOME_DIR = Path(__file__).resolve().parent
HOME_COUNTRIES = HOME_DIR / "data" / "home_europe_countries_ne50m.geojson"

# 지도에 보일 권역 핀: ④ 광고 타이밍의 4개 권역(북부·서부·동부·남부)마다 대표 도시 1곳 (④ WEATHER_REGIONS의 첫 도시)
# pop: 도시 인구 (2025-12-31, Zensus 2022 기준 주 통계청 추계, 주민등록 주소지 기준) → 핀 둘레 원 크기
HOME_CITIES = [
    {"region": "북부", "city": "Hamburg", "ko": "함부르크", "lat": 53.55, "lon": 9.99, "pop": 1869473},
    {"region": "서부", "city": "Köln", "ko": "쾰른", "lat": 50.94, "lon": 6.96, "pop": 1025523},
    {"region": "동부", "city": "Berlin", "ko": "베를린", "lat": 52.52, "lon": 13.40, "pop": 3700577},
    {"region": "남부", "city": "München", "ko": "뮌헨", "lat": 48.14, "lon": 11.58, "pop": 1505036},
]
HOME_POP_SOURCE = "도시 인구: 2025-12-31 (Zensus 2022 기준 주 통계청 추계)"
HOME_HALO_MAX = 96             # 가장 큰 도시(베를린) 원 지름 (기준 화면 px). 원 넓이가 인구에 비례하게 지름 = 최대 × √(인구 ÷ 최대 인구)
# 지도에 이름을 보여 줄 이웃 나라 (이름이 들어갈 자리의 경도, 위도)
HOME_NEIGHBORS = [
    ("프랑스", 4.2, 47.6), ("폴란드", 18.6, 52.3), ("체코", 15.4, 49.75), ("오스트리아", 14.6, 47.55),
    ("스위스", 8.1, 46.75), ("네덜란드", 5.6, 52.6), ("벨기에", 4.5, 50.55), ("덴마크", 9.2, 56.1),
    ("이탈리아", 11.2, 44.4),
]
HOME_SAMPLE_TEMPS = [26, 30, 31, 33]   # API 실패 시 샘플 (여름 폭염일 가정, HOME_CITIES 순서)
HOME_WEEKDAYS = "월화수목금토일"

# 구 설정: 중심(독일 중앙)에서 구 가장자리까지 실제 거리 HOME_GLOBE_CAP도
HOME_CENTER = (10.45, 51.15)   # (경도, 위도)
HOME_GLOBE_CAP = 10            # 지구본을 가운데에 조금 작게 두면서 독일이 크게 보이는 범위
HOME_GLOBE_PX = 1000           # 구 이미지 한 변 픽셀
HOME_SVG_SIZE = 600            # SVG 좌표계
HOME_GLOBE_R = 250             # SVG 안 구 반지름 (바깥에 레퍼런스 같은 하얀 테두리를 둘 자리)

# 지도 색 (레퍼런스처럼 하얀 지구본: 흰 땅 · 옅은 회보라 바다 · 회색 국경 + 연보라 독일)
HOME_MAP_BBOX = {"lon": (-12, 36), "lat": (34, 66)}
HOME_MAP_RES = 60              # 지도 그림: 1도당 60px
HOME_MAP_SEA = (222, 224, 236)
HOME_MAP_LAND = (246, 246, 250)
HOME_MAP_BORDER = (212, 214, 226)
HOME_MAP_DE = (189, 178, 248)
HOME_MAP_DE_SIDE = (128, 112, 222)     # 독일 판의 옆면 (아래·오른쪽으로 두께가 보이게)
HOME_MAP_DE_BORDER = (123, 108, 242)
HOME_MAP_SHADOW = (205, 207, 222)      # 나라가 바다 위에 살짝 뜬 그림자
HOME_MAP_DE_SHADOW = (168, 170, 186)   # 독일 판이 이웃 나라 위에 드리운 그림자
# 도시 핀 색: 평소 보라, 더위 주의 주황, 폭염경보 빨강 (경고일 때만 색이 튐)
HOME_PIN, HOME_PIN_WARN, HOME_PIN_HOT = "#7B6CF2", "#F9A65A", "#F2546B"


def _home_map_xy(lon, lat):
    (lon_min, _), (_, lat_max) = HOME_MAP_BBOX["lon"], HOME_MAP_BBOX["lat"]
    return (lon - lon_min) * HOME_MAP_RES, (lat_max - lat) * HOME_MAP_RES


@lru_cache(maxsize=1)
def home_map_image():
    """경도/위도 평면에 그린 지도 → numpy 배열 (0~1). 입체감: 나라는 바다 위에 살짝 뜬 그림자,
    독일은 두께(옆면)가 보이는 솟아오른 판 + 이웃 나라 위로 드리운 그림자"""
    (lon_min, lon_max), (lat_min, lat_max) = HOME_MAP_BBOX["lon"], HOME_MAP_BBOX["lat"]
    size = (round((lon_max - lon_min) * HOME_MAP_RES), round((lat_max - lat_min) * HOME_MAP_RES))
    img = Image.new("RGB", size, HOME_MAP_SEA)
    draw = ImageDraw.Draw(img)
    features = json.loads(HOME_COUNTRIES.read_text(encoding="utf-8"))["features"]

    def rings(f, dx=0, dy=0):
        return [[(x + dx, y + dy) for x, y in (_home_map_xy(*pt) for pt in poly[0])] for poly in f["geometry"]["coordinates"]]

    others = [f for f in features if f["properties"]["iso"] != "DEU"]
    germany = [f for f in features if f["properties"]["iso"] == "DEU"]
    for f in others:   # 1) 나라 그림자 (바다 위, 오른쪽 아래로)
        for ring in rings(f, 4, 6):
            draw.polygon(ring, fill=HOME_MAP_SHADOW)
    for f in others:   # 2) 나라 + 흰 국경
        for ring in rings(f):
            draw.polygon(ring, fill=HOME_MAP_LAND)
            draw.line(ring + ring[:1], fill=HOME_MAP_BORDER, width=3)
    for f in germany:  # 3) 독일 판: 그림자 → 옆면(두께) → 윗면 → 국경
        for ring in rings(f, 14, 20):
            draw.polygon(ring, fill=HOME_MAP_DE_SHADOW)
        for step in range(10, 0, -2):
            for ring in rings(f, step * 0.7, step):
                draw.polygon(ring, fill=HOME_MAP_DE_SIDE)
        for ring in rings(f):
            draw.polygon(ring, fill=HOME_MAP_DE)
            draw.line(ring + ring[:1], fill=HOME_MAP_DE_BORDER, width=5)
    return np.asarray(img, dtype=np.float32) / 255


def _home_sample(img, lon, lat):
    """경도/위도 배열 → 지도 색 (쌍선형 보간)"""
    h, w = img.shape[:2]
    (lon_min, lon_max), (lat_min, lat_max) = HOME_MAP_BBOX["lon"], HOME_MAP_BBOX["lat"]
    x = np.clip((lon - lon_min) / (lon_max - lon_min) * (w - 1), 0, w - 1.001)
    y = np.clip((lat_max - lat) / (lat_max - lat_min) * (h - 1), 0, h - 1.001)
    x0, y0 = x.astype(int), y.astype(int)
    fx, fy = (x - x0)[..., None], (y - y0)[..., None]
    top = img[y0, x0] * (1 - fx) + img[y0, x0 + 1] * fx
    bottom = img[y0 + 1, x0] * (1 - fx) + img[y0 + 1, x0 + 1] * fx
    return top * (1 - fy) + bottom * fy


@lru_cache(maxsize=1)
def home_globe_image():
    """지도를 독일 중심 구에 입힌 WebP(data URI). 처음 한 번만 계산"""
    n = HOME_GLOBE_PX
    yy, xx = np.mgrid[0:n, 0:n]
    u = (xx + 0.5) / n * 2 - 1
    v = 1 - (yy + 0.5) / n * 2
    r = np.hypot(u, v)
    rc = np.clip(r, 0, 1)

    # 구 위 점 → 중심에서의 거리(c)와 방위(theta) → 경도/위도 (가장자리로 갈수록 압축돼 둥글게 보임)
    c = np.arcsin(rc) / (math.pi / 2) * math.radians(HOME_GLOBE_CAP)
    theta = np.arctan2(u, v)
    lon0, lat0 = map(math.radians, HOME_CENTER)
    lat = np.arcsin(math.sin(lat0) * np.cos(c) + math.cos(lat0) * np.sin(c) * np.cos(theta))
    lon = lon0 + np.arctan2(np.sin(theta) * np.sin(c) * math.cos(lat0), np.cos(c) - math.sin(lat0) * np.sin(lat))
    color = _home_sample(home_map_image(), np.degrees(lon), np.degrees(lat))

    # 구 입체감: 왼쪽 위에서 빛 → 오른쪽 아래 가장자리는 어둡게, 왼쪽 위에 반사광, 가장자리에 얇은 대기 빛
    z = np.sqrt(np.clip(1 - rc ** 2, 0, 1))
    light = np.clip(-0.5 * u + 0.55 * v + 0.67 * z, 0, 1)
    # 입체감 더 강하게: 빛 반대쪽(오른쪽 아래)은 보랏빛 그늘, 왼쪽 위 반사광, 가장자리 얇은 빛
    shade = (0.6 + 0.48 * light)[..., None]
    color = color * shade + np.array([0.10, 0.08, 0.22]) * (1 - shade) * 0.35
    spec = np.exp(-((u + 0.36) ** 2 + (v - 0.40) ** 2) / 0.06)[..., None] * 0.28
    color = color + spec
    rim = (rc ** 16)[..., None] * 0.5
    color = color * (1 - rim) + np.array([0.90, 0.88, 1.0]) * rim

    alpha = np.clip((1 - r) * n / 2, 0, 1)
    rgba = np.dstack([np.clip(color, 0, 1) * (alpha > 0)[..., None], alpha])
    buf = io.BytesIO()
    Image.fromarray((rgba * 255).astype(np.uint8), "RGBA").save(buf, "WEBP", quality=88)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def _home_project(lon, lat):
    """경도/위도 → (SVG 좌표 x, y, 구 안에 보이는지) (home_globe_image와 같은 투영)"""
    lon0, lat0 = map(math.radians, HOME_CENTER)
    la, lo = math.radians(lat), math.radians(lon)
    cos_c = math.sin(lat0) * math.sin(la) + math.cos(lat0) * math.cos(la) * math.cos(lo - lon0)
    c = math.acos(min(max(cos_c, -1), 1))
    theta = math.atan2(
        math.sin(lo - lon0) * math.cos(la),
        math.cos(lat0) * math.sin(la) - math.sin(lat0) * math.cos(la) * math.cos(lo - lon0),
    )
    k = c / math.radians(HOME_GLOBE_CAP)
    r = math.sin(min(k, 1) * math.pi / 2)
    mid = HOME_SVG_SIZE / 2
    return mid + HOME_GLOBE_R * r * math.sin(theta), mid - HOME_GLOBE_R * r * math.cos(theta), k < 0.9


@st.cache_data(ttl=3600, show_spinner=False)
def home_fetch_temps():
    """Open-Meteo(무료, 키 불필요) 현재 기온·체감·습도 + 7일 최고. 성공한 결과만 1시간 저장 (실패하면 예외 → 저장 안 됨)"""
    params = {
        "latitude": ",".join(str(c["lat"]) for c in HOME_CITIES),
        "longitude": ",".join(str(c["lon"]) for c in HOME_CITIES),
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m",
        "daily": "temperature_2m_max",
        "forecast_days": 7,
        "timezone": "Europe/Berlin",
    }
    res = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=5)
    res.raise_for_status()
    data = res.json()
    data = data if isinstance(data, list) else [data]
    out = []
    for c, d in zip(HOME_CITIES, data):
        maxes, days = d["daily"]["temperature_2m_max"], d["daily"]["time"]
        week_i = max(range(1, len(maxes)), key=lambda i: maxes[i])   # 내일부터 이번 주 중 가장 더운 날
        out.append({**c, "temp": float(d["current"]["temperature_2m"]), "feels": float(d["current"]["apparent_temperature"]),
                    "humidity": float(d["current"]["relative_humidity_2m"]), "tomorrow": float(maxes[1]),
                    "week_max": float(maxes[week_i]), "week_day": HOME_WEEKDAYS[date.fromisoformat(days[week_i]).weekday()],
                    "daily": [{"day": HOME_WEEKDAYS[date.fromisoformat(dd).weekday()], "max": float(m)}
                              for dd, m in zip(days, maxes)]})
    return out


def home_sample_daily(values):
    """샘플·시연용 7일 최고 기온 목록 (오늘 요일부터)"""
    today = date.today().weekday()
    return [{"day": HOME_WEEKDAYS[(today + i) % 7], "max": float(v)} for i, v in enumerate(values)]


def home_get_temps():
    """(도시별 기온 목록, 실시간 여부). 조회 실패 시 샘플 기온, 다음 새로고침 때 다시 시도"""
    try:
        return home_fetch_temps(), True
    except Exception:
        return [{**c, "temp": float(t), "feels": float(t), "humidity": 55.0, "tomorrow": float(t + 1),
                 "week_max": float(t + 2), "week_day": "토",
                 "daily": home_sample_daily([t, t + 1, t, t + 1, t + 2, t + 1, t])}
                for c, t in zip(HOME_CITIES, HOME_SAMPLE_TEMPS)], False


def home_city_layer(temps, warning_of):
    """지구본 위 이웃 나라 이름 + 권역 핀 (말풍선: 기온 · 권역 · 대표 도시, 점, 인구만큼 큰 원). 경보 권역만 주황/빨강.
    마우스를 올리면 인구·체감·습도·예보 표시. warning_of(도시) → ("폭염경보" / "더위 주의" / "", 기준 기온)"""
    top_pop = max((c["pop"] for c in HOME_CITIES), default=1)
    out = []
    for name, lon, lat in HOME_NEIGHBORS:
        x, y, visible = _home_project(lon, lat)
        if visible:
            out.append(f'<span class="home-country" style="left:{x / HOME_SVG_SIZE * 100:.2f}%;'
                       f'top:{y / HOME_SVG_SIZE * 100:.2f}%">{name}</span>')
    for p in temps:
        x, y, _ = _home_project(p["lon"], p["lat"])
        level, _ = warning_of(p)
        color = HOME_PIN_HOT if level == "폭염경보" else HOME_PIN_WARN if level else HOME_PIN
        advice = "광고 빈도 올리기 추천" if level else "평소 빈도 유지"
        badge = f'<i class="home-city-warn">{level}</i>' if level else ""
        pop = p.get("pop") or 0
        halo = HOME_HALO_MAX * math.sqrt(pop / top_pop) if pop else 30   # 원 넓이 ∝ 인구
        out.append(
            f'<div class="home-city{" home-city-alert" if level else ""}" style="left:{x / HOME_SVG_SIZE * 100:.2f}%;'
            f'top:{y / HOME_SVG_SIZE * 100:.2f}%;--c:{color};--halo:{halo:.0f}">'
            f'<i class="home-city-halo"></i><i class="home-city-dot"></i>'
            f'<span class="home-city-chip"><b>{p["temp"]:.0f}°</b><span><em>{p.get("region", "")}</em>{p.get("ko", p["city"])}</span>{badge}</span>'
            f'<div class="home-city-tip"><b>{p.get("region", "")} · {p.get("ko", p["city"])} ({p["city"]})</b>'
            f'<span>인구 {pop / 10000:,.0f}만 명</span>'
            f'<span>체감 {p.get("feels", p["temp"]):.0f}° · 습도 {p.get("humidity", 0):.0f}%</span>'
            f'<span>내일 최고 {p.get("tomorrow", p["temp"]):.0f}° · 이번 주 최고 {p.get("week_max", p["temp"]):.0f}° ({p.get("week_day", "")})</span>'
            f'<em>{advice}</em></div></div>'
        )
    return "".join(out)


def home_svg_img(svg, cls):
    """st.html은 <svg>를 지우므로 data URI <img>로 바꿔 넣기"""
    data = base64.b64encode(svg.encode("utf-8")).decode()
    return f'<img class="{cls}" src="data:image/svg+xml;base64,{data}" alt="">'


def home_globe_svg():
    """지도 구 (<img> 태그) + 레퍼런스 같은 테두리 2개: 안쪽은 불투명한 두꺼운 하얀 고리,
    간격을 두고 바깥쪽은 살짝 투명하고 더 얇은 하얀 고리. 바닥 그림자는 CSS(.home-globe-shadow)로"""
    mid, r = HOME_SVG_SIZE / 2, HOME_GLOBE_R
    globe = home_globe_image()
    svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {HOME_SVG_SIZE} {HOME_SVG_SIZE}">
  <circle cx="{mid}" cy="{mid}" r="{r + 13}" fill="none" stroke="#FFFFFF" stroke-opacity="1" stroke-width="18"/>
  <circle cx="{mid}" cy="{mid}" r="{r + 40}" fill="none" stroke="#FFFFFF" stroke-opacity="0.6" stroke-width="7"/>
  <image x="{mid - r}" y="{mid - r}" width="{2 * r}" height="{2 * r}" href="{globe}" xlink:href="{globe}"/>
</svg>"""
    return home_svg_img(svg, "home-globe-svg")
