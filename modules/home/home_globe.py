# 홈 중앙 비주얼: 우주에서 내려다본 독일 (위성 사진을 구에 입히고 주요 도시 기온 표시)
# 위성 사진: NASA Blue Marble Next Generation (2004-07, 퍼블릭 도메인) 유럽 중부 크롭
#   images/home_europe_bluemarble_01.jpg = 경도 -10~31, 위도 38~64, 1도당 40px
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

import ui_theme as ui

HOME_DIR = Path(__file__).resolve().parent
HOME_EARTH_IMAGE = HOME_DIR / "images" / "home_europe_bluemarble_01.jpg"
HOME_EARTH_BBOX = {"lon": (-10, 31), "lat": (38, 64)}
HOME_GEOJSON = Path(ui.BASE) / "assets" / "germany_states.geojson"   # PM 관리 파일, 읽기만

# 기온을 보여 줄 독일 주요 도시
HOME_CITIES = [
    {"city": "Hamburg", "lat": 53.55, "lon": 9.99},
    {"city": "Berlin", "lat": 52.52, "lon": 13.40},
    {"city": "Köln", "lat": 50.94, "lon": 6.96},
    {"city": "Dresden", "lat": 51.05, "lon": 13.74},
    {"city": "Frankfurt", "lat": 50.11, "lon": 8.68},
    {"city": "Stuttgart", "lat": 48.78, "lon": 9.18, "dy": -6},
    {"city": "München", "lat": 48.14, "lon": 11.58, "dy": 5},
]
HOME_SAMPLE_TEMPS = [26, 31, 30, 32, 31, 30, 33]   # API 실패 시 샘플 (여름 폭염일 가정)
HOME_WEEKDAYS = "월화수목금토일"

# 구 설정: 중심(독일 중앙)에서 구 가장자리까지 실제 거리 HOME_GLOBE_CAP도
HOME_CENTER = (10.45, 51.15)   # (경도, 위도)
HOME_GLOBE_CAP = 12
HOME_GLOBE_PX = 760            # 구 이미지 한 변 픽셀
HOME_SVG_SIZE = 600            # SVG 좌표계
HOME_GLOBE_R = 245             # SVG 안 구 반지름

# 레퍼런스 색 (구 주변 빛, 기온 점)
HOME_GLOW = "#8FA8FF"
HOME_TEMP_COLD, HOME_TEMP_WARM, HOME_TEMP_HOT = "#46A6F5", "#F9A65A", "#F2546B"


HOME_MASK_RES = 100   # 독일 영역 격자: 1도당 100칸


