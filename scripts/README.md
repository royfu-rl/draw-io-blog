# scripts

## 流程

1. 选图
   - `fetch_papergallery.py`：拉 PaperGallery 256 张 pipeline 图 + 元数据，拼联系表目测
   - `fetch_arxiv_figs.py <id>...`：下 arXiv 源码包，抽出原始图（PDF 转 PNG）
2. 复刻（每张图循环 3 轮以上）
   - 写 `output/drawio/NN-name.drawio`（未压缩 XML）
   - `render_drawio.py output/drawio/NN-name.drawio`
     - 出 `output/render/NN-name.png`
     - 出 `middle_processing/compare/NN-name.png`（上原图、下复刻），看图改坐标 / 颜色 / 字号
3. 字体收尾：`normalize_fonts.py output/drawio/*.drawio`
   - draw.io 会把 `css?family=X` 改成只请求 400/500，粗体变假粗；脚本统一改成 css2 + 显式字重
4. 出画廊：`build_gallery.py` → `output/gallery.html`（数据在 `middle_processing/figures.json`）

## 复刻要点

- 图元全部原生：框、箭头、文字、token、矩阵都可编辑
- 图标用矢量 SVG 内嵌（`image=data:image/svg+xml,<base64>`，**不写 `;base64`**）
  - Fluent Emoji Flat / Twemoji / Tabler / Simple Icons（jsdelivr 可直连）
- 照片类素材从原图裁切内嵌，不栅格化含文字的区域
- 颜色用 PIL 从原图取色，不凭感觉

## 环境（换 pod 要重装）

- `pip install playwright pymupdf && python3 -m playwright install chromium`
- `viewer-static.min.js`：draw.io 官方 viewer，已放在本目录
- 渲染时会屏蔽 Google Fonts、只用本机字体，所以复刻用到的字体要先装进 `/usr/share/fonts` 或 `~/.fonts`
  - 来源：`https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/<family>/`（文件名带 `[wght]` 时 curl 加 `-g`）
  - Helvetica / Times / Courier 由 `apt install fonts-liberation` 提供同度量替身

