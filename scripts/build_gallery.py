"""figures.json + 复刻产物 → output/gallery.html（Warm Editorial 风格画廊）。

用法: python3 -I build_gallery.py [--out output/gallery.html]   （--out 相对项目根，如 index.html）
输入:
    middle_processing/figures.json   每张图的元数据 + 设计要点
    output/{original,render,drawio}/ 原图 / 复刻渲染 / drawio 源文件
"""
import argparse
import html
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"

RULES = [
    ("一图一套设计系统", "1 个字体家族、2–3 个主色、统一线宽与圆角。BLIP-2 只有一蓝一黄加灰，Llama 2 只用一组蓝灰，照样耐看。"),
    ("颜色即语义，省掉图例", "冻结 = 蓝 + 雪花、可训练 = 橙 / 紫 + 火焰（Flamingo、AgentThink、LLaMA-Omni）；LC-R1 的序列色条本身就是图例。"),
    ("形状也是编码", "Llama 2：数据 = 圆环、过程 = 菱形、模型 = 椭圆；MHA2MLA：梯形 = Linear、斜纹 = Cached；JanusVLN：立方体 = 3D token。"),
    ("阶段 = 等宽面板 + 彩色标题条", "MERIT、AgentThink、μ-Bench、MSSBench 都是这套：浅底面板 + 高饱和标题胶囊或编号徽章，阶段间用粗箭头 / chevron。"),
    ("用褪色和对称讲主次", "DiT 把对照变体整体褪色；ToT 四栏同骨架只改中间；JanusVLN 左右镜像、Motus 三栏并列，差异一眼可见。"),
    ("线条克制，强调色只给关键流", "细灰连线从模块下方穿过（LLaMA-Omni），折线统一圆角（Mamba）；只有反馈环 / 训练流用亮色或渐变（InstructGPT、GRAPE）。"),
]


def cell_count(drawio: Path) -> int:
    return len(re.findall(r'<mxCell [^>]*(?:vertex|edge)="1"', drawio.read_text(encoding="utf-8")))