def _home_germany_grid():
    """독일 경계(GeoJSON)를 경도/위도 격자 흑백 이미지로 칠함 (True = 독일 땅)"""
    data = json.loads(HOME_GEOJSON.read_text(encoding="utf-8"))
    (lon_min, lon_max), (lat_min, lat_max) = ui.GERMANY_BBOX["lon"], ui.GERMANY_BBOX["lat"]
    size = (round((lon_max - lon_min) * HOME_MASK_RES), round((lat_max - lat_min) * HOME_MASK_RES))
    grid = Image.new("1", size, 0)
    draw = ImageDraw.Draw(grid)
    for feature in data["features"]:
        geom = feature["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        for poly in polys:
            draw.polygon([((x - lon_min) * HOME_MASK_RES, (lat_max - y) * HOME_MASK_RES) for x, y in poly[0]], fill=1)
    return np.array(grid, dtype=bool)


def _home_in_germany(lon, lat):
    """경도/위도 배열 → 독일 땅 여부 배열"""
    grid = _home_germany_grid()
    ix = np.floor((lon - ui.GERMANY_BBOX["lon"][0]) * HOME_MASK_RES).astype(int)
    iy = np.floor((ui.GERMANY_BBOX["lat"][1] - lat) * HOME_MASK_RES).astype(int)
    ok = (ix >= 0) & (ix < grid.shape[1]) & (iy >= 0) & (iy < grid.shape[0])
    return ok & grid[np.clip(iy, 0, grid.shape[0] - 1), np.clip(ix, 0, grid.shape[1] - 1)]


def _home_close(mask, k):
    """닫힘 연산(팽창 k번 → 침식 k번): 작은 구멍과 틈 메우기"""
    def shift_all(m, op):
        return op.reduce([m, np.roll(m, 1, 0), np.roll(m, -1, 0), np.roll(m, 1, 1), np.roll(m, -1, 1)])
    for _ in range(k):
        mask = shift_all(mask, np.logical_or)
    for _ in range(k):
        mask = shift_all(mask, np.logical_and)
    return mask


def _home_sample(img, lon, lat):
    """경도/위도 배열 → 위성 사진 색 (쌍선형 보간)"""
    h, w = img.shape[:2]
    (lon_min, lon_max), (lat_min, lat_max) = HOME_EARTH_BBOX["lon"], HOME_EARTH_BBOX["lat"]
    x = np.clip((lon - lon_min) / (lon_max - lon_min) * (w - 1), 0, w - 1.001)
    y = np.clip((lat_max - lat) / (lat_max - lat_min) * (h - 1), 0, h - 1.001)
    x0, y0 = x.astype(int), y.astype(int)
    fx, fy = (x - x0)[..., None], (y - y0)[..., None]
    top = img[y0, x0] * (1 - fx) + img[y0, x0 + 1] * fx
    bottom = img[y0 + 1, x0] * (1 - fx) + img[y0 + 1, x0 + 1] * fx
    return top * (1 - fy) + bottom * fy


@lru_cache(maxsize=1)
def home_globe_image():
    """위성 사진을 구에 입힌 WebP(data URI). 처음 한 번만 계산"""
    img = np.asarray(Image.open(HOME_EARTH_IMAGE).convert("RGB"), dtype=np.float32) / 255
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
    lon, lat = np.degrees(lon), np.degrees(lat)

    color = np.clip(_home_sample(img, lon, lat) ** 0.8 * 1.3, 0, 1)

    # 독일만 밝게, 주변국은 어둡고 푸르게
    mask = _home_close(_home_in_germany(lon, lat), 2)   # 주 경계 사이 틈 메우기
    dim = color * 0.55 + np.array([0.04, 0.07, 0.16])
    color = np.where(mask[..., None], np.clip(color * 1.15, 0, 1), dim)

    # 독일 국경선 (마스크 경계를 1px 두껍게)
    edge = mask & ~(np.roll(mask, 1, 0) & np.roll(mask, -1, 0) & np.roll(mask, 1, 1) & np.roll(mask, -1, 1))
    edge = edge | np.roll(edge, 1, 0) | np.roll(edge, 1, 1)
    color = np.where(edge[..., None], color * 0.15 + 0.85, color)

    # 빛(왼쪽 위) + 가장자리 대기(푸른 빛)
    z = np.sqrt(np.clip(1 - rc ** 2, 0, 1))
    light = np.clip(-0.45 * u + 0.5 * v + 0.74 * z, 0, 1)
    color = color * (0.45 + 0.75 * light)[..., None]
    rim = (rc ** 8)[..., None] * 0.6
    color = color * (1 - rim) + np.array([0.55, 0.66, 1.0]) * rim

    alpha = np.clip((1 - r) * n / 2, 0, 1)
    rgba = np.dstack([np.clip(color, 0, 1) * (alpha > 0)[..., None], alpha])
    buf = io.BytesIO()
    Image.fromarray((rgba * 255).astype(np.uint8), "RGBA").save(buf, "WEBP", quality=86)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def _home_project(lon, lat):
    """경도/위도 → SVG 좌표 (home_globe_image와 같은 투영)"""
    lon0, lat0 = map(math.radians, HOME_CENTER)
    la, lo = math.radians(lat), math.radians(lon)
    cos_c = math.sin(lat0) * math.sin(la) + math.cos(lat0) * math.cos(la) * math.cos(lo - lon0)
    c = math.acos(min(max(cos_c, -1), 1))
    theta = math.atan2(
        math.sin(lo - lon0) * math.cos(la),
        math.cos(lat0) * math.sin(la) - math.sin(lat0) * math.cos(la) * math.cos(lo - lon0),
    )
    r = math.sin(min(c / math.radians(HOME_GLOBE_CAP), 1) * math.pi / 2)
    mid = HOME_SVG_SIZE / 2
    return mid + HOME_GLOBE_R * r * math.sin(theta), mid - HOME_GLOBE_R * r * math.cos(theta)


@st.cache_data(ttl=3600, show_spinner=False)
def home_fetch_temps():
    """Open-Meteo(무료, 키 불필요) 현재 기온·체감·습도 + 내일 최고. 성공한 결과만 1시간 저장 (실패하면 예외 → 저장 안 됨)"""
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
                    "week_max": float(maxes[week_i]), "week_day": HOME_WEEKDAYS[date.fromisoformat(days[week_i]).weekday()]})
    return out


