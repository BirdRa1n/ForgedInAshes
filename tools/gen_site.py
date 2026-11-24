"""Tutorial site of the mod (static HTML for Vercel), generated from the mod's own data so it grows with the mod.

Sources:
  - recipes.xml / blocks.xml / items.xml after the mod's patches (fe_common.patched): every fe* item and block gets a
    page (what it is, where it is made, the ingredients with links down to the vanilla materials, what uses it);
  - every machine of the mod gets a page with all the recipes it makes (the mod's and the vanilla ones moved to it);
  - Data/fe_processes.xml: every <chain> becomes a production-line tutorial (planned ones marked "em construção");
  - Localization.csv of the mod and of the game: names and descriptions in pt-BR.
No game files are copied (no icons); the only image is the mod's own render (Art/feKinetic/preview_lineup.png).

Output: site/ (index.html, itens/*.html, maquinas/*.html, linhas/*.html, style.css, app.js, vercel.json).
Deploy: Vercel project with "Root Directory" = site (no build command).

Usage: python tools/gen_site.py
"""
import csv
import html
import re
import shutil
import sys
from collections import defaultdict

from lxml import etree

import fe_common as fe

SITE = fe.REPO / "site"
PROC = fe.MOD_DIR / "Data" / "fe_processes.xml"
KIND_PT = {"melt": "Fundir", "cast": "Moldar", "press": "Prensar", "turn": "Tornear", "crush": "Triturar",
           "wash": "Lavar", "mix": "Misturar", "dry": "Secar", "distill": "Destilar", "spin": "Fiar",
           "assemble": "Montar", "sequence": "Montar em sequência"}
FLUID_PT = {"water": "Água", "steam": "Vapor", "oil": "Óleo", "gasoline": "Gasolina", "lubricant": "Lubrificante"}


def esc(s):
    return html.escape(s or "", quote=True)


def slug(s):
    return re.sub(r"[^A-Za-z0-9_-]", "-", s)


# ------------------------------------------------------------------ localization
def load_loc():
    loc = {}
    for path in (fe.vanilla_config() / "Localization.csv", fe.MOD_CONFIG / "Localization.csv"):
        if not path.exists():
            continue
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = csv.reader(f)
            head = next(rows)
            ki = head.index("Key")
            ci = head.index("brazilian") if "brazilian" in head else None
            ei = head.index("english")
            for r in rows:
                if len(r) <= ei or not r[ki]:
                    continue
                v = r[ci] if ci is not None and len(r) > ci and r[ci] else r[ei]
                loc[r[ki]] = v.replace("\\n", "\n")
    return loc


# ------------------------------------------------------------------ data
def load():
    recipes, _ = fe.patched("recipes.xml")
    blocks, _ = fe.patched("blocks.xml")
    items, _ = fe.patched("items.xml")
    rec = defaultdict(list)          # product -> [recipe elements]
    for r in recipes.iter("recipe"):
        if r.get("name"):
            rec[r.get("name")].append(r)
    props = {}
    for e in list(blocks.iter("block")) + list(items.iter("item")):
        d = {}
        for p in e.findall("property"):
            if p.get("name"):
                d[p.get("name")] = p.get("value")
        props[e.get("name")] = d
    block_names = {e.get("name") for e in blocks.iter("block")}
    return rec, props, block_names