def card(f: dict, k: int, p: str) -> str:
    e = html.escape
    fid, done = f["id"], (OUT / "render" / f"{f['id']}.png").exists()
    img = f"{p}render/{fid}.png" if done else f"{p}original/{fid}.png"
    sw = "".join(f'<button class="sw" style="--c:{c}" data-hex="{c}" title="点击复制 {c}"></button>' for c in f.get("palette", []))
    take = "".join(f"<li>{e(t)}</li>" for t in f.get("takeaways_zh", []))
    fonts = " · ".join(e(x) for x in f.get("fonts", []))
    cells = cell_count(OUT / "drawio" / f"{fid}.drawio") if (OUT / "drawio" / f"{fid}.drawio").exists() else 0
    kind = "流程图" if f["type"] == "workflow" else "架构图"
    notes = ""
    if f.get("raster_embeds") or f.get("known_diffs"):
        notes = (f'<details><summary>复刻说明</summary><dl>'
                 f'<dt>可编辑图元</dt><dd>{cells} 个</dd>'
                 f'<dt>位图嵌入</dt><dd>{e(f.get("raster_embeds", "—"))}</dd>'
                 f'<dt>与原图差异</dt><dd>{e(f.get("known_diffs", "—"))}</dd></dl></details>')
    links = (f'<a href="{p}drawio/{fid}.drawio" download>⬇ .drawio</a>' if done else '<span class="pending">复刻中…</span>')
    links += f'<a href="{p}original/{fid}.png" target="_blank">原图 PNG</a>'
    links += f'<a href="{p}render/{fid}.png" target="_blank">复刻 PNG</a>' if done else ""
    return f"""
<article class="card r" style="animation-delay:{.05 * k + .3:.2f}s" data-type="{f['type']}">
  <div class="plate"><span><b>PLATE {fid[:2]}</b> · {kind} · {e(f['source'])}</span>
    <div class="seg">{'<button class="on" data-v="render">draw.io 复刻</button>' if done else ''}<button {'' if done else 'class="on"'} data-v="original">原图</button></div></div>
  <div class="viewer">
    <img loading="lazy" src="{img}" data-render="{p}render/{fid}.png" data-original="{p}original/{fid}.png" alt="{e(f['name'])}">
  </div>
  <div class="body">
    <h3>{e(f['name'])}<span class="fig">{e(f['fig'])}</span></h3>
    <p class="paper"><a href="https://arxiv.org/abs/{f['arxiv']}" target="_blank">{e(f['paper'])}</a><span class="venue">{e(f['venue'])}</span></p>
    {f'<div class="meta"><div class="sws">{sw}</div><div class="fonts">{fonts}</div></div>' if sw else ''}
    {f'<ul class="take">{take}</ul>' if take else ''}
    {notes}
    <div class="links">{links}</div>
  </div>
</article>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="output/gallery.html")
    out = ROOT / ap.parse_args().out
    rel = os.path.relpath(OUT, out.parent)
    p = "" if rel == "." else f"{rel}/"  # 页面到 output/ 的相对前缀
    figs = json.loads((ROOT / "middle_processing/figures.json").read_text(encoding="utf-8"))
    done = [f for f in figs if (OUT / "render" / f"{f['id']}.png").exists()]
    n_wf = sum(f["type"] == "workflow" for f in figs)
    cells = sum(cell_count(OUT / "drawio" / f"{f['id']}.drawio") for f in done)
    rules = "".join(f'<li><b>{html.escape(a)}</b><span>{html.escape(b)}</span></li>' for a, b in RULES)
    page = TEMPLATE.format(
        n=len(figs), n_done=len(done), n_wf=n_wf, n_arch=len(figs) - n_wf, cells=f"{cells:,}",
        cards="".join(card(f, k, p) for k, f in enumerate(figs)), rules=rules)
    out.write_text(page, encoding="utf-8")
    print(f"{out.name}: {len(done)}/{len(figs)} reproduced, {cells} cells")


TEMPLATE = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>学术流程图图鉴</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,500;0,9..144,900;1,9..144,300;1,9..144,400&family=Newsreader:ital,opsz@0,6..72;1,6..72&family=JetBrains+Mono:wght@400;500&family=Noto+Serif+SC:wght@400;600;900&family=Noto+Sans+SC:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root{{--paper:#f3efe6;--ink:#211d18;--clay:#c2562f;--clay2:#8f3b1e;--sage:#5c6a52;--gold:#b8893a;--line:#ddd5c6;--mute:#7d7464;
    --serif:'Newsreader','Noto Serif SC',serif;--display:'Fraunces','Noto Serif SC',serif;--mono:'JetBrains Mono','Noto Sans SC',monospace}}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:var(--paper);color:var(--ink);font-family:var(--serif);font-size:17px;line-height:1.75;
    background-image:radial-gradient(circle at 85% 0%,rgba(194,86,47,.12),transparent 45%),radial-gradient(circle at 0% 80%,rgba(92,106,82,.12),transparent 40%);background-attachment:fixed}}
  .grain{{position:fixed;inset:0;z-index:0;pointer-events:none;opacity:.5;mix-blend-mode:multiply;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.05'/%3E%3C/svg%3E")}}
  .wrap{{max-width:1320px;margin:0 auto;padding:0 32px;position:relative;z-index:1}}
  @keyframes rise{{from{{opacity:0;transform:translateY(24px)}}to{{opacity:1;transform:none}}}}
  .r{{opacity:0;animation:rise .85s cubic-bezier(.2,.7,.2,1) forwards}}
  .d1{{animation-delay:.05s}}.d2{{animation-delay:.16s}}.d3{{animation-delay:.27s}}.d4{{animation-delay:.38s}}

  header{{padding:12vh 0 5vh;max-width:900px}}
  .tag{{font-family:var(--mono);font-size:12px;letter-spacing:.4em;text-transform:uppercase;color:var(--clay);margin-bottom:26px}}
  h1{{font-family:var(--display);font-weight:900;font-size:clamp(48px,8vw,96px);line-height:.98;letter-spacing:-.02em;font-variation-settings:"opsz" 144}}
  h1 em{{font-style:italic;font-weight:300;color:var(--clay)}}
  .lede{{font-size:20px;color:#3a342b;margin-top:30px;max-width:760px}}
  .byline{{display:flex;gap:28px;flex-wrap:wrap;margin-top:34px;padding-top:20px;border-top:1.5px solid var(--ink);
    font-family:var(--mono);font-size:12px;color:var(--mute);letter-spacing:.06em}}
  .byline b{{color:var(--ink);font-weight:500}}

  .stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:12px;overflow:hidden;margin:10px 0 56px}}
  .stat{{background:var(--paper);padding:24px 22px}}
  .stat .v{{font-family:var(--display);font-weight:900;font-size:44px;color:var(--clay2);line-height:1;font-variation-settings:"opsz" 100}}
  .stat .l{{font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--mute);margin-top:10px}}

  h2{{font-family:var(--display);font-weight:500;font-size:clamp(28px,3.4vw,40px);letter-spacing:-.015em;line-height:1.15;margin:0 0 8px}}
  h2 .num{{font-family:var(--mono);font-size:.34em;color:var(--clay);vertical-align:super;margin-right:.6em}}
  .sub{{color:var(--mute);margin-bottom:26px}}
  .howto{{display:grid;grid-template-columns:repeat(3,1fr);gap:22px;margin:26px 0 64px;counter-reset:s}}
  .howto li{{list-style:none;border-top:1.5px solid var(--ink);padding-top:14px;counter-increment:s}}
  .howto li::before{{content:"0" counter(s);font-family:var(--mono);font-size:12px;color:var(--clay);display:block;margin-bottom:6px}}
  .howto b{{font-family:var(--display);font-weight:500;font-size:20px;display:block;margin-bottom:4px}}
  .howto span{{color:#4a4338;font-size:16px}}
  code{{font-family:var(--mono);font-size:.82em;background:rgba(194,86,47,.08);padding:1px 6px;border-radius:4px;color:var(--clay2)}}

  .filters{{display:flex;gap:10px;margin:0 0 28px;position:sticky;top:0;z-index:5;padding:14px 0;background:linear-gradient(var(--paper) 70%,transparent)}}
  .filters button{{font-family:var(--mono);font-size:12px;letter-spacing:.08em;border:1px solid var(--ink);background:transparent;color:var(--ink);
    padding:7px 16px;border-radius:30px;cursor:pointer}}
  .filters button.on{{background:var(--ink);color:var(--paper)}}

  .grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:34px}}
  .card{{background:#fffdf8;border:1px solid var(--line);border-radius:14px;overflow:hidden;box-shadow:0 20px 44px -30px rgba(80,50,20,.45);display:flex;flex-direction:column}}
  .card.hide{{display:none}}
  .plate{{display:flex;justify-content:space-between;align-items:center;gap:10px;font-family:var(--mono);font-size:11px;letter-spacing:.12em;color:var(--mute);padding:9px 12px 9px 18px;border-bottom:1px solid var(--line)}}
  .plate b{{color:var(--clay);font-weight:500}}
  .viewer{{position:relative;background:#fff;border-bottom:1px solid var(--line);aspect-ratio:16/9;display:flex;align-items:center;justify-content:center;padding:18px;cursor:zoom-in}}
  .viewer img{{max-width:100%;max-height:100%;object-fit:contain}}
  .seg{{display:flex;flex:none;letter-spacing:0;background:rgba(243,239,230,.92);border:1px solid var(--line);border-radius:20px;padding:2px;z-index:2}}
  .seg button{{font-family:var(--mono);font-size:11px;border:0;background:transparent;color:var(--mute);padding:4px 10px;border-radius:16px;cursor:pointer}}
  .seg button.on{{background:var(--ink);color:var(--paper)}}
  .body{{padding:20px 22px 18px;display:flex;flex-direction:column;gap:12px;flex:1}}
  .card h3{{font-family:var(--display);font-weight:900;font-size:28px;line-height:1.1;letter-spacing:-.01em}}
  .card h3 .fig{{font-family:var(--mono);font-weight:400;font-size:12px;color:var(--mute);margin-left:10px;letter-spacing:.06em}}
  .paper{{font-size:15px;line-height:1.5;color:#4a4338}}
  .paper a{{color:inherit;text-decoration:none;border-bottom:1px solid var(--line)}}
  .paper a:hover{{color:var(--clay2);border-color:var(--clay)}}
  .venue{{font-family:var(--mono);font-size:11px;color:var(--clay2);background:rgba(194,86,47,.09);padding:2px 8px;border-radius:10px;margin-left:8px;white-space:nowrap}}
  .meta{{display:flex;align-items:center;gap:14px;flex-wrap:wrap}}
  .sws{{display:flex}}
  .sw{{width:26px;height:26px;border-radius:50%;background:var(--c);border:2px solid #fffdf8;margin-right:-6px;cursor:pointer;box-shadow:0 0 0 1px var(--line);transition:transform .15s}}
  .sw:hover{{transform:translateY(-3px);z-index:1}}
  .fonts{{font-family:var(--mono);font-size:11.5px;color:var(--mute)}}
  .take{{list-style:none;font-size:15.5px;line-height:1.6;color:#2c2820}}
  .take li{{padding-left:18px;position:relative;margin:5px 0}}
  .take li::before{{content:"";position:absolute;left:2px;top:.62em;width:7px;height:7px;border-radius:50%;background:var(--clay)}}
  details{{font-size:14px;color:#4a4338}}
  details summary{{font-family:var(--mono);font-size:11.5px;letter-spacing:.06em;color:var(--mute);cursor:pointer}}
  details dl{{display:grid;grid-template-columns:auto 1fr;gap:4px 14px;margin-top:8px}}
  details dt{{font-family:var(--mono);font-size:11px;color:var(--mute);padding-top:3px}}
  .links{{display:flex;gap:8px;flex-wrap:wrap;margin-top:auto;padding-top:6px}}
  .links a,.links .pending{{font-family:var(--mono);font-size:11.5px;text-decoration:none;color:var(--ink);border:1px solid var(--line);padding:5px 12px;border-radius:20px}}
  .links a:first-child{{background:var(--clay);border-color:var(--clay);color:#fff}}
  .links a:hover{{border-color:var(--ink)}}
  .links .pending{{color:var(--mute);border-style:dashed}}

  .rules{{margin:80px 0 0;display:grid;grid-template-columns:repeat(3,1fr);gap:0 34px;list-style:none}}
  .rules li{{border-top:1.5px solid var(--ink);padding:16px 0 28px}}
  .rules b{{font-family:var(--display);font-weight:500;font-size:21px;display:block;margin-bottom:6px}}
  .rules span{{color:#4a4338;font-size:16px}}
  footer{{margin:9vh 0 12vh;padding-top:30px;border-top:1.5px solid var(--ink);font-family:var(--mono);font-size:12px;color:var(--mute);line-height:2}}
  footer a{{color:var(--clay2)}}

  .lb{{position:fixed;inset:0;z-index:20;background:rgba(33,29,24,.86);display:none;overflow:auto;padding:40px 4vw}}
  .lb.on{{display:block}}
  .lb figure{{background:#fff;border-radius:10px;padding:18px;margin:0 auto 24px;max-width:1500px}}
  .lb figcaption{{font-family:var(--mono);font-size:12px;letter-spacing:.12em;color:var(--clay);margin-bottom:10px}}
  .lb img{{width:100%;display:block}}
  .lb .x{{position:fixed;top:16px;right:22px;font-family:var(--mono);color:var(--paper);font-size:13px;cursor:pointer;letter-spacing:.1em}}
  .toast{{position:fixed;bottom:28px;left:50%;transform:translateX(-50%);background:var(--ink);color:var(--paper);font-family:var(--mono);font-size:12px;padding:8px 16px;border-radius:20px;opacity:0;transition:opacity .2s;z-index:30}}
  .toast.on{{opacity:1}}
  @media(max-width:900px){{.grid{{grid-template-columns:1fr}}.howto,.rules{{grid-template-columns:1fr}}.stats{{grid-template-columns:repeat(2,1fr)}}}}
  @media(max-width:560px){{.wrap{{padding:0 16px}}body{{font-size:16px}}}}
</style>
</head>
<body>
<div class="grain"></div>
<div class="wrap">

<header>
  <div class="tag r d1">Figure Atlas · {n} Plates</div>
  <h1 class="r d2">学术流程图<br><em>图鉴</em></h1>
  <p class="lede r d3">从 PaperGallery 策展的 256 张框架图与 16 篇经典论文中，挑出 {n} 张最耐看的流程图 / 架构图，全部用 draw.io 一比一复刻成可编辑源文件。画新图时，先在这里找一张气质相近的，下载 .drawio 改字换色即可。</p>
  <div class="byline r d4"><span><b>{n_done}/{n}</b> 已复刻</span><span>来源 · PaperGallery + arXiv</span><span>2026.11.05</span></div>
</header>

<section class="stats r d4">
  <div class="stat"><div class="v">{n}</div><div class="l">张入选图</div></div>
  <div class="stat"><div class="v">{n_wf}</div><div class="l">流程图 workflow</div></div>
  <div class="stat"><div class="v">{n_arch}</div><div class="l">架构图 architecture</div></div>
  <div class="stat"><div class="v">{cells}</div><div class="l">可编辑图元</div></div>
</section>

<h2 class="r d4"><span class="num">01</span>怎么用</h2>
<ol class="howto r d4">
  <li><b>按气质找图</b><span>流程图看 01–11，模型架构看 12–20。卡片右上角可切换「复刻 / 原图」，点图放大对比。</span></li>
  <li><b>下载 .drawio 改</b><span>橙色按钮下载源文件，用 draw.io 打开：文字、颜色、箭头全部可编辑，图标是矢量 SVG。</span></li>
  <li><b>抄配色和字体</b><span>色点点击即复制 hex；字体列在色点旁边，Google Fonts 可直接在 draw.io 里加载。</span></li>
</ol>

<h2><span class="num">02</span>图版</h2>
<p class="sub">每张卡片下方是它「为什么好看」的三条拆解。</p>
<nav class="filters">
  <button class="on" data-f="all">全部 {n}</button><button data-f="workflow">流程图 {n_wf}</button><button data-f="architecture">架构图 {n_arch}</button>
</nav>
<main class="grid">{cards}
</main>

<section>
  <h2 style="margin-top:80px"><span class="num">03</span>复刻 20 张图之后的六条心法</h2>
  <ul class="rules">{rules}</ul>
</section>

<footer>
  候选池 · <a href="https://longhz140516.github.io/PaperGallery/images/pipeline/" target="_blank">PaperGallery / Pipeline</a>（256 张）+ arXiv 源码包中的原始矢量图<br>
  复刻工具链 · draw.io XML → 官方 viewer + headless Chromium 渲染 → 与原图逐轮对比（scripts/render_drawio.py）<br>
  图标 · Fluent Emoji Flat / Tabler / Simple Icons（矢量 SVG 内嵌）；照片类素材从原图裁切
</footer>
</div>

<div class="lb" id="lb"><div class="x">ESC 关闭 ✕</div><figure><figcaption>原图 ORIGINAL</figcaption><img id="lbo"></figure><figure><figcaption>DRAW.IO 复刻</figcaption><img id="lbr"></figure></div>
<div class="toast" id="toast"></div>
<script>
  document.querySelectorAll('.seg button').forEach(b => b.onclick = ev => {{
    ev.stopPropagation();
    const v = b.closest('.card'), img = v.querySelector('.viewer img');
    v.querySelectorAll('.seg button').forEach(x => x.classList.toggle('on', x === b));
    img.src = img.dataset[b.dataset.v];
  }});
  const lb = document.getElementById('lb');
  document.querySelectorAll('.viewer').forEach(v => v.onclick = () => {{
    const img = v.querySelector('img'), done = v.closest('.card').querySelector('[data-v=render]');
    document.getElementById('lbo').src = img.dataset.original;
    document.getElementById('lbr').src = done ? img.dataset.render : '';
    document.getElementById('lbr').parentElement.style.display = done ? '' : 'none';
    lb.classList.add('on');
  }});
  lb.onclick = () => lb.classList.remove('on');
  document.onkeydown = e => {{ if (e.key === 'Escape') lb.classList.remove('on'); }};
  document.querySelectorAll('.filters button').forEach(b => b.onclick = () => {{
    document.querySelectorAll('.filters button').forEach(x => x.classList.toggle('on', x === b));
    document.querySelectorAll('.card').forEach(c => c.classList.toggle('hide', b.dataset.f !== 'all' && c.dataset.type !== b.dataset.f));
  }});
  const toast = document.getElementById('toast');
  document.querySelectorAll('.sw').forEach(s => s.onclick = () => {{
    navigator.clipboard && navigator.clipboard.writeText(s.dataset.hex);
    toast.textContent = '已复制 ' + s.dataset.hex; toast.classList.add('on');
    setTimeout(() => toast.classList.remove('on'), 1200);
  }});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()

