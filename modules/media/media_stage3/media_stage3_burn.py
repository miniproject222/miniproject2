# 3. 매체 제작 > 3단계 ④: 초안 영상에 한국어 설명 자막을 '구워 넣기' (내려받은 영상 파일만 열어도 자막이 보이게)
# 자막 한 줄 묶음(cue)마다 글자 그림(PNG, 공통 폰트 SUIT)을 만들고, ffmpeg로 그 시간에만 영상 아래쪽에 겹칩니다.
# ffmpeg는 imageio-ffmpeg 패키지에 들어 있는 실행 파일을 씁니다 (requirements.txt: imageio-ffmpeg). 없으면 굽지 않고 None.
import io
import subprocess
import tempfile
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

MEDIA_S3_BURN_FONT = Path(__file__).resolve().parents[3] / "common" / "fonts" / "SUIT-Bold.otf"   # 공통 폰트 (읽기만)


def media_s3_burn_ready() -> bool:
    try:
        import imageio_ffmpeg  # noqa: F401
        return True
    except ImportError:
        return False


def _media_s3_video_size(ffmpeg: str, path: str) -> tuple[int, int]:
    """영상 가로·세로 (ffmpeg -i 출력에서 읽음). 못 읽으면 480p 16:9."""
    import re
    out = subprocess.run([ffmpeg, "-hide_banner", "-i", path], capture_output=True, text=True, errors="ignore").stderr
    m = re.search(r"Video:.*?(\d{3,4})x(\d{3,4})", out)
    return (int(m.group(1)), int(m.group(2))) if m else (854, 480)


MEDIA_S3_BURN_LATIN = ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf",
                       "LiberationSans-Bold.ttf", "LiberationSans-Regular.ttf")   # ü·ä·ö·ß용 시스템 폰트 (Windows·Linux)


def _media_s3_fonts(size: int) -> tuple:
    """(한글 폰트 SUIT, 독일어 ü·ä·ö·ß처럼 SUIT에 없는 글자용 시스템 폰트 또는 None)."""
    latin = None
    for name in MEDIA_S3_BURN_LATIN:
        try:
            latin = ImageFont.truetype(name, size)
            break
        except OSError:
            continue
    return ImageFont.truetype(str(MEDIA_S3_BURN_FONT), size), latin


def _media_s3_plain(ch: str) -> str:
    """시스템 폰트가 없을 때: ü → u, ß → ss처럼 기본 글자로 (빈칸으로 빠지는 것보다 나음)."""
    import unicodedata
    if ch == "ß":
        return "ss"
    return "".join(c for c in unicodedata.normalize("NFD", ch) if not unicodedata.combining(c)) or ch


def _media_s3_runs(text: str, fonts: tuple) -> list:
    """글을 (조각, 폰트)로 나눔: 라틴 확장 글자(ü·ä·ö·ß·é 등)만 두 번째 폰트로 (없으면 기본 글자로 바꿔 SUIT로)."""
    runs = []
    for ch in text:
        latin = 0xC0 <= ord(ch) <= 0x24F
        if latin and fonts[1] is None:
            ch, latin = _media_s3_plain(ch), False
        f = fonts[1] if latin else fonts[0]
        if runs and runs[-1][1] is f:
            runs[-1][0] += ch
        else:
            runs.append([ch, f])
    return runs


def _media_s3_len(draw, text: str, fonts: tuple) -> float:
    return sum(draw.textlength(t, font=f) for t, f in _media_s3_runs(text, fonts))


def _media_s3_wrap(draw, text: str, font, width: int) -> list:
    """글자를 폭에 맞게 여러 줄로 (한글은 띄어쓰기 단위, 길면 글자 단위)."""
    lines, cur = [], ""
    for word in text.split(" "):
        test = (cur + " " + word).strip()
        if _media_s3_len(draw, test, font) <= width:
            cur = test
            continue
        if cur:
            lines.append(cur)
        cur = word
        while _media_s3_len(draw, cur, font) > width:   # 한 단어가 너무 길면 글자 단위로 자름
            cut = len(cur)
            while cut > 1 and _media_s3_len(draw, cur[:cut], font) > width:
                cut -= 1
            lines.append(cur[:cut])
            cur = cur[cut:]
    if cur:
        lines.append(cur)
    return lines


def _media_s3_sub_png(lines: list, w: int, h: int) -> bytes:
    """자막 그림: 영상 폭에 맞춘 투명 PNG, 반투명 검은 띠 위에 흰 글자 (첫 줄은 노란색 = A안·B안 표시)."""
    size = max(14, h // 26)
    font = _media_s3_fonts(size)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    rows = []
    for i, line in enumerate(lines):
        rows += [(r, i == 0) for r in _media_s3_wrap(probe, line, font, int(w * 0.92))]
    gap = int(size * 0.35)
    box_h = len(rows) * (size + gap) + gap * 2
    img = Image.new("RGBA", (w, box_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, box_h], fill=(0, 0, 0, 150))
    y = gap
    for text, first in rows:
        x = (w - _media_s3_len(d, text, font)) / 2
        for part, f in _media_s3_runs(text, font):   # 조각마다 맞는 폰트로 이어 그림
            d.text((x, y), part, font=f, fill=(255, 220, 90, 255) if first else (255, 255, 255, 255))
            x += d.textlength(part, font=f)
        y += size + gap
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


@st.cache_data(show_spinner=False, max_entries=20)
def media_s3_burn_subs(content: bytes, cues: list) -> bytes | None:
    """영상(MP4)에 자막 cue [(시작초, 끝초, [줄…])]를 구워 넣은 새 MP4. ffmpeg가 없거나 실패하면 None.
    같은 영상·같은 자막은 한 번만 굽고 기억해 둠 (내려받기 버튼이 화면마다 다시 그려져도 다시 굽지 않음)."""
    if not cues or not media_s3_burn_ready():
        return None
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.TemporaryDirectory() as tmp:
        src, out = Path(tmp) / "in.mp4", Path(tmp) / "out.mp4"
        src.write_bytes(content)
        w, h = _media_s3_video_size(ffmpeg, str(src))
        args, chain, last = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src)], [], "0:v"
        for i, (a, b, lines) in enumerate(cues, 1):
            png = Path(tmp) / f"s{i}.png"
            png.write_bytes(_media_s3_sub_png(lines, w, h))
            args += ["-i", str(png)]
            chain.append(f"[{last}][{i}:v]overlay=0:H-h-{h // 24}:enable='between(t,{a:.3f},{b:.3f})'[v{i}]")
            last = f"v{i}"
        args += ["-filter_complex", ";".join(chain), "-map", f"[{last}]", "-map", "0:a?",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "copy",
                 "-movflags", "+faststart", str(out)]
        try:
            subprocess.run(args, check=True, capture_output=True, timeout=180)
        except (subprocess.SubprocessError, OSError):
            return None
        return out.read_bytes() if out.exists() else None
