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
from PIL import Image, ImageDraw, ImageFilter

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
# 가장 큰 도시(베를린) 원 지름 (기준 화면 px). 원 넓이가 인구에 비례하게 지름 = 최대 × √(인구 ÷ 최대 인구)
# (2026-10-26 PM: 가장 큰 원 = 예전 서부(쾰른) 원 크기 96 × √(1,025,523 ÷ 3,700,577) ≈ 51, 나머지는 같은 비율로 작아짐)
HOME_HALO_MAX = 51
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

# 지도 색 (2026-10-26 PM: 흰 석고 입체 지구본 사진처럼 · 국경선 없이 흰 땅이 살짝 솟은 질감 + 연보라 독일, 독일 테두리 없음)
HOME_MAP_BBOX = {"lon": (-12, 36), "lat": (34, 66)}
HOME_MAP_RES = 60              # 지도 그림: 1도당 60px
HOME_MAP_SEA = (234, 235, 241)         # 바다: 아주 옅은 회색 석고
HOME_MAP_LAND = (252, 252, 254)        # 땅: 흰 석고
HOME_MAP_DE = (204, 195, 250)          # 독일: 연보라 (테두리 없이 색만)
HOME_RELIEF_SEED = 7                   # 석고 잔 질감 무늬 (값을 바꾸면 무늬만 달라짐)
# 도시 핀 색: 평소 보라, 더위 주의 주황, 폭염경보 빨강 (경고일 때만 색이 튐)
HOME_PIN, HOME_PIN_WARN, HOME_PIN_HOT = "#7B6CF2", "#F9A65A", "#F2546B"


def _home_map_xy(lon, lat):
    (lon_min, _), (_, lat_max) = HOME_MAP_BBOX["lon"], HOME_MAP_BBOX["lat"]
    return (lon - lon_min) * HOME_MAP_RES, (lat_max - lat) * HOME_MAP_RES