def main():
    loc = load_loc()
    rec, props, block_names = load()

    def name(n):
        return loc.get(n) or n

    def desc(n):
        k = props.get(n, {}).get("DescriptionKey") or n + "Desc"
        return loc.get(k, "")

    mod_things = sorted(n for n in rec if n.startswith("fe"))
    areas = defaultdict(list)        # craft area -> [(product, recipe)]
    for n, rs in rec.items():
        for r in rs:
            a = r.get("craft_area")
            if a and a.startswith("fe"):
                areas[a].append((n, r))
    used_in = defaultdict(set)
    for n in mod_things:
        for r in rec[n]:
            for ing in r.findall("ingredient"):
                used_in[ing.get("name")].add(n)

    def link(n, depth=1):
        up = "../" * depth
        if n in rec and n.startswith("fe"):
            return '<a href="%sitens/%s.html">%s</a>' % (up, slug(n), esc(name(n)))
        if n in areas:
            return '<a href="%smaquinas/%s.html">%s</a>' % (up, slug(n), esc(name(n)))
        return '<span class="vanilla" title="%s">%s</span>' % (esc(n), esc(name(n)))

    def where(r, depth=1):
        a = r.get("craft_area")
        if not a:
            return "na mão (inventário)"
        if a in areas or a.startswith("fe"):
            return link(a, depth) if a in areas else esc(name(a))
        return esc({"workbench": "Bancada", "forge": "Forja", "chemistryStation": "Estação Química",
                    "campfire": "Fogueira", "cementMixer": "Misturador de Cimento"}.get(a, a))

    def tree(n, seen, depth, top):
        """the craft tree of a mod thing, down to vanilla materials"""
        rs = rec.get(n)
        if not rs or not n.startswith("fe") or n in seen or depth > 5:
            return ""
        r = rs[0]
        out = ['<ul class="tree">']
        for ing in r.findall("ingredient"):
            i = ing.get("name")
            sub = tree(i, seen | {n}, depth + 1, top)
            out.append('<li><span class="qty">%s×</span> %s%s</li>' % (esc(ing.get("count")), link(i, top),
                                                                        sub and ('<div class="sub">feito em %s</div>%s'
                                                                                 % (where(rec[i][0], top), sub))))
        out.append("</ul>")
        return "".join(out)

    procs, chains, pnames = {}, [], {}
    if PROC.exists():
        root = etree.parse(str(PROC)).getroot()
        for e in root:
            if not isinstance(e.tag, str):
                continue
            if e.tag in ("fluid", "machine", "item"):
                pnames[e.get("name")] = e.get("text")
            elif e.tag == "process":
                procs[e.get("id")] = e
            elif e.tag == "chain":
                chains.append(e)

    def pname(n):
        return pnames.get(n) or FLUID_PT.get(n) or name(n)

    # ------------------------------------------------------------ output
    if SITE.exists():
        for sub in ("itens", "maquinas", "linhas"):
            shutil.rmtree(SITE / sub, ignore_errors=True)
    for sub in ("itens", "maquinas", "linhas", "img"):
        (SITE / sub).mkdir(parents=True, exist_ok=True)
    lineup = fe.REPO / "Art" / "feKinetic" / "preview_lineup.png"
    if lineup.exists():
        shutil.copy(lineup, SITE / "img" / "maquinas.png")

    def page(title, body, depth):
        up = "../" * depth
        return ("<!doctype html>\n<html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
                "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
                "<title>%s · Ferro &amp; Engrenagem</title><link rel=\"stylesheet\" href=\"%sstyle.css\"></head><body>"
                "<header class=\"top\"><a class=\"brand\" href=\"%sindex.html\"><span class=\"gear\">⚙</span> Ferro &amp; "
                "Engrenagem</a><nav><a href=\"%sindex.html#linhas\">Linhas</a><a href=\"%sindex.html#itens\">Itens</a>"
                "<a href=\"%sindex.html#maquinas\">Máquinas</a></nav></header><main>%s</main>"
                "<footer>Mod para 7 Days to Die · tutoriais gerados a partir dos arquivos do mod · "
                "valores sujeitos a balanceamento</footer><script src=\"%sapp.js\"></script></body></html>\n"
                % (esc(title), up, up, up, up, up, body, up))

    # item pages
    for n in mod_things:
        rs = rec[n]
        parts = ['<p class="crumb"><a href="../index.html#itens">Itens</a> / %s</p>' % esc(name(n)),
                 "<h1>%s</h1>" % esc(name(n))]
        d = desc(n)
        if d:
            parts.append('<p class="lead">%s</p>' % esc(d).replace("\n", "<br>"))
        for r in rs:
            parts.append('<section class="card"><h2>Como fazer</h2><p>Fabricado em <b>%s</b> · rende <b>%s</b> · '
                         'tempo %s s</p>' % (where(r), esc(r.get("count", "1")), esc(r.get("craft_time", "padrão"))))
            parts.append('<ol class="steps">')
            for ing in r.findall("ingredient"):
                i = ing.get("name")
                hint = ""
                if i in rec and i.startswith("fe"):
                    hint = ' <span class="hint">(feito em %s)</span>' % where(rec[i][0])
                parts.append('<li><span class="qty">%s×</span> %s%s</li>' % (esc(ing.get("count")), link(i), hint))
            parts.append("</ol></section>")
        t = tree(n, set(), 0, 1)
        if t:
            parts.append('<section class="card"><h2>Árvore completa</h2><p class="muted">Tudo o que precisa, até os '
                         'materiais do jogo.</p>%s</section>' % t)
        if used_in.get(n):
            parts.append('<section class="card"><h2>Usado em</h2><p class="chips">%s</p></section>'
                         % " ".join(link(u) for u in sorted(used_in[n], key=name)))
        if n in areas:
            parts.append('<p><a class="btn" href="../maquinas/%s.html">Ver o que esta máquina fabrica →</a></p>'
                         % slug(n))
        (SITE / "itens" / (slug(n) + ".html")).write_text(page(name(n), "".join(parts), 1), encoding="utf-8")

    # machine pages
    for a in sorted(areas):
        rows = sorted(areas[a], key=lambda pr: name(pr[0]))
        body = ['<p class="crumb"><a href="../index.html#maquinas">Máquinas</a> / %s</p>' % esc(name(a)),
                "<h1>%s</h1>" % esc(name(a))]
        if desc(a):
            body.append('<p class="lead">%s</p>' % esc(desc(a)).replace("\n", "<br>"))
        if a in rec:
            body.append('<p><a class="btn" href="../itens/%s.html">Como construir esta máquina →</a></p>' % slug(a))
        body.append('<input class="filter" placeholder="Filtrar receitas..." data-target="#rl">')
        body.append('<table id="rl" class="list"><thead><tr><th>Produto</th><th>Rende</th><th>Ingredientes</th>'
                    '</tr></thead><tbody>')
        for n, r in rows:
            ings = ", ".join("%s× %s" % (esc(i.get("count")), link(i.get("name"))) for i in r.findall("ingredient"))
            body.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (link(n), esc(r.get("count", "1")), ings))
        body.append("</tbody></table>")
        (SITE / "maquinas" / (slug(a) + ".html")).write_text(page(name(a), "".join(body), 1), encoding="utf-8")

    # production lines
    def io(p, which):
        out = []
        names = (p.get("input") if which == "in" else p.get("output")) or ""
        counts = (p.get("count") if which == "in" else p.get("out_count")) or ""
        cs = counts.split(",")
        for k, n in enumerate(x for x in names.split(",") if x):
            out.append("%s× %s" % (esc(cs[k] if k < len(cs) else "1"), esc(pname(n))))
        f = p.get("fluid_in") if which == "in" else p.get("fluid_out")
        if f:
            out.append("%s L %s" % (esc(p.get("liters") if which == "in" else p.get("out_liters")), esc(pname(f))))
        if which == "in" and p.get("mold"):
            out.append("molde: %s" % esc(pname(p.get("mold"))))
        return out

    chain_cards = []
    for c in chains:
        steps = [procs[s] for s in c.get("steps", "").split(",") if s in procs]
        planned = any(p.get("planned") == "true" for p in steps)
        badge = ('<span class="badge wip">em construção · %s</span>' % esc(c.get("phase", ""))) if planned else \
            '<span class="badge ok">disponível</span>'
        body = ['<p class="crumb"><a href="../index.html#linhas">Linhas de produção</a> / %s</p>' % esc(c.get("text")),
                "<h1>%s %s</h1>" % (esc(c.get("text")), badge),
                '<p class="lead">Linha de produção completa, do material bruto ao produto. Cada passo é uma máquina; '
                'esteiras, calhas e canos ligam uma à outra.</p><ol class="flow">']
        for k, p in enumerate(steps, 1):
            body.append('<li class="step"><div class="num">%d</div><div class="what"><span class="kind">%s</span> '
                        '<b>%s</b>%s<div class="io"><span>%s</span><span class="arrow">→</span><span>%s</span></div>'
                        '<p>%s</p></div></li>'
                        % (k, esc(KIND_PT.get(p.get("kind"), p.get("kind"))), esc(pname(p.get("machine"))),
                           (' <span class="muted">· %s s%s</span>' % (esc(p.get("time")),
                                                                     (" · %s UT" % esc(p.get("torque")))
                                                                     if p.get("torque") else "")),
                           " + ".join(io(p, "in")), " + ".join(io(p, "out")), esc(p.get("text"))))
        body.append("</ol>")
        (SITE / "linhas" / (slug(c.get("product")) + ".html")).write_text(page(c.get("text"), "".join(body), 1),
                                                                           encoding="utf-8")
        chain_cards.append('<a class="tile line" href="linhas/%s.html"><b>%s</b>%s<span>%d passos</span></a>'
                           % (slug(c.get("product")), esc(c.get("text")), badge, len(steps)))

    # index
    groups = defaultdict(list)
    for n in mod_things:
        a = rec[n][0].get("craft_area") or "inventario"
        groups[a].append(n)
    item_html = []
    for a in sorted(groups, key=lambda g: name(g)):
        title = name(a) if a != "inventario" else "Na mão / estações do jogo"
        tiles = "".join('<a class="tile" data-name="%s" href="itens/%s.html"><b>%s</b><span>%s</span></a>'
                        % (esc((name(n) + " " + n).lower()), slug(n), esc(name(n)),
                           "máquina" if n in block_names else "item") for n in sorted(groups[a], key=name))
        item_html.append('<h3>%s</h3><div class="grid">%s</div>' % (esc(title), tiles))
    machine_tiles = "".join('<a class="tile" href="maquinas/%s.html"><b>%s</b><span>%d receitas</span></a>'
                            % (slug(a), esc(name(a)), len(areas[a])) for a in sorted(areas, key=name))
    img = '<img class="hero-img" src="img/maquinas.png" alt="Máquinas do mod">' if lineup.exists() else ""
    index = page("Tutoriais", """
<section class="hero"><h1>Ferro &amp; Engrenagem</h1>
<p class="lead">Máquinas, eixos, vapor e esteiras para 7 Days to Die. Aqui fica o passo a passo de cada item do mod:
onde fabricar, o que precisa e as linhas de produção completas.</p>%s</section>
<section class="card how"><h2>Como funciona</h2><ol>
<li><b>Energia mecânica:</b> uma fonte (manivela, roda d'água, motor) gira um eixo; eixos, caixas de engrenagem e
embreagens levam o torque até as máquinas.</li>
<li><b>Fluidos:</b> canos levam água, vapor, óleo, gasolina e lubrificante entre bombas, caixas e motores.</li>
<li><b>Esteiras:</b> levam itens entre baús e máquinas; o Funil tira itens dos baús e das máquinas.</li>
<li><b>Receita fixa:</b> segure E numa máquina, escolha a produção, e ela fabrica sozinha com o que chega.</li>
</ol></section>
<section id="linhas"><h2>Linhas de produção (modo Create)</h2>
<p class="muted">Itens avançados passam por várias máquinas: fundir, moldar, prensar, misturar, montar.</p>
<div class="grid">%s</div></section>
<section id="itens"><h2>Itens e blocos do mod</h2><input class="filter" placeholder="Buscar item..." data-target="#itens">
%s</section>
<section id="maquinas"><h2>Máquinas</h2><div class="grid">%s</div></section>
""" % (img, "".join(chain_cards), "".join(item_html), machine_tiles), 0)
    (SITE / "index.html").write_text(index, encoding="utf-8")
    (SITE / "style.css").write_text(CSS, encoding="utf-8")
    (SITE / "app.js").write_text(JS, encoding="utf-8")
    (SITE / "vercel.json").write_text('{\n  "cleanUrls": true,\n  "trailingSlash": false\n}\n', encoding="utf-8")
    print("site: %d itens, %d maquinas, %d linhas -> %s" % (len(mod_things), len(areas), len(chains),
                                                         SITE.relative_to(fe.REPO)))
    return 0


