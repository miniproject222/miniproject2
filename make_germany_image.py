"""
make_germany_image.py
assets/germany_states.geojson(독일 16개 주 경계) → assets/germany.png 생성

- 팔레트 색으로 칠한 독일 지도 이미지를 만듭니다.
- 이미지 범위(경도·위도)를 ui_theme.GERMANY_BBOX 와 정확히 맞춰 저장하므로,
  나중에 지역별 온도를 같은 좌표로 이미지 위에 겹쳐 표시할 수 있습니다.
- 실행: python make_germany_image.py   (최초 1회, 색을 바꿨을 때만 다시 실행)
"""

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

from ui_theme import GERMANY_BBOX, PALETTE

BASE = Path(__file__).parent
GEOJSON = BASE / "assets" / "germany_states.geojson"
OUT = BASE / "assets" / "germany.png"


def iter_rings(geometry):
    """Polygon / MultiPolygon 의 외곽 링 좌표만 꺼냄"""
    if geometry["type"] == "Polygon":
        yield geometry["coordinates"][0]
    elif geometry["type"] == "MultiPolygon":
        for poly in geometry["coordinates"]:
            yield poly[0]


def main() -> None:
    data = json.loads(GEOJSON.read_text(encoding="utf-8"))

    lon_min, lon_max = GERMANY_BBOX["lon"]
    lat_min, lat_max = GERMANY_BBOX["lat"]
    # 위도 51° 부근에서 경도 1°가 위도 1°보다 짧으므로 세로 비율 보정
    k = 1 / math.cos(math.radians((lat_min + lat_max) / 2))
    height_in = 12
    width_in = height_in * (lon_max - lon_min) / ((lat_max - lat_min) * k)

    fig = plt.figure(figsize=(width_in, height_in), dpi=120)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    ax.set_aspect(k)
    ax.axis("off")

    for feature in data["features"]:
        for ring in iter_rings(feature["geometry"]):
            ax.add_patch(
                Polygon(
                    ring,
                    closed=True,
                    facecolor=PALETTE["lavender"],
                    edgecolor="#FFFFFF",
                    linewidth=1.6,
                    joinstyle="round",
                )
            )

    OUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUT, transparent=True)
    plt.close(fig)
    print(f"저장 완료: {OUT}")


if __name__ == "__main__":
    main()
