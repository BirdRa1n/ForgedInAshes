import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useData, bestRoutes, plan, machineName, itemName, fluidName, KIND_VERB, fmtQty } from "./data";
import { Icon, Chip, ItemCard, Bars, Stat } from "./components";
import { GUIDES } from "./guides";

const Model3D = lazy(() => import("./Model3D"));

function Viewer({ model, height }) {
  return (
    <div className="stage" style={height ? { height } : undefined}>
      <Suspense fallback={<div className="center" style={{ minHeight: "100%" }}><div className="spinner" /></div>}>
        <Model3D key={model} name={model} />
      </Suspense>
      {!height && <span className="hint3d">arraste para girar · role para aproximar</span>}
    </div>
  );
}

function useTitle(t) {
  useEffect(() => {
    document.title = (t ? t + " · " : "") + "ForgedInAshes";
  }, [t]);
}

// ================================================================= home
export function Home() {
  const db = useData();
  useTitle("");
  const showcase = useMemo(
    () => ["feSteamTurbine", "feM_Foundry", "feSteamEngine", "feMechDrill", "feConveyor", "feWindmill", "feBoilerDrum", "feCondenser"]
      .map((m) => db.list.find((it) => it.model === m))
      .filter(Boolean),
    [db]
  );
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((x) => (x + 1) % showcase.length), 9000);
    return () => clearInterval(t);
  }, [showcase.length]);
  const cur = showcase[i];
  const s = db.stats;
  return (
    <div className="fade-in">
      <section className="hero">
        <div>
          <div className="eyebrow">mod para 7 Days to Die</div>
          <h1 style={{ marginTop: 10 }}>
            Ferro &amp; <span>Engrenagem</span>
          </h1>
          <p className="lead">
            Indústria de verdade no apocalipse: eixos, esteiras, canos, caldeiras e linhas de produção no estilo Create. Cada item do
            jogo passa por máquinas que você monta, liga e automatiza.
          </p>
          <div className="actions">
            <Link className="btn" to="/linhas">Ver linhas de produção</Link>
            <Link className="btn ghost" to="/guias/primeiros-passos">Primeiros passos</Link>
          </div>
          <div className="chips" style={{ marginTop: 26 }}>
            <span className="pill brass">{s.blocks} blocos</span>
            <span className="pill">{s.items} peças e materiais</span>
            <span className="pill">{s.processes} processos</span>
            <span className="pill">{s.models} modelos 3D</span>
          </div>
        </div>
        {cur && (
          <div>
            <Viewer model={cur.model} />
            <div className="stage-cap" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
              <Link to={`/item/${cur.id}`} className="chip"><Icon id={cur.id} size={26} /><b>{cur.name}</b></Link>
              <div className="stage dots" style={{ height: "auto", border: 0, background: "none", display: "flex", gap: 6 }}>
                {showcase.map((m, k) => (
                  <button key={m.id} className={k === i ? "on" : ""} onClick={() => setI(k)} aria-label={m.name}
                          style={{ width: k === i ? 22 : 9, height: 9, borderRadius: 6, border: 0, cursor: "pointer", background: k === i ? "var(--brass)" : "var(--line2)" }} />
                ))}
              </div>
            </div>
          </div>
        )}
      </section>

      <section className="section">
        <div className="section-head">
          <div><div className="eyebrow">indicadores</div><h2>O mod em números</h2></div>
          <Link className="btn ghost" to="/indicadores">Todos os indicadores</Link>
        </div>
        <div className="stats">
          <Stat v={`${s.coverage[0]}/${s.coverage[1]}`} l="itens do jogo fabricáveis pelo mod" s="cobertura completa" />
          <Stat v={s.machines} l="máquinas e bancadas" />
          <Stat v={s.processes} l="processos de cadeia" />
          <Stat v={s.recipes} l="receitas" />
          <Stat v={s.fluids} l="fluidos e gases" />
          <Stat v={s.models} l="modelos 3D" />
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <div><div className="eyebrow">tutoriais automáticos</div><h2>Linhas de produção</h2></div>
          <Link className="btn ghost" to="/linhas">Todas</Link>
        </div>
        <div className="grid g3">
          {db.featured.slice(0, 6).map((f) => <LineCard key={f.id} f={f} />)}
        </div>
      </section>

      <section className="section">
        <div className="section-head"><div><div className="eyebrow">conceitos</div><h2>Guias</h2></div></div>
        <div className="grid g3">
          {GUIDES.map((g) => (
            <Link key={g.id} className="lines-card" to={`/guias/${g.id}`}>
              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                <Icon id={g.icon} size={44} />
                <div><h3>{g.title}</h3><div className="muted" style={{ fontSize: 13 }}>{g.sub}</div></div>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

function LineCard({ f }) {
  const db = useData();
  const p = useMemo(() => plan(db, f.id, 1), [db, f.id]);
  return (
    <Link className="lines-card fade-in" to={`/linha/${f.id}`}>
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <Icon id={f.id} size={48} />
        <div><h3>{f.title}</h3><div className="muted" style={{ fontSize: 13 }}>{itemName(db, f.id)}</div></div>
      </div>
      <p style={{ color: "var(--ink2)", fontSize: 14 }}>{f.text}</p>
      <div className="meta">
        <span className="pill brass">{p.steps.length} etapas</span>
        <span className="pill">{p.machines.length} máquinas</span>
        <span className="pill">{p.raw.length + p.rawFluids.length} matérias-primas</span>
      </div>
    </Link>
  );
}

// ================================================================= catalog
const CAT_ORDER = ["Energia", "Usina termelétrica", "Transmissão", "Fluidos", "Logística", "Processamento", "Estações em linha",
  "Bancadas", "Máquinas no mundo", "Sinais", "Peças e materiais", "Moldes", "Outros"];

export function Catalog({ machinesOnly }) {
  const db = useData();
  const [params, setParams] = useSearchParams();
  const cat = params.get("cat") || "";
  const [q, setQ] = useState("");
  useTitle(machinesOnly ? "Máquinas" : "Catálogo");
  const all = useMemo(() => db.list.filter((it) => it.mod && (!machinesOnly || it.block)), [db, machinesOnly]);
  const cats = useMemo(() => {
    const c = {};
    for (const it of all) c[it.cat] = (c[it.cat] || 0) + 1;
    return CAT_ORDER.filter((k) => c[k]).map((k) => [k, c[k]]);
  }, [all]);
  const qq = q.trim().toLowerCase();
  const shown = all
    .filter((it) => (!cat || it.cat === cat) && (!qq || it.name.toLowerCase().includes(qq) || it.id.toLowerCase().includes(qq)))
    .sort((a, b) => (b.model ? 1 : 0) - (a.model ? 1 : 0) || a.name.localeCompare(b.name, "pt"));
  return (
    <div className="fade-in">
      <div className="eyebrow">{machinesOnly ? "blocos do mod" : "tudo do mod"}</div>
      <h1 style={{ margin: "8px 0 20px" }}>{machinesOnly ? "Máquinas e blocos" : "Catálogo"}</h1>
      <input className="input" placeholder="Filtrar por nome…" value={q} onChange={(e) => setQ(e.target.value)} style={{ marginBottom: 14 }} />
      <div className="filters">
        <button className={!cat ? "on" : ""} onClick={() => setParams({})}>Tudo<span className="count">{all.length}</span></button>
        {cats.map(([c, n]) => (
          <button key={c} className={cat === c ? "on" : ""} onClick={() => setParams({ cat: c })}>{c}<span className="count">{n}</span></button>
        ))}
      </div>
      <div className="grid g4">{shown.map((it) => <ItemCard key={it.id} id={it.id} />)}</div>
      {!shown.length && <p className="muted">Nada encontrado.</p>}
    </div>
  );
}

// ================================================================= item page
function RouteCard({ r }) {
  const db = useData();
  const p = r.data;
  return (
    <div className="route">
      <div className="rh">
        {r.machine ? <Chip id={r.machine} size={22} /> : <span className="pill">Inventário</span>}
        {r.type === "process" && <span className="pill brass">{db.kinds[p.kind] || p.kind}</span>}
        {r.t ? <span className="pill">⏱ {fmtQty(r.t)} s</span> : null}
        {p.torque ? <span className="pill">⚙ {p.torque} UT</span> : null}
        {p.bar ? <span className="pill fluid">{p.bar} bar</span> : null}
        {p.heat ? <span className="pill molten">calor</span> : null}
        {r.byproduct && <span className="pill">subproduto</span>}
      </div>
      <div className="flow">
        <div className="chips">
          {r.ing.map(([i, n]) => <Chip key={i} id={i} qty={n} />)}
          {r.fin.map(([f, l]) => <Chip key={f} id={f} qty={l} fluid />)}
          {p.mold && <Chip id={p.mold} />}
        </div>
        <span className="arrow">→</span>
        <div className="chips">
          {r.out && !r.byproduct && <Chip id={r.out[0]} qty={r.out[1]} />}
          {(r.fout || []).map(([f, l]) => <Chip key={f} id={f} qty={l} fluid />)}
          {p.extra && <Chip id={p.extra[0]} qty={p.extra[1]} />}
        </div>
      </div>
      {p.text && <p className="muted" style={{ fontSize: 13, marginTop: 10 }}>{p.text}</p>}
    </div>
  );
}

function TreeNode({ n, depth }) {
  const db = useData();
  const [open, setOpen] = useState(depth < 2);
  const has = n.children && n.children.length > 0;
  return (
    <li>
      <div className="tnode">
        {has ? <button className="tog" onClick={() => setOpen(!open)}>{open ? "−" : "+"}</button> : <span style={{ width: 22 }} />}
        <Chip id={n.id} qty={n.qty} fluid={n.fluid} />
        {n.route && (
          <span className="by">em <b>{machineName(db, n.route.machine)}</b>{n.crafts > 1 ? ` · ${n.crafts}×` : ""}</span>
        )}
        {n.raw && <span className="pill">matéria-prima</span>}
        {n.tool && <span className="pill">molde (não gasta)</span>}
      </div>
      {has && open && (
        <ul className="tree">{n.children.map((c, k) => <TreeNode key={k} n={c} depth={depth + 1} />)}</ul>
      )}
    </li>
  );
}

export function PlanView({ id, qty = 1, compact }) {
  const db = useData();
  const p = useMemo(() => plan(db, id, qty), [db, id, qty]);
  const [tab, setTab] = useState("steps");
  if (!p.steps.length) return <p className="muted">Não é fabricado: vem do mundo (loot, mineração, colheita ou comerciante).</p>;
  return (
    <div>
      <div className="tabs">
        <button className={tab === "steps" ? "on" : ""} onClick={() => setTab("steps")}>Passo a passo ({p.steps.length})</button>
        <button className={tab === "tree" ? "on" : ""} onClick={() => setTab("tree")}>Árvore</button>
        <button className={tab === "need" ? "on" : ""} onClick={() => setTab("need")}>Máquinas e matéria-prima</button>
      </div>
      {tab === "steps" && (
        <div className="steps">
          {p.steps.map(({ key, route, crafts }) => (
            <div className="step" key={key}>
              <div>
                <div className="sh">
                  <span>{route.type === "process" ? KIND_VERB[route.data.kind] || "Faça" : "Fabrique"} em</span>
                  {route.machine ? <Chip id={route.machine} size={22} /> : <span className="pill">Inventário (na mão)</span>}
                  {crafts > 1 && <span className="pill">{crafts}×</span>}
                  {route.t ? <span className="pill">⏱ {fmtQty(route.t * crafts)} s</span> : null}
                  {route.data.torque ? <span className="pill">⚙ {route.data.torque} UT</span> : null}
                  {route.data.heat ? <span className="pill molten">calor</span> : null}
                  {route.data.bar ? <span className="pill fluid">{route.data.bar} bar</span> : null}
                </div>
                <div className="flow" style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  <div className="chips">
                    {route.ing.map(([i, n]) => <Chip key={i} id={i} qty={n * crafts} />)}
                    {route.fin.map(([f, l]) => <Chip key={f} id={f} qty={l * crafts} fluid />)}
                    {route.data.mold && <Chip id={route.data.mold} />}
                  </div>
                  <span className="arrow">→</span>
                  <div className="chips">
                    {route.out && <Chip id={route.out[0]} qty={route.out[1] * crafts} />}
                    {(route.fout || []).map(([f, l]) => <Chip key={f} id={f} qty={l * crafts} fluid />)}
                  </div>
                </div>
                {route.data.text && !compact && <div className="txt">{route.data.text}</div>}
              </div>
            </div>
          ))}
        </div>
      )}
      {tab === "tree" && <ul className="tree"><TreeNode n={p.tree} depth={0} /></ul>}
      {tab === "need" && (
        <div className="grid g2">
          <div className="card">
            <h3 style={{ marginBottom: 12 }}>Máquinas ({p.machines.length})</h3>
            <div className="chips">{p.machines.map((m) => (m ? <Chip key={m} id={m} /> : <span key="inv" className="pill">Inventário</span>))}</div>
          </div>
          <div className="card">
            <h3 style={{ marginBottom: 12 }}>Matéria-prima</h3>
            <div className="chips">
              {p.raw.map(([i, n]) => <Chip key={i} id={i} qty={n} />)}
              {p.rawFluids.map(([f, l]) => <Chip key={f} id={f} qty={l} fluid />)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function ItemPage() {
  const { id } = useParams();
  const db = useData();
  const it = db.items[id];
  useTitle(it ? it.name : id);
  const [tab, setTab] = useState("how");
  useEffect(() => { setTab("how"); window.scrollTo(0, 0); }, [id]);
  if (!it) return <p>Item não encontrado: {id}</p>;
  const routes = bestRoutes(db, id);
  const makes = db.byMachine[id] || [];
  const used = [...(db.usedIn[id] || [])].filter((x) => db.items[x]);
  const e = it.energy;
  return (
    <div className="fade-in">
      <div className="crumb"><Link to="/catalogo">Catálogo</Link> / <Link to={`/catalogo?cat=${encodeURIComponent(it.cat)}`}>{it.cat}</Link> / {it.name}</div>
      <div className="ipage">
        <div className="viewer">
          {it.model ? <Viewer model={it.model} /> : <div className="bigicon"><Icon id={id} size={180} /></div>}
          <div className="chips" style={{ marginTop: 12 }}>
            {e.torqueOut ? <span className="pill brass">⚡ gera {e.torqueOut} UT{e.rpm ? ` a ${e.rpm} RPM` : ""}</span> : null}
            {e.torqueCost ? <span className="pill">⚙ consome {e.torqueCost} UT</span> : null}
            {e.watts ? <span className="pill">🔌 {e.watts} W</span> : null}
            {e.minWatts ? <span className="pill">🔌 {e.minWatts} W de motor</span> : null}
            {e.capacity ? <span className="pill fluid">{fmtQty(e.capacity)} L</span> : null}
            {e.maxBar ? <span className="pill fluid">até {e.maxBar} bar</span> : null}
            {e.outBar ? <span className="pill fluid">sai a {e.outBar} bar</span> : null}
            {e.range ? <span className="pill">alcance {e.range}</span> : null}
          </div>
        </div>
        <div>
          <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
            <Icon id={id} size={56} />
            <div>
              <div className="eyebrow">{it.cat}</div>
              <h1 style={{ fontSize: 32 }}>{it.name}</h1>
            </div>
          </div>
          {it.desc && <p className="lead" style={{ marginTop: 14, whiteSpace: "pre-line" }}>{it.desc}</p>}
          {it.how.length > 0 && (
            <div className="card" style={{ marginTop: 18 }}>
              <h3 style={{ marginBottom: 8 }}>Como ligar</h3>
              <ul className="how">{it.how.map((h, k) => <li key={k}>{h}</li>)}</ul>
            </div>
          )}
          <div className="tabs" style={{ marginTop: 24 }}>
            <button className={tab === "how" ? "on" : ""} onClick={() => setTab("how")}>Como fazer ({routes.length})</button>
            <button className={tab === "line" ? "on" : ""} onClick={() => setTab("line")}>Linha completa</button>
            {makes.length > 0 && <button className={tab === "makes" ? "on" : ""} onClick={() => setTab("makes")}>O que faz ({makes.length})</button>}
            {used.length > 0 && <button className={tab === "used" ? "on" : ""} onClick={() => setTab("used")}>Usado em ({used.length})</button>}
          </div>
          {tab === "how" && (routes.length ? routes.map((r, k) => <RouteCard key={k} r={r} />)
            : <p className="muted">Não é fabricado: vem do mundo (loot, mineração, colheita ou comerciante).</p>)}
          {tab === "line" && <PlanView id={id} />}
          {tab === "makes" && <div>{makes.slice(0, 120).map((r, k) => <RouteCard key={k} r={r} />)}</div>}
          {tab === "used" && <div className="grid g3">{used.slice(0, 120).map((u) => <ItemCard key={u} id={u} />)}</div>}
        </div>
      </div>
    </div>
  );
}

// ================================================================= lines
export function Lines() {
  const db = useData();
  useTitle("Linhas de produção");
  const [q, setQ] = useState("");
  const qq = q.trim().toLowerCase();
  const any = qq ? db.list.filter((it) => (db.routes[it.id] || []).length && it.name.toLowerCase().includes(qq)).slice(0, 24) : [];
  return (
    <div className="fade-in">
      <div className="eyebrow">tutoriais gerados dos dados do mod</div>
      <h1 style={{ margin: "8px 0 10px" }}>Linhas de produção</h1>
      <p className="lead" style={{ marginBottom: 22 }}>Qualquer item vira um tutorial: a árvore até as matérias-primas, as máquinas e o passo a passo na ordem certa. Escolha um destaque ou procure qualquer item.</p>
      <input className="input" placeholder="Montar a linha de… (ex.: pólvora, pneu, motor)" value={q} onChange={(e) => setQ(e.target.value)} />
      {any.length > 0 && (
        <div className="grid g4" style={{ marginTop: 14 }}>
          {any.map((it) => (
            <Link key={it.id} className="icard" to={`/linha/${it.id}`}>
              <div className="top-row"><Icon id={it.id} size={40} /><div className="nm">{it.name}</div></div>
            </Link>
          ))}
        </div>
      )}
      <div className="grid g3" style={{ marginTop: 26 }}>{db.featured.map((f) => <LineCard key={f.id} f={f} />)}</div>
    </div>
  );
}

export function LinePage() {
  const { id } = useParams();
  const db = useData();
  const [qty, setQty] = useState(1);
  const f = db.featured.find((x) => x.id === id);
  const it = db.items[id];
  useTitle("Linha: " + (it ? it.name : id));
  if (!it) return <p>Item não encontrado: {id}</p>;
  const machines = plan(db, id, qty).machines.filter((m) => db.items[m] && db.items[m].model).slice(0, 4);
  return (
    <div className="fade-in">
      <div className="crumb"><Link to="/linhas">Linhas</Link> / {it.name}</div>
      <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
        <Icon id={id} size={64} />
        <div style={{ flex: 1 }}>
          <div className="eyebrow">linha de produção</div>
          <h1 style={{ fontSize: 34 }}>{f ? f.title : it.name}</h1>
          {f && <p className="lead" style={{ marginTop: 6 }}>{f.text}</p>}
        </div>
        <label className="pill" style={{ gap: 10 }}>Quantidade
          <input type="number" min="1" max="999" value={qty} onChange={(e) => setQty(Math.max(1, Math.min(999, +e.target.value || 1)))}
                 style={{ width: 70, background: "transparent", border: 0, color: "var(--ink)", font: "inherit" }} />
        </label>
        <Link className="btn ghost" to={`/item/${id}`}>Ver item</Link>
      </div>
      {machines.length > 0 && (
        <div className="grid g4" style={{ marginTop: 22 }}>
          {machines.map((m) => (
            <Link key={m} to={`/item/${m}`} className="card" style={{ padding: 0, overflow: "hidden" }}>
              <div style={{ height: 180 }}><Viewer model={db.items[m].model} height={180} /></div>
              <div style={{ padding: "10px 14px", fontWeight: 650 }}>{db.items[m].name}</div>
            </Link>
          ))}
        </div>
      )}
      <div style={{ marginTop: 26 }}><PlanView id={id} qty={qty} /></div>
    </div>
  );
}

// ================================================================= guides
function Rich({ text }) {
  const parts = [];
  const re = /\[\[(\w+)(?:\|(\d+))?\]\]/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    parts.push(<Chip key={m.index} id={m[1]} qty={m[2] ? +m[2] : undefined} size={22} />);
    last = re.lastIndex;
  }
  if (last < text.length) parts.push(text.slice(last));
  return <>{parts}</>;
}

export function Guides() {
  useTitle("Guias");
  return (
    <div className="fade-in">
      <div className="eyebrow">conceitos</div>
      <h1 style={{ margin: "8px 0 22px" }}>Guias</h1>
      <div className="grid g2">
        {GUIDES.map((g) => (
          <Link key={g.id} className="lines-card" to={`/guias/${g.id}`}>
            <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
              <Icon id={g.icon} size={52} />
              <div><h2 style={{ fontSize: 19 }}>{g.title}</h2><div className="muted">{g.sub}</div></div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function GuidePage() {
  const { id } = useParams();
  const db = useData();
  const g = GUIDES.find((x) => x.id === id);
  useTitle(g ? g.title : "Guia");
  if (!g) return <p>Guia não encontrado.</p>;
  const model = g.model && db.list.find((it) => it.model === g.model);
  return (
    <div className="fade-in">
      <div className="crumb"><Link to="/guias">Guias</Link> / {g.title}</div>
      <div className={model ? "ipage" : ""}>
        {model && <div className="viewer"><Viewer model={model.model} /></div>}
        <div className="prose">
          <div className="eyebrow">guia</div>
          <h1 style={{ margin: "6px 0 4px", color: "var(--ink)" }}>{g.title}</h1>
          <p className="muted">{g.sub}</p>
          {g.blocks.map((b, k) => {
            if (b.h) return <h2 key={k}>{b.h}</h2>;
            if (b.p) return <p key={k}><Rich text={b.p} /></p>;
            if (b.note) return <div key={k} className="callout"><Rich text={b.note} /></div>;
            if (b.ul) return <ul key={k}>{b.ul.map((x, j) => <li key={j}><Rich text={x} /></li>)}</ul>;
            if (b.ol) return <ol key={k}>{b.ol.map((x, j) => <li key={j}><Rich text={x} /></li>)}</ol>;
            if (b.line) return <div key={k} className="card" style={{ margin: "18px 0" }}><h3 style={{ marginBottom: 12 }}>Linha: {itemName(db, b.line)}</h3><PlanView id={b.line} compact /></div>;
            return null;
          })}
        </div>
      </div>
    </div>
  );
}

// ================================================================= indicators
export function Stats() {
  const db = useData();
  useTitle("Indicadores");
  const s = db.stats;
  const nm = (m) => machineName(db, m);
  return (
    <div className="fade-in">
      <div className="eyebrow">gerado dos arquivos do mod · {db.generated}</div>
      <h1 style={{ margin: "8px 0 22px" }}>Indicadores</h1>
      <div className="stats">
        <Stat v={`${Math.round((100 * s.coverage[0]) / s.coverage[1])}%`} l={`cobertura: ${s.coverage[0]} de ${s.coverage[1]} itens do jogo`} s="todos fabricáveis pelo mod" />
        <Stat v={s.blocks} l="blocos do mod" />
        <Stat v={s.items} l="peças, materiais e moldes" />
        <Stat v={s.machines} l="máquinas e bancadas" />
        <Stat v={s.processes} l="processos de cadeia" />
        <Stat v={s.recipes} l="receitas no total" />
        <Stat v={s.fluids} l="fluidos e gases" />
        <Stat v={s.models} l="modelos 3D próprios" />
      </div>
      <div className="grid g2" style={{ marginTop: 22 }}>
        <div className="card">
          <h2>Processos por máquina</h2>
          <Bars rows={s.procByMachine.map(([m, n]) => [nm(m), n, `/item/${m}`])} tip={(l, v) => `${l}: ${v} processos`} />
        </div>
        <div className="card">
          <h2>Receitas por bancada</h2>
          <Bars rows={s.recByArea.map(([m, n]) => [nm(m), n, `/item/${m}`])} tip={(l, v) => `${l}: ${v} receitas`} />
        </div>
        <div className="card">
          <h2>Fontes de torque (UT)</h2>
          <Bars rows={s.sources.map(([m, n]) => [nm(m), n, `/item/${m}`])} unit=" UT" tip={(l, v) => `${l}: até ${v} UT`} />
        </div>
        <div className="card">
          <h2>Blocos por categoria</h2>
          <Bars rows={s.blockCats.map(([c, n]) => [c, n, `/catalogo?cat=${encodeURIComponent(c)}`])} tip={(l, v) => `${l}: ${v} blocos`} />
        </div>
        <div className="card">
          <h2>Processos por tipo</h2>
          <Bars rows={s.kinds.map(([k, n]) => [db.kinds[k] || k, n])} tip={(l, v) => `${l}: ${v} processos`} />
        </div>
      </div>
    </div>
  );
}