CSS = """:root{--bg:#16191a;--panel:#20262a;--line:#33403f;--paint:#6f8f7a;--orange:#f08a24;--text:#e8e4dc;
--muted:#9aa5a0;--link:#ffb067}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--link);text-decoration:none}a:hover{text-decoration:underline}
.top{position:sticky;top:0;z-index:5;display:flex;justify-content:space-between;align-items:center;gap:1rem;
padding:.7rem 1.4rem;background:#111415ee;border-bottom:3px solid var(--orange)}
.brand{font-weight:800;color:var(--text);font-size:1.1rem}.gear{color:var(--orange)}
nav a{margin-left:1.1rem;color:var(--muted)}nav a:hover{color:var(--text)}
main{max-width:1080px;margin:0 auto;padding:1.5rem 1.2rem 3rem}
h1{font-size:2rem;margin:.4rem 0}h2{color:var(--orange);margin-top:2.2rem}h3{color:var(--paint);margin:1.6rem 0 .6rem}
.lead{font-size:1.08rem;color:#cfd6d1;max-width:72ch}.muted,.hint{color:var(--muted)}
.hero{padding:1rem 0}.hero-img{width:100%;border-radius:10px;border:1px solid var(--line);margin-top:1rem}
.card{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--paint);border-radius:8px;
padding:.4rem 1.2rem 1rem;margin:1.2rem 0}.card h2{margin-top:.8rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:.7rem}
.tile{display:flex;flex-direction:column;gap:.2rem;background:var(--panel);border:1px solid var(--line);
border-radius:8px;padding:.8rem 1rem;color:var(--text)}.tile:hover{border-color:var(--orange);text-decoration:none}
.tile span{color:var(--muted);font-size:.85rem}.tile.line{border-left:4px solid var(--orange)}
.badge{display:inline-block;font-size:.75rem;font-weight:700;padding:.1rem .5rem;border-radius:99px;
vertical-align:middle}.badge.ok{background:#2f5d3a;color:#c9f3d2}.badge.wip{background:#5a3b12;color:#ffd29a}
.steps li,.tree li{margin:.25rem 0}.qty{display:inline-block;min-width:2.6rem;color:var(--orange);font-weight:700}
.vanilla{color:#d9d2c3;border-bottom:1px dotted #777}
.tree{list-style:none;padding-left:1.1rem;border-left:2px solid var(--line);margin:.3rem 0}
.sub{font-size:.85rem;color:var(--muted);margin-left:2.6rem}
.chips a{display:inline-block;background:#2a3236;border-radius:99px;padding:.15rem .7rem;margin:.15rem}
.btn{display:inline-block;background:var(--orange);color:#1b1206;font-weight:700;padding:.45rem 1rem;
border-radius:6px}.btn:hover{text-decoration:none;filter:brightness(1.1)}
.list{width:100%;border-collapse:collapse;margin-top:.8rem}.list th,.list td{text-align:left;padding:.45rem .5rem;
border-bottom:1px solid var(--line);vertical-align:top}.list th{color:var(--muted);font-weight:600}
.filter{width:100%;max-width:420px;padding:.55rem .8rem;border-radius:6px;border:1px solid var(--line);
background:#101314;color:var(--text);margin:.4rem 0 .6rem}
.flow{list-style:none;padding:0;counter-reset:s}.step{display:flex;gap:1rem;background:var(--panel);
border:1px solid var(--line);border-radius:8px;padding:.9rem 1rem;margin:.7rem 0;position:relative}
.step+.step:before{content:"";position:absolute;left:2.05rem;top:-.75rem;height:.75rem;border-left:3px solid var(--orange)}
.num{flex:0 0 2.2rem;height:2.2rem;border-radius:50%;background:var(--orange);color:#1b1206;font-weight:800;
display:flex;align-items:center;justify-content:center}.kind{color:var(--paint);font-weight:700;
text-transform:uppercase;font-size:.78rem;letter-spacing:.05em}.io{margin:.35rem 0;font-family:ui-monospace,Consolas,monospace;
font-size:.9rem;display:flex;flex-wrap:wrap;gap:.5rem;align-items:center}.io span{background:#111516;padding:.15rem .5rem;
border-radius:4px}.io .arrow{background:none;color:var(--orange)}.what p{margin:.2rem 0 0;color:#cfd6d1}
.crumb{color:var(--muted);font-size:.9rem;margin:0}
footer{text-align:center;color:var(--muted);font-size:.85rem;padding:2rem 1rem;border-top:1px solid var(--line)}
@media (max-width:600px){nav a{margin-left:.6rem}h1{font-size:1.6rem}}
"""

JS = """document.querySelectorAll('.filter').forEach(function (inp) {
  inp.addEventListener('input', function () {
    var q = inp.value.trim().toLowerCase();
    var scope = document.querySelector(inp.dataset.target);
    if (!scope) return;
    scope.querySelectorAll('.tile, tbody tr').forEach(function (el) {
      var t = (el.dataset.name || el.textContent).toLowerCase();
      el.style.display = !q || t.indexOf(q) >= 0 ? '' : 'none';
    });
    scope.querySelectorAll('h3').forEach(function (h) {
      var g = h.nextElementSibling;
      if (!g) return;
      var any = Array.prototype.some.call(g.children, function (c) { return c.style.display !== 'none'; });
      h.style.display = any ? '' : 'none';
      g.style.display = any ? '' : 'none';
    });
  });
});
"""

if __name__ == "__main__":
    sys.exit(main())