def home_get_temps():
    """(도시별 기온 목록, 실시간 여부). 조회 실패 시 샘플 기온, 다음 새로고침 때 다시 시도"""
    try:
        return home_fetch_temps(), True
    except Exception:
        return [{**c, "temp": float(t), "feels": float(t), "humidity": 55.0, "tomorrow": float(t + 1),
                 "week_max": float(t + 2), "week_day": "토"}
                for c, t in zip(HOME_CITIES, HOME_SAMPLE_TEMPS)], False


def _home_mix(c1, c2, t):
    """두 HEX 색을 t(0~1) 비율로 섞기"""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(a, b))


def _home_temp_color(temp, lo=0, hi=35):
    """기온 색: 차가움(파랑) → 따뜻함(주황) → 더움(빨강)"""
    t = min(max((temp - lo) / (hi - lo), 0), 1)
    if t < 0.5:
        return _home_mix(HOME_TEMP_COLD, HOME_TEMP_WARM, t * 2)
    return _home_mix(HOME_TEMP_WARM, HOME_TEMP_HOT, (t - 0.5) * 2)


def home_city_layer(temps, warning_of):
    """지구본 위 도시 기온 이름표 (HTML). 경보 도시는 빨간 표시, 마우스를 올리면 체감·습도·예보 표시
    warning_of(도시) → ("폭염경보" / "더위 주의" / "", 기준 기온)"""
    out = []
    for p in temps:
        x, y = _home_project(p["lon"], p["lat"])
        level, _ = warning_of(p)
        color = HOME_TEMP_HOT if level == "폭염경보" else _home_temp_color(p["temp"])
        advice = "광고 빈도 올리기 추천" if level else "평소 빈도 유지"
        badge = f'<i class="home-city-warn">{level}</i>' if level else ""
        out.append(
            f'<div class="home-city{" home-city-alert" if level else ""}" style="left:{x / HOME_SVG_SIZE * 100:.2f}%;'
            f'top:{y / HOME_SVG_SIZE * 100:.2f}%;--c:{color};--dy:{p.get("dy", 0)}">'
            f'<i class="home-city-dot"></i>'
            f'<span class="home-city-chip">{p["city"]} <b>{p["temp"]:.0f}°</b>{badge}</span>'
            f'<div class="home-city-tip"><b>{p["city"]}</b>'
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
    """레퍼런스처럼 빛 번짐 + 동심원(천천히 도는 점선 고리) 위에 위성 구 (<img> 태그)"""
    mid, r = HOME_SVG_SIZE / 2, HOME_GLOBE_R
    rings = "".join(
        f'<circle cx="{mid}" cy="{mid}" r="{rr}" fill="none" stroke="#FFFFFF" stroke-opacity="{op}" stroke-width="{sw}"/>'
        for rr, op, sw in [(r + 22, 0.9, 10), (r + 44, 0.6, 14)]
    )
    globe = home_globe_image()
    svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {HOME_SVG_SIZE} {HOME_SVG_SIZE}">
  <defs>
    <radialGradient id="glow" cx="50%" cy="50%" r="50%">
      <stop offset="70%" stop-color="{HOME_GLOW}" stop-opacity="0.55">
        <animate attributeName="stop-opacity" values="0.55;0.3;0.55" dur="5s" repeatCount="indefinite"/>
      </stop>
      <stop offset="100%" stop-color="{HOME_GLOW}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <circle cx="{mid}" cy="{mid}" r="{mid}" fill="url(#glow)"/>
  {rings}
  <circle cx="{mid}" cy="{mid}" r="{r + 54}" fill="none" stroke="#FFFFFF" stroke-opacity="0.8" stroke-width="2" stroke-dasharray="2 14">
    <animateTransform attributeName="transform" type="rotate" from="0 {mid} {mid}" to="360 {mid} {mid}" dur="60s" repeatCount="indefinite"/>
  </circle>
  <image x="{mid - r}" y="{mid - r}" width="{2 * r}" height="{2 * r}" href="{globe}" xlink:href="{globe}"/>
</svg>"""
    return home_svg_img(svg, "home-globe-svg")
