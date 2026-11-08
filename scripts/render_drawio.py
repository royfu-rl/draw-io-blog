"""drawio → PNG，用 draw.io 官方 viewer 在 headless chromium 里渲染；顺带出一张「原图 / 复刻」对比图。

用法: python3 render_drawio.py <a.drawio> [b.drawio ...] [--scale 2]
产出:
    output/render/<stem>.png               复刻渲染图
    middle_processing/compare/<stem>.png   上：原图 output/original/<stem>.png  下：复刻
"""
import argparse
import os
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
VIEWER = Path(__file__).with_name("viewer-static.min.js")
PAGE = """<!doctype html><html><head><meta charset="utf-8">
<style>body{margin:0;background:#fff}</style></head><body><div id="c"></div></body></html>"""
MOUNT = """xml => new GraphViewer(document.getElementById('c'), mxUtils.parseXml(xml).documentElement,
    {border: 16, toolbar: null, nav: false, resize: true, highlight: 'none', lightbox: false})"""


def render(page, src: Path, dst: Path) -> None:
    page.set_content(PAGE)
    page.add_script_tag(path=str(VIEWER))
    page.evaluate(MOUNT, src.read_text(encoding="utf-8"))
    page.wait_for_selector("#c svg")
    page.wait_for_timeout(1500)  # 等外链字体（jsdelivr）/ 图片
    page.evaluate("document.fonts.ready")
    page.locator("#c svg").first.screenshot(path=str(dst))


def compare(original: Path, rendered: Path, dst: Path) -> None:
    a, b = Image.open(original).convert("RGB"), Image.open(rendered).convert("RGB")
    w = 1800
    a = a.resize((w, round(a.height * w / a.width)))
    b = b.resize((w, round(b.height * w / b.width)))
    font = ImageFont.truetype("LiberationSans-Bold.ttf", 28)
    canvas = Image.new("RGB", (w, a.height + b.height + 100), "white")
    d = ImageDraw.Draw(canvas)
    d.text((10, 8), "ORIGINAL", fill="red", font=font)
    canvas.paste(a, (0, 48))
    d.line([(0, a.height + 56), (w, a.height + 56)], fill="red", width=3)
    d.text((10, a.height + 62), "DRAW.IO REPRODUCTION", fill="red", font=font)
    canvas.paste(b, (0, a.height + 100))
    canvas.save(dst)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--scale", type=float, default=2)
    args = ap.parse_args()
    (ROOT / "output/render").mkdir(parents=True, exist_ok=True)
    (ROOT / "middle_processing/compare").mkdir(parents=True, exist_ok=True)
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    with sync_playwright() as p:
        browser = p.chromium.launch(proxy={"server": proxy} if proxy else None)
        page = browser.new_page(viewport={"width": 4000, "height": 3000}, device_scale_factor=args.scale)
        # 屏蔽 Google Fonts：走代理时好时坏，加载一半会让文字退回衬线体；改用本机已装的同名字体，结果稳定
        page.route(re.compile(r"fonts\.(googleapis|gstatic)\.com"), lambda route: route.abort())
        for src in args.files:
            dst = ROOT / "output/render" / f"{src.stem}.png"
            render(page, src.resolve(), dst)
            original = ROOT / "output/original" / f"{src.stem}.png"
            if original.exists():
                compare(original, dst, ROOT / "middle_processing/compare" / f"{src.stem}.png")
            print(f"ok  {dst}")
        browser.close()


if __name__ == "__main__":
    main()