def _home_blur(arr, radius):
    """0~1 배열 흐리게 (PIL 가우시안)"""
    img = Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8), "L")
    return np.asarray(img.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255


@lru_cache(maxsize=1)
def home_map_image():
    """경도/위도 평면에 그린 지도 → numpy 배열 (0~1). 흰 석고 입체 지구본 느낌:
    국경선 없이 땅 전체를 하나로 보고, 해안에서 안쪽으로 살짝 솟은 높이 + 잔잔한 울퉁불퉁 무늬를 만든 뒤
    왼쪽 위에서 빛을 비춰 음영(밝은 면·그늘)을 넣음. 바다에는 땅이 드리운 옅은 그림자. 독일은 연보라 색만 (테두리 없음).
    실제 산 높이 데이터는 쓰지 않고 땅 모양으로 흉내 냄 (PM 결정)"""
    (lon_min, lon_max), (lat_min, lat_max) = HOME_MAP_BBOX["lon"], HOME_MAP_BBOX["lat"]
    size = (round((lon_max - lon_min) * HOME_MAP_RES), round((lat_max - lat_min) * HOME_MAP_RES))
    features = json.loads(HOME_COUNTRIES.read_text(encoding="utf-8"))["features"]

    def mask(feats):
        img = Image.new("L", size, 0)
        draw = ImageDraw.Draw(img)
        for f in feats:
            for poly in f["geometry"]["coordinates"]:
                draw.polygon([_home_map_xy(*pt) for pt in poly[0]], fill=255)
        return np.asarray(img, dtype=np.float32) / 255

    land = mask(features)
    de = _home_blur(mask([f for f in features if f["properties"]["iso"] == "DEU"]), 1.2)   # 독일 가장자리만 살짝 부드럽게

    # 높이: 해안에서 안쪽으로 솟는 땅 + 굵은 굴곡 + 잔 알갱이 (석고 질감)
    rng = np.random.default_rng(HOME_RELIEF_SEED)
    w, h = size
    coarse = np.asarray(Image.fromarray((rng.random((h // 40 + 1, w // 40 + 1)) * 255).astype(np.uint8), "L")
                        .resize(size, Image.BICUBIC), dtype=np.float32) / 255
    fine = _home_blur(rng.random((h, w)).astype(np.float32), 1.0)
    height = _home_blur(land, 6) * 1.0 + land * (coarse * 0.25 + fine * 0.30)

    # 빛 (왼쪽 위): 기울기가 빛 쪽이면 밝게, 반대면 그늘 — 땅에만 (바다는 매끈하고 낮게 보이게)
    gy, gx = np.gradient(height)
    edge = _home_blur(land, 2)   # 해안선 바로 바깥까지만 음영이 번지게
    shade = 1 + np.clip((-gx - gy) * 8, -0.22, 0.10) * edge
    drop = _home_blur(np.roll(np.roll(land, 5, axis=0), 4, axis=1), 5) * (1 - land)   # 바다 위 땅 그림자

    sea, ground, purple = (np.array(c, dtype=np.float32) / 255 for c in (HOME_MAP_SEA, HOME_MAP_LAND, HOME_MAP_DE))
    color = sea * (1 - land[..., None]) + ground * land[..., None]
    color = color * (1 - de[..., None]) + purple * de[..., None]
    color = color * shade[..., None] * (1 - drop[..., None] * 0.10)
    return np.clip(color, 0, 1)


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
def home_land_masks():
    """경도/위도 평면의 땅·독일 마스크 (H, W, 2) 0~1 — 점 지구본에서 '이 점이 땅인가'를 볼 때 씀"""
    (lon_min, lon_max), (lat_min, lat_max) = HOME_MAP_BBOX["lon"], HOME_MAP_BBOX["lat"]
    size = (round((lon_max - lon_min) * HOME_MAP_RES), round((lat_max - lat_min) * HOME_MAP_RES))
    features = json.loads(HOME_COUNTRIES.read_text(encoding="utf-8"))["features"]

    def mask(feats):
        img = Image.new("L", size, 0)
        draw = ImageDraw.Draw(img)
        for f in feats:
            for poly in f["geometry"]["coordinates"]:
                draw.polygon([_home_map_xy(*pt) for pt in poly[0]], fill=255)
        return np.asarray(img, dtype=np.float32) / 255

    return np.dstack([mask(features), mask([f for f in features if f["properties"]["iso"] == "DEU"])])


# 매끈한 광택 지구본 (2026-10-26 PM: 'ANY Currency' 레퍼런스 분위기 — 흰색→옅은 라벤더 광택 구, 질감 없이 평평하게 칠한 땅,
# 독일은 보라→네이비 그라데이션(보라가 더 많게), 나머지 나라는 옅은 라벤더라 독일이 돋보임)
HOME_SOFT_WHITE = (0.93, 0.93, 0.97)      # 바다 밝은 쪽 (2026-10-26 PM: 흰색 → 연보라·회색을 살짝 섞어 진하게)
HOME_SOFT_LAVENDER = (0.74, 0.74, 0.86)   # 바다 어두운 쪽 (연보라 + 회색)
HOME_SOFT_LAND = (0.95, 0.95, 1.00)       # 독일 말고 나머지 땅 (거의 흰색, 바다보다 살짝 밝게)
HOME_SOFT_LILAC = (0.70, 0.62, 1.00)      # 독일 그라데이션 맨 앞 (밝은 보라, 북서쪽 끝)
HOME_SOFT_PURPLE = (0.50, 0.41, 0.95)     # 독일 그라데이션 가운데 (보라)
HOME_SOFT_NAVY = (0.12, 0.15, 0.44)       # 독일 그라데이션 끝 (네이비, 더 진하게)
HOME_MESH_TL = (0.33, 0.47, 0.87)         # 독일 메시 그라데이션: 왼쪽 위 (로열 블루)
HOME_MESH_TR = (0.45, 0.76, 0.96)         # 오른쪽 위 (하늘색)
HOME_MESH_BL = (0.52, 0.40, 0.88)         # 왼쪽 아래 (보라)
HOME_MESH_BR = (0.74, 0.86, 0.98)         # 오른쪽 아래 (옅은 하늘빛, 흰 땅과 구분되게 아주 희지는 않게)
HOME_SOFT_PURPLE_SHARE = 0.45             # 독일 그라데이션에서 보라가 차지하는 비율 (작을수록 네이비가 넓음, 0.62 → 0.45)


@lru_cache(maxsize=1)
def home_globe_image():
    """매끈한 광택 지구본 WebP(data URI). 처음 한 번만 계산.
    구 바탕: 왼쪽 위 흰색 → 아래·오른쪽 옅은 라벤더, 넓은 광택. 땅: 테두리·질감 없이 평평한 색 (빛에 따라 아주 조금만 어둡게).
    독일: 왼쪽 위 보라 → 오른쪽 아래 네이비 대각선 그라데이션 (앞쪽 62%는 보라에 가깝게)."""
    n = HOME_GLOBE_PX
    yy, xx = np.mgrid[0:n, 0:n]
    u = (xx + 0.5) / n * 2 - 1
    v = 1 - (yy + 0.5) / n * 2
    r = np.hypot(u, v)
    rc = np.clip(r, 0, 1)
    c = np.arcsin(rc) / (math.pi / 2) * math.radians(HOME_GLOBE_CAP)
    theta = np.arctan2(u, v)
    lon0, lat0 = map(math.radians, HOME_CENTER)
    lat = np.arcsin(math.sin(lat0) * np.cos(c) + math.cos(lat0) * np.sin(c) * np.cos(theta))
    lon = lon0 + np.arctan2(np.sin(theta) * np.sin(c) * math.cos(lat0), np.cos(c) - math.sin(lat0) * np.sin(lat))
    masks = _home_sample(home_land_masks(), np.degrees(lon), np.degrees(lat))
    land, de = masks[..., 0:1], masks[..., 1:2]

    # 구 바탕: 빛(왼쪽 위)에 따라 흰색 ↔ 옅은 라벤더
    z = np.sqrt(np.clip(1 - rc ** 2, 0, 1))
    light = np.clip(-0.42 * u + 0.55 * v + 0.72 * z, 0, 1)[..., None]
    sphere = np.array(HOME_SOFT_LAVENDER) * (1 - light ** 1.3) + np.array(HOME_SOFT_WHITE) * light ** 1.3

    # 독일 대각선 그라데이션: 독일이 차지한 화면 범위 안에서 왼쪽 위(0) → 오른쪽 아래(1)
    inside = masks[..., 1] > 0.5
    if inside.any():
        x0, x1 = xx[inside].min(), xx[inside].max()
        y0, y1 = yy[inside].min(), yy[inside].max()
        t = ((xx - x0) / max(x1 - x0, 1) + (yy - y0) / max(y1 - y0, 1)) / 2
    else:
        t = np.zeros_like(u)
    # 2026-10-26 PM: 메시 그라데이션 (레퍼런스 'Modern Mesh Gradient') — 독일 범위의 네 모서리 색을 부드럽게 섞음
    #   왼쪽 위 로열 블루 · 오른쪽 위 하늘색 · 왼쪽 아래 보라 · 오른쪽 아래 아주 옅은 하늘빛
    #   (예전 3색 보라→네이비는 HOME_SOFT_LILAC/PURPLE/NAVY 상수로 남겨 둠)
    if inside.any():
        tx = np.clip((xx - x0) / max(x1 - x0, 1), 0, 1)[..., None]
        ty = np.clip((yy - y0) / max(y1 - y0, 1), 0, 1)[..., None]
    else:
        tx = ty = np.zeros_like(u)[..., None]
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)    # 가장자리 쪽 색이 넓게, 가운데는 부드럽게 섞이게
    top = np.array(HOME_MESH_TL) * (1 - tx) + np.array(HOME_MESH_TR) * tx
    bottom = np.array(HOME_MESH_BL) * (1 - tx) + np.array(HOME_MESH_BR) * tx
    germany = top * (1 - ty) + bottom * ty

    flat = 0.90 + 0.10 * light                            # 땅은 평평하게 (빛 영향 아주 조금)
    color = sphere * (1 - land) + np.array(HOME_SOFT_LAND) * flat * land
    color = color * (1 - de) + germany * (0.94 + 0.06 * light) * de

    # 광택: 왼쪽 위 넓은 반사광 + 가장자리 옅은 라벤더 빛
    spec = np.exp(-((u + 0.36) ** 2 + (v - 0.42) ** 2) / 0.10)[..., None] * 0.06   # 2026-10-26 PM: 광 줄임 (0.22 → 0.06)
    color = color + spec
    # 가장자리: 아주 살짝 어둡게 (경계 그림자) + 맨 끝 얇은 옅은 빛
    color = color * (1 - (rc ** 6)[..., None] * 0.10)
    rim = (rc ** 22)[..., None] * 0.30
    color = color * (1 - rim) + np.array([0.88, 0.87, 0.97]) * rim

    alpha = np.clip((1 - r) * n / 2, 0, 1)
    rgba = np.dstack([np.clip(color, 0, 1) * (alpha > 0)[..., None], alpha])
    buf = io.BytesIO()
    Image.fromarray((rgba * 255).astype(np.uint8), "RGBA").save(buf, "WEBP", quality=90)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


# 하얀 무광 석고 지구본 (2026-10-26 PM: 흰색 위에 흰색 · 바다는 아주 고운 점 무늬 · 땅은 매끈하게 살짝 솟은 판 + 옅은 그림자,
# 파랑·초록 같은 진한 색 없이 거의 흰색. 독일만 아주 옅은 연보라로 위치 표시)
HOME_WHITE_SEA = (0.925, 0.925, 0.935)    # 바다: 아주 옅은 회백색
HOME_WHITE_LAND = (0.985, 0.985, 0.99)    # 땅: 거의 흰색
HOME_WHITE_DE = (0.93, 0.91, 0.99)        # 독일: 아주 옅은 연보라
HOME_SEA_DOT_STEP = 5                     # 바다 점 무늬 간격 (구 이미지 px)


@lru_cache(maxsize=1)
def home_white_map():
    """경도/위도 평면의 하얀 지도 (H, W, 4): RGB + 땅 마스크.
    땅은 바다보다 살짝 솟은 판: 해안 안쪽 가장자리에 빛 받는 면(왼쪽 위)·그늘(오른쪽 아래), 바다 위에 땅 그림자."""
    masks = home_land_masks()
    land, de = masks[..., 0], _home_blur(masks[..., 1], 1.0)
    # 해안에서만 생기는 경사(판 가장자리)로 음영: 높이 = 살짝 흐린 땅 마스크
    gy, gx = np.gradient(_home_blur(land, 3))
    bevel = np.clip((-gx - gy) * 6, -0.16, 0.10) * land
    drop = _home_blur(np.roll(np.roll(land, 7, axis=0), 5, axis=1), 4) * (1 - land)   # 바다 위 땅 그림자 (오른쪽 아래)
    sea, ground, purple = (np.array(c, dtype=np.float32) for c in (HOME_WHITE_SEA, HOME_WHITE_LAND, HOME_WHITE_DE))
    color = sea * (1 - land[..., None]) + ground * land[..., None]
    color = color * (1 - de[..., None]) + purple * de[..., None]
    color = color * (1 + bevel[..., None]) * (1 - drop[..., None] * 0.13)
    return np.dstack([np.clip(color, 0, 1), land])


@lru_cache(maxsize=1)
def home_globe_image_white():
    """(보관) 하얀 무광 석고 지구본 WebP(data URI) — 2026-10-26 밤 버전. 지금은 home_globe_image()의 매끈한 광택 지구본을 씀.
    부드러운 스튜디오 빛(왼쪽 위)으로 옅은 회색 그늘만 넣고(낮은 대비), 바다에는 아주 고운 점 무늬."""
    n = HOME_GLOBE_PX
    yy, xx = np.mgrid[0:n, 0:n]
    u = (xx + 0.5) / n * 2 - 1
    v = 1 - (yy + 0.5) / n * 2
    r = np.hypot(u, v)
    rc = np.clip(r, 0, 1)
    c = np.arcsin(rc) / (math.pi / 2) * math.radians(HOME_GLOBE_CAP)
    theta = np.arctan2(u, v)
    lon0, lat0 = map(math.radians, HOME_CENTER)
    lat = np.arcsin(math.sin(lat0) * np.cos(c) + math.cos(lat0) * np.sin(c) * np.cos(theta))
    lon = lon0 + np.arctan2(np.sin(theta) * np.sin(c) * math.cos(lat0), np.cos(c) - math.sin(lat0) * np.sin(lat))
    m = _home_sample(home_white_map(), np.degrees(lon), np.degrees(lat))
    color, land = m[..., :3], m[..., 3]

    # 바다 점 무늬: 아주 작은 점을 촘촘히 (땅에는 없음)
    s = HOME_SEA_DOT_STEP
    dist = np.hypot(xx % s - s / 2, yy % s - s / 2)
    dots = np.clip(1.15 - dist, 0, 1) * (1 - np.clip(land * 1.5, 0, 1))
    color = color * (1 - dots[..., None] * 0.12)

    # 구 음영: 부드러운 빛, 옅은 회색 그늘 (낮은 대비 · 밝은 톤)
    z = np.sqrt(np.clip(1 - rc ** 2, 0, 1))
    light = np.clip(-0.45 * u + 0.5 * v + 0.74 * z, 0, 1)[..., None]
    shade = 0.80 + 0.24 * light
    color = color * shade + np.array([0.55, 0.55, 0.58]) * (1 - shade) * 0.25
    spec = np.exp(-((u + 0.38) ** 2 + (v - 0.42) ** 2) / 0.18)[..., None] * 0.06   # 은은한 광택 (무광)
    color = color + spec
    rim = (rc ** 20)[..., None] * 0.35
    color = color * (1 - rim) + np.array([0.97, 0.97, 0.98]) * rim

    alpha = np.clip((1 - r) * n / 2, 0, 1)
    rgba = np.dstack([np.clip(color, 0, 1) * (alpha > 0)[..., None], alpha])
    buf = io.BytesIO()
    Image.fromarray((rgba * 255).astype(np.uint8), "RGBA").save(buf, "WEBP", quality=90)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


# 점 지구본 (2026-10-26 PM: '글로벌 무역 분석 대시보드' 느낌 — 연하늘→진한 페리윙클 그라데이션 구, 광택, 흰·연하늘 점 대륙)
HOME_DOT_STEP = 11              # 점 간격 (구 이미지 px)
HOME_DOT_R = 2.6                # 점 반지름 (독일은 조금 크게)
HOME_SPHERE_LIGHT = (0.80, 0.87, 1.00)   # 구 밝은 쪽 (연하늘)
HOME_SPHERE_DEEP = (0.36, 0.40, 0.86)    # 구 어두운 쪽 (진한 페리윙클 블루)
HOME_DOT_LAND = (0.94, 0.96, 1.00)       # 대륙 점 (흰·연하늘)
HOME_DOT_DE = (0.80, 0.70, 1.00)         # 독일 점 (연보라, 위치를 알아보게)


@lru_cache(maxsize=1)
def home_globe_image_dots():
    """(보관) 점 지구본 WebP(data URI) — 2026-10-26 저녁 버전. 지금은 home_globe_image()의 하얀 석고 지구본을 씀.
    구 바탕은 빛(왼쪽 위)에 따라 연하늘→페리윙클 그라데이션 + 광택, 대륙은 일정한 간격의 빛나는 점(살짝 번지는 빛)."""
    n = HOME_GLOBE_PX
    yy, xx = np.mgrid[0:n, 0:n]
    u = (xx + 0.5) / n * 2 - 1
    v = 1 - (yy + 0.5) / n * 2
    r = np.hypot(u, v)
    rc = np.clip(r, 0, 1)
    c = np.arcsin(rc) / (math.pi / 2) * math.radians(HOME_GLOBE_CAP)
    theta = np.arctan2(u, v)
    lon0, lat0 = map(math.radians, HOME_CENTER)
    lat = np.arcsin(math.sin(lat0) * np.cos(c) + math.cos(lat0) * np.sin(c) * np.cos(theta))
    lon = lon0 + np.arctan2(np.sin(theta) * np.sin(c) * math.cos(lat0), np.cos(c) - math.sin(lat0) * np.sin(lat))
    masks = _home_sample(home_land_masks(), np.degrees(lon), np.degrees(lat))   # (n, n, 2)

    # 구 바탕: 왼쪽 위 빛 → 연하늘, 반대쪽 → 진한 페리윙클
    z = np.sqrt(np.clip(1 - rc ** 2, 0, 1))
    light = np.clip(-0.45 * u + 0.5 * v + 0.74 * z, 0, 1)[..., None]
    color = np.array(HOME_SPHERE_DEEP) * (1 - light) + np.array(HOME_SPHERE_LIGHT) * light

    # 대륙 점: 칸마다 가운데에 점 하나, 그 칸 가운데가 땅이면 그림 (해안에서 점이 잘리지 않게)
    s = HOME_DOT_STEP
    cy, cx = (yy // s) * s + s // 2, (xx // s) * s + s // 2
    cy, cx = np.clip(cy, 0, n - 1), np.clip(cx, 0, n - 1)
    land_c, de_c = masks[cy, cx, 0], masks[cy, cx, 1]
    dist = np.hypot(xx - cx, yy - cy)
    radius = HOME_DOT_R + 1.1 * (de_c > 0.5)
    dot = np.clip(radius - dist + 0.5, 0, 1) * (land_c > 0.5) * (rc[cy, cx] < 0.985)
    glow = _home_blur(dot, 2.2) * 0.40                       # 점 둘레가 살짝 빛나게
    dot_col = np.where((de_c > 0.5)[..., None], np.array(HOME_DOT_DE), np.array(HOME_DOT_LAND))
    bright = (0.75 + 0.35 * light)                          # 빛 반대쪽 점은 조금 어둡게
    color = color * (1 - glow[..., None]) + dot_col * bright * glow[..., None]
    color = color * (1 - dot[..., None]) + dot_col * bright * dot[..., None]

    # 광택: 왼쪽 위 부드러운 반사광 + 가장자리 얇은 흰 빛
    spec = np.exp(-((u + 0.40) ** 2 + (v - 0.45) ** 2) / 0.16)[..., None] * 0.13   # 넓고 약한 광택
    color = color + spec
    rim = (rc ** 14)[..., None] * 0.55
    color = color * (1 - rim) + np.array([0.92, 0.95, 1.0]) * rim

    alpha = np.clip((1 - r) * n / 2, 0, 1)
    rgba = np.dstack([np.clip(color, 0, 1) * (alpha > 0)[..., None], alpha])
    buf = io.BytesIO()
    Image.fromarray((rgba * 255).astype(np.uint8), "RGBA").save(buf, "WEBP", quality=90)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def home_globe_image_relief():
    """(보관) 흰 석고 입체 지구본 — 2026-10-26 오후 버전. 지금은 home_globe_image()의 점 지구본을 씀"""
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
    # 흰 석고 구: 빛 반대쪽(오른쪽 아래)은 옅은 회색 그늘(보랏빛 줄임), 왼쪽 위 은은한 반사광, 가장자리 얇은 흰 빛
    shade = (0.72 + 0.36 * light)[..., None]
    color = color * shade + np.array([0.30, 0.30, 0.38]) * (1 - shade) * 0.25
    spec = np.exp(-((u + 0.36) ** 2 + (v - 0.40) ** 2) / 0.08)[..., None] * 0.14
    color = color + spec
    rim = (rc ** 18)[..., None] * 0.45
    color = color * (1 - rim) + np.array([0.96, 0.96, 1.0]) * rim

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
    """지구본 구 (<img> 태그) + 레퍼런스처럼 구를 감싼 두꺼운 반투명 흰 띠 (2026-10-26 PM, 굵기 28 → 38).
    멀리 떨어진 반투명 흰 얇은 선은 CSS(.home-globe::after, 구 반지름의 약 1.55배)로 그림.
    바닥 그림자는 CSS(.home-globe-shadow)로"""
    mid, r = HOME_SVG_SIZE / 2, HOME_GLOBE_R
    globe = home_globe_image()
    svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {HOME_SVG_SIZE} {HOME_SVG_SIZE}">
  <circle cx="{mid}" cy="{mid}" r="{r + 19}" fill="none" stroke="#FFFFFF" stroke-opacity="0.55" stroke-width="38"/>
  <image x="{mid - r}" y="{mid - r}" width="{2 * r}" height="{2 * r}" href="{globe}" xlink:href="{globe}"/>
</svg>"""
    return home_svg_img(svg, "home-globe-svg")
