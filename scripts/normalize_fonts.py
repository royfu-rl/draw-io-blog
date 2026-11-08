"""把 drawio 里的 Google Fonts 引用统一成 css2 + 显式字重。

为什么: draw.io 会把短格式 `css?family=X` 改写成只请求 400/500，粗体变成浏览器模拟的假粗体。
用法: python3 -I normalize_fonts.py <a.drawio> [...]   （原地改写，并逐个校验 URL 返回 200）
"""
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# 没写字重时按字体实际提供的字重补全；只有 400 的字体保持 400
DEFAULT_WEIGHTS = {
    "Nunito": "400;700;800", "Carlito": "400;700", "Comic Relief": "400;700", "Montserrat": "400;600;700",
    "Source Sans 3": "400;600;700", "Lato": "400;700", "Cabin": "400;700", "Cutive Mono": "400", "Didact Gothic": "400",
}


def to_css2(url: str) -> str:
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["family"][0]
    name, _, spec = q.partition(":")
    if not spec:
        return f"https://fonts.googleapis.com/css2?family={name.replace(' ', '+')}:wght@{DEFAULT_WEIGHTS.get(name, '400;700')}"
    tokens = spec.split(",")
    if any(t.endswith("i") for t in tokens):
        axes = sorted({(1 if t.endswith("i") else 0, int(t.rstrip("i") or 400)) for t in tokens})
        return f"https://fonts.googleapis.com/css2?family={name.replace(' ', '+')}:ital,wght@" + ";".join(f"{i},{w}" for i, w in axes)
    return f"https://fonts.googleapis.com/css2?family={name.replace(' ', '+')}:wght@" + ";".join(sorted(tokens, key=int))


def ok(url: str) -> bool:
    for _ in range(5):  # 代理偶发 502，重试
        try:
            return urllib.request.urlopen(url, timeout=20).status == 200
        except urllib.error.HTTPError as e:
            return e.code == 200
        except OSError:
            time.sleep(2)
    return False


def main(files: list[str]) -> None:
    for f in map(Path, files):
        text = f.read_text(encoding="utf-8")
        olds = set(re.findall(r"fontSource=([^;\"&]+)", text))
        for old in olds:
            url = urllib.parse.unquote(old)
            if "fonts.googleapis.com/css?" not in url:
                continue
            new = to_css2(url)
            if not ok(new):
                print(f"SKIP {f.name}: {new} 无效，保留原值")
                continue
            text = text.replace(f"fontSource={old}", "fontSource=" + urllib.parse.quote(new, safe=""))
            print(f"{f.name}: {url.split('family=')[1]} -> {new.split('family=')[1]}")
        f.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])

