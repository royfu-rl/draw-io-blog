"""PaperGallery pipeline 候选池：解析元数据 → 下载图片 → 拼联系表（供人工目测筛选）。

用法: python3 -I fetch_papergallery.py <middle_processing 目录>
产出:
    <dir>/papergallery/meta.json        全部条目 {id,title,conference,tags,image}
    <dir>/papergallery/img/*.jpg        原图
    <dir>/papergallery/sheet_XX.jpg     3x4 联系表，格子左上角是序号
"""
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = "https://longhz140516.github.io"
COLS, ROWS, CELL = 3, 4, (640, 400)


def parse(page: str) -> list[dict]:
    t = html.unescape(page)
    items = []
    for m in re.finditer(r'"id":\[0,"(pipeline-[^"]+)"\],"title":\[0,"(.*?)"\].*?"conference":\[0,"(.*?)"\],"image":\[0,"(.*?)"\],"tags":\[1,\[(.*?)\]\]\]', t):
        pid, title, conf, image, tags = m.groups()
        items.append({"id": pid, "title": title, "conference": conf, "image": image,
                      "tags": re.findall(r'\[0,"(.*?)"\]', tags)})
    return list({i["id"]: i for i in items}.values())


def download(item: dict, out: Path) -> None:
    dst = out / Path(item["image"]).name
    if not dst.exists():
        urllib.request.urlretrieve(BASE + urllib.parse.quote(item["image"]), dst)


def sheets(items: list[dict], img_dir: Path, out: Path) -> None:
    font = ImageFont.truetype("LiberationSans-Bold.ttf", 28)
    per = COLS * ROWS
    for s in range(0, len(items), per):
        sheet = Image.new("RGB", (COLS * CELL[0], ROWS * CELL[1]), "white")
        for k, item in enumerate(items[s:s + per]):
            im = Image.open(img_dir / Path(item["image"]).name).convert("RGB")
            im.thumbnail((CELL[0] - 10, CELL[1] - 10))
            x, y = (k % COLS) * CELL[0], (k // COLS) * CELL[1]
            sheet.paste(im, (x + 5, y + 5))
            ImageDraw.Draw(sheet).text((x + 8, y + 6), str(s + k), fill="red", font=font)
        sheet.save(out / f"sheet_{s // per:02d}.jpg", quality=85)


def main(root: str) -> None:
    out = Path(root) / "papergallery"
    (out / "img").mkdir(parents=True, exist_ok=True)
    page = urllib.request.urlopen(BASE + "/PaperGallery/images/pipeline/").read().decode()
    items = parse(page)
    with ThreadPoolExecutor(16) as ex:
        list(ex.map(lambda i: download(i, out / "img"), items))
    for k, item in enumerate(items):
        item["idx"] = k
    (out / "meta.json").write_text(json.dumps(items, ensure_ascii=False, indent=1))
    sheets(items, out / "img", out)
    print(f"{len(items)} items -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])

