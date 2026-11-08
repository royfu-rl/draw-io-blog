"""经典论文候选：下 arXiv 源码包 → 抽出所有图文件 → PDF 图转 PNG → 每篇拼一张联系表。

用法: python3 -I fetch_arxiv_figs.py <middle_processing 目录> <arxiv_id> [<arxiv_id> ...]
产出:
    <dir>/arxiv/<id>/src/        解包后的源码（只读，不执行）
    <dir>/arxiv/<id>/figs/       图文件（PDF 已转 PNG）
    <dir>/arxiv/<id>/sheet.jpg   联系表，格子标文件名
"""
import gzip
import io
import sys
import tarfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont

EXTS = {".png", ".jpg", ".jpeg", ".pdf"}
MIN_BYTES = 20_000  # 过滤图标、小插图


def unpack(blob: bytes, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(fileobj=io.BytesIO(blob)) as tf:
            safe = [m for m in tf.getmembers() if m.isfile() and not m.name.startswith(("/", "..")) and ".." not in m.name]
            tf.extractall(dst, members=safe)
    except tarfile.ReadError:  # 单文件投稿：gzip 过的 tex
        (dst / "main.tex").write_bytes(gzip.decompress(blob))


def to_png(src: Path, dst: Path) -> None:
    if src.suffix.lower() == ".pdf":
        with fitz.open(src) as doc:
            doc[0].get_pixmap(dpi=200).save(dst.with_suffix(".png"))
    else:
        Image.open(src).convert("RGB").save(dst.with_suffix(".png"))


def sheet(figs: list[Path], out: Path) -> None:
    if not figs:
        return
    cols, w, h = 4, 520, 360
    rows = (len(figs) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * w, rows * (h + 30)), "white")
    font = ImageFont.truetype("LiberationSans-Regular.ttf", 18)
    for k, f in enumerate(figs):
        im = Image.open(f).convert("RGB")
        im.thumbnail((w - 10, h - 10))
        x, y = (k % cols) * w, (k // cols) * (h + 30)
        canvas.paste(im, (x + 5, y + 30))
        ImageDraw.Draw(canvas).text((x + 5, y + 5), f.name[:48], fill="blue", font=font)
    canvas.save(out, quality=85)


def fetch(root: Path, aid: str) -> str:
    base = root / "arxiv" / aid
    if not (base / "src").exists():
        req = urllib.request.Request(f"https://arxiv.org/e-print/{aid}", headers={"User-Agent": "Mozilla/5.0"})
        unpack(urllib.request.urlopen(req, timeout=120).read(), base / "src")
    figs_dir = base / "figs"
    figs_dir.mkdir(exist_ok=True)
    for f in (base / "src").rglob("*"):
        if f.suffix.lower() in EXTS and f.stat().st_size >= MIN_BYTES:
            name = str(f.relative_to(base / "src")).replace("/", "__")
            try:
                to_png(f, figs_dir / name)
            except Exception as e:  # 坏图跳过
                print(aid, f.name, e)
    figs = sorted(figs_dir.glob("*.png"))
    sheet(figs, base / "sheet.jpg")
    return f"{aid}: {len(figs)} figs"


def main(root: str, ids: list[str]) -> None:
    with ThreadPoolExecutor(6) as ex:
        for msg in ex.map(lambda a: fetch(Path(root), a), ids):
            print(msg)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])

